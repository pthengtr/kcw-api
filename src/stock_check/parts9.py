from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import log1p
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.stock_check.config import StockCheckSettings, get_stock_check_settings


@dataclass
class ProductRow:
    bcode: str
    descr: str
    pcode: str
    mcode: str
    location1: str
    location2: str
    qtyoh2: float
    ui1: str
    mtp2: float
    canceled: str

    def as_dict(self) -> dict[str, Any]:
        return {
            "bcode": self.bcode,
            "descr": self.descr,
            "pcode": self.pcode,
            "mcode": self.mcode,
            "location1": self.location1,
            "location2": self.location2,
            "qtyoh2": self.qtyoh2,
            "ui1": self.ui1,
            "mtp2": self.mtp2,
            "canceled": self.canceled,
        }


def _odbc_url(settings: StockCheckSettings, *, writer: bool = False) -> str:
    user = settings.pos_mssql_username
    password = settings.pos_mssql_password
    if writer and settings.pos_mssql_writer_username:
        user = settings.pos_mssql_writer_username
        password = settings.pos_mssql_writer_password
    odbc = (
        f"DRIVER={{{settings.pos_mssql_driver}}};"
        f"SERVER={settings.pos_mssql_server};"
        f"DATABASE={settings.pos_mssql_database};"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc)


@lru_cache(maxsize=2)
def get_parts9_engine(*, writer: bool = False) -> Engine:
    settings = get_stock_check_settings()
    return create_engine(_odbc_url(settings, writer=writer), pool_pre_ping=True)


def clear_parts9_engine_cache() -> None:
    get_parts9_engine.cache_clear()


def _parse_qty(value: Any) -> float:
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text_value = str(value).strip().replace(",", "")
    if not text_value:
        return 0.0
    try:
        return float(text_value)
    except ValueError:
        return 0.0


def _row_to_product(row: Any) -> ProductRow:
    return ProductRow(
        bcode=str(row["BCODE"] or "").strip(),
        descr=str(row["DESCR"] or "").strip(),
        pcode=str(row["PCODE"] or "").strip(),
        mcode=str(row["MCODE"] or "").strip(),
        location1=str(row["LOCATION1"] or "").strip(),
        location2=str(row["LOCATION2"] or "").strip(),
        qtyoh2=_parse_qty(row["QTYOH2"]),
        ui1=str(row["UI1"] or "").strip(),
        mtp2=_parse_qty(row["MTP2"]) or 1.0,
        canceled=str(row["CANCELED"] or "N").strip().upper() or "N",
    )


_PRODUCT_SELECT = """
SELECT
  BCODE, DESCR, PCODE, MCODE, LOCATION1, LOCATION2, QTYOH2, UI1, MTP2, CANCELED
FROM dbo.ICMAS
"""


def get_product_by_bcode(bcode: str, engine: Engine | None = None) -> ProductRow | None:
    code = (bcode or "").strip()
    if not code:
        return None
    eng = engine or get_parts9_engine(writer=False)
    sql = text(_PRODUCT_SELECT + " WHERE LTRIM(RTRIM(BCODE)) = :bcode")
    with eng.connect() as conn:
        row = conn.execute(sql, {"bcode": code}).mappings().first()
    if not row:
        return None
    return _row_to_product(row)


def lookup_products(query: str, *, limit: int = 20, engine: Engine | None = None) -> list[ProductRow]:
    q = (query or "").strip()
    if not q:
        return []
    eng = engine or get_parts9_engine(writer=False)
    # Exact bcode first
    exact = get_product_by_bcode(q, engine=eng)
    if exact:
        return [exact]
    sql = text(
        _PRODUCT_SELECT
        + """
        WHERE UPPER(LTRIM(RTRIM(COALESCE(CANCELED,'')))) <> 'Y'
          AND (
            LTRIM(RTRIM(BCODE)) = :q
            OR LTRIM(RTRIM(PCODE)) = :q
            OR LTRIM(RTRIM(MCODE)) = :q
            OR PCODE LIKE :like
            OR MCODE LIKE :like
            OR DESCR LIKE :like
          )
        ORDER BY BCODE
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(
            sql,
            {"q": q, "like": f"%{q}%"},
        ).mappings().fetchmany(limit)
    return [_row_to_product(r) for r in rows]


def list_candidate_products(
    *,
    exclude_bcodes: set[str],
    with_stock_only: bool = True,
    limit_scan: int = 5000,
    engine: Engine | None = None,
) -> list[ProductRow]:
    eng = engine or get_parts9_engine(writer=False)
    limit = max(1, min(int(limit_scan), 20000))
    sql = text(
        f"""
        SELECT TOP {limit}
          BCODE, DESCR, PCODE, MCODE, LOCATION1, LOCATION2, QTYOH2, UI1, MTP2, CANCELED
        FROM dbo.ICMAS
        WHERE UPPER(LTRIM(RTRIM(COALESCE(CANCELED,'')))) <> 'Y'
        ORDER BY LOCATION1, BCODE
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(sql).mappings().fetchall()
    out: list[ProductRow] = []
    for row in rows:
        product = _row_to_product(row)
        if not product.bcode or product.bcode in exclude_bcodes:
            continue
        if with_stock_only and product.qtyoh2 <= 0:
            continue
        out.append(product)
    return out


def score_product(
    product: ProductRow,
    *,
    last_audited_at: float | None,
    now: float,
) -> float:
    """Higher = pick sooner. Local-only scoring (no cloud sales in v1)."""
    score = 0.0
    if last_audited_at is None:
        score += 500.0
    else:
        days = max(0.0, (now - last_audited_at) / 86400.0)
        score += min(400.0, days * 1.5)
    score += min(60.0, log1p(max(0.0, product.qtyoh2)) * 8.0)
    # Soft prefer items that have a location filled
    if product.location1:
        score += 5.0
    return score


def pick_top_products(
    products: list[ProductRow],
    *,
    audits: dict[str, dict],
    count: int,
    now: float,
) -> list[ProductRow]:
    ranked: list[tuple[float, str, ProductRow]] = []
    for product in products:
        audit = audits.get(product.bcode)
        last_at = float(audit["last_audited_at"]) if audit else None
        score = score_product(product, last_audited_at=last_at, now=now)
        loc = product.location1 or ""
        ranked.append((score, loc, product))
    # High score first; within similar scores, cluster by location
    ranked.sort(key=lambda item: (-item[0], item[1], item[2].bcode))
    # Soft location clustering: take top score then prefer same location block
    if not ranked:
        return []
    chosen: list[ProductRow] = []
    used: set[str] = set()
    # First pass: greedily by score but boost continuity of location
    current_loc = ranked[0][1]
    while len(chosen) < count and len(used) < len(ranked):
        best_idx = None
        best_key = None
        for idx, (score, loc, product) in enumerate(ranked):
            if product.bcode in used:
                continue
            # Prefer same location lightly
            adj = score + (25.0 if loc and loc == current_loc else 0.0)
            key = (adj, loc == current_loc, -idx)
            if best_key is None or key > best_key:
                best_key = key
                best_idx = idx
        if best_idx is None:
            break
        _score, loc, product = ranked[best_idx]
        chosen.append(product)
        used.add(product.bcode)
        if loc:
            current_loc = loc
    return chosen

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.db.mssql_host import pick_mssql_server
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
    # Legacy PARTS9: QTYMIN < 0 (usually -1) = do not restock / skip ICLOW.
    qtymin: float = 0.0
    model: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "bcode": self.bcode,
            "descr": self.descr,
            "pcode": self.pcode,
            "mcode": self.mcode,
            "model": self.model,
            "location1": self.location1,
            "location2": self.location2,
            "qtyoh2": self.qtyoh2,
            "ui1": self.ui1,
            "mtp2": self.mtp2,
            "canceled": self.canceled,
            "qtymin": self.qtymin,
        }

    @property
    def do_not_restock(self) -> bool:
        """True when operators marked the SKU off the buy list (QTYMIN < 0)."""
        return self.qtymin < 0


def _odbc_url(settings: StockCheckSettings, *, writer: bool = False) -> str:
    user = settings.pos_mssql_username
    password = settings.pos_mssql_password
    if writer and settings.pos_mssql_writer_username:
        user = settings.pos_mssql_writer_username
        password = settings.pos_mssql_writer_password
    odbc = (
        f"DRIVER={{{settings.pos_mssql_driver}}};"
        f"SERVER={pick_mssql_server(settings.pos_mssql_server)};"
        f"DATABASE={settings.pos_mssql_database};"
        f"UID={user};"
        f"PWD={password};"
        "TrustServerCertificate=yes;"
    )
    return "mssql+pyodbc:///?odbc_connect=" + quote_plus(odbc)


_engines: dict[bool, Engine] = {}


def get_parts9_engine(*, writer: bool = False) -> Engine:
    if writer not in _engines:
        settings = get_stock_check_settings()
        _engines[writer] = create_engine(
            _odbc_url(settings, writer=writer),
            pool_pre_ping=True,
            pool_size=2,
            max_overflow=1,
            pool_timeout=30,
            connect_args={"timeout": 30},
        )
    return _engines[writer]


def clear_parts9_engine_cache() -> None:
    for eng in list(_engines.values()):
        try:
            eng.dispose()
        except Exception:  # noqa: BLE001
            pass
    _engines.clear()


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
        qtymin=_parse_qty(row["QTYMIN"]) if "QTYMIN" in row.keys() else 0.0,
        model=str(row["MODEL"] or "").strip() if "MODEL" in row.keys() else "",
    )


_PRODUCT_SELECT = """
SELECT
  BCODE, DESCR, PCODE, MCODE, MODEL, LOCATION1, LOCATION2, QTYOH2, UI1, MTP2, CANCELED, QTYMIN
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
            OR LTRIM(RTRIM(MODEL)) = :q
            OR PCODE LIKE :like
            OR MCODE LIKE :like
            OR MODEL LIKE :like
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


def get_products_by_bcodes(
    bcodes: set[str] | list[str],
    *,
    engine: Engine | None = None,
    chunk_size: int = 400,
) -> list[ProductRow]:
    codes = sorted({str(b).strip() for b in bcodes if str(b).strip()})
    if not codes:
        return []
    eng = engine or get_parts9_engine(writer=False)
    out: list[ProductRow] = []
    size = max(50, min(int(chunk_size), 800))
    with eng.connect() as conn:
        for i in range(0, len(codes), size):
            chunk = codes[i : i + size]
            placeholders = ", ".join(f":b{j}" for j in range(len(chunk)))
            sql = text(
                _PRODUCT_SELECT
                + f"""
                WHERE UPPER(LTRIM(RTRIM(COALESCE(CANCELED,'')))) <> 'Y'
                  AND LTRIM(RTRIM(BCODE)) IN ({placeholders})
                """
            )
            params = {f"b{j}": code for j, code in enumerate(chunk)}
            rows = conn.execute(sql, params).mappings().fetchall()
            for row in rows:
                product = _row_to_product(row)
                if product.bcode:
                    out.append(product)
    return out


def list_negative_stock_products(
    *,
    exclude_bcodes: set[str] | None = None,
    engine: Engine | None = None,
) -> list[ProductRow]:
    eng = engine or get_parts9_engine(writer=False)
    exclude = exclude_bcodes or set()
    sql = text(
        _PRODUCT_SELECT
        + """
        WHERE UPPER(LTRIM(RTRIM(COALESCE(CANCELED,'')))) <> 'Y'
          AND ISNUMERIC(REPLACE(CONVERT(varchar(50), QTYOH2), ',', '')) = 1
          AND CONVERT(float, REPLACE(CONVERT(varchar(50), QTYOH2), ',', '')) < 0
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(sql).mappings().fetchall()
    out: list[ProductRow] = []
    for row in rows:
        product = _row_to_product(row)
        if product.bcode and product.bcode not in exclude:
            out.append(product)
    return out


def list_never_counted_stock_products(
    *,
    audited_bcodes: set[str],
    exclude_bcodes: set[str],
    limit: int = 200,
    engine: Engine | None = None,
) -> list[ProductRow]:
    eng = engine or get_parts9_engine(writer=False)
    limit = max(1, min(int(limit), 2000))
    sql = text(
        f"""
        SELECT TOP {limit * 3}
          BCODE, DESCR, PCODE, MCODE, MODEL, LOCATION1, LOCATION2, QTYOH2, UI1, MTP2, CANCELED, QTYMIN
        FROM dbo.ICMAS
        WHERE UPPER(LTRIM(RTRIM(COALESCE(CANCELED,'')))) <> 'Y'
          AND ISNUMERIC(REPLACE(CONVERT(varchar(50), QTYOH2), ',', '')) = 1
          AND CONVERT(float, REPLACE(CONVERT(varchar(50), QTYOH2), ',', '')) > 0
          AND (QTYMIN IS NULL OR QTYMIN >= 0)
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
        if product.bcode in audited_bcodes:
            continue
        out.append(product)
        if len(out) >= limit:
            break
    return out


@dataclass(frozen=True)
class StockMovement:
    billno: str
    billdate: datetime
    billtime: str
    billtype: str
    qty_delta: float
    jourtype: str

    @property
    def kind_label(self) -> str:
        jt = (self.jourtype or "").strip().upper()
        if jt in {"SJ", "SA"} or (self.billno or "").upper().startswith(("SA", "3SA")):
            return "ปรับสต็อก"
        bt = (self.billtype or "").strip()
        if bt == "1":
            return "ขาย/ออก"
        if bt == "2":
            return "รับ/เข้า"
        return "เคลื่อนไหว"


def list_stock_movements(
    bcode: str,
    *,
    since: datetime,
    until: datetime | None = None,
    limit: int = 30,
    engine: Engine | None = None,
) -> list[StockMovement]:
    """SIDET lines for one SKU between timestamps (for drift review)."""
    code = (bcode or "").strip()
    if not code:
        return []
    eng = engine or get_parts9_engine(writer=False)
    limit = max(1, min(int(limit), 100))
    sql = text(
        f"""
        SELECT TOP {limit}
          LTRIM(RTRIM(m.BILLNO)) AS billno,
          m.BILLDATE AS billdate,
          LTRIM(RTRIM(COALESCE(m.BILLTIME, ''))) AS billtime,
          LTRIM(RTRIM(COALESCE(m.BILLTYPE, ''))) AS billtype,
          LTRIM(RTRIM(COALESCE(m.JOURTYPE, ''))) AS jourtype,
          d.QTY AS qty_raw
        FROM dbo.SIDET d WITH (NOLOCK)
        INNER JOIN dbo.SIMAS m WITH (NOLOCK)
          ON d.BILLNO = m.BILLNO
         AND d.BILLDATE = m.BILLDATE
         AND d.BILLTYPE = m.BILLTYPE
         AND d.JOURMODE = m.JOURMODE
        WHERE LTRIM(RTRIM(d.BCODE)) = :bcode
          AND UPPER(LTRIM(RTRIM(COALESCE(m.CANCELED,'')))) <> 'Y'
          AND LTRIM(RTRIM(COALESCE(m.JOURMODE,''))) <> '0'
          AND m.BILLDATE >= :since
          AND (:until IS NULL OR m.BILLDATE <= :until)
        ORDER BY m.BILLDATE DESC, m.BILLTIME DESC, m.BILLNO DESC
        """
    )
    with eng.connect() as conn:
        rows = conn.execute(
            sql,
            {"bcode": code, "since": since, "until": until},
        ).mappings().fetchall()

    out: list[StockMovement] = []
    for row in rows:
        qty = _parse_qty(row.get("qty_raw"))
        billtype = str(row.get("billtype") or "").strip()
        if billtype == "1":
            qty_delta = -abs(qty)
        elif billtype == "2":
            qty_delta = abs(qty)
        else:
            qty_delta = qty
        bd = row.get("billdate")
        if isinstance(bd, datetime):
            billdate = bd
        else:
            billdate = datetime.fromisoformat(str(bd)[:19])
        out.append(
            StockMovement(
                billno=str(row.get("billno") or "").strip(),
                billdate=billdate,
                billtime=str(row.get("billtime") or "").strip(),
                billtype=billtype,
                qty_delta=qty_delta,
                jourtype=str(row.get("jourtype") or "").strip(),
            )
        )
    return out

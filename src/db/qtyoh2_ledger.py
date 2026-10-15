"""Rebuild ICMAS.QTYOH2 from the KAcc product-open ledger identity.

Line-only (confirmed 2026-09-24, open test 12051563 → 215):

  QTYOH2 = QTYBEG2
         + Σ PIDET QTY×MTP   (line CANCELED <> 'Y')
         − Σ SIDET QTY×MTP   (JOURMODE <> '0', line CANCELED <> 'Y')

No PIMAS/SIMAS header filter (header cancel with active line stays in the sum).
Does not modify QTYBEG2.

Used on stock-check take / ondemand search / product open, parts9-explorer product detail,
and HQ PO stock reads — not a PIDET trigger. Flag: QTYOH2_SYNC_ON_READ (default on).
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Iterable

from sqlalchemy import text
from sqlalchemy.engine import Connection, Engine

log = logging.getLogger(__name__)

_TRUE = {"1", "true", "yes", "on"}

_READ_SQL = text(
    """
    SELECT
        i.ID AS icmas_id,
        CONVERT(float, COALESCE(i.QTYBEG2, 0)) AS beg,
        CONVERT(float, i.QTYOH2) AS old_qtyoh2,
        (
            SELECT COALESCE(SUM(
                CONVERT(float, p.QTY)
                * COALESCE(NULLIF(CONVERT(float, p.MTP), 0), 1.0)
            ), 0)
            FROM dbo.PIDET AS p
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(50), p.BCODE))) = :bcode
              AND UPPER(LTRIM(RTRIM(COALESCE(p.CANCELED, N'')))) <> N'Y'
        ) AS pi_units,
        (
            SELECT COALESCE(SUM(
                CONVERT(float, d.QTY)
                * COALESCE(NULLIF(CONVERT(float, d.MTP), 0), 1.0)
            ), 0)
            FROM dbo.SIDET AS d
            WHERE LTRIM(RTRIM(CONVERT(nvarchar(50), d.BCODE))) = :bcode
              AND LTRIM(RTRIM(COALESCE(d.JOURMODE, N''))) <> N'0'
              AND UPPER(LTRIM(RTRIM(COALESCE(d.CANCELED, N'')))) <> N'Y'
        ) AS si_units
    FROM dbo.ICMAS AS i
    WHERE LTRIM(RTRIM(CONVERT(nvarchar(50), i.BCODE))) = :bcode
    """
)

_UPDATE_SQL = text(
    """
    UPDATE dbo.ICMAS
    SET QTYOH2 = :new_qtyoh2
    WHERE ID = :icmas_id
      AND EXISTS (
        SELECT CONVERT(float, :new_qtyoh2)
        EXCEPT
        SELECT CONVERT(float, QTYOH2)
      )
    """
)


def qtyoh2_sync_on_read_enabled() -> bool:
    raw = (os.getenv("QTYOH2_SYNC_ON_READ") or "1").strip().lower()
    return raw in _TRUE


@dataclass(frozen=True)
class Qtyoh2SyncResult:
    bcode: str
    old_qtyoh2: float | None
    new_qtyoh2: float | None
    updated: bool
    skipped: bool
    reason: str = ""


def _as_float(value) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _floats_differ(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a != b
    return abs(a - b) > 1e-9


_BATCH = 200


def _bcode_expr(alias: str) -> str:
    return f"LTRIM(RTRIM(CONVERT(nvarchar(50), {alias}.BCODE)))"


def _missing(code: str) -> Qtyoh2SyncResult:
    return Qtyoh2SyncResult(
        bcode=code,
        old_qtyoh2=None,
        new_qtyoh2=None,
        updated=False,
        skipped=True,
        reason="missing_product",
    )


def _write_qty(
    conn: Connection,
    *,
    code: str,
    icmas_id: int,
    beg: float,
    old: float | None,
    pi_units: float,
    si_units: float,
) -> Qtyoh2SyncResult:
    new = beg + pi_units - si_units
    if not _floats_differ(old, new):
        return Qtyoh2SyncResult(
            bcode=code,
            old_qtyoh2=old,
            new_qtyoh2=new,
            updated=False,
            skipped=False,
            reason="unchanged",
        )
    result = conn.execute(
        _UPDATE_SQL,
        {"icmas_id": icmas_id, "new_qtyoh2": new},
    )
    updated = bool(result.rowcount and result.rowcount > 0)
    return Qtyoh2SyncResult(
        bcode=code,
        old_qtyoh2=old,
        new_qtyoh2=new,
        updated=updated,
        skipped=False,
        reason="updated" if updated else "unchanged",
    )


def _sync_one(conn: Connection, bcode: str) -> Qtyoh2SyncResult:
    code = (bcode or "").strip()
    if not code:
        return Qtyoh2SyncResult(
            bcode="",
            old_qtyoh2=None,
            new_qtyoh2=None,
            updated=False,
            skipped=True,
            reason="empty_bcode",
        )
    row = conn.execute(_READ_SQL, {"bcode": code}).mappings().first()
    if not row:
        return _missing(code)
    return _write_qty(
        conn,
        code=code,
        icmas_id=int(row["icmas_id"]),
        beg=_as_float(row["beg"]) or 0.0,
        old=_as_float(row["old_qtyoh2"]),
        pi_units=_as_float(row["pi_units"]) or 0.0,
        si_units=_as_float(row["si_units"]) or 0.0,
    )


def _sum_by_bcode(conn: Connection, sql: str, codes: list[str]) -> dict[str, float]:
    params = {f"b{n}": code for n, code in enumerate(codes)}
    found: dict[str, float] = {}
    for row in conn.execute(text(sql), params).mappings().all():
        bcode = str(row.get("bcode") or "").strip()
        if bcode:
            found[bcode] = _as_float(row.get("units")) or 0.0
    return found


def _sync_chunk(conn: Connection, codes: list[str]) -> list[Qtyoh2SyncResult]:
    """One ICMAS read plus one PIDET and one SIDET sum for the whole chunk.

    Same ledger identity as ``_sync_one``. A product with more than one ICMAS
    row keeps the lowest ID.
    """
    placeholders = ", ".join(f":b{n}" for n in range(len(codes)))
    params = {f"b{n}": code for n, code in enumerate(codes)}
    icmas_sql = text(
        f"""
        SELECT
            i.ID AS icmas_id,
            {_bcode_expr("i")} AS bcode,
            CONVERT(float, COALESCE(i.QTYBEG2, 0)) AS beg,
            CONVERT(float, i.QTYOH2) AS old_qtyoh2
        FROM dbo.ICMAS AS i
        WHERE {_bcode_expr("i")} IN ({placeholders})
        ORDER BY i.ID
        """
    )
    products: dict[str, dict] = {}
    for row in conn.execute(icmas_sql, params).mappings().all():
        bcode = str(row.get("bcode") or "").strip()
        if bcode and bcode not in products:
            products[bcode] = row
    pi_sql = f"""
        SELECT {_bcode_expr("p")} AS bcode,
               COALESCE(SUM(
                   CONVERT(float, p.QTY)
                   * COALESCE(NULLIF(CONVERT(float, p.MTP), 0), 1.0)
               ), 0) AS units
        FROM dbo.PIDET AS p
        WHERE UPPER(LTRIM(RTRIM(COALESCE(p.CANCELED, N'')))) <> N'Y'
          AND {_bcode_expr("p")} IN ({placeholders})
        GROUP BY {_bcode_expr("p")}
    """
    si_sql = f"""
        SELECT {_bcode_expr("d")} AS bcode,
               COALESCE(SUM(
                   CONVERT(float, d.QTY)
                   * COALESCE(NULLIF(CONVERT(float, d.MTP), 0), 1.0)
               ), 0) AS units
        FROM dbo.SIDET AS d
        WHERE LTRIM(RTRIM(COALESCE(d.JOURMODE, N''))) <> N'0'
          AND UPPER(LTRIM(RTRIM(COALESCE(d.CANCELED, N'')))) <> N'Y'
          AND {_bcode_expr("d")} IN ({placeholders})
        GROUP BY {_bcode_expr("d")}
    """
    pi = _sum_by_bcode(conn, pi_sql, codes)
    si = _sum_by_bcode(conn, si_sql, codes)
    out: list[Qtyoh2SyncResult] = []
    for code in codes:
        row = products.get(code)
        if not row:
            out.append(_missing(code))
            continue
        out.append(
            _write_qty(
                conn,
                code=code,
                icmas_id=int(row["icmas_id"]),
                beg=_as_float(row["beg"]) or 0.0,
                old=_as_float(row["old_qtyoh2"]),
                pi_units=pi.get(code, 0.0),
                si_units=si.get(code, 0.0),
            )
        )
    return out


def sync_qtyoh2_from_ledger(
    bcode: str,
    *,
    engine: Engine,
) -> Qtyoh2SyncResult:
    """Recompute and optionally write QTYOH2 for one BCODE."""
    if not qtyoh2_sync_on_read_enabled():
        return Qtyoh2SyncResult(
            bcode=(bcode or "").strip(),
            old_qtyoh2=None,
            new_qtyoh2=None,
            updated=False,
            skipped=True,
            reason="flag_off",
        )
    code = (bcode or "").strip()
    if not code:
        return Qtyoh2SyncResult(
            bcode="",
            old_qtyoh2=None,
            new_qtyoh2=None,
            updated=False,
            skipped=True,
            reason="empty_bcode",
        )
    try:
        with engine.begin() as conn:
            result = _sync_one(conn, code)
        if result.updated:
            log.info(
                "qtyoh2 ledger sync %s: %s → %s",
                result.bcode,
                result.old_qtyoh2,
                result.new_qtyoh2,
            )
        return result
    except Exception as exc:  # noqa: BLE001 — callers must still show the product
        log.warning("qtyoh2 ledger sync failed for %s: %s", code, exc)
        return Qtyoh2SyncResult(
            bcode=code,
            old_qtyoh2=None,
            new_qtyoh2=None,
            updated=False,
            skipped=True,
            reason=f"error:{type(exc).__name__}",
        )


def sync_qtyoh2_from_ledger_many(
    bcodes: Iterable[str],
    *,
    engine: Engine,
) -> list[Qtyoh2SyncResult]:
    """Batch sync (one transaction). Per-SKU errors are skipped, not raised."""
    if not qtyoh2_sync_on_read_enabled():
        return [
            Qtyoh2SyncResult(
                bcode=str(b).strip(),
                old_qtyoh2=None,
                new_qtyoh2=None,
                updated=False,
                skipped=True,
                reason="flag_off",
            )
            for b in bcodes
            if str(b).strip()
        ]
    codes: list[str] = []
    seen: set[str] = set()
    for raw in bcodes:
        code = str(raw).strip()
        if not code or code in seen:
            continue
        seen.add(code)
        codes.append(code)
    if not codes:
        return []
    out: list[Qtyoh2SyncResult] = []
    try:
        with engine.begin() as conn:
            for start in range(0, len(codes), _BATCH):
                chunk = codes[start : start + _BATCH]
                try:
                    results = _sync_chunk(conn, chunk)
                except Exception as exc:  # noqa: BLE001
                    log.warning("qtyoh2 ledger chunk failed, syncing one by one: %s", exc)
                    results = []
                    for code in chunk:
                        try:
                            results.append(_sync_one(conn, code))
                        except Exception as row_exc:  # noqa: BLE001
                            log.warning("qtyoh2 ledger sync failed for %s: %s", code, row_exc)
                            results.append(
                                Qtyoh2SyncResult(
                                    bcode=code,
                                    old_qtyoh2=None,
                                    new_qtyoh2=None,
                                    updated=False,
                                    skipped=True,
                                    reason=f"error:{type(row_exc).__name__}",
                                )
                            )
                for result in results:
                    out.append(result)
                    if result.updated:
                        log.info(
                            "qtyoh2 ledger sync %s: %s → %s",
                            result.bcode,
                            result.old_qtyoh2,
                            result.new_qtyoh2,
                        )
    except Exception as exc:  # noqa: BLE001
        log.warning("qtyoh2 ledger batch sync aborted: %s", exc)
        return [
            Qtyoh2SyncResult(
                bcode=c,
                old_qtyoh2=None,
                new_qtyoh2=None,
                updated=False,
                skipped=True,
                reason=f"error:{type(exc).__name__}",
            )
            for c in codes
        ]
    return out

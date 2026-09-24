"""Rebuild ICMAS.QTYOH2 from the KAcc product-open ledger identity.

Line-only (confirmed 2026-09-24, open test 12051563 → 215):

  QTYOH2 = QTYBEG2
         + Σ PIDET QTY×MTP   (line CANCELED <> 'Y')
         − Σ SIDET QTY×MTP   (JOURMODE <> '0', line CANCELED <> 'Y')

No PIMAS/SIMAS header filter (header cancel with active line stays in the sum).
Does not modify QTYBEG2.

Used on stock-check take / ondemand search / product open and parts9-explorer product detail —
not a PIDET trigger. Flag: QTYOH2_SYNC_ON_READ (default on).
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
        return Qtyoh2SyncResult(
            bcode=code,
            old_qtyoh2=None,
            new_qtyoh2=None,
            updated=False,
            skipped=True,
            reason="missing_product",
        )
    beg = _as_float(row["beg"]) or 0.0
    old = _as_float(row["old_qtyoh2"])
    pi_units = _as_float(row["pi_units"]) or 0.0
    si_units = _as_float(row["si_units"]) or 0.0
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
        {"icmas_id": int(row["icmas_id"]), "new_qtyoh2": new},
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
            for code in codes:
                try:
                    result = _sync_one(conn, code)
                except Exception as exc:  # noqa: BLE001
                    log.warning("qtyoh2 ledger sync failed for %s: %s", code, exc)
                    result = Qtyoh2SyncResult(
                        bcode=code,
                        old_qtyoh2=None,
                        new_qtyoh2=None,
                        updated=False,
                        skipped=True,
                        reason=f"error:{type(exc).__name__}",
                    )
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

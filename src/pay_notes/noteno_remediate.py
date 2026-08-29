from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.pay_notes.db import get_pay_notes_supabase_client, get_reminder, rename_reminder
from src.pay_notes.noteno import display_noteno, format_suffixed_noteno
from src.pay_notes.parts9 import (
    open_note_has_mixed_pi_stamps,
    open_unvouchered_note_exists,
)
from src.pay_notes.storage import relocate_bill_images
from src.stock_check.parts9 import get_parts9_engine


def _remediation_target(site: str, acct: str, bare: str, *, engine: Engine) -> str:
    for suffix in range(1, 1000):
        candidate = format_suffixed_noteno(bare, suffix)
        if not open_unvouchered_note_exists(site, acct, candidate, engine=engine):
            return candidate
    raise RuntimeError(f"no remediation suffix for {acct}/{bare}")


def remediate_open_mixed_noteno(
    *,
    site: str,
    acctno: str,
    bare_noteno: str,
    engine: Engine | None = None,
    dry_run: bool = True,
    relocate_images: bool = True,
) -> dict[str, Any] | None:
    """Rename an open note whose PIMAS rows mix paid ghosts + open bills on one NOTENO."""
    acct = (acctno or "").strip()
    bare = display_noteno(bare_noteno)
    if not acct or not bare:
        return None
    if not open_unvouchered_note_exists(site, acct, bare, engine=engine):
        return None
    if not open_note_has_mixed_pi_stamps(site, acct, bare, engine=engine):
        return None

    eng = engine or get_parts9_engine(writer=True)
    stored = _remediation_target(site, acct, bare, engine=eng)
    result: dict[str, Any] = {
        "acctno": acct,
        "from_noteno": bare,
        "to_noteno": stored,
        "dry_run": dry_run,
    }
    if dry_run:
        return result

    with eng.begin() as conn:
        hdr = conn.execute(
            text(
                """
                UPDATE dbo.PVMAS
                SET NOTENO = :stored
                WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                  AND LTRIM(RTRIM(NOTENO)) = :bare
                  AND NOTED = 'Y'
                  AND ISNULL(VOUCED, 'N') = 'N'
                  AND ISNULL(CANCELED, 'N') <> 'Y'
                """
            ),
            {"acctno": acct, "bare": bare, "stored": stored},
        )
        bills = conn.execute(
            text(
                """
                UPDATE dbo.PIMAS
                SET NOTENO = :stored
                WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                  AND LTRIM(RTRIM(NOTENO)) = :bare
                  AND ISNULL(PAID, 'N') = 'N'
                  AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                  AND ISNULL(CANCELED, 'N') <> 'Y'
                """
            ),
            {"acctno": acct, "bare": bare, "stored": stored},
        )
        result["pvmas_rows"] = hdr.rowcount
        result["pimas_rows"] = bills.rowcount

    client = get_pay_notes_supabase_client()
    if get_reminder(client, acct, bare):
        rename_reminder(client, acct, bare, stored)
        result["reminder_renamed"] = True
    if relocate_images and stored != bare:
        moved = relocate_bill_images(client, acct, bare, stored)
        result["images_moved"] = moved
    return result


def list_open_mixed_noteno_collisions(site: str, *, engine: Engine | None = None) -> list[dict[str, Any]]:
    from src.parts9_explorer.db import get_site_engine

    eng = engine or get_site_engine((site or "hq").strip().lower())
    sql = text(
        """
        SELECT LTRIM(RTRIM(p.ACCTNO)) AS acctno,
               LTRIM(RTRIM(p.NOTENO)) AS noteno,
               SUM(CASE WHEN i.PAID = 'Y' OR ISNULL(LTRIM(RTRIM(i.VOUCNO2)), '') <> '' THEN 1 ELSE 0 END) AS paid_cnt,
               SUM(CASE WHEN ISNULL(i.PAID, 'N') = 'N' AND ISNULL(LTRIM(RTRIM(i.VOUCNO2)), '') = '' THEN 1 ELSE 0 END) AS open_cnt
        FROM dbo.PVMAS p
        JOIN dbo.PIMAS i
          ON LTRIM(RTRIM(i.ACCTNO)) = LTRIM(RTRIM(p.ACCTNO))
         AND LTRIM(RTRIM(i.NOTENO)) = LTRIM(RTRIM(p.NOTENO))
        WHERE p.NOTED = 'Y'
          AND ISNULL(p.VOUCED, 'N') = 'N'
          AND ISNULL(p.CANCELED, 'N') <> 'Y'
          AND ISNULL(LTRIM(RTRIM(p.NOTENO)), '') <> ''
        GROUP BY LTRIM(RTRIM(p.ACCTNO)), LTRIM(RTRIM(p.NOTENO))
        HAVING SUM(CASE WHEN i.PAID = 'Y' OR ISNULL(LTRIM(RTRIM(i.VOUCNO2)), '') <> '' THEN 1 ELSE 0 END) > 0
           AND SUM(CASE WHEN ISNULL(i.PAID, 'N') = 'N' AND ISNULL(LTRIM(RTRIM(i.VOUCNO2)), '') = '' THEN 1 ELSE 0 END) > 0
        ORDER BY acctno, noteno
        """
    )
    with eng.connect() as conn:
        return [dict(r) for r in conn.execute(sql).mappings().all()]

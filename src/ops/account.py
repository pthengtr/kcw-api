"""Live APMAS vendor card for ops PO (matches kcw-v2 PoAccountDialog)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.ops.po import _row, _s, _site
from src.parts9_explorer.db import get_site_engine

_APMAS_COLS = (
    "LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) AS ACCTNO, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR1,'')))) AS ADDR1, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR2,'')))) AS ADDR2, "
    "LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PHONE,'')))) AS PHONE, "
    "LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(MOBILE,'')))) AS MOBILE, "
    "LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(FAX,'')))) AS FAX, "
    "LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(CONTACT,'')))) AS CONTACT, "
    "LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(EMAIL,'')))) AS EMAIL, "
    "TERM, "
    "LTRIM(RTRIM(CONVERT(nvarchar(4000), COALESCE(REMARKS,'')))) AS REMARKS, "
    "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) AS CANCELED"
)

_PO_SNAP_COLS = (
    "LTRIM(RTRIM(CONVERT(nvarchar(80), DOCNO))) AS DOCNO, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR1,'')))) AS ADDR1, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ADDR2,'')))) AS ADDR2, "
    "LTRIM(RTRIM(CONVERT(nvarchar(120), COALESCE(ATTN,'')))) AS ATTN"
)


def _nullish(value: Any) -> str | None:
    s = _s(value)
    return s or None


def get_account_detail(
    *,
    acctno: str,
    site: str = "hq",
    docno: str | None = None,
) -> dict[str, Any] | None:
    code = (acctno or "").strip()
    if not code:
        return None
    site_key = _site(site)
    doc = (docno or "").strip() or None

    apmas: dict[str, Any] | None = None
    try:
        engine = get_site_engine("hq")
        with engine.connect() as conn:
            row = conn.execute(
                text(f"SELECT {_APMAS_COLS} FROM dbo.APMAS WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) = :a"),
                {"a": code},
            ).mappings().first()
            if row:
                apmas = _row(row)
    except Exception:
        apmas = None

    po_snapshot: dict[str, Any] | None = None
    if doc:
        try:
            engine = get_site_engine(site_key)
            with engine.connect() as conn:
                prow = conn.execute(
                    text(
                        f"SELECT {_PO_SNAP_COLS} FROM dbo.POMAS "
                        f"WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), DOCNO))) = :d"
                    ),
                    {"d": doc},
                ).mappings().first()
                if prow:
                    pr = _row(prow)
                    po_snapshot = {
                        "docno": _s(pr.get("DOCNO")) or doc,
                        "acctname": _nullish(pr.get("ACCTNAME")),
                        "addr1": _nullish(pr.get("ADDR1")),
                        "addr2": _nullish(pr.get("ADDR2")),
                        "attn": _nullish(pr.get("ATTN")),
                    }
        except Exception:
            po_snapshot = None

    if not apmas and not po_snapshot:
        return {
            "acctno": code,
            "acctname": None,
            "addr1": None,
            "addr2": None,
            "phone": None,
            "tax_id": None,
            "fax": None,
            "contact": None,
            "email": None,
            "term": None,
            "remarks": None,
            "canceled": None,
            "po_snapshot": None,
            "source": "po_only",
        }

    if not apmas:
        return {
            "acctno": code,
            "acctname": po_snapshot.get("acctname") if po_snapshot else None,
            "addr1": po_snapshot.get("addr1") if po_snapshot else None,
            "addr2": po_snapshot.get("addr2") if po_snapshot else None,
            "phone": None,
            "tax_id": None,
            "fax": None,
            "contact": None,
            "email": None,
            "term": None,
            "remarks": None,
            "canceled": None,
            "po_snapshot": po_snapshot,
            "source": "po_only",
        }

    term = apmas.get("TERM")
    return {
        "acctno": _s(apmas.get("ACCTNO")) or code,
        "acctname": _nullish(apmas.get("ACCTNAME"))
        or (po_snapshot.get("acctname") if po_snapshot else None),
        "addr1": _nullish(apmas.get("ADDR1"))
        or (po_snapshot.get("addr1") if po_snapshot else None),
        "addr2": _nullish(apmas.get("ADDR2"))
        or (po_snapshot.get("addr2") if po_snapshot else None),
        "phone": _nullish(apmas.get("PHONE")),
        "tax_id": _nullish(apmas.get("MOBILE")),
        "fax": _nullish(apmas.get("FAX")),
        "contact": _nullish(apmas.get("CONTACT")),
        "email": _nullish(apmas.get("EMAIL")),
        "term": str(term).strip() if term is not None and str(term).strip() else None,
        "remarks": _nullish(apmas.get("REMARKS")),
        "canceled": _nullish(apmas.get("CANCELED")),
        "po_snapshot": po_snapshot,
        "source": "apmas",
    }

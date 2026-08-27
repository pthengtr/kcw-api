"""Live HQ PIMAS/PIDET resolve for ICLOW RCVDNO (matches kcw-v2 fetchPiDetail)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.ops.po import _row, _s
from src.parts9_explorer.db import get_site_engine

_PI_HEADER = (
    "LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) AS BILLNO_TRIM, "
    "BILLNO AS BILLNO_RAW, "
    "CONVERT(varchar(10), BILLDATE, 23) AS BILLDATE, "
    "LTRIM(RTRIM(CONVERT(nvarchar(40), COALESCE(ACCTNO,'')))) AS ACCTNO, "
    "LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME, "
    "AFTERTAX, "
    "LTRIM(RTRIM(CONVERT(nvarchar(80), COALESCE(PO,'')))) AS PO, "
    "LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) AS CANCELED, "
    "LTRIM(RTRIM(CONVERT(nvarchar(4000), COALESCE(REMARKS,'')))) AS REMARKS"
)


def bill_key12(value: str | None) -> str:
    return (value or "").strip()[:12]


def _space_key12(value: str | None) -> str:
    return bill_key12(value).replace(" ", "")


def resolve_pimas_billno(rcvdno: str) -> dict[str, Any] | None:
    """Return {billno, billno_raw, match_method} or None."""
    key = (rcvdno or "").strip()
    if not key:
        return None
    key12 = bill_key12(key)
    engine = get_site_engine("hq")
    with engine.connect() as conn:
        exact = conn.execute(
            text(
                f"SELECT TOP 1 {_PI_HEADER} FROM dbo.PIMAS "
                f"WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) = :k "
                f"AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'"
            ),
            {"k": key},
        ).mappings().first()
        if exact:
            r = _row(exact)
            return {
                "billno": _s(r.get("BILLNO_TRIM")),
                "billno_raw": r.get("BILLNO_RAW"),
                "match_method": "exact",
            }

        # left-12 / padded variants
        like = f"%{key12}%"
        cands = conn.execute(
            text(
                f"SELECT TOP 40 {_PI_HEADER} FROM dbo.PIMAS "
                f"WHERE CONVERT(nvarchar(80), BILLNO) LIKE :like "
                f"AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y'"
            ),
            {"like": like},
        ).mappings().all()

    matched: list[tuple[int, int, int, str, Any, str]] = []
    for c in cands:
        r = _row(c)
        bill = _s(r.get("BILLNO_TRIM"))
        if bill_key12(bill) != key12:
            continue
        # exact trim > shorter bill > lexical
        exact_rank = 0 if bill == key else 1
        matched.append(
            (
                exact_rank,
                len(bill),
                0,
                bill,
                r.get("BILLNO_RAW"),
                "exact",
            )
        )
    if matched:
        matched.sort(key=lambda t: (t[0], t[1], t[3]))
        bill, raw, method = matched[0][3], matched[0][4], matched[0][5]
        return {"billno": bill, "billno_raw": raw, "match_method": method}

    # Implied: equal after stripping spaces inside left-12
    sk = _space_key12(key)
    if not sk:
        return None
    with engine.connect() as conn:
        cands2 = conn.execute(
            text(
                f"SELECT TOP 80 {_PI_HEADER} FROM dbo.PIMAS "
                f"WHERE LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(CANCELED,'')))) <> 'Y' "
                f"AND REPLACE(LEFT(LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))), 12), ' ', '') = :sk"
            ),
            {"sk": sk},
        ).mappings().all()
    implied: list[tuple[int, int, str, Any]] = []
    for c in cands2:
        r = _row(c)
        bill = _s(r.get("BILLNO_TRIM"))
        # Only treat as pattern when BILLNO itself contains spaces in left-12
        if _space_key12(bill) == bill_key12(bill):
            # no spaces in bill left-12 — already covered by exact path ideally
            if bill != key:
                continue
        rank = 0 if bill.replace(" ", "") == key.replace(" ", "") else 1
        implied.append((rank, len(bill), bill, r.get("BILLNO_RAW")))
    if implied:
        implied.sort(key=lambda t: (t[0], t[1], t[2]))
        bill, raw = implied[0][2], implied[0][3]
        return {"billno": bill, "billno_raw": raw, "match_method": "pattern"}
    return None


def resolve_pimas_batch(rcvdnos: list[str]) -> dict[str, dict[str, Any]]:
    """Map rcvdno -> {pimas_matched_billno, pimas_match_method, pimas_link_missing}."""
    out: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for raw in rcvdnos:
        key = (raw or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        hit = resolve_pimas_billno(key)
        if hit:
            out[key] = {
                "pimas_matched_billno": hit["billno"],
                "pimas_match_method": hit["match_method"],
                "pimas_link_missing": False,
            }
        else:
            out[key] = {
                "pimas_matched_billno": None,
                "pimas_match_method": None,
                "pimas_link_missing": True,
            }
    return out


def get_pi_detail(*, billno_or_rcvdno: str) -> dict[str, Any] | None:
    key = (billno_or_rcvdno or "").strip()
    if not key:
        return None
    resolved = resolve_pimas_billno(key)
    engine = get_site_engine("hq")
    bill_row = None
    match_method = None
    matched_rcvdno = None
    billno_raw = None
    billno = key

    with engine.connect() as conn:
        if resolved:
            billno = resolved["billno"]
            billno_raw = resolved.get("billno_raw")
            match_method = resolved["match_method"]
            if billno != key:
                matched_rcvdno = key
            bill_row = conn.execute(
                text(
                    f"SELECT TOP 1 {_PI_HEADER} FROM dbo.PIMAS "
                    f"WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) = :b"
                ),
                {"b": billno},
            ).mappings().first()
            if not bill_row and billno_raw is not None:
                bill_row = conn.execute(
                    text(f"SELECT TOP 1 {_PI_HEADER} FROM dbo.PIMAS WHERE BILLNO = :b"),
                    {"b": billno_raw},
                ).mappings().first()
        else:
            bill_row = conn.execute(
                text(
                    f"SELECT TOP 1 {_PI_HEADER} FROM dbo.PIMAS "
                    f"WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) = :k"
                ),
                {"k": key},
            ).mappings().first()
            if bill_row:
                match_method = "exact"

        if not bill_row:
            return None

        r = _row(bill_row)
        billno = _s(r.get("BILLNO_TRIM")) or billno
        billno_raw = r.get("BILLNO_RAW") if billno_raw is None else billno_raw
        acctno = _s(r.get("ACCTNO")) or None
        acctname = _s(r.get("ACCTNAME")) or None
        if acctno and not acctname:
            ap = conn.execute(
                text(
                    "SELECT LTRIM(RTRIM(CONVERT(nvarchar(200), COALESCE(ACCTNAME,'')))) AS ACCTNAME "
                    "FROM dbo.APMAS WHERE LTRIM(RTRIM(CONVERT(nvarchar(40), ACCTNO))) = :a"
                ),
                {"a": acctno},
            ).mappings().first()
            if ap:
                acctname = _s(ap.get("ACCTNAME")) or None

        lines: list[dict[str, Any]] = []
        for raw_key in (billno_raw, billno):
            if raw_key is None or (isinstance(raw_key, str) and not raw_key.strip()):
                continue
            line_rows = conn.execute(
                text(
                    """
                    SELECT TOP 500
                      BILLNO, BCODE, DETAIL, QTY, UI, PRICE, AMOUNT, BILLTYPE, CANCELED
                    FROM dbo.PIDET
                    WHERE BILLNO = :b
                      AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(BILLTYPE,'')))) IN ('1','2','3')
                    ORDER BY LINE
                    """
                ),
                {"b": raw_key},
            ).mappings().all()
            if not line_rows and isinstance(raw_key, str):
                line_rows = conn.execute(
                    text(
                        """
                        SELECT TOP 500
                          BILLNO, BCODE, DETAIL, QTY, UI, PRICE, AMOUNT, BILLTYPE, CANCELED
                        FROM dbo.PIDET
                        WHERE LTRIM(RTRIM(CONVERT(nvarchar(80), BILLNO))) = :b
                          AND LTRIM(RTRIM(CONVERT(nvarchar(10), COALESCE(BILLTYPE,'')))) IN ('1','2','3')
                        ORDER BY LINE
                        """
                    ),
                    {"b": billno},
                ).mappings().all()
            for lr in line_rows:
                rr = _row(lr)
                if _s(rr.get("CANCELED")).upper() == "Y":
                    continue
                lines.append(
                    {
                        "billno": _s(rr.get("BILLNO")) or billno,
                        "bcode": _s(rr.get("BCODE")) or None,
                        "detail": _s(rr.get("DETAIL")) or None,
                        "qty": rr.get("QTY"),
                        "ui": _s(rr.get("UI")) or None,
                        "price": rr.get("PRICE"),
                        "amount": rr.get("AMOUNT"),
                    }
                )
            if lines:
                break

    return {
        "header": {
            "billno": billno,
            "billdate": _s(r.get("BILLDATE"))[:10] or None,
            "acctno": acctno,
            "acctname": acctname,
            "po": _s(r.get("PO")) or None,
            "aftertax": r.get("AFTERTAX"),
            "canceled": _s(r.get("CANCELED")) or None,
            "remarks": _s(r.get("REMARKS")) or None,
            "matched_rcvdno": matched_rcvdno,
            "match_method": match_method,
        },
        "lines": lines,
        "live": True,
    }

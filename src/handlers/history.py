from src.queries import (
    get_purchase_history_by_bcode,
    get_sales_history_by_bcode,
)
from zoneinfo import ZoneInfo

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
DEFAULT_HISTORY_LIMIT = 3
MAX_HISTORY_LIMIT = 10

BRANCH_ALIASES = {
    "HQ": "HQ",
    "สนญ": "HQ",
    "SYP": "SYP",
    "สาขา": "SYP",
}


def _extract_history_args(user_text: str) -> tuple[str | None, str | None, int]:
    parts = (user_text or "").strip().split()

    if len(parts) < 2:
        return None, None, DEFAULT_HISTORY_LIMIT

    bcode = parts[1].strip()
    branch = None
    limit = DEFAULT_HISTORY_LIMIT

    for token in parts[2:]:
        token_clean = token.strip()
        token_upper = token_clean.upper()

        if token_upper in BRANCH_ALIASES:
            branch = BRANCH_ALIASES[token_upper]
        elif token_clean in BRANCH_ALIASES:
            branch = BRANCH_ALIASES[token_clean]
        elif token_clean.isdigit():
            limit = min(int(token_clean), MAX_HISTORY_LIMIT)

    return bcode, branch, limit

def _format_local_dt(dt):
    if not dt:
        return "-"

    try:
        local_dt = dt.astimezone(BANGKOK_TZ)

        be_year = local_dt.year + 543
        yy = be_year % 100

        return local_dt.strftime(f"%d/%m/{yy:02d} %H:%M")
    except Exception:
        return str(dt)

def is_history_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return (
        t.startswith("ประวัติซื้อ")
        or t.startswith("ประวัติขาย")
        or t.startswith("ซื้อ ")
        or t.startswith("ขาย ")
    )


def _extract_bcode_and_limit(user_text: str) -> tuple[str | None, int]:
    parts = (user_text or "").strip().split()

    if len(parts) < 2:
        return None, DEFAULT_HISTORY_LIMIT

    bcode = parts[1].strip()
    limit = DEFAULT_HISTORY_LIMIT

    if len(parts) >= 3 and parts[2].isdigit():
        limit = min(int(parts[2]), MAX_HISTORY_LIMIT)

    return bcode, limit


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _format_amount_with_vat(amount: float, taxic: str) -> tuple[float, float]:
    """
    Returns:
        base_amount, vat_amount

    Assumption:
    - TAXIC == 'Y' means amount includes VAT
    - otherwise VAT = 0
    """
    if (taxic or "").strip().upper() == "Y":
        base = amount / 1.07
        vat = amount - base
        return base, vat

    return amount, 0.0


def _fmt_short_date(s: str) -> str:
    """
    Convert YYYY-MM-DD -> DD/MM/YY (Thai Buddhist Era)
    Example:
        2026-03-19 -> 19/03/69
    """
    if not s:
        return "-"

    try:
        year = int(s[0:4]) + 543
        yy = year % 100
        mm = s[5:7]
        dd = s[8:10]
        return f"{dd}/{mm}/{yy:02d}"
    except Exception:
        return s


def _format_sales_history(result: dict, bcode: str, limit: int, branch: str | None = None) -> str:
    rows = result.get("rows", [])
    product_name = result.get("product_name") or "-"
    latest = result.get("latest_summary")
    updated = result.get("latest_ingested_at")

    if not rows:
        if branch:
            return f"ไม่พบประวัติขายสำหรับ {bcode} ({branch})"
        return f"ไม่พบประวัติขายสำหรับ {bcode}"

    title = f"ประวัติขาย {bcode}"
    if branch:
        title += f" | {branch}"

    lines = [
        title,
        product_name,
        "",
        f"ล่าสุด {len(rows)} รายการ",
    ]

    if updated:
        lines.append(f"อัปเดต: {_format_local_dt(updated)}")

    if latest:
        lines.extend([
            "",
            "ล่าสุด:",
            _fmt_short_date(latest["billdate"]),
            f"บิล {latest['billno']}",
            f"จำนวน {latest['qty']:,.0f} | {latest['unit_amount']:,.2f}/หน่วย",
        ])

    for row in rows:
        amount = _safe_float(row.get("AMOUNT"))
        qty = _safe_float(row.get("QTY"))
        taxic = row.get("TAXIC", "")
        acctno = row.get("ACCTNO") or "-"
        row_branch = row.get("BRANCH") or "-"
        base_amount, vat_amount = _format_amount_with_vat(amount, taxic)

        lines.extend([
            "",
            f"• {_fmt_short_date(row.get('BILLDATE', '-'))}",
            # f"  {row.get('BILLNO', '-')} | {row_branch}",
            f"  จำนวน {qty:,.0f} | ราคา {(base_amount/qty):,.2f}",
            # f"  ภาษี {vat_amount:,.2f}",
            f"  ลูกค้า {acctno}",
        ])

    if limit < result.get("total_found", len(rows)):
        more_cmd = f"ขาย {bcode}"
        if branch:
            more_cmd += f" {branch}"
        more_cmd += " 10"
        lines.extend(["", f"พิมพ์ '{more_cmd}' เพื่อดูเพิ่ม"])

    return "\n".join(lines)

def _format_purchase_history(result: dict, bcode: str, limit: int) -> str:
    rows = result.get("rows", [])
    product_name = result.get("product_name") or "-"
    latest = result.get("latest_summary")
    updated = result.get("latest_ingested_at")

    if not rows:
        return f"ไม่พบประวัติซื้อสำหรับ {bcode}"

    lines = [
        f"ประวัติซื้อ {bcode}",
        product_name,
        "",
        f"ล่าสุด {len(rows)} รายการ",
    ]

    if updated:
        lines.append(f"อัปเดต: {_format_local_dt(updated)}")

    if latest:
        lines.extend([
            "",
            "ล่าสุด:",
            _fmt_short_date(latest["billdate"]),
            f"บิล {latest['billno']}",
            f"จำนวน {latest['qty']:,.0f} | {latest['unit_amount']:,.2f}/หน่วย",
        ])

    for row in rows:
        amount = _safe_float(row.get("AMOUNT"))
        qty = _safe_float(row.get("QTY"))
        taxic = row.get("TAXIC", "")
        acct_no = row.get("ACCTNO") or "-"
        base_amount, vat_amount = _format_amount_with_vat(amount, taxic)

        lines.extend([
            "",
            f"• {_fmt_short_date(row.get('BILLDATE', '-'))}",
            # f"  {row.get('BILLNO', '-')} | HQ",
            f"  จำนวน {qty:,.0f} | ราคา {(base_amount/qty):,.2f}",
            # f"  vat {vat_amount:,.2f}",
            f"  บริษัท {acct_no}",
        ])

    if limit < result.get("total_found", len(rows)):
        lines.extend(["", f"พิมพ์ 'ซื้อ {bcode} 10' เพื่อดูเพิ่ม"])

    return "\n".join(lines)

def handle_history_query(engine, user_text: str) -> str:
    text = (user_text or "").strip()
    bcode, branch, limit = _extract_history_args(text)

    if not bcode:
        return (
            "กรุณาระบุรหัสสินค้าครับ\n"
            "เช่น:\n"
            "• ประวัติซื้อ 22010585\n"
            "• ประวัติขาย 22010585\n"
            "• ขาย 22010585 HQ\n"
            "• ขาย 22010585 SYP\n"
            "• ขาย 22010585 สนญ\n"
            "• ขาย 22010585 สาขา\n"
            "• ขาย 22010585 HQ 10"
        )

    if text.startswith("ประวัติซื้อ") or text.startswith("ซื้อ "):
        result = get_purchase_history_by_bcode(engine, bcode=bcode, limit=limit)
        return _format_purchase_history(result, bcode, limit)

    if text.startswith("ประวัติขาย") or text.startswith("ขาย "):
        result = get_sales_history_by_bcode(
            engine,
            bcode=bcode,
            branch=branch,
            limit=limit,
        )
        return _format_sales_history(result, bcode, limit, branch=branch)

    return "ยังไม่เข้าใจคำสั่งครับ"
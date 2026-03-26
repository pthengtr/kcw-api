from zoneinfo import ZoneInfo

from src.queries import get_product_snapshot_by_bcode


BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


def is_product_snapshot_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return t.startswith("สินค้า ")


def _extract_bcode(user_text: str) -> str | None:
    parts = (user_text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip()


def _safe_float(value) -> float:
    try:
        return float(value or 0)
    except Exception:
        return 0.0


def _fmt_short_date(s: str) -> str:
    """
    YYYY-MM-DD -> DD/MM/YY (Thai Buddhist Era)
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


def _format_local_dt(dt) -> str:
    if not dt:
        return "-"

    try:
        local_dt = dt.astimezone(BANGKOK_TZ)
        be_year = local_dt.year + 543
        yy = be_year % 100
        return local_dt.strftime(f"%d/%m/{yy:02d} %H:%M")
    except Exception:
        return str(dt)


def handle_product_snapshot_query(engine, user_text: str) -> str:
    bcode = _extract_bcode(user_text)

    if not bcode:
        return (
            "กรุณาระบุรหัสสินค้าครับ\n"
            "เช่น:\n"
            "• สินค้า 22010585"
        )

    result = get_product_snapshot_by_bcode(engine, bcode)
    if not result:
        return f"ไม่พบข้อมูลสินค้าสำหรับ {bcode}"

    product_name = result.get("product_name") or "-"
    stock_total = _safe_float(result.get("stock_total"))
    stock_hq = _safe_float(result.get("stock_hq"))
    stock_syp = _safe_float(result.get("stock_syp"))

    purchase = result.get("last_purchase") or {}
    sales = result.get("last_sale") or {}

    updated = result.get("latest_ingested_at")

    lines = [
        f"สินค้า {bcode}",
        product_name,
        "",
        f"สต็อก สนญ {stock_hq:,.0f} | สาขา {stock_syp:,.0f}",
        f"รวม {stock_total:,.0f}",
    ]

    if updated:
        lines.append(f"อัปเดต: {_format_local_dt(updated)}")

    if purchase:
        lines.extend([
            "",
            "ซื้อล่าสุด:",
            _fmt_short_date(purchase.get("billdate")),
            f"บิล {purchase.get('billno', '-')}",
            f"บริษัท {purchase.get('acct', '-')}",
            f"จำนวน {purchase.get('qty', 0):,.0f} | {purchase.get('unit_amount', 0):,.2f}/หน่วย",
        ])

    BRANCH_LABEL = {
        "HQ": "สนญ",
        "SYP": "สาขา"
    }

    if sales:
        branch = sales.get("branch") or "-"
        lines.extend([
            "",
            "ขายล่าสุด:",
            _fmt_short_date(sales.get("billdate")),
            f"บิล {sales.get('billno', '-')} | {BRANCH_LABEL.get(branch, branch)}",
            f"ลูกค้า {sales.get('acct', '-')}",
            f"จำนวน {sales.get('qty', 0):,.0f} | {sales.get('unit_amount', 0):,.2f}/หน่วย",
        ])

    return "\n".join(lines)
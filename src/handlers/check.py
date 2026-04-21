from zoneinfo import ZoneInfo

from src.queries import get_quick_order_check_by_bcode


BANGKOK_TZ = ZoneInfo("Asia/Bangkok")
VALID_PREFIXES = ("เช็ค", "check")
STATUS_EMOJI = {
    "green": "🟢",
    "orange": "🟠",
    "red": "🔴",
}


def is_check_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(t == prefix or t.startswith(prefix + " ") for prefix in VALID_PREFIXES)


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


def _fmt_short_date(s: str | None) -> str:
    if not s:
        return "-"

    try:
        year = int(s[0:4]) + 543
        yy = year % 100
        mm = s[5:7]
        dd = s[8:10]
        return f"{dd}/{mm}/{yy:02d}"
    except Exception:
        return str(s)


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


def handle_check_query(engine, user_text: str) -> str:
    bcode = _extract_bcode(user_text)

    if not bcode:
        return (
            "กรุณาระบุรหัสสินค้าแบบเต็มครับ\n"
            "เช่น:\n"
            "• เช็ค 22010585\n"
            "• check 22010585"
        )

    result = get_quick_order_check_by_bcode(engine, bcode)
    if not result:
        return f"ไม่พบรหัสสินค้า {bcode}"

    product_name = result.get("product_name") or "-"
    stock_total = _safe_float(result.get("stock_total"))
    stock_hq = _safe_float(result.get("stock_hq"))
    stock_syp = _safe_float(result.get("stock_syp"))

    emoji = STATUS_EMOJI.get(result.get("status_key"), "⚪")
    status_label = result.get("status_label") or "-"
    status_reason = result.get("status_reason") or "-"

    sale = result.get("last_sale") or {}
    purchase = result.get("last_purchase") or {}
    months_window = int(result.get("months_window") or 6)

    lines = [
        f"สินค้า {bcode}",
        product_name,
        "",
        f"สถานะ: {emoji} {status_label}",
        status_reason,
        "",
        "สต๊อก:",
        f"• สนญ {stock_hq:,.0f}",
        f"• สาขา {stock_syp:,.0f}",
        f"• รวม {stock_total:,.0f}",
        "",
        "ข้อมูลย่อ:",
        f"• ขายล่าสุด: {_fmt_short_date(sale.get('billdate')) if sale else f'ไม่พบในข้อมูล {months_window} เดือน'}",
        f"• ซื้อเข้าล่าสุด: {_fmt_short_date(purchase.get('billdate')) if purchase else f'ไม่พบในข้อมูล {months_window} เดือน'}",
    ]

    if result.get("status_key") in {"orange", "red"}:
        lines.extend([
            "",
            "คำแนะนำ:",
            "กรุณาตรวจสอบในระบบหลักก่อนสั่งซื้อ",
        ])

    updated = result.get("latest_ingested_at")
    if updated:
        lines.extend([
            "",
            f"อัปเดต: {_format_local_dt(updated)}",
        ])

    lines.extend([
        "",
        f"ตรวจสอบจากข้อมูลย้อนหลัง {months_window} เดือนล่าสุด",
    ])

    return "\n".join(lines)
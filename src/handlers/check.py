from zoneinfo import ZoneInfo

from src.queries import get_quick_order_check_by_bcode, get_product_snapshot_by_bcode


BANGKOK_TZ = ZoneInfo("Asia/Bangkok")

VALID_PREFIXES = ("เช็ค", "check")

STATUS_EMOJI = {
    "green": "",
    "orange": "",
    "red": "",
}

BRANCH_LABEL = {
    "HQ": "สนญ",
    "SYP": "สาขา",
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


def _pick_first(*values):
    for value in values:
        if value not in (None, "", {}):
            return value
    return None


def _format_purchase_line(purchase: dict, months_window: int) -> list[str]:
    if not purchase:
        return [f"• ซื้อเข้าล่าสุด: ไม่พบในข้อมูล {months_window} เดือน"]

    date = _fmt_short_date(purchase.get("billdate"))
    acct = purchase.get("acct") or purchase.get("acctname") or "-"
    qty = _safe_float(purchase.get("qty"))
    unit_amount = _safe_float(purchase.get("unit_amount"))

    lines = [
        f"• ซื้อเข้าล่าสุด: {date}",
    ]

    if acct != "-":
        lines.append(f"  บริษัท {acct}")

    if qty or unit_amount:
        lines.append(f"  จำนวน {qty:,.0f} | {unit_amount:,.2f}/หน่วย")

    return lines


def _format_sale_line(sale: dict, months_window: int) -> list[str]:
    if not sale:
        return [f"• ขายล่าสุด: ไม่พบในข้อมูล {months_window} เดือน"]

    date = _fmt_short_date(sale.get("billdate"))
    branch = sale.get("branch") or "-"
    branch_label = BRANCH_LABEL.get(branch, branch)
    acct = sale.get("acct") or "ทั่วไป"
    qty = _safe_float(sale.get("qty"))
    unit_amount = _safe_float(sale.get("unit_amount"))

    lines = [
        f"• ขายล่าสุด: {date} | {branch_label}",
    ]

    if acct:
        lines.append(f"  ลูกค้า {acct}")

    if qty or unit_amount:
        lines.append(f"  จำนวน {qty:,.0f} | {unit_amount:,.2f}/หน่วย")

    return lines


def build_check_quick_reply(bcode: str) -> dict:
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "จัดการรูป",
                    "text": f"รูป {bcode}",
                },
            },
        ]
    }


def handle_check_query(engine, user_text: str) -> str:
    bcode = _extract_bcode(user_text)
    if not bcode:
        return (
            "กรุณาระบุรหัสสินค้าแบบเต็มครับ\n"
            "เช่น:\n"
            "• เช็ค 22010585\n"
            "• check 22010585"
        )

    check_result = get_quick_order_check_by_bcode(engine, bcode)
    snapshot_result = get_product_snapshot_by_bcode(engine, bcode)

    if not check_result and not snapshot_result:
        return f"ไม่พบรหัสสินค้า {bcode}"

    check_result = check_result or {}
    snapshot_result = snapshot_result or {}

    product_name = _pick_first(
        check_result.get("product_name"),
        snapshot_result.get("product_name"),
        "-",
    )

    stock_total = _safe_float(_pick_first(check_result.get("stock_total"), snapshot_result.get("stock_total"), 0))
    stock_hq = _safe_float(_pick_first(check_result.get("stock_hq"), snapshot_result.get("stock_hq"), 0))
    stock_syp = _safe_float(_pick_first(check_result.get("stock_syp"), snapshot_result.get("stock_syp"), 0))

    status_key = check_result.get("status_key")
    emoji = STATUS_EMOJI.get(status_key, "")
    status_label = check_result.get("status_label") or "-"
    status_reason = check_result.get("status_reason") or "-"

    months_window = int(check_result.get("months_window") or 6)

    # Prefer snapshot transaction detail because it has branch/customer/vendor/qty/price.
    sale = _pick_first(snapshot_result.get("last_sale"), check_result.get("last_sale"), {}) or {}
    purchase = _pick_first(snapshot_result.get("last_purchase"), check_result.get("last_purchase"), {}) or {}

    updated = _pick_first(
        check_result.get("latest_ingested_at"),
        snapshot_result.get("latest_ingested_at"),
    )

    lines = [
        f"สินค้า {bcode}",
        str(product_name),
        "",
        "สต๊อก:",
        f"• สนญ {stock_hq:,.0f}",
        f"• สาขา {stock_syp:,.0f}",
        f"• รวม {stock_total:,.0f}",
    ]

    if check_result:
        lines.extend(
            [
                "",
                f"สถานะ: {emoji} {status_label}".strip(),
                status_reason,
            ]
        )

    lines.extend(
        [
            "",
            "ซื้อ-ขาย ล่าสุด:",
            *_format_sale_line(sale, months_window),
            *_format_purchase_line(purchase, months_window),
        ]
    )

    if status_key in {"orange", "red"}:
        lines.extend(
            [
                "",
                "คำแนะนำ:",
                "กรุณาตรวจสอบในระบบหลักก่อนสั่งซื้อ",
            ]
        )

    if updated:
        lines.extend(
            [
                "",
                f"อัปเดต: {_format_local_dt(updated)}",
            ]
        )

    if check_result:
        lines.extend(
            [
                "",
                f"ตรวจสอบจากข้อมูลย้อนหลัง {months_window} เดือนล่าสุด",
            ]
        )

    return "\n".join(lines)


def handle_check_response(engine, user_text: str) -> dict:
    text = handle_check_query(engine, user_text)
    bcode = _extract_bcode(user_text)

    response = {
        "type": "text",
        "text": text,
    }

    if bcode and not text.startswith("กรุณาระบุ") and not text.startswith("ไม่พบ"):
        response["quickReply"] = build_check_quick_reply(bcode)

    return response
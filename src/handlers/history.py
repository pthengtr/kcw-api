from src.queries import (
    get_purchase_history_by_bcode,
    get_sales_history_by_bcode,
)

DEFAULT_HISTORY_LIMIT = 3
MAX_HISTORY_LIMIT = 10


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


def _format_purchase_history(result: dict, bcode: str, limit: int) -> str:
    rows = result.get("rows", [])
    product_name = result.get("product_name") or "-"
    latest = result.get("latest_summary")

    if not rows:
        return f"ไม่พบประวัติซื้อสำหรับ {bcode}"

    lines = [
        f"ประวัติซื้อ {bcode}",
        f"{product_name}",
        f"(ล่าสุด {len(rows)} รายการ)",
    ]

    if latest:
        lines.append(
            "สรุปล่าสุด: "
            f"{latest['billdate']} | "
            f"บิล {latest['billno']} | "
            f"จำนวน {latest['qty']:,.0f} | "
            f"เฉลี่ย/หน่วย {latest['unit_amount']:,.2f}"
        )

    for row in rows:
        amount = _safe_float(row.get("AMOUNT"))
        qty = _safe_float(row.get("QTY"))
        taxic = row.get("TAXIC", "")
        acct_no = row.get("ACCT_NO") or "-"
        base_amount, vat_amount = _format_amount_with_vat(amount, taxic)

        lines.append(
            f"• {row.get('BILLDATE', '-')} | บิล {row.get('BILLNO', '-')}\n"
            f"  จำนวน {qty:,.0f} | สุทธิ {amount:,.2f}\n"
            f"  มูลค่า {base_amount:,.2f} | VAT {vat_amount:,.2f}\n"
            f"  TAXIC {taxic or '-'} | ACCT {acct_no}"
        )

    if limit < result.get("total_found", len(rows)):
        lines.append(f"พิมพ์ 'ซื้อ {bcode} 10' เพื่อดูเพิ่ม")

    return "\n".join(lines)


def _format_sales_history(result: dict, bcode: str, limit: int) -> str:
    rows = result.get("rows", [])
    product_name = result.get("product_name") or "-"
    latest = result.get("latest_summary")

    if not rows:
        return f"ไม่พบประวัติขายสำหรับ {bcode}"

    lines = [
        f"ประวัติขาย {bcode}",
        f"{product_name}",
        f"(ล่าสุด {len(rows)} รายการ)",
    ]

    if latest:
        lines.append(
            "สรุปล่าสุด: "
            f"{latest['billdate']} | "
            f"บิล {latest['billno']} | "
            f"จำนวน {latest['qty']:,.0f} | "
            f"เฉลี่ย/หน่วย {latest['unit_amount']:,.2f}"
        )

    for row in rows:
        amount = _safe_float(row.get("AMOUNT"))
        qty = _safe_float(row.get("QTY"))
        taxic = row.get("TAXIC", "")
        acctno = row.get("ACCTNO") or "-"
        base_amount, vat_amount = _format_amount_with_vat(amount, taxic)

        lines.append(
            f"• {row.get('BILLDATE', '-')} | บิล {row.get('BILLNO', '-')}\n"
            f"  จำนวน {qty:,.0f} | สุทธิ {amount:,.2f}\n"
            f"  มูลค่า {base_amount:,.2f} | VAT {vat_amount:,.2f}\n"
            f"  TAXIC {taxic or '-'} | ACCT {acctno}"
        )

    if limit < result.get("total_found", len(rows)):
        lines.append(f"พิมพ์ 'ขาย {bcode} 10' เพื่อดูเพิ่ม")

    return "\n".join(lines)


def handle_history_query(engine, user_text: str) -> str:
    text = (user_text or "").strip()
    bcode, limit = _extract_bcode_and_limit(text)

    if not bcode:
        return (
            "กรุณาระบุรหัสสินค้าครับ\n"
            "เช่น:\n"
            "• ประวัติซื้อ 22010585\n"
            "• ประวัติขาย 22010585\n"
            "• ซื้อ 22010585 10\n"
            "• ขาย 22010585 10"
        )

    if text.startswith("ประวัติซื้อ") or text.startswith("ซื้อ "):
        result = get_purchase_history_by_bcode(engine, bcode=bcode, limit=limit)
        return _format_purchase_history(result, bcode, limit)

    if text.startswith("ประวัติขาย") or text.startswith("ขาย "):
        result = get_sales_history_by_bcode(engine, bcode=bcode, limit=limit)
        return _format_sales_history(result, bcode, limit)

    return "ยังไม่เข้าใจคำสั่งครับ"
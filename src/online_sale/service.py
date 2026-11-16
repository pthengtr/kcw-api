from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from src.online_sale import parts9
from src.online_sale.config import get_online_sale_settings
from src.online_sale.errors import OnlineSaleError
from src.online_sale.sheets.cntad import render_cntad_sheet
from src.online_sale.sheets.pick import render_pick_sheet
from src.online_sale.sheets.tad import render_tad_sheet
from src.online_sale.shops import (
    channel_label,
    customer_name_without_shop,
    list_platforms,
    list_shops,
    load_shop,
    party_from_armas,
    tax_id_from_remarks,
)
from src.online_sale.writers.cntad_simas import post_cntad
from src.online_sale.writers.tad_simas import post_tad, update_tad

RETURN_REASONS = (
    ("cancel_order", "ยกเลิกคำสั่งซื้อ"),
    ("return_goods", "คืนสินค้า"),
    ("other", "อื่นๆ"),
)


def meta_payload() -> dict[str, Any]:
    settings = get_online_sale_settings()
    return {
        "platforms": list_platforms(),
        "return_reasons": [{"id": k, "label": v} for k, v in RETURN_REASONS],
        "write_enabled": settings.write_enabled,
        "po_max_len": 15,
    }


def shops_payload(platform: str) -> dict[str, Any]:
    return {"shops": list_shops(platform)}


def product_payload(code: str) -> dict[str, Any]:
    return {"product": parts9.lookup_product(code)}


def check_po_payload(
    acctno: str, online_po: str, *, exclude_billno: str = ""
) -> dict[str, Any]:
    po = (online_po or "").strip()
    if not po:
        raise OnlineSaleError("po", "ใส่เลขคำสั่งซื้อ")
    if len(po) > 15:
        raise OnlineSaleError("po", "เลขคำสั่งซื้อยาวเกิน 15 ตัวอักษร")
    dups = parts9.find_duplicate_po(acctno, po, exclude_billno=exclude_billno)
    return {"ok": not dups, "duplicates": dups}


def _to_search_hits(raw_q: str) -> list[dict[str, Any]]:
    """Resolve TO/RVO docnos from the to_bill overlay."""
    q = (raw_q or "").strip().upper()
    if not q:
        return []
    try:
        from src.to_bill.db import get_invoice_by_docno, list_invoices
        from src.to_bill.numbering import buddhist_yymm, recent_months
    except Exception:
        return []

    hits: list[dict[str, Any]] = []
    if q.startswith("TO") or q.startswith("RVO"):
        try:
            inv = get_invoice_by_docno(q)
        except Exception:
            inv = None
        if inv:
            hits.append(inv)
            return hits
        months = [buddhist_yymm()]
        try:
            months = [m["yymm"] for m in recent_months()][:6] or months
        except Exception:
            pass
        for yymm in months:
            try:
                rows = list_invoices(status="", q=q, yymm=yymm, kind="")
            except Exception:
                continue
            for row in rows:
                docno = str(row.get("docno") or "").strip().upper()
                if docno == q or q in docno:
                    hits.append(row)
            if hits:
                break
    return hits


def search_payload(
    *,
    q: str = "",
    platform: str = "",
    acctno: str = "",
    date_from: str = "",
    date_to: str = "",
) -> dict[str, Any]:
    df = (date_from or "").strip() or None
    dt = (date_to or "").strip() or None
    date_to_excl = None
    if dt:
        try:
            date_to_excl = (date.fromisoformat(dt) + timedelta(days=1)).isoformat()
        except ValueError:
            date_to_excl = dt
    raw_q = (q or "").strip()
    upper_q = raw_q.upper()
    bills: list[dict[str, Any]] = []
    if not (upper_q.startswith("TO") or upper_q.startswith("RVO")):
        bills = parts9.search_bills(
            q=q,
            acctno=acctno,
            date_from=df,
            date_to=date_to_excl,
            platform=platform,
        )

    to_hits = _to_search_hits(raw_q)

    # Attach issued/draft TO docnos onto TAD rows when available.
    try:
        from src.to_bill.db import open_for_bills

        tad_nos = [b["billno"] for b in bills if b.get("kind") == "tad"]
        opened = open_for_bills(tad_nos) if tad_nos else {}
        for bill in bills:
            docs = opened.get(bill["billno"]) or []
            tax = next((d for d in docs if d.get("doc_kind") != "rvo"), None)
            if tax and tax.get("docno"):
                bill["to_docno"] = tax["docno"]
                bill["to_status"] = tax.get("status")
    except Exception:
        pass

    return {"bills": bills, "to_invoices": to_hits}


def bill_payload(billno: str) -> dict[str, Any]:
    return {"bill": parts9.load_bill(billno)}


def return_preview_payload(tad_billno: str) -> dict[str, Any]:
    bill = parts9.load_bill(tad_billno)
    if bill["kind"] != "tad":
        raise OnlineSaleError("tad", "คืนสินค้าได้จากบิล TAD เท่านั้น")
    if bill["canceled"]:
        raise OnlineSaleError("tad", "บิลนี้ถูกยกเลิกแล้ว")
    returned = parts9.returned_qty_by_bcode(bill["billno"])
    lines = []
    for ln in bill["lines"]:
        sold = abs(Decimal(str(ln["qty"])))
        already = returned.get(ln["bcode"], Decimal("0"))
        remain = sold - already
        lines.append(
            {
                **ln,
                "sold_qty": float(sold),
                "returned_qty": float(already),
                "remain_qty": float(remain),
            }
        )
    return {"bill": bill, "lines": lines, "reasons": meta_payload()["return_reasons"]}


def save_sale_payload(body: dict[str, Any], actor: str) -> dict[str, Any]:
    settings = get_online_sale_settings()
    if not settings.write_enabled:
        raise OnlineSaleError("write_disabled", "ยังไม่เปิด ONLINE_SALE_WRITE_ENABLED", status=403)
    shop = load_shop(str(body.get("acctno") or ""))
    po = str(body.get("online_po") or "").strip()
    check = check_po_payload(shop["acctno"], po)
    if not check["ok"]:
        dup = check["duplicates"][0]["billno"]
        raise OnlineSaleError("duplicate_po", f"เลขคำสั่งซื้อซ้ำกับบิล {dup}")
    result = post_tad(
        acctno=shop["acctno"],
        acctname=shop["bill_acctname"],
        online_po=po,
        remarks=shop["remarks"],
        operator=actor,
        lines=list(body.get("lines") or []),
        allow_oversell=bool(body.get("allow_oversell")),
    )
    bill = parts9.load_bill(result["billno"])
    return {"ok": True, "result": result, "bill": bill}


def update_sale_payload(billno: str, body: dict[str, Any], actor: str) -> dict[str, Any]:
    settings = get_online_sale_settings()
    if not settings.write_enabled:
        raise OnlineSaleError("write_disabled", "ยังไม่เปิด ONLINE_SALE_WRITE_ENABLED", status=403)
    exact = (billno or "").strip().upper()
    existing = parts9.load_bill(exact)
    if existing["kind"] != "tad":
        raise OnlineSaleError("bill", "แก้ไขได้เฉพาะบิล TAD")
    if existing["canceled"]:
        raise OnlineSaleError("bill", "บิลนี้ถูกยกเลิกแล้ว แก้ไขไม่ได้")
    shop = load_shop(str(body.get("acctno") or ""))
    po = str(body.get("online_po") or "").strip()
    check = check_po_payload(shop["acctno"], po, exclude_billno=exact)
    if not check["ok"]:
        dup = check["duplicates"][0]["billno"]
        raise OnlineSaleError("duplicate_po", f"เลขคำสั่งซื้อซ้ำกับบิล {dup}")
    result = update_tad(
        billno=exact,
        acctno=shop["acctno"],
        acctname=shop["bill_acctname"],
        online_po=po,
        remarks=shop["remarks"],
        operator=actor,
        lines=list(body.get("lines") or []),
        allow_oversell=bool(body.get("allow_oversell")),
    )
    bill = parts9.load_bill(result["billno"])
    return {"ok": True, "result": result, "bill": bill}


def save_return_payload(body: dict[str, Any], actor: str) -> dict[str, Any]:
    settings = get_online_sale_settings()
    if not settings.write_enabled:
        raise OnlineSaleError("write_disabled", "ยังไม่เปิด ONLINE_SALE_WRITE_ENABLED", status=403)
    tad = str(body.get("tad_billno") or "").strip().upper()
    preview = return_preview_payload(tad)
    bill = preview["bill"]
    reason_id = str(body.get("reason_id") or "").strip()
    reason_note = str(body.get("reason_note") or "").strip()
    reason_label = dict(RETURN_REASONS).get(reason_id, "")
    if not reason_label:
        raise OnlineSaleError("reason", "เลือกเหตุผลในการคืนสินค้า")
    if reason_id == "other" and not reason_note:
        raise OnlineSaleError("reason", "ระบุเหตุผลอื่นๆ")
    reason_text = reason_note if reason_id == "other" else reason_label

    remain_map = {ln["bcode"]: Decimal(str(ln["remain_qty"])) for ln in preview["lines"]}
    price_map = {ln["bcode"]: ln for ln in bill["lines"]}
    return_lines = []
    for raw in body.get("lines") or []:
        bcode = str(raw.get("bcode") or "").strip()
        qty = abs(float(raw.get("qty") or 0))
        if qty <= 0:
            continue
        remain = float(remain_map.get(bcode, Decimal("0")))
        if qty > remain + 1e-9:
            raise OnlineSaleError("qty", f"{bcode} คืนได้สูงสุด {remain:g}")
        src = price_map.get(bcode)
        if not src:
            raise OnlineSaleError("lines", f"{bcode} ไม่ได้อยู่ในบิลเดิม")
        return_lines.append(
            {
                "bcode": bcode,
                "qty": qty,
                "price": src["price"],
                "detail": src["detail"],
                "ui": src["ui"],
            }
        )
    if not return_lines:
        raise OnlineSaleError("lines", "ระบุจำนวนที่คืนอย่างน้อย 1 รายการ")

    result = post_cntad(
        tad_billno=tad,
        acctno=bill["acctno"],
        acctname=bill["acctname"],
        remarks=bill.get("remarks") or "",
        operator=actor,
        lines=return_lines,
        reason=reason_text,
    )
    cn = parts9.load_bill(result["billno"])
    cn["reason"] = reason_text
    cn["tad_billno"] = tad
    return {"ok": True, "result": result, "bill": cn, "original": bill}


def print_tad_html(billno: str) -> str:
    bill = parts9.load_bill(billno)
    if bill["kind"] != "tad":
        raise OnlineSaleError("bill", "พิมพ์ใบ TAD ได้จากบิล TAD เท่านั้น")
    return render_tad_sheet(bill)


def print_pick_html(billno: str) -> str:
    bill = parts9.load_bill(billno)
    if bill["kind"] != "tad":
        raise OnlineSaleError("bill", "พิมพ์ใบจัดสินค้าได้จากบิล TAD เท่านั้น")
    try:
        from src.transfer.parts9 import product_thumb_url
    except Exception:  # pragma: no cover - optional import path
        product_thumb_url = None  # type: ignore[assignment]
    for ln in bill.get("lines") or []:
        code = str(ln.get("bcode") or "").strip()
        if product_thumb_url and code and not ln.get("photo"):
            ln["photo"] = product_thumb_url(code)
    return render_pick_sheet(bill)


def print_cntad_html(billno: str, *, reason: str = "") -> str:
    bill = parts9.load_bill(billno)
    if bill["kind"] != "cntad":
        raise OnlineSaleError("bill", "พิมพ์ใบลดหนี้ได้จาก CNTAD เท่านั้น")
    original = None
    tad_ref = bill.get("online_po") or ""
    if tad_ref.upper().startswith("TAD"):
        try:
            original = parts9.load_bill(tad_ref)
        except OnlineSaleError:
            original = None
    party = party_from_armas(str(bill.get("acctno") or ""))
    raw_name = party["customer_name"] or bill.get("acctname") or ""
    bill["customer_name"] = customer_name_without_shop(str(raw_name))
    bill["customer_address"] = party["address"]
    # Prefer SIMAS REMARKS (## + 13 digits), same source as the VAT books.
    bill["customer_tax_id"] = (
        tax_id_from_remarks(bill.get("remarks"))
        or party["tax_id"]
        or tax_id_from_remarks((original or {}).get("remarks") if original else "")
    )
    bill["tad_billno"] = tad_ref
    if original:
        bill["tad_bill_date"] = original.get("bill_date")
        bill["order_id"] = original.get("online_po") or ""
        if not bill.get("shop_name"):
            bill["shop_name"] = original.get("shop_name") or ""
        if not bill.get("platform"):
            bill["platform"] = original.get("platform") or ""
    bill["channel"] = channel_label(bill.get("platform"), bill.get("shop_name"))
    return render_cntad_sheet(bill, original=original, reason=reason)

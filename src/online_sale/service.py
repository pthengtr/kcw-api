from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from src.online_sale import parts9
from src.online_sale.config import get_online_sale_settings
from src.online_sale.errors import OnlineSaleError
from src.online_sale.sheets.cntad import render_cntad_sheet
from src.online_sale.sheets.tad import render_tad_sheet
from src.online_sale.shops import list_platforms, list_shops, load_shop
from src.online_sale.writers.cntad_simas import post_cntad
from src.online_sale.writers.tad_simas import post_tad

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


def check_po_payload(acctno: str, online_po: str) -> dict[str, Any]:
    po = (online_po or "").strip()
    if not po:
        raise OnlineSaleError("po", "ใส่เลขคำสั่งซื้อ")
    if len(po) > 15:
        raise OnlineSaleError("po", "เลขคำสั่งซื้อยาวเกิน 15 ตัวอักษร")
    dups = parts9.find_duplicate_po(acctno, po)
    return {"ok": not dups, "duplicates": dups}


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
    # make date_to inclusive by bumping one day for SQL < next day
    date_to_excl = None
    if dt:
        try:
            date_to_excl = (date.fromisoformat(dt) + timedelta(days=1)).isoformat()
        except ValueError:
            date_to_excl = dt
    bills = parts9.search_bills(
        q=q,
        acctno=acctno,
        date_from=df,
        date_to=date_to_excl,
        platform=platform,
    )
    # Enrich with TO docs from to_bill when q looks like TO or we have TAD hits
    to_hits: list[dict[str, Any]] = []
    raw_q = (q or "").strip().upper()
    if raw_q.startswith("TO") or any(b["kind"] == "tad" for b in bills):
        try:
            from src.to_bill.service import month_list, search as to_search

            if raw_q.startswith("TO"):
                to_hits = month_list(q=raw_q).get("invoices") or []
            elif raw_q.startswith("TAD"):
                # issued TO for this TAD via search path
                for hit in to_search(raw_q):
                    if hit.get("docno"):
                        to_hits.append(hit)
        except Exception:
            to_hits = []
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
    return render_cntad_sheet(bill, original=original, reason=reason)

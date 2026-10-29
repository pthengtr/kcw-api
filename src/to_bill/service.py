from __future__ import annotations

from decimal import Decimal

from src.to_bill.buyers import (
    Buyer,
    armas_prefill,
    is_generic_party,
    parse_buyer,
    shop_label,
    usable_tax_id,
    validate_buyer,
)
from src.to_bill.config import get_to_bill_settings
from src.to_bill.errors import ToBillError
from src.to_bill.kss import LiveBill, load_tad, search_tad
from src.to_bill import db


def _money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(Decimal("0.01"))


def _qty(value) -> Decimal:
    return Decimal(str(value or 0))


def changed_from_kss(saved: dict, live: LiveBill) -> bool:
    if str(saved.get("tad_billno") or "") != live.billno:
        return True
    pairs = (
        ("beforetax", live.beforetax),
        ("tax", live.tax),
        ("aftertax", live.aftertax),
        ("discount", live.discount),
    )
    for key, live_value in pairs:
        if _money(saved.get(key)) != _money(live_value):
            return True
    if bool(saved.get("kss_canceled")) != live.canceled:
        return True
    lines = saved.get("lines") or []
    if len(lines) != len(live.lines):
        return True
    for saved_line, live_line in zip(lines, live.lines):
        if str(saved_line.get("bcode") or "") != live_line.bcode:
            return True
        if str(saved_line.get("detail") or "") != live_line.detail:
            return True
        if _qty(saved_line.get("qty")) != live_line.qty:
            return True
        if _money(saved_line.get("amount")) != _money(live_line.amount):
            return True
    return False


def _seller_ready() -> bool:
    return len(usable_tax_id(get_to_bill_settings().seller_tax_id)) == 13


def _decorate(row: dict, live: LiveBill | None) -> dict:
    from src.to_bill.sheet import build_sheet

    out = dict(row)
    out["generic_name"] = is_generic_party(str(row.get("acctname_kss") or ""))
    out["shop_label"] = shop_label(row.get("acctname_kss"), row.get("acctno"))
    out["seller_ready"] = _seller_ready()
    status = row.get("status")
    if status == "draft":
        out["kss_changed"] = bool(live and changed_from_kss(row, live))
        out["armas_prefill"] = armas_prefill(live.armas) if live else None
        try:
            out["next_docno"] = db.peek_next_docno()
        except Exception:
            out["next_docno"] = ""
        out["sheet_html"] = ""
    else:
        out["kss_changed"] = False
        out["armas_prefill"] = None
        out["next_docno"] = row.get("docno") or ""
        out["kss_canceled_now"] = bool(live.canceled) if live else False
        out["sheet_html"] = build_sheet(out, seller_tax_id=get_to_bill_settings().seller_tax_id)
    return out


def _load_live(billno: str) -> LiveBill | None:
    try:
        return load_tad(billno)
    except ToBillError:
        return None


def search(q: str) -> dict:
    hits = search_tad(q)
    opened = db.open_for_bills([hit.billno for hit in hits])
    rows = []
    for hit in hits:
        link = opened.get(hit.billno)
        rows.append(
            {
                "billno": hit.billno,
                "bill_date": hit.bill_date.isoformat() if hit.bill_date else None,
                "acctname": hit.acctname,
                "generic_name": is_generic_party(hit.acctname),
                "shop_label": shop_label(hit.acctname, hit.acctno),
                "online_po": hit.online_po,
                "aftertax": float(hit.aftertax),
                "canceled": hit.canceled,
                "open": link,
            }
        )
    return {"q": (q or "").strip(), "hits": rows}


def open_draft(billno: str, actor: str) -> dict:
    exact = (billno or "").strip().upper()
    if not exact.startswith("TAD"):
        raise ToBillError("bill", "ใช้ได้กับบิล TAD ของสำนักงานใหญ่", status=400)
    existing = db.find_open(exact)
    if existing:
        live = _load_live(exact)
        decorated = _decorate(existing, live)
        decorated["generic_name"] = is_generic_party(str(existing.get("acctname_kss") or ""))
        return decorated
    live = load_tad(exact)
    if not live:
        raise ToBillError("missing", "ไม่พบบิล TAD ใน KSS", status=404)
    if live.canceled:
        raise ToBillError("canceled", "บิลนี้ถูกยกเลิกใน KSS จึงออกใบเต็มไม่ได้")
    created = db.create_draft(live, actor)
    return _decorate(created, live)


def get_one(invoice_id: str) -> dict:
    row = db.get_invoice(invoice_id)
    if not row:
        raise ToBillError("missing", "ไม่พบใบเต็ม", status=404)
    live = _load_live(str(row.get("tad_billno") or ""))
    return _decorate(row, live)


def refresh(invoice_id: str, actor: str) -> dict:
    current = db.get_invoice(invoice_id)
    if not current:
        raise ToBillError("missing", "ไม่พบใบเต็ม", status=404)
    if current.get("status") != "draft":
        raise ToBillError("not_draft", "ดึงใหม่ได้เฉพาะฉบับร่าง")
    live = load_tad(str(current.get("tad_billno") or ""))
    if not live:
        raise ToBillError("missing", "ไม่พบบิล TAD ใน KSS", status=404)
    saved = db.refresh_draft(invoice_id, live, actor)
    return _decorate(saved, live)


def save(invoice_id: str, payload: dict) -> dict:
    try:
        buyer = parse_buyer(payload)
    except ValueError as exc:
        raise ToBillError("buyer", str(exc), status=400) from exc
    saved = db.save_buyer(invoice_id, buyer)
    live = _load_live(str(saved.get("tad_billno") or ""))
    return _decorate(saved, live)


def issue(invoice_id: str, payload: dict, actor: str) -> dict:
    try:
        buyer = parse_buyer(payload)
    except ValueError as exc:
        raise ToBillError("buyer", str(exc), status=400) from exc
    problem = validate_buyer(buyer)
    current = db.get_invoice(invoice_id)
    if not current:
        raise ToBillError("missing", "ไม่พบใบเต็ม", status=404)
    if current.get("status") != "draft":
        raise ToBillError("not_draft", "ออกเอกสารได้เฉพาะฉบับร่าง")
    if problem or not _seller_ready():
        db.save_buyer(invoice_id, buyer)
        if problem:
            raise ToBillError("buyer", problem, status=400)
        raise ToBillError(
            "seller_tax",
            "ยังไม่ได้ตั้งเลขประจำตัวผู้เสียภาษีของผู้ขาย (TO_BILL_SELLER_TAX_ID)",
        )
    live = load_tad(str(current.get("tad_billno") or ""))
    if not live:
        raise ToBillError("missing", "ไม่พบบิล TAD ใน KSS", status=404)
    if live.canceled:
        raise ToBillError("canceled", "บิลนี้ถูกยกเลิกใน KSS จึงออกใบเต็มไม่ได้")
    if changed_from_kss(current, live):
        raise ToBillError(
            "stale",
            "ข้อมูล KSS เปลี่ยนแล้ว กดดึงจาก KSS อีกครั้งก่อนออกเอกสาร",
        )
    issued = db.issue_invoice(invoice_id, live, buyer, actor)
    return _decorate(issued, live)


def void(invoice_id: str, reason: str, actor: str) -> dict:
    text = (reason or "").strip()
    if not text:
        raise ToBillError("reason", "ระบุเหตุผลที่ยกเลิก", status=400)
    if len(text) > 300:
        raise ToBillError("reason", "เหตุผลยาวเกินไป", status=400)
    saved = db.void_invoice(invoice_id, text, actor)
    return _decorate(saved, _load_live(str(saved.get("tad_billno") or "")))


def printed(invoice_id: str, actor: str) -> None:
    db.mark_printed(invoice_id, actor)


def month_list(*, status: str, q: str, yymm: str) -> dict:
    from src.to_bill.numbering import buddhist_yymm

    token = (yymm or "").strip() or buddhist_yymm()
    try:
        rows = db.list_invoices(status=status, q=q, yymm=token)
    except ValueError as exc:
        raise ToBillError("yymm", "เดือนไม่ถูกต้อง", status=400) from exc
    return {"yymm": token, "rows": rows}


def buyers(q: str) -> dict:
    return {"q": q, "buyers": db.suggest_buyers(q)}


def next_number() -> dict:
    docno = db.peek_next_docno()
    return {
        "docno": docno,
        "note": "เลขจริงจะถูกจองตอนออกเอกสาร ถ้ามีคนออกพร้อมกันเลขอาจขยับ",
    }


def buyer_from_payload(payload: dict) -> Buyer:
    return parse_buyer(payload)

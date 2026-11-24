from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from src.online_sale import drafts as draft_store
from src.online_sale import parts9
from src.online_sale.config import get_online_sale_settings
from src.online_sale.errors import OnlineSaleError
from src.online_sale.bill_sheets import get_bill_sheet_reason, save_bill_sheet
from src.online_sale.issuers import resolve_print_issuer, save_doc_issuer
from src.online_sale.sheets.cntad import render_cntad_sheet
from src.online_sale.sheets.pick import render_pick_sheet
from src.online_sale.sheets.tad import render_tad_sheet
from src.online_sale.shops import (
    PO_LEN_BY_PLATFORM,
    channel_label,
    customer_name_without_shop,
    list_platforms,
    list_shops,
    load_shop,
    party_from_armas,
    tax_id_from_remarks,
    validate_online_po,
)
from src.online_sale.writers.cntad_simas import post_cntad
from src.online_sale.writers.tad_simas import post_tad, update_tad
from src.staff.errors import StaffMappingError
from src.staff.profiles import issuer_label_for_actor, require_staff_mapping

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
        "po_len_by_platform": dict(PO_LEN_BY_PLATFORM),
        # Hard ceiling for PARTS9 SIMAS.PO (nvarchar(30)); exact lengths come from po_len_by_platform.
        "po_max_len": 30,
    }


def shops_payload(platform: str) -> dict[str, Any]:
    return {"shops": list_shops(platform)}


def product_payload(code: str) -> dict[str, Any]:
    return {"product": parts9.lookup_product(code)}


def check_po_payload(
    acctno: str,
    online_po: str,
    *,
    platform: str = "",
    exclude_billno: str = "",
    exclude_draft_id: str = "",
) -> dict[str, Any]:
    plat = (platform or "").strip().lower()
    if not plat and (acctno or "").strip():
        try:
            plat = str(load_shop(acctno).get("platform") or "").strip().lower()
        except OnlineSaleError:
            plat = ""
    po = validate_online_po(plat, online_po)
    dups = parts9.find_duplicate_po(acctno, po, exclude_billno=exclude_billno)
    try:
        draft_dups = draft_store.find_duplicate_draft_po(
            acctno, po, exclude_draft_id=exclude_draft_id
        )
    except Exception:
        draft_dups = []
    all_dups = list(dups) + list(draft_dups)
    return {
        "ok": not all_dups,
        "duplicates": all_dups,
        "online_po": po,
        "platform": plat,
        "expected_len": PO_LEN_BY_PLATFORM.get(plat),
        "actual_len": len(po),
    }


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
    kind: str = "",
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
    kind_key = (kind or "").strip().lower()
    want_drafts = kind_key in ("", "all", "draft", "drafts")
    want_bills = kind_key in ("", "all", "tad", "cntad", "bill", "bills")

    bills: list[dict[str, Any]] = []
    draft_rows: list[dict[str, Any]] = []

    if want_drafts and not (upper_q.startswith("TO") or upper_q.startswith("RVO")):
        try:
            draft_rows = draft_store.list_drafts(
                q=q,
                platform=platform,
                acctno=acctno,
                date_from=date_from,
                date_to=date_to,
            )
        except Exception:
            draft_rows = []

    if want_bills and kind_key != "draft" and kind_key != "drafts":
        if not (upper_q.startswith("TO") or upper_q.startswith("RVO")):
            bills = parts9.search_bills(
                q=q,
                acctno=acctno,
                date_from=df,
                date_to=date_to_excl,
                platform=platform,
            )

    to_hits: list[dict[str, Any]] = []
    if want_bills and kind_key not in ("draft", "drafts"):
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

    # Drafts first so pick staff see open orders before posted TAD.
    return {"bills": list(draft_rows) + list(bills), "to_invoices": to_hits, "drafts": draft_rows}


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


def _guard_staff_mapping(
    *,
    line_user_id: str,
    display_name: str,
    confirm_unmapped: bool,
) -> str:
    """Return printable issuer label; warn unless confirm_unmapped."""
    try:
        mapped = require_staff_mapping(line_user_id, display_name)
        if mapped.get("issuer_label"):
            return str(mapped["issuer_label"])
    except StaffMappingError as exc:
        if not confirm_unmapped:
            raise OnlineSaleError(exc.code, exc.message, status=exc.status) from exc
    return issuer_label_for_actor(
        line_user_id=line_user_id,
        display_name=display_name,
    )


def save_sale_payload(
    body: dict[str, Any],
    actor: str,
    *,
    line_user_id: str = "",
    confirm_unmapped: bool = False,
) -> dict[str, Any]:
    settings = get_online_sale_settings()
    if not settings.write_enabled:
        raise OnlineSaleError("write_disabled", "ยังไม่เปิด ONLINE_SALE_WRITE_ENABLED", status=403)
    issuer_label = _guard_staff_mapping(
        line_user_id=line_user_id,
        display_name=actor,
        confirm_unmapped=confirm_unmapped,
    )
    shop = load_shop(str(body.get("acctno") or ""))
    platform = str(body.get("platform") or shop.get("platform") or "").strip()
    po = validate_online_po(platform, body.get("online_po"))
    draft_id = str(body.get("draft_id") or "").strip()
    check = check_po_payload(
        shop["acctno"],
        po,
        platform=platform,
        exclude_draft_id=draft_id,
    )
    if not check["ok"]:
        dup = check["duplicates"][0]["billno"]
        raise OnlineSaleError("duplicate_po", f"เลขคำสั่งซื้อซ้ำกับ {dup}")
    if draft_id:
        # Ensure draft still open before cutting stock / issuing TAD.
        draft = draft_store.get_draft(draft_id)
        if draft["status"] not in ("open", "printed"):
            raise OnlineSaleError("draft", "ฉบับร่างนี้ขายหรือยกเลิกไปแล้ว")
    result = post_tad(
        acctno=shop["acctno"],
        acctname=shop["bill_acctname"],
        online_po=po,
        remarks=shop["remarks"],
        operator=actor,
        lines=list(body.get("lines") or []),
        allow_oversell=bool(body.get("allow_oversell")),
    )
    try:
        save_doc_issuer(
            result["billno"],
            line_user_id=line_user_id,
            display_name=actor,
            issuer_label=issuer_label,
        )
    except Exception:
        pass
    if draft_id:
        try:
            draft_store.mark_draft_sold(draft_id, result["billno"], actor)
        except OnlineSaleError:
            # TAD already posted — surface soft warning via response.
            pass
    bill = parts9.load_bill(result["billno"])
    bill["issuer_label"] = issuer_label
    try:
        save_bill_sheet(
            result["billno"], kind="tad", html=render_tad_sheet(_enrich_tad_for_print(bill))
        )
    except Exception:
        pass
    return {"ok": True, "result": result, "bill": bill}


def save_draft_payload(body: dict[str, Any], actor: str) -> dict[str, Any]:
    settings = get_online_sale_settings()
    if not settings.write_enabled:
        raise OnlineSaleError("write_disabled", "ยังไม่เปิด ONLINE_SALE_WRITE_ENABLED", status=403)
    shop = load_shop(str(body.get("acctno") or ""))
    platform = str(body.get("platform") or shop.get("platform") or "").strip()
    po = validate_online_po(platform, body.get("online_po"))
    draft_id = str(body.get("draft_id") or "").strip()
    check = check_po_payload(
        shop["acctno"],
        po,
        platform=platform,
        exclude_draft_id=draft_id,
    )
    if not check["ok"]:
        dup = check["duplicates"][0]["billno"]
        raise OnlineSaleError("duplicate_po", f"เลขคำสั่งซื้อซ้ำกับ {dup}")
    payload = dict(
        platform=platform,
        acctno=shop["acctno"],
        acctname=shop.get("bill_acctname") or shop.get("acctname") or "",
        shop_name=shop.get("shop_name") or "",
        online_po=po,
        lines=list(body.get("lines") or []),
        actor=actor,
    )
    if draft_id:
        draft = draft_store.update_draft(draft_id, **payload)
    else:
        draft = draft_store.create_draft(**payload)
    return {"ok": True, "draft": draft}


def draft_payload(draft_id: str) -> dict[str, Any]:
    return {"draft": draft_store.get_draft(draft_id)}


def cancel_draft_payload(draft_id: str, actor: str) -> dict[str, Any]:
    settings = get_online_sale_settings()
    if not settings.write_enabled:
        raise OnlineSaleError("write_disabled", "ยังไม่เปิด ONLINE_SALE_WRITE_ENABLED", status=403)
    draft = draft_store.cancel_draft(draft_id, actor)
    return {"ok": True, "draft": draft}


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
    platform = str(body.get("platform") or shop.get("platform") or "").strip()
    po = validate_online_po(platform, body.get("online_po"))
    check = check_po_payload(
        shop["acctno"], po, platform=platform, exclude_billno=exact
    )
    if not check["ok"]:
        dup = check["duplicates"][0]["billno"]
        raise OnlineSaleError("duplicate_po", f"เลขคำสั่งซื้อซ้ำกับ {dup}")
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
    bill["issuer_label"] = resolve_print_issuer(bill)
    try:
        save_bill_sheet(
            result["billno"], kind="tad", html=render_tad_sheet(_enrich_tad_for_print(bill))
        )
    except Exception:
        pass
    return {"ok": True, "result": result, "bill": bill}


def save_return_payload(
    body: dict[str, Any],
    actor: str,
    *,
    line_user_id: str = "",
    confirm_unmapped: bool = False,
) -> dict[str, Any]:
    settings = get_online_sale_settings()
    if not settings.write_enabled:
        raise OnlineSaleError("write_disabled", "ยังไม่เปิด ONLINE_SALE_WRITE_ENABLED", status=403)
    issuer_label = _guard_staff_mapping(
        line_user_id=line_user_id,
        display_name=actor,
        confirm_unmapped=confirm_unmapped,
    )
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
                "mtp": src.get("mtp") or 1,
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
    try:
        save_doc_issuer(
            result["billno"],
            line_user_id=line_user_id,
            display_name=actor,
            issuer_label=issuer_label,
        )
    except Exception:
        pass
    cn = parts9.load_bill(result["billno"])
    cn["issuer_label"] = issuer_label
    enriched, original = _enrich_cntad_for_print(cn, reason=reason_text)
    try:
        save_bill_sheet(
            result["billno"],
            kind="cntad",
            html=render_cntad_sheet(enriched, original=original, reason=reason_text),
            reason=reason_text,
        )
    except Exception:
        pass
    return {"ok": True, "result": result, "bill": enriched, "original": original}


def _enrich_tad_for_print(bill: dict[str, Any]) -> dict[str, Any]:
    """Buyer block + channel so VAT/online TAD match CNTAD meta layout."""
    out = dict(bill)
    party = party_from_armas(str(out.get("acctno") or ""))
    raw_name = party["customer_name"] or out.get("acctname") or ""
    out["customer_name"] = customer_name_without_shop(str(raw_name))
    out["customer_address"] = party["address"] or out.get("customer_address") or ""
    out["customer_tax_id"] = (
        tax_id_from_remarks(out.get("remarks"))
        or party["tax_id"]
        or out.get("customer_tax_id")
        or ""
    )
    out["channel"] = channel_label(out.get("platform"), out.get("shop_name"))
    out["issuer_label"] = (
        str(out.get("issuer_label") or "").strip() or resolve_print_issuer(out)
    )
    return out


def _enrich_cntad_for_print(
    bill: dict[str, Any], *, reason: str = ""
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Same enrichment for post snapshot and live/VAT reprint."""
    out = dict(bill)
    original = None
    tad_ref = out.get("tad_billno") or out.get("online_po") or ""
    if str(tad_ref).upper().startswith("TAD") or str(tad_ref).upper().startswith("3TAD"):
        try:
            original = parts9.load_bill(str(tad_ref))
        except OnlineSaleError:
            original = None
    party = party_from_armas(str(out.get("acctno") or ""))
    raw_name = party["customer_name"] or out.get("acctname") or ""
    out["customer_name"] = customer_name_without_shop(str(raw_name))
    out["customer_address"] = party["address"]
    out["customer_tax_id"] = (
        tax_id_from_remarks(out.get("remarks"))
        or party["tax_id"]
        or tax_id_from_remarks((original or {}).get("remarks") if original else "")
    )
    out["tad_billno"] = tad_ref
    if original:
        out["tad_bill_date"] = original.get("bill_date")
        out["order_id"] = original.get("online_po") or ""
        if not out.get("shop_name"):
            out["shop_name"] = original.get("shop_name") or ""
        if not out.get("platform"):
            out["platform"] = original.get("platform") or ""
    out["channel"] = channel_label(out.get("platform"), out.get("shop_name"))
    out["issuer_label"] = (
        str(out.get("issuer_label") or "").strip() or resolve_print_issuer(out)
    )
    reason_text = (
        (reason or "").strip()
        or str(out.get("reason") or "").strip()
        or get_bill_sheet_reason(str(out.get("billno") or ""))
    )
    out["reason"] = reason_text
    return out, original


def print_tad_html(billno: str) -> str:
    bill = parts9.load_bill(billno)
    if bill["kind"] != "tad":
        raise OnlineSaleError("bill", "พิมพ์ใบ TAD ได้จากบิล TAD เท่านั้น")
    html = render_tad_sheet(_enrich_tad_for_print(bill))
    try:
        save_bill_sheet(bill["billno"], kind="tad", html=html)
    except Exception:
        pass
    return html


def _attach_pick_photos(bill: dict[str, Any]) -> None:
    try:
        from src.transfer.parts9 import product_thumb_url
    except Exception:  # pragma: no cover - optional import path
        product_thumb_url = None  # type: ignore[assignment]
    for ln in bill.get("lines") or []:
        code = str(ln.get("bcode") or "").strip()
        if product_thumb_url and code and not ln.get("photo"):
            ln["photo"] = product_thumb_url(code)


def _attach_pick_stock(bill: dict[str, Any]) -> None:
    """Refresh on-hand qty + ICMAS name extras for the pick sheet."""
    for ln in bill.get("lines") or []:
        code = str(ln.get("bcode") or "").strip()
        if not code:
            continue
        try:
            product = parts9.lookup_product(code)
        except Exception:
            continue
        if not product:
            continue
        try:
            ln["qtyoh2"] = float(product.get("qtyoh2") or 0)
        except (TypeError, ValueError):
            pass
        if not ln.get("location1") and (product.get("location") or product.get("location1")):
            ln["location1"] = product.get("location1") or product.get("location") or ""
        for key in ("brand", "model", "pcode", "mcode"):
            value = str(product.get(key) or "").strip()
            if value:
                ln[key] = value


def print_pick_html(
    billno: str = "",
    *,
    billnos: list[str] | None = None,
    draft_ids: list[str] | None = None,
) -> str:
    """Print pick sheet from drafts only (order id), not from posted TAD."""
    ids: list[str] = []
    for raw in list(draft_ids or []) + list(billnos or []) + ([billno] if billno else []):
        for part in str(raw or "").replace(";", ",").split(","):
            exact = part.strip()
            if exact and exact not in ids:
                ids.append(exact)
    if not ids:
        raise OnlineSaleError("draft", "เลือกฉบับร่างที่จะพิมพ์ใบจัดสินค้า")
    bills = draft_store.drafts_for_pick(ids)
    for bill in bills:
        _attach_pick_photos(bill)
        _attach_pick_stock(bill)
    try:
        draft_store.mark_drafts_printed(ids)
    except Exception:
        pass
    if len(bills) == 1:
        return render_pick_sheet(bills[0])
    return render_pick_sheet(bills=bills)


def print_cntad_html(billno: str, *, reason: str = "") -> str:
    bill = parts9.load_bill(billno)
    if bill["kind"] != "cntad":
        raise OnlineSaleError("bill", "พิมพ์ใบลดหนี้ได้จาก CNTAD เท่านั้น")
    enriched, original = _enrich_cntad_for_print(bill, reason=reason)
    reason_text = str(enriched.get("reason") or "").strip()
    html = render_cntad_sheet(enriched, original=original, reason=reason_text)
    try:
        save_bill_sheet(
            bill["billno"], kind="cntad", html=html, reason=reason_text or None
        )
    except Exception:
        pass
    return html

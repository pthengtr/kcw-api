from __future__ import annotations

from datetime import date
from typing import Any

from src.hq_receive import db
from src.hq_receive import invoice_ai
from src.hq_receive import stickers as sticker_svc
from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.iclow_open import list_open_lines, list_open_vendors, search_vendors
from src.hq_receive.rules import (
    RULES_SUMMARY,
    VARIANCE_CHANGE_PRODUCT,
    VARIANCE_ACTIONS,
    line_bill_qty,
    line_sticker_qty,
    totals_mismatch,
)
from src.hq_receive.writers.credit_note_pimas import stamp_vendor_cn_doc
from src.hq_receive.writers.receive_pimas import post_vendor_receive
from src.transfer.writers._engine import writer_engine_for_branch


def _line_amount(line: dict[str, Any]) -> float:
    amount = float(line.get("amount") or 0)
    if amount > 0:
        return amount
    # Draft totals follow bill qty (money on the vendor invoice).
    qty = line_bill_qty(line) if line.get("bill_qty") is not None else float(line.get("qty") or 0)
    cost = float(line.get("cost") or 0)
    discount = float(line.get("discount") or 0)
    return max(0.0, qty * cost - discount)


def _normalize_lines(lines: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for raw in lines or []:
        bill_qty = float(raw["bill_qty"]) if raw.get("bill_qty") is not None else float(raw.get("qty") or 0)
        if raw.get("received_qty") is not None:
            received_qty = float(raw.get("received_qty") or 0)
        else:
            received_qty = bill_qty
        if bill_qty <= 0 and received_qty <= 0:
            continue
        status = str(raw.get("status") or "ok").lower()
        if status not in {"ok", "hold", "mismatch"}:
            status = "ok"
        action = str(raw.get("variance_action") or "").strip().lower() or None
        if action and action not in VARIANCE_ACTIONS:
            action = None
        if action == VARIANCE_CHANGE_PRODUCT:
            status = "hold"
            raw = {**raw, "hold_reason": raw.get("hold_reason") or "เปลี่ยนสินค้า"}
        row = {
            "iclow_id": raw.get("iclow_id"),
            "bcode": str(raw.get("bcode") or "").strip(),
            "descr": raw.get("descr") or "",
            "bill_qty": bill_qty,
            "received_qty": received_qty,
            "qty": bill_qty if bill_qty > 0 else received_qty,
            "variance_action": action,
            "ui": raw.get("ui") or "",
            "cost": float(raw.get("cost") or 0),
            "discount": float(raw.get("discount") or 0),
            "amount": 0.0,
            "po_docno": raw.get("po_docno") or raw.get("hq_po_docno") or "",
            "status": status,
            "hold_reason": raw.get("hold_reason"),
            "force_ok": bool(raw.get("force_ok")),
            "match_score": raw.get("match_score"),
            "flags": list(raw.get("flags") or []),
        }
        row["amount"] = _line_amount(row)
        if not row["bcode"] and status != "hold":
            raise HqReceiveError("missing_bcode", "มีรายการที่ไม่มีรหัสสินค้า")
        if not row["bcode"]:
            row["bcode"] = f"HOLD-{len(out)+1}"
            row["status"] = "hold"
        out.append(row)
    return out


def _totals(lines: list[dict[str, Any]], payload: dict[str, Any]) -> dict[str, float]:
    subtotal = sum(
        _line_amount(ln)
        for ln in lines
        if str(ln.get("status") or "ok").lower() != "hold"
    )
    discount = float(payload.get("discount") or 0)
    before = max(0.0, subtotal - discount)
    tax = float(payload.get("tax") or 0)
    vat_rate = payload.get("vat_rate")
    if tax <= 0 and vat_rate in (7, "7", 7.0):
        tax = round(before * 0.07, 2)
    net = float(payload.get("net") or 0) or round(before + tax, 2)
    return {
        "subtotal": round(subtotal, 2),
        "discount": round(discount, 2),
        "vat": round(tax, 2),
        "tax": round(tax, 2),
        "net": round(net, 2),
    }


def vendors_payload(*, q: str = "") -> dict[str, Any]:
    return {"vendors": search_vendors(q)}


def open_vendors_payload() -> dict[str, Any]:
    return {"vendors": list_open_vendors()}


def open_lines_payload(*, acctno: str = "", q: str = "") -> dict[str, Any]:
    lines = list_open_lines(acctno=acctno, q=q)
    return {"lines": lines, "count": len(lines)}


def create_draft(payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    lines = _normalize_lines(payload.get("lines"))
    if not lines:
        raise HqReceiveError("empty_lines", "ยังไม่มีรายการสินค้า")
    totals = _totals(lines, payload)
    po_docnos = sorted(
        {
            str(ln.get("po_docno") or "").strip()
            for ln in lines
            if str(ln.get("po_docno") or "").strip()
        }
    )
    body = {
        "vendor_acctno": str(payload.get("vendor_acctno") or "").strip(),
        "vendor_name": payload.get("vendor_name"),
        "vendor_billno": str(payload.get("vendor_billno") or "").strip(),
        "vendor_bill_date": payload.get("vendor_bill_date") or None,
        "receive_date": payload.get("receive_date") or date.today().isoformat(),
        "pay_method": payload.get("pay_method") or "credit",
        "receiver": payload.get("receiver") or actor,
        "po_docnos": payload.get("po_docnos") or po_docnos,
        "extraction_id": payload.get("extraction_id"),
        "lines": lines,
        "notes": payload.get("notes"),
        "created_by": actor,
        "updated_by": actor,
        **totals,
    }
    if not body["vendor_acctno"]:
        raise HqReceiveError("missing_vendor", "ยังไม่ได้เลือกเจ้าหนี้")
    return db.create_receipt(body)


def save_draft(receipt_id: str, payload: dict[str, Any], *, actor: str) -> dict[str, Any]:
    lines = _normalize_lines(payload.get("lines")) if "lines" in payload else None
    body = dict(payload)
    if lines is not None:
        if not lines:
            raise HqReceiveError("empty_lines", "ยังไม่มีรายการสินค้า")
        body["lines"] = lines
        body.update(_totals(lines, payload))
        body["po_docnos"] = payload.get("po_docnos") or sorted(
            {
                str(ln.get("po_docno") or "").strip()
                for ln in lines
                if str(ln.get("po_docno") or "").strip()
            }
        )
    body["updated_by"] = actor
    return db.update_receipt(receipt_id, body)


def get_draft(receipt_id: str) -> dict[str, Any]:
    return db.get_receipt(receipt_id)


def history_payload(*, limit: int = 40) -> dict[str, Any]:
    return {"receipts": db.list_history(limit=limit)}


def confirm_receipt(receipt_id: str, *, actor: str) -> dict[str, Any]:
    receipt = db.get_receipt(receipt_id)
    if receipt.get("status") not in {"draft", "dry_run"}:
        raise HqReceiveError("already_confirmed", "ใบรับนี้ยืนยันแล้ว")

    warnings: list[str] = []
    if totals_mismatch(receipt.get("expected_net"), receipt.get("net")):
        warnings.append("ยอดสุทธิในฟอร์มไม่ตรงกับยอดบิลที่ AI อ่านได้")

    result = post_vendor_receive(receipt, operator=actor)
    dry_run = bool(result.get("dry_run"))
    kcw_billno = result.get("kcw_billno") or result.get("pimas_billno") or ""
    pimas_billno = result.get("pimas_billno") or kcw_billno or ""
    if dry_run and not kcw_billno:
        kcw_billno = "(preview)"
        pimas_billno = "(preview)"

    credit_note_row = None
    cn_meta = result.get("credit_note")
    cn_billno = result.get("cn_billno") or (cn_meta or {}).get("cn_billno")
    if cn_meta and cn_billno and not dry_run:
        try:
            credit_note_row = db.save_credit_note(
                {
                    "receipt_id": receipt_id,
                    "source_pimas_billno": str(pimas_billno),
                    "cn_billno": str(cn_billno),
                    "vendor_acctno": receipt.get("vendor_acctno"),
                    "vendor_name": receipt.get("vendor_name"),
                    "is_vat": bool(cn_meta.get("is_vat")),
                    "status": cn_meta.get("status") or (
                        "awaiting_vendor_doc" if cn_meta.get("is_vat") else "completed"
                    ),
                    "beforetax": cn_meta.get("beforetax"),
                    "tax": cn_meta.get("tax"),
                    "aftertax": cn_meta.get("aftertax"),
                    "lines": cn_meta.get("lines") or [],
                    "created_by": actor,
                }
            )
            if credit_note_row.get("status") == "awaiting_vendor_doc":
                warnings.append(
                    f"สร้างใบลดหนี้ชั่วคราว {cn_billno} — กรอกเลขที่/วันที่จากเจ้าหนี้ที่แท็บใบลดหนี้"
                )
            else:
                warnings.append(f"สร้างใบลดหนี้ {cn_billno}")
        except HqReceiveError as exc:
            if exc.code == "credit_note_duplicate":
                credit_note_row = db.find_active_credit_note_for_source(str(pimas_billno))
                warnings.append(exc.message)
            else:
                raise
    elif cn_meta and dry_run:
        warnings.append(
            "Dry-run: จะสร้างใบลดหนี้ "
            + str((cn_meta.get("prefix") or "") + "…")
            + (" (รอเอกสาร VAT)" if cn_meta.get("is_vat") else "")
        )

    saved = db.mark_confirmed(
        receipt_id,
        kcw_billno=str(kcw_billno),
        pimas_billno=str(pimas_billno),
        actor=actor,
        dry_run=dry_run,
    )
    sticker_lines = [
        {
            "bcode": ln.get("bcode"),
            "qty": line_sticker_qty(ln),
            "descr": ln.get("descr") or "",
        }
        for ln in (saved.get("lines") or receipt.get("lines") or [])
        if str(ln.get("status") or "ok").lower() != "hold" and line_sticker_qty(ln) > 0
    ]
    return {
        "receipt": saved,
        "write": result,
        "credit_note": credit_note_row,
        "sticker_lines": sticker_lines,
        "write_enabled": get_hq_receive_settings().write_enabled,
        "warnings": warnings,
    }


def credit_notes_payload(*, status: str = "", limit: int = 80) -> dict[str, Any]:
    return {"credit_notes": db.list_credit_notes(status=status, limit=limit)}


def fill_vendor_credit_note(
    credit_note_id: str,
    *,
    vendor_cn_no: str,
    vendor_cn_date: str | None,
    actor: str,
) -> dict[str, Any]:
    row = db.get_credit_note(credit_note_id)
    note = str(vendor_cn_no or "").strip()
    if not note:
        raise HqReceiveError("missing_vendor_cn", "กรอกเลขที่ใบลดหนี้จากเจ้าหนี้")
    settings = get_hq_receive_settings()
    if settings.write_enabled:
        engine = writer_engine_for_branch("hq")
        with engine.begin() as conn:
            stamp_vendor_cn_doc(
                conn,
                cn_billno=str(row.get("cn_billno") or ""),
                vendor_cn_no=note,
                vendor_cn_date=vendor_cn_date,
            )
    saved = db.complete_credit_note(
        credit_note_id,
        vendor_cn_no=note,
        vendor_cn_date=vendor_cn_date,
        actor=actor,
    )
    return {
        "credit_note": saved,
        "write_enabled": settings.write_enabled,
        "parts9_updated": bool(settings.write_enabled),
    }


def extract_invoice(
    *,
    image_bytes: bytes,
    content_type: str | None,
    vendor_acctno: str,
    file_name: str,
    actor: str,
) -> dict[str, Any]:
    return invoice_ai.extract_invoice_from_image(
        image_bytes,
        content_type=content_type,
        vendor_acctno=vendor_acctno,
        file_name=file_name,
        actor=actor,
    )


def match_invoice(extraction_id: str, *, vendor_acctno: str = "", actor: str = "") -> dict[str, Any]:
    matched = invoice_ai.match_extraction_to_open(
        extraction_id, vendor_acctno=vendor_acctno
    )
    if matched.get("discrepancies"):
        db.save_discrepancies(
            matched["discrepancies"],
            extraction_id=extraction_id,
            actor=actor,
        )
    return matched


def discrepancies_payload(*, status: str = "open", limit: int = 80) -> dict[str, Any]:
    return {"discrepancies": db.list_discrepancies(status=status, limit=limit)}


def sticker_config() -> dict[str, Any]:
    return sticker_svc.config_payload()


def sticker_preview(body: dict[str, Any]) -> dict[str, Any]:
    return sticker_svc.preview(
        body.get("lines") or [],
        printer_model=str(body.get("printer_model") or ""),
        all_previews=bool(body.get("all_previews")),
    )


def sticker_print(body: dict[str, Any], *, actor: str) -> dict[str, Any]:
    return sticker_svc.print_or_download(
        body.get("lines") or [],
        action=str(body.get("action") or "download"),
        printer_model=str(body.get("printer_model") or ""),
        printer_host=str(body.get("printer_host") or ""),
        receipt_id=body.get("receipt_id"),
        pimas_billno=body.get("pimas_billno"),
        actor=actor,
    )


def sticker_jobs(*, receipt_id: str | None = None, limit: int = 40) -> dict[str, Any]:
    return {"jobs": sticker_svc.list_jobs(receipt_id=receipt_id, limit=limit)}


def meta_payload() -> dict[str, Any]:
    settings = get_hq_receive_settings()
    return {
        "service": "kcw-hq-receive",
        "write_enabled": settings.write_enabled,
        "listen_port": settings.hq_receive_listen_port,
        "today": date.today().isoformat(),
        "cost_tolerance_pct": settings.hq_receive_cost_tolerance_pct,
        "qty_tolerance": settings.hq_receive_qty_tolerance,
        "total_tolerance": settings.hq_receive_total_tolerance,
        "sticker_printer_model": settings.hq_receive_sticker_printer_model,
        "rules": RULES_SUMMARY,
    }

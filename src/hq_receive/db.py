from __future__ import annotations

import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.guards import HqReceiveError

SCHEMA = "hq_receive"

# Process-local fallback when Supabase schema is not applied yet.
_MEMORY: dict[str, dict[str, Any]] = {}
_MEMORY_EXTRACTIONS: dict[str, dict[str, Any]] = {}
_MEMORY_DISCREPANCIES: list[dict[str, Any]] = []
_MEMORY_PRINT_JOBS: list[dict[str, Any]] = []
_MEMORY_CREDIT_NOTES: dict[str, dict[str, Any]] = {}


@lru_cache
def get_hq_receive_supabase_client() -> Client:
    settings = get_hq_receive_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise HqReceiveError("supabase_missing", "ยังไม่ได้ตั้ง Supabase สำหรับรับสินค้าเข้า")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _table(client: Client, name: str):
    return client.schema(SCHEMA).from_(name)


def _rows(resp) -> list[dict[str, Any]]:
    return [dict(row) for row in (resp.data or [])]


def _first(resp) -> dict[str, Any]:
    data = resp.data
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    if isinstance(data, dict):
        return dict(data)
    return {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _use_memory() -> bool:
    try:
        client = get_hq_receive_supabase_client()
        _table(client, "receipts").select("receipt_id").limit(1).execute()
        return False
    except Exception:
        return True


def create_receipt(payload: dict[str, Any]) -> dict[str, Any]:
    receipt_id = str(uuid.uuid4())
    row = {
        "receipt_id": receipt_id,
        "short_id": payload.get("short_id") or receipt_id[:8].upper(),
        "status": "draft",
        "vendor_acctno": payload.get("vendor_acctno") or "",
        "vendor_name": payload.get("vendor_name"),
        "vendor_billno": payload.get("vendor_billno") or "",
        "vendor_bill_date": payload.get("vendor_bill_date"),
        "receive_date": payload.get("receive_date"),
        "pay_method": payload.get("pay_method") or "credit",
        "receiver": payload.get("receiver") or "",
        "po_docnos": payload.get("po_docnos") or [],
        "kcw_billno": payload.get("kcw_billno"),
        "pimas_billno": None,
        "subtotal": float(payload.get("subtotal") or 0),
        "discount": float(payload.get("discount") or 0),
        "vat": float(payload.get("vat") or 0),
        "net": float(payload.get("net") or 0),
        "lines": payload.get("lines") or [],
        "notes": payload.get("notes"),
        "extraction_id": payload.get("extraction_id"),
        "created_by": payload.get("created_by"),
        "updated_by": payload.get("updated_by"),
        "created_at": _now(),
        "updated_at": _now(),
        "confirmed_at": None,
    }
    if _use_memory():
        _MEMORY[receipt_id] = row
        row = dict(row)
        row["_storage"] = "memory"
        return row

    client = get_hq_receive_supabase_client()
    lines = row.pop("lines")
    inserted = _first(_table(client, "receipts").insert(row).execute())
    line_rows = []
    for i, line in enumerate(lines, start=1):
        line_rows.append(_line_row(inserted["receipt_id"], i * 10, line))
    if line_rows:
        _table(client, "lines").insert(line_rows).execute()
    inserted["lines"] = line_rows
    inserted["_storage"] = "supabase"
    return inserted


def _line_row(receipt_id: str, line_no: int, line: dict[str, Any]) -> dict[str, Any]:
    bill_qty = line.get("bill_qty")
    received_qty = line.get("received_qty")
    qty = float(line.get("qty") or 0)
    return {
        "receipt_id": receipt_id,
        "line_no": line_no,
        "iclow_id": line.get("iclow_id"),
        "bcode": line.get("bcode") or "",
        "descr": line.get("descr"),
        "qty": qty,
        "bill_qty": float(bill_qty) if bill_qty is not None else qty,
        "received_qty": float(received_qty) if received_qty is not None else qty,
        "variance_action": line.get("variance_action"),
        "ui": line.get("ui"),
        "cost": float(line.get("cost") or 0),
        "discount": float(line.get("discount") or 0),
        "amount": float(line.get("amount") or 0),
        "po_docno": line.get("po_docno") or line.get("hq_po_docno"),
        "status": line.get("status") or "ok",
        "hold_reason": line.get("hold_reason"),
    }


def update_receipt(receipt_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    rid = str(receipt_id or "").strip()
    if not rid:
        raise HqReceiveError("missing_id", "ไม่พบรหัสใบรับ")

    if _use_memory() or rid in _MEMORY:
        row = _MEMORY.get(rid)
        if not row:
            raise HqReceiveError("not_found", "ไม่พบใบรับสินค้า")
        if row.get("status") != "draft":
            raise HqReceiveError("not_draft", "ใบรับนี้ยืนยันแล้ว แก้ไขไม่ได้")
        for key in (
            "vendor_acctno",
            "vendor_name",
            "vendor_billno",
            "vendor_bill_date",
            "receive_date",
            "pay_method",
            "receiver",
            "po_docnos",
            "subtotal",
            "discount",
            "vat",
            "net",
            "lines",
            "notes",
            "extraction_id",
            "updated_by",
        ):
            if key in payload:
                row[key] = payload[key]
        row["updated_at"] = _now()
        _MEMORY[rid] = row
        out = dict(row)
        out["_storage"] = "memory"
        return out

    client = get_hq_receive_supabase_client()
    existing = _first(
        _table(client, "receipts").select("*").eq("receipt_id", rid).limit(1).execute()
    )
    if not existing:
        raise HqReceiveError("not_found", "ไม่พบใบรับสินค้า")
    if existing.get("status") != "draft":
        raise HqReceiveError("not_draft", "ใบรับนี้ยืนยันแล้ว แก้ไขไม่ได้")

    patch = {k: payload[k] for k in (
        "vendor_acctno",
        "vendor_name",
        "vendor_billno",
        "vendor_bill_date",
        "receive_date",
        "pay_method",
        "receiver",
        "po_docnos",
        "subtotal",
        "discount",
        "vat",
        "net",
        "notes",
        "extraction_id",
        "updated_by",
    ) if k in payload}
    patch["updated_at"] = _now()
    updated = _first(
        _table(client, "receipts").update(patch).eq("receipt_id", rid).execute()
    )
    if "lines" in payload:
        _table(client, "lines").delete().eq("receipt_id", rid).execute()
        line_rows = []
        for i, line in enumerate(payload.get("lines") or [], start=1):
            line_rows.append(_line_row(rid, i * 10, line))
        if line_rows:
            _table(client, "lines").insert(line_rows).execute()
        updated["lines"] = line_rows
    else:
        updated["lines"] = _rows(
            _table(client, "lines").select("*").eq("receipt_id", rid).order("line_no").execute()
        )
    updated["_storage"] = "supabase"
    return updated


def get_receipt(receipt_id: str) -> dict[str, Any]:
    rid = str(receipt_id or "").strip()
    if rid in _MEMORY:
        out = dict(_MEMORY[rid])
        out["_storage"] = "memory"
        return out
    if _use_memory():
        raise HqReceiveError("not_found", "ไม่พบใบรับสินค้า")
    client = get_hq_receive_supabase_client()
    row = _first(
        _table(client, "receipts").select("*").eq("receipt_id", rid).limit(1).execute()
    )
    if not row:
        raise HqReceiveError("not_found", "ไม่พบใบรับสินค้า")
    row["lines"] = _rows(
        _table(client, "lines").select("*").eq("receipt_id", rid).order("line_no").execute()
    )
    row["_storage"] = "supabase"
    return row


def mark_confirmed(
    receipt_id: str,
    *,
    kcw_billno: str,
    pimas_billno: str,
    actor: str,
    dry_run: bool,
) -> dict[str, Any]:
    rid = str(receipt_id or "").strip()
    # Dry-run keeps draft so the operator can confirm again after enabling writes.
    status = "draft" if dry_run else "confirmed"
    if rid in _MEMORY or _use_memory():
        row = _MEMORY.get(rid)
        if not row:
            raise HqReceiveError("not_found", "ไม่พบใบรับสินค้า")
        row["status"] = status
        if not dry_run:
            row["kcw_billno"] = kcw_billno
            row["pimas_billno"] = pimas_billno
            row["confirmed_at"] = _now()
        row["updated_by"] = actor
        row["updated_at"] = _now()
        row["last_dry_run_at"] = _now() if dry_run else row.get("last_dry_run_at")
        _MEMORY[rid] = row
        out = dict(row)
        out["_storage"] = "memory"
        out["_dry_run"] = dry_run
        return out

    client = get_hq_receive_supabase_client()
    patch: dict[str, Any] = {
        "status": status,
        "updated_by": actor,
        "updated_at": _now(),
    }
    if not dry_run:
        patch.update(
            {
                "kcw_billno": kcw_billno,
                "pimas_billno": pimas_billno,
                "confirmed_at": _now(),
            }
        )
    updated = _first(
        _table(client, "receipts")
        .update(patch)
        .eq("receipt_id", rid)
        .execute()
    )
    updated["lines"] = _rows(
        _table(client, "lines").select("*").eq("receipt_id", rid).order("line_no").execute()
    )
    updated["_storage"] = "supabase"
    updated["_dry_run"] = dry_run
    return updated


def list_history(*, limit: int = 40) -> list[dict[str, Any]]:
    if _use_memory():
        rows = sorted(
            _MEMORY.values(),
            key=lambda r: r.get("updated_at") or "",
            reverse=True,
        )
        return [{**r, "_storage": "memory"} for r in rows[:limit]]
    client = get_hq_receive_supabase_client()
    return _rows(
        _table(client, "receipts")
        .select(
            "receipt_id,short_id,status,vendor_acctno,vendor_name,vendor_billno,"
            "kcw_billno,pimas_billno,receive_date,net,confirmed_at,updated_at,extraction_id"
        )
        .order("updated_at", desc=True)
        .limit(limit)
        .execute()
    )


def save_extraction(row: dict[str, Any]) -> dict[str, Any]:
    eid = str(row.get("extraction_id") or uuid.uuid4())
    payload = {
        "extraction_id": eid,
        "vendor_acctno": row.get("vendor_acctno") or "",
        "file_name": row.get("file_name"),
        "content_type": row.get("content_type"),
        "file_sha256": row.get("file_sha256"),
        "raw_text": row.get("raw_text"),
        "structured": row.get("structured") or {},
        "confidence": row.get("confidence"),
        "created_by": row.get("created_by"),
        "created_at": row.get("created_at") or _now(),
    }
    lines = row.get("lines") or (payload["structured"].get("lines") if isinstance(payload["structured"], dict) else [])
    _MEMORY_EXTRACTIONS[eid] = {**row, **payload, "lines": lines}

    if _use_memory():
        out = dict(_MEMORY_EXTRACTIONS[eid])
        out["_storage"] = "memory"
        return out

    client = get_hq_receive_supabase_client()
    inserted = _first(_table(client, "invoice_extractions").insert(payload).execute())
    line_rows = []
    for i, line in enumerate(lines or [], start=1):
        line_rows.append(
            {
                "extraction_id": eid,
                "line_no": int(line.get("line_no") or i * 10),
                "raw_code": line.get("raw_code"),
                "raw_name": line.get("raw_name"),
                "brand": line.get("brand"),
                "model": line.get("model"),
                "qty": line.get("qty"),
                "ui": line.get("ui"),
                "cost": line.get("cost"),
                "discount": line.get("discount"),
                "amount": line.get("amount"),
                "confidence": line.get("confidence"),
            }
        )
    if line_rows:
        _table(client, "invoice_extraction_lines").insert(line_rows).execute()
    inserted["lines"] = line_rows
    inserted["structured"] = payload["structured"]
    inserted["_storage"] = "supabase"
    _MEMORY_EXTRACTIONS[eid] = inserted
    return inserted


def get_extraction(extraction_id: str) -> dict[str, Any]:
    eid = str(extraction_id or "").strip()
    if eid in _MEMORY_EXTRACTIONS:
        return dict(_MEMORY_EXTRACTIONS[eid])
    if _use_memory():
        raise HqReceiveError("not_found", "ไม่พบผลอ่านบิล")
    client = get_hq_receive_supabase_client()
    row = _first(
        _table(client, "invoice_extractions")
        .select("*")
        .eq("extraction_id", eid)
        .limit(1)
        .execute()
    )
    if not row:
        raise HqReceiveError("not_found", "ไม่พบผลอ่านบิล")
    lines = _rows(
        _table(client, "invoice_extraction_lines")
        .select("*")
        .eq("extraction_id", eid)
        .order("line_no")
        .execute()
    )
    row["lines"] = lines
    _MEMORY_EXTRACTIONS[eid] = row
    return row


def save_discrepancies(
    items: list[dict[str, Any]],
    *,
    receipt_id: str | None = None,
    extraction_id: str | None = None,
    actor: str = "",
) -> list[dict[str, Any]]:
    saved: list[dict[str, Any]] = []
    for item in items or []:
        row = {
            "discrepancy_id": str(uuid.uuid4()),
            "receipt_id": receipt_id,
            "extraction_id": extraction_id,
            "iclow_id": item.get("iclow_id"),
            "bcode": item.get("bcode"),
            "kind": item.get("kind") or "other",
            "detail": item.get("detail") or {},
            "status": item.get("status") or "open",
            "created_by": actor,
            "created_at": _now(),
        }
        _MEMORY_DISCREPANCIES.insert(0, row)
        saved.append(row)

    if _use_memory() or not saved:
        return saved

    try:
        client = get_hq_receive_supabase_client()
        _table(client, "discrepancies").insert(saved).execute()
    except Exception:
        for row in saved:
            row["_storage"] = "memory"
    return saved


def list_discrepancies(*, status: str = "open", limit: int = 80) -> list[dict[str, Any]]:
    st = (status or "").strip().lower()
    rows = list(_MEMORY_DISCREPANCIES)
    if st:
        rows = [r for r in rows if str(r.get("status") or "").lower() == st]
    if _use_memory():
        return rows[:limit]
    try:
        client = get_hq_receive_supabase_client()
        q = _table(client, "discrepancies").select("*").order("created_at", desc=True).limit(limit)
        if st:
            q = q.eq("status", st)
        db_rows = _rows(q.execute())
        if db_rows:
            return db_rows
    except Exception:
        pass
    return rows[:limit]


def save_print_job(job: dict[str, Any]) -> dict[str, Any]:
    row = {
        "job_id": job.get("job_id") or str(uuid.uuid4()),
        "receipt_id": job.get("receipt_id"),
        "pimas_billno": job.get("pimas_billno"),
        "printer_model": job.get("printer_model"),
        "printer_host": job.get("printer_host"),
        "action": job.get("action") or "download",
        "copies": int(job.get("copies") or 0),
        "lines": job.get("lines") or [],
        "created_by": job.get("created_by"),
        "created_at": job.get("created_at") or _now(),
    }
    _MEMORY_PRINT_JOBS.insert(0, row)
    if _use_memory():
        row["_storage"] = "memory"
        return row
    try:
        client = get_hq_receive_supabase_client()
        inserted = _first(_table(client, "barcode_print_jobs").insert(row).execute())
        inserted["_storage"] = "supabase"
        return inserted
    except Exception:
        row["_storage"] = "memory"
        return row


def list_print_jobs(*, receipt_id: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
    rid = (receipt_id or "").strip()
    rows = list(_MEMORY_PRINT_JOBS)
    if rid:
        rows = [r for r in rows if str(r.get("receipt_id") or "") == rid]
    if _use_memory():
        return rows[:limit]
    try:
        client = get_hq_receive_supabase_client()
        q = (
            _table(client, "barcode_print_jobs")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
        )
        if rid:
            q = q.eq("receipt_id", rid)
        db_rows = _rows(q.execute())
        if db_rows:
            return db_rows
    except Exception:
        pass
    return rows[:limit]


def find_active_credit_note_for_source(source_pimas_billno: str) -> dict[str, Any] | None:
    source = str(source_pimas_billno or "").strip()
    if not source:
        return None
    for row in _MEMORY_CREDIT_NOTES.values():
        if (
            str(row.get("source_pimas_billno") or "").strip() == source
            and str(row.get("status") or "") != "canceled"
        ):
            return dict(row)
    if _use_memory():
        return None
    try:
        client = get_hq_receive_supabase_client()
        row = _first(
            _table(client, "credit_notes")
            .select("*")
            .eq("source_pimas_billno", source)
            .neq("status", "canceled")
            .limit(1)
            .execute()
        )
        return row or None
    except Exception:
        return None


def save_credit_note(row: dict[str, Any]) -> dict[str, Any]:
    source = str(row.get("source_pimas_billno") or "").strip()
    existing = find_active_credit_note_for_source(source)
    if existing:
        raise HqReceiveError(
            "credit_note_duplicate",
            f"มีใบลดหนี้ {existing.get('cn_billno')} สำหรับบิล {source} อยู่แล้ว",
        )
    cid = str(row.get("credit_note_id") or uuid.uuid4())
    payload = {
        "credit_note_id": cid,
        "receipt_id": row.get("receipt_id"),
        "source_pimas_billno": source,
        "cn_billno": str(row.get("cn_billno") or "").strip(),
        "vendor_acctno": row.get("vendor_acctno") or "",
        "vendor_name": row.get("vendor_name"),
        "is_vat": bool(row.get("is_vat")),
        "status": row.get("status") or "awaiting_vendor_doc",
        "vendor_cn_no": row.get("vendor_cn_no"),
        "vendor_cn_date": row.get("vendor_cn_date"),
        "beforetax": float(row.get("beforetax") or 0),
        "tax": float(row.get("tax") or 0),
        "aftertax": float(row.get("aftertax") or 0),
        "lines": row.get("lines") or [],
        "created_by": row.get("created_by"),
        "updated_by": row.get("updated_by") or row.get("created_by"),
        "created_at": row.get("created_at") or _now(),
        "updated_at": row.get("updated_at") or _now(),
        "completed_at": row.get("completed_at"),
    }
    if payload["status"] == "completed" and not payload.get("completed_at"):
        payload["completed_at"] = _now()
    _MEMORY_CREDIT_NOTES[cid] = payload
    if _use_memory():
        out = dict(payload)
        out["_storage"] = "memory"
        return out
    try:
        client = get_hq_receive_supabase_client()
        inserted = _first(_table(client, "credit_notes").insert(payload).execute())
        inserted["_storage"] = "supabase"
        _MEMORY_CREDIT_NOTES[cid] = inserted
        return inserted
    except Exception as exc:
        # Unique violation → treat as duplicate.
        msg = str(exc).lower()
        if "duplicate" in msg or "unique" in msg:
            raise HqReceiveError(
                "credit_note_duplicate",
                f"มีใบลดหนี้สำหรับบิล {source} อยู่แล้ว",
            ) from exc
        payload["_storage"] = "memory"
        return payload


def list_credit_notes(*, status: str = "", limit: int = 80) -> list[dict[str, Any]]:
    st = (status or "").strip().lower()
    rows = sorted(
        _MEMORY_CREDIT_NOTES.values(),
        key=lambda r: r.get("updated_at") or "",
        reverse=True,
    )
    if st:
        rows = [r for r in rows if str(r.get("status") or "").lower() == st]
    if _use_memory():
        return [{**r, "_storage": "memory"} for r in rows[:limit]]
    try:
        client = get_hq_receive_supabase_client()
        q = (
            _table(client, "credit_notes")
            .select("*")
            .order("updated_at", desc=True)
            .limit(limit)
        )
        if st:
            q = q.eq("status", st)
        db_rows = _rows(q.execute())
        if db_rows:
            return db_rows
    except Exception:
        pass
    return [{**r, "_storage": "memory"} for r in rows[:limit]]


def get_credit_note(credit_note_id: str) -> dict[str, Any]:
    cid = str(credit_note_id or "").strip()
    if cid in _MEMORY_CREDIT_NOTES:
        out = dict(_MEMORY_CREDIT_NOTES[cid])
        out["_storage"] = "memory"
        return out
    if _use_memory():
        raise HqReceiveError("not_found", "ไม่พบใบลดหนี้")
    client = get_hq_receive_supabase_client()
    row = _first(
        _table(client, "credit_notes")
        .select("*")
        .eq("credit_note_id", cid)
        .limit(1)
        .execute()
    )
    if not row:
        raise HqReceiveError("not_found", "ไม่พบใบลดหนี้")
    row["_storage"] = "supabase"
    _MEMORY_CREDIT_NOTES[cid] = row
    return row


def complete_credit_note(
    credit_note_id: str,
    *,
    vendor_cn_no: str,
    vendor_cn_date: str | None,
    actor: str,
) -> dict[str, Any]:
    row = get_credit_note(credit_note_id)
    if str(row.get("status") or "") == "canceled":
        raise HqReceiveError("cn_canceled", "ใบลดหนี้นี้ยกเลิกแล้ว")
    if str(row.get("status") or "") == "completed" and row.get("vendor_cn_no"):
        raise HqReceiveError("cn_already_completed", "กรอกเลขที่เจ้าหนี้แล้ว")
    patch = {
        "vendor_cn_no": str(vendor_cn_no or "").strip(),
        "vendor_cn_date": vendor_cn_date,
        "status": "completed",
        "completed_at": _now(),
        "updated_by": actor,
        "updated_at": _now(),
    }
    row.update(patch)
    _MEMORY_CREDIT_NOTES[str(row["credit_note_id"])] = row
    if row.get("_storage") == "memory" or _use_memory():
        out = dict(row)
        out["_storage"] = "memory"
        return out
    try:
        client = get_hq_receive_supabase_client()
        updated = _first(
            _table(client, "credit_notes")
            .update(patch)
            .eq("credit_note_id", row["credit_note_id"])
            .execute()
        )
        updated["_storage"] = "supabase"
        _MEMORY_CREDIT_NOTES[str(updated["credit_note_id"])] = updated
        return updated
    except Exception:
        out = dict(row)
        out["_storage"] = "memory"
        return out

"""Barcode sticker helpers for HQ receive — reuse transfer TSPL renderer, site=HQ."""

from __future__ import annotations

import base64
import uuid
from typing import Any

from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.guards import HqReceiveError
from src.transfer.parts9 import fetch_sticker_catalog
from src.transfer.sticker import (
    build_batch_tspl,
    count_copies,
    is_lan_printer_host,
    normalize_printer_model,
    render_label_png,
    resolve_sticker_labels,
    send_tspl,
    sticker_config_payload,
    validate_batch,
)

_MEMORY_JOBS: list[dict[str, Any]] = []


def config_payload() -> dict[str, Any]:
    settings = get_hq_receive_settings()
    return sticker_config_payload(
        model=settings.hq_receive_sticker_printer_model,
        host=settings.hq_receive_sticker_printer_host,
    )


def _labels_from_lines(lines: list[dict[str, Any]]):
    catalog = fetch_sticker_catalog(
        [str(ln.get("bcode") or "") for ln in lines],
        site="hq",
    )
    return resolve_sticker_labels(lines, catalog, site="hq")


def preview(lines: list[dict[str, Any]], *, printer_model: str = "", all_previews: bool = False) -> dict[str, Any]:
    if not lines:
        raise HqReceiveError("empty_stickers", "ยังไม่ได้เลือกสินค้าสำหรับสติ๊กเกอร์")
    labels = _labels_from_lines(lines)
    problem = validate_batch(labels)
    if problem and not labels:
        raise HqReceiveError("sticker_invalid", problem)
    model = normalize_printer_model(
        printer_model or get_hq_receive_settings().hq_receive_sticker_printer_model
    )
    label_payloads = []
    preview_b64 = ""
    for i, label in enumerate(labels):
        row = label.as_preview_dict()
        if all_previews or i == 0:
            png_b64 = base64.standard_b64encode(
                render_label_png(label, printer_model=model)
            ).decode("ascii")
            row["preview_png_b64"] = png_b64
            if i == 0:
                preview_b64 = png_b64
        label_payloads.append(row)
    return {
        "printer_model": model,
        "copies": count_copies(labels),
        "labels": label_payloads,
        "preview_png_b64": preview_b64,
    }


def print_or_download(
    lines: list[dict[str, Any]],
    *,
    action: str = "download",
    printer_model: str = "",
    printer_host: str = "",
    receipt_id: str | None = None,
    pimas_billno: str | None = None,
    actor: str = "",
) -> dict[str, Any]:
    if not lines:
        raise HqReceiveError("empty_stickers", "ยังไม่ได้เลือกสินค้าสำหรับสติ๊กเกอร์")
    settings = get_hq_receive_settings()
    labels = _labels_from_lines(lines)
    problem = validate_batch(labels)
    if problem:
        raise HqReceiveError("sticker_invalid", problem)
    model = normalize_printer_model(printer_model or settings.hq_receive_sticker_printer_model)
    payload = build_batch_tspl(labels, printer_model=model)
    copies = count_copies(labels)
    act = (action or "download").strip().lower()
    host = (printer_host or settings.hq_receive_sticker_printer_host or "").strip()

    job = {
        "job_id": str(uuid.uuid4()),
        "receipt_id": receipt_id,
        "pimas_billno": pimas_billno,
        "printer_model": model,
        "printer_host": host,
        "action": act,
        "copies": copies,
        "lines": [
            {"bcode": str(ln.get("bcode") or ""), "qty": int(ln.get("qty") or 1)}
            for ln in lines
        ],
        "created_by": actor,
    }
    _MEMORY_JOBS.insert(0, job)
    try:
        from src.hq_receive import db as receive_db

        receive_db.save_print_job(job)
    except Exception:
        job["_storage"] = "memory"

    if act == "download":
        return {
            "job": job,
            "download": True,
            "prn_b64": base64.standard_b64encode(payload).decode("ascii"),
            "filename": f"kcw-hq-receive-{pimas_billno or receipt_id or 'stickers'}.prn",
            "copies": copies,
        }

    if not host:
        raise HqReceiveError(
            "need_host",
            "ยังไม่ได้ตั้งค่า IP เครื่องพิมพ์ — กรอก LAN หรือดาวน์โหลดไฟล์ .prn",
        )
    if not is_lan_printer_host(host):
        raise HqReceiveError("bad_host", "IP เครื่องพิมพ์ต้องอยู่ในวง LAN / Tailscale")
    send_tspl(host, payload)
    return {"job": job, "printed": True, "host": host, "copies": copies}


def list_jobs(*, receipt_id: str | None = None, limit: int = 40) -> list[dict[str, Any]]:
    rid = (receipt_id or "").strip()
    rows = list(_MEMORY_JOBS)
    try:
        from src.hq_receive import db as receive_db

        db_rows = receive_db.list_print_jobs(receipt_id=rid or None, limit=limit)
        if db_rows:
            return db_rows
    except Exception:
        pass
    if rid:
        rows = [j for j in rows if str(j.get("receipt_id") or "") == rid]
    return rows[:limit]

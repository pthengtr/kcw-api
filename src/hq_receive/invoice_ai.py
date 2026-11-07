"""Vendor purchase-invoice OCR/extract + match against HQ ค้างรับ."""

from __future__ import annotations

import base64
import hashlib
import json
import logging
import os
import re
import uuid
from datetime import date
from difflib import SequenceMatcher
from typing import Any

from src.ai.openai_client import (
    extract_text_from_response,
    extract_usage_from_response,
    get_openai_client,
)
from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.iclow_open import list_open_lines
from src.hq_receive.rules import classify_line, cost_mismatch, qty_mismatch

logger = logging.getLogger("kcw.hq_receive.invoice_ai")

_MEMORY_EXTRACTIONS: dict[str, dict[str, Any]] = {}

INVOICE_EXTRACT_PROMPT = """
You extract a Thai auto-parts vendor purchase invoice (ใบส่งของ / ใบกำกับภาษีซื้อ) for warehouse receiving.

Return JSON only. No markdown fences.

Schema:
{
  "vendor_name": string,
  "vendor_billno": string,
  "bill_date": string,
  "pay_method": string,
  "subtotal": number,
  "discount": number,
  "vat": number,
  "net": number,
  "lines": [
    {
      "raw_code": string,
      "raw_name": string,
      "brand": string,
      "model": string,
      "qty": number,
      "ui": string,
      "cost": number,
      "discount": number,
      "amount": number,
      "confidence": number
    }
  ],
  "warnings": [string]
}

Rules:
- vendor_billno = supplier invoice number (เลขที่บิล / Invoice No).
- bill_date = YYYY-MM-DD when possible; else empty string.
- lines = product rows only (รหัส/ชื่อ/จำนวน/ราคา), not totals.
- cost = unit cost before line discount when visible.
- amount = line total after discount when visible; else qty*cost.
- confidence = 0..1 for that line.
- Do not invent products. Skip unreadable rows and warn.
- If nothing found: empty lines + warning.
""".strip()


def _strip_json_fences(text: str) -> str:
    cleaned = (text or "").strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
    return cleaned.strip()


def _safe_parse_json(text: str) -> dict[str, Any]:
    cleaned = _strip_json_fences(text)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except Exception:
        logger.exception("hq_receive_invoice_json_parse_failed raw=%s", cleaned[:500])
    return {"error": "invalid_json", "warnings": ["Could not parse model output as JSON"], "lines": []}


def _norm_code(value: str) -> str:
    return re.sub(r"[\s\-_/\\.]", "", (value or "").strip().upper())


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_structured(raw: dict[str, Any]) -> dict[str, Any]:
    lines_out: list[dict[str, Any]] = []
    for i, line in enumerate(raw.get("lines") or [], start=1):
        if not isinstance(line, dict):
            continue
        qty = _as_float(line.get("qty"))
        cost = _as_float(line.get("cost"))
        discount = _as_float(line.get("discount"))
        amount = _as_float(line.get("amount"))
        if amount <= 0 and qty > 0:
            amount = max(0.0, qty * cost - discount)
        raw_code = str(line.get("raw_code") or line.get("code") or "").strip()
        raw_name = str(line.get("raw_name") or line.get("name") or line.get("descr") or "").strip()
        if not raw_code and not raw_name and qty <= 0:
            continue
        lines_out.append(
            {
                "line_no": i * 10,
                "raw_code": raw_code,
                "raw_name": raw_name,
                "brand": str(line.get("brand") or "").strip(),
                "model": str(line.get("model") or "").strip(),
                "qty": qty,
                "ui": str(line.get("ui") or "").strip(),
                "cost": cost,
                "discount": discount,
                "amount": amount,
                "confidence": max(0.0, min(1.0, _as_float(line.get("confidence"), 0.5))),
            }
        )
    bill_date = str(raw.get("bill_date") or "").strip()[:10]
    if bill_date and not re.match(r"^\d{4}-\d{2}-\d{2}$", bill_date):
        bill_date = ""
    return {
        "vendor_name": str(raw.get("vendor_name") or "").strip(),
        "vendor_billno": str(raw.get("vendor_billno") or raw.get("billno") or "").strip(),
        "bill_date": bill_date,
        "pay_method": str(raw.get("pay_method") or "").strip(),
        "subtotal": _as_float(raw.get("subtotal")),
        "discount": _as_float(raw.get("discount")),
        "vat": _as_float(raw.get("vat") or raw.get("tax")),
        "net": _as_float(raw.get("net") or raw.get("total")),
        "lines": lines_out,
        "warnings": [str(w) for w in (raw.get("warnings") or []) if w],
    }


def _default_model() -> str:
    settings = get_hq_receive_settings()
    return (
        (settings.hq_receive_ai_model or "").strip()
        or os.getenv("OPENAI_VISION_MODEL", "").strip()
        or os.getenv("OPENAI_MODEL", "").strip()
        or "gpt-5"
    )


def extract_invoice_from_image(
    image_bytes: bytes,
    *,
    content_type: str | None = None,
    vendor_acctno: str = "",
    file_name: str = "",
    actor: str = "",
    model: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    if not image_bytes:
        raise HqReceiveError("empty_image", "ไฟล์บิลว่าง")

    mime = (content_type or "image/jpeg").split(";")[0].strip() or "image/jpeg"
    if mime == "application/pdf":
        raise HqReceiveError(
            "pdf_unsupported",
            "ตอนนี้รองรับรูป JPG/PNG — แปลง PDF เป็นรูปก่อน หรือคีย์มือ",
        )

    sha = hashlib.sha256(image_bytes).hexdigest()
    extraction_id = str(uuid.uuid4())
    structured: dict[str, Any]
    usage: dict[str, Any] = {}
    raw_text = ""

    empty = {
        "vendor_name": "",
        "vendor_billno": "",
        "bill_date": date.today().isoformat(),
        "pay_method": "",
        "subtotal": 0,
        "discount": 0,
        "vat": 0,
        "net": 0,
        "lines": [],
        "warnings": [],
    }
    try:
        from src.ai.openai_client import OPENAI_API_KEY as _MODULE_KEY
    except Exception:
        _MODULE_KEY = ""
    api_key = (os.getenv("OPENAI_API_KEY") or _MODULE_KEY or "").strip()
    if not api_key:
        structured = {
            **empty,
            "warnings": [
                "ยังไม่ได้ตั้ง OPENAI_API_KEY — สร้าง extraction ว่างให้คีย์มือ / อัปโหลดใหม่ทีหลัง"
            ],
        }
    else:
        try:
            b64 = base64.b64encode(image_bytes).decode("ascii")
            image_url = f"data:{mime};base64,{b64}"
            client = get_openai_client()
            resp = client.responses.create(
                model=(model or _default_model()),
                reasoning={"effort": "none"},
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": INVOICE_EXTRACT_PROMPT}],
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "input_text",
                                "text": (
                                    "Extract this vendor purchase invoice for HQ goods receive. "
                                    f"Hint vendor acctno={vendor_acctno or '-'}. Return JSON only."
                                ),
                            },
                            {"type": "input_image", "image_url": image_url},
                        ],
                    },
                ],
                timeout=timeout,
            )
            raw_text = extract_text_from_response(resp)
            usage = extract_usage_from_response(resp)
            structured = _normalize_structured(_safe_parse_json(raw_text))
        except Exception as exc:
            logger.exception("hq_receive_invoice_extract_failed")
            # Keep receiving usable without AI (manual path).
            structured = {
                **empty,
                "warnings": [f"อ่านบิลไม่สำเร็จ — ใช้คีย์มือได้: {exc}"],
            }

    confidences = [float(ln.get("confidence") or 0) for ln in structured.get("lines") or []]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
    row = {
        "extraction_id": extraction_id,
        "vendor_acctno": (vendor_acctno or "").strip(),
        "file_name": file_name or "",
        "content_type": mime,
        "file_sha256": sha,
        "raw_text": raw_text[:20000],
        "structured": structured,
        "confidence": round(avg_conf, 4),
        "created_by": actor,
        "usage": usage,
        "lines": structured.get("lines") or [],
    }
    _MEMORY_EXTRACTIONS[extraction_id] = row
    try:
        from src.hq_receive import db as receive_db

        receive_db.save_extraction(row)
    except Exception:
        logger.exception("hq_receive_save_extraction_failed")
        row["_storage"] = "memory"
    else:
        row["_storage"] = row.get("_storage") or "supabase"
    return row


def get_extraction(extraction_id: str) -> dict[str, Any]:
    eid = str(extraction_id or "").strip()
    if eid in _MEMORY_EXTRACTIONS:
        return dict(_MEMORY_EXTRACTIONS[eid])
    try:
        from src.hq_receive import db as receive_db

        return receive_db.get_extraction(eid)
    except Exception as exc:
        raise HqReceiveError("not_found", "ไม่พบผลอ่านบิล") from exc


def _score_match(invoice_line: dict[str, Any], open_line: dict[str, Any]) -> float:
    inv_code = _norm_code(str(invoice_line.get("raw_code") or ""))
    open_code = _norm_code(str(open_line.get("bcode") or ""))
    score = 0.0
    if inv_code and open_code and inv_code == open_code:
        score += 0.7
    elif inv_code and open_code and (inv_code in open_code or open_code in inv_code):
        score += 0.45
    inv_name = " ".join(
        [
            str(invoice_line.get("raw_name") or ""),
            str(invoice_line.get("brand") or ""),
            str(invoice_line.get("model") or ""),
        ]
    ).strip().lower()
    open_name = " ".join(
        [
            str(open_line.get("descr") or ""),
            str(open_line.get("mcode") or ""),
            str(open_line.get("bcode") or ""),
        ]
    ).strip().lower()
    if inv_name and open_name:
        score += 0.3 * SequenceMatcher(None, inv_name, open_name).ratio()
    if not qty_mismatch(open_line.get("qty"), invoice_line.get("qty")):
        score += 0.05
    return min(1.0, score)


def match_extraction_to_open(
    extraction_id: str,
    *,
    vendor_acctno: str = "",
    min_score: float = 0.55,
) -> dict[str, Any]:
    extraction = get_extraction(extraction_id)
    acct = (vendor_acctno or extraction.get("vendor_acctno") or "").strip()
    open_lines = list_open_lines(acctno=acct) if acct else list_open_lines()
    used: set[int] = set()
    matched: list[dict[str, Any]] = []
    discrepancies: list[dict[str, Any]] = []

    for inv in extraction.get("lines") or extraction.get("structured", {}).get("lines") or []:
        best = None
        best_score = 0.0
        for open_line in open_lines:
            iclow_id = int(open_line.get("iclow_id") or 0)
            if iclow_id in used:
                continue
            score = _score_match(inv, open_line)
            if score > best_score:
                best_score = score
                best = open_line
        row: dict[str, Any]
        if best and best_score >= min_score:
            used.add(int(best["iclow_id"]))
            qty = _as_float(inv.get("qty"), _as_float(best.get("qty")))
            cost = _as_float(inv.get("cost"))
            flags = classify_line(
                open_qty=_as_float(best.get("qty")),
                receive_qty=qty,
                open_cost=None,
                receive_cost=cost or None,
                known_product=True,
            )
            if cost_mismatch(None, None):
                pass
            if qty_mismatch(best.get("qty"), qty):
                kind = "over_po" if qty > float(best.get("qty") or 0) else "under_po"
                discrepancies.append(
                    {
                        "kind": kind,
                        "bcode": best.get("bcode"),
                        "iclow_id": best.get("iclow_id"),
                        "detail": {
                            "open_qty": best.get("qty"),
                            "invoice_qty": qty,
                            "score": best_score,
                        },
                    }
                )
            row = {
                "iclow_id": best.get("iclow_id"),
                "bcode": best.get("bcode"),
                "descr": best.get("descr") or inv.get("raw_name") or "",
                "qty": qty,
                "ui": inv.get("ui") or best.get("ui") or "",
                "cost": cost,
                "discount": _as_float(inv.get("discount")),
                "amount": _as_float(inv.get("amount")),
                "po_docno": best.get("hq_po_docno") or best.get("docno") or "",
                "status": "hold" if "over_po" in flags["flags"] else flags["status"],
                "match_score": round(best_score, 4),
                "invoice_raw_code": inv.get("raw_code"),
                "invoice_raw_name": inv.get("raw_name"),
                "flags": flags["flags"],
            }
        else:
            discrepancies.append(
                {
                    "kind": "unknown_product",
                    "bcode": inv.get("raw_code") or "",
                    "iclow_id": None,
                    "detail": {
                        "raw_name": inv.get("raw_name"),
                        "qty": inv.get("qty"),
                        "best_score": best_score,
                    },
                }
            )
            row = {
                "iclow_id": None,
                "bcode": str(inv.get("raw_code") or "").strip(),
                "descr": inv.get("raw_name") or "",
                "qty": _as_float(inv.get("qty")),
                "ui": inv.get("ui") or "",
                "cost": _as_float(inv.get("cost")),
                "discount": _as_float(inv.get("discount")),
                "amount": _as_float(inv.get("amount")),
                "po_docno": "",
                "status": "hold" if not str(inv.get("raw_code") or "").strip() else "mismatch",
                "match_score": round(best_score, 4),
                "invoice_raw_code": inv.get("raw_code"),
                "invoice_raw_name": inv.get("raw_name"),
                "flags": ["unknown_product"],
            }
        matched.append(row)

    header = extraction.get("structured") or {}
    return {
        "extraction_id": extraction_id,
        "vendor_acctno": acct,
        "header": {
            "vendor_name": header.get("vendor_name") or extraction.get("vendor_name"),
            "vendor_billno": header.get("vendor_billno"),
            "bill_date": header.get("bill_date"),
            "subtotal": header.get("subtotal"),
            "discount": header.get("discount"),
            "vat": header.get("vat"),
            "net": header.get("net"),
            "pay_method": header.get("pay_method"),
        },
        "lines": matched,
        "discrepancies": discrepancies,
        "unmatched_open": [
            ln for ln in open_lines if int(ln.get("iclow_id") or 0) not in used
        ],
    }

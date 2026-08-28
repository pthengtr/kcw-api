from __future__ import annotations

import base64
import json
import logging
import os
import re
from typing import Any

from src.ai.openai_client import (
    extract_text_from_response,
    extract_usage_from_response,
    get_openai_client,
)

logger = logging.getLogger("kcw.pay_notes.ai_vision")

AMOUNT_TOLERANCE = 0.01
AUTO_ASSIGN_SCORE = 70

BILL_LINES_SYSTEM_PROMPT = """
You extract purchase bill / invoice rows from images for a Thai auto-parts AP clerk.

Return JSON only. No markdown fences.

Schema:
{
  "lines": [{"billno": string, "amount": number}],
  "total_amount": number,
  "warnings": [string]
}

Rules:
- One object per bill/invoice row on the document (not product line items inside a bill).
- "billno" = invoice/bill number as printed (preserve Thai/alphanumeric).
- "amount" = amount for that bill row (after tax if that's what is shown).
- "total_amount" = document grand total if visible (ยอดรวม / จำนวนเงินรวม).
- Do not invent rows. Skip unreadable rows and add a warning.
- If no bill table found: {"lines": [], "total_amount": 0, "warnings": ["no bills detected"]}
""".strip()

PAYMENT_VERIFY_SYSTEM_PROMPT = """
You read Thai bank transfer payment slip images for accounts payable verification.

Return JSON only. No markdown fences.

Schema:
{
  "extracted_amount": number,
  "transfer_date": string,
  "reference": string,
  "warnings": [string]
}

Rules:
- Read the **transfer amount / จำนวนเงินที่โอน / amount debited** only.
- Ignore account balance, available balance, and reference-only numbers.
- If multiple amounts appear, use the main transfer/debit amount.
- Use 0 for extracted_amount if unreadable and add a warning.
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
        logger.exception("ai_vision_json_parse_failed raw=%s", cleaned[:500])
    return {"error": "invalid_json", "warnings": ["Could not parse model output as JSON"]}


def normalize_billno(value: str) -> str:
    text = (value or "").strip().upper()
    return re.sub(r"[\s\-_/\\.]", "", text)


def amounts_match(a: float, b: float, *, tolerance: float = AMOUNT_TOLERANCE) -> bool:
    return abs(round(float(a or 0) - float(b or 0), 2)) <= tolerance


def compare_payment_amounts(extracted: float, expected: float) -> dict[str, Any]:
    diff = round(float(extracted or 0) - float(expected or 0), 2)
    return {
        "extracted_amount": round(float(extracted or 0), 2),
        "expected_amount": round(float(expected or 0), 2),
        "difference": diff,
        "match": amounts_match(extracted, expected),
    }


def _score_pair(
    extracted_billno: str,
    extracted_amount: float,
    candidate_billno: str,
    candidate_amount: float,
) -> tuple[int, str]:
    en = normalize_billno(extracted_billno)
    cn = normalize_billno(candidate_billno)
    amount_ok = amounts_match(extracted_amount, candidate_amount)
    if not en and not amount_ok:
        return 0, ""
    if en and cn and en == cn and amount_ok:
        return 100, "amount+billno"
    if amount_ok and en and cn and (en.endswith(cn) or cn.endswith(en) or en in cn or cn in en):
        return 80, "amount+billno"
    if amount_ok:
        return 70, "amount"
    if en and cn and en == cn:
        return 50, "billno"
    if en and cn and (en.endswith(cn) or cn.endswith(en)):
        return 45, "billno"
    return 0, ""


MATCH_REASON_LABELS = {
    "amount+billno": "เลขบิล + ยอด",
    "amount": "ยอดตรง (เลขบิลไม่ตรง)",
    "billno": "เลขบิลตรง (ยอดไม่ตรง)",
    "manual": "เลือกเอง",
}


def match_bill_lines(
    extracted_lines: list[dict[str, Any]],
    pickable_bills: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = [
        {
            "billno": str(b.get("BILLNO") or "").strip(),
            "aftertax": round(float(b.get("AFTERTAX") or 0), 2),
        }
        for b in pickable_bills
        if str(b.get("BILLNO") or "").strip()
    ]
    slots = []
    for raw in extracted_lines or []:
        if not isinstance(raw, dict):
            continue
        billno = str(raw.get("billno") or "").strip()
        try:
            amount = round(float(raw.get("amount") or 0), 2)
        except (TypeError, ValueError):
            amount = 0.0
        if billno or amount > 0:
            slots.append({"billno": billno, "amount": amount})

    pairs: list[tuple[int, int, int, str]] = []
    for si, slot in enumerate(slots):
        for ci, cand in enumerate(candidates):
            score, match_type = _score_pair(
                slot["billno"], slot["amount"], cand["billno"], cand["aftertax"]
            )
            if score > 0:
                pairs.append((score, si, ci, match_type))
    pairs.sort(key=lambda x: (-x[0], x[1], x[2]))

    used_slots: set[int] = set()
    used_cands: set[int] = set()
    assignments: dict[int, tuple[int, int, str]] = {}

    for score, si, ci, match_type in pairs:
        if si in used_slots or ci in used_cands:
            continue
        if score < AUTO_ASSIGN_SCORE:
            continue
        # Do not auto-assign when multiple candidates tie for this slot at the same score.
        tied = sum(
            1
            for sc, s2, c2, _ in pairs
            if s2 == si and sc == score and c2 not in used_cands and sc >= AUTO_ASSIGN_SCORE
        )
        if tied > 1:
            continue
        assignments[si] = (ci, score, match_type)
        used_slots.add(si)
        used_cands.add(ci)

    line_results: list[dict[str, Any]] = []
    auto_selected: list[str] = []
    ambiguous_extracted: list[str] = []
    unmatched_extracted: list[str] = []

    for si, slot in enumerate(slots):
        if si in assignments:
            ci, score, match_type = assignments[si]
            cand = candidates[ci]
            auto_selected.append(cand["billno"])
            line_results.append(
                {
                    "extracted": dict(slot),
                    "matched": {
                        "billno": cand["billno"],
                        "aftertax": cand["aftertax"],
                        "match": match_type,
                        "match_label": MATCH_REASON_LABELS.get(match_type, match_type),
                        "confidence": "high" if score >= 80 else "medium",
                        "score": score,
                    },
                    "status": "matched",
                }
            )
            continue

        near = []
        for ci, cand in enumerate(candidates):
            if ci in used_cands:
                continue
            score, match_type = _score_pair(
                slot["billno"], slot["amount"], cand["billno"], cand["aftertax"]
            )
            if score >= 45:
                near.append(
                    {
                        "billno": cand["billno"],
                        "aftertax": cand["aftertax"],
                        "score": score,
                        "match": match_type,
                    }
                )
        near.sort(key=lambda x: -x["score"])

        status = "unmatched"
        if len(near) > 1 and near[0]["score"] == near[1]["score"]:
            status = "ambiguous"
            ambiguous_extracted.append(slot["billno"] or f"line-{si + 1}")
        elif not near:
            unmatched_extracted.append(slot["billno"] or f"line-{si + 1}")

        line_results.append(
            {
                "extracted": dict(slot),
                "matched": None,
                "status": status,
                "candidates": near[:5],
            }
        )

    selected_total = round(
        sum(float(ln["matched"]["aftertax"]) for ln in line_results if ln.get("matched")),
        2,
    )
    slot_sum = round(sum(float(s["amount"]) for s in slots), 2)
    extracted_total = slot_sum

    total_match = amounts_match(extracted_total, selected_total) if auto_selected else False
    if slots and not auto_selected:
        total_match = False

    return {
        "lines": line_results,
        "auto_selected_billnos": auto_selected,
        "ambiguous": ambiguous_extracted,
        "unmatched": unmatched_extracted,
        "extracted_total": extracted_total,
        "selected_total": selected_total,
        "total_match": total_match,
        "total_difference": round(extracted_total - selected_total, 2),
        "warnings": [],
    }


def _vision_extract(
    *,
    image_bytes: bytes,
    content_type: str | None,
    system_prompt: str,
    user_text: str,
    model: str,
    timeout: float,
) -> dict[str, Any]:
    if not image_bytes:
        return {"error": "empty_image", "warnings": ["Image is empty"]}

    mime = (content_type or "image/jpeg").split(";")[0].strip() or "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    image_url = f"data:{mime};base64,{b64}"

    client = get_openai_client()
    resp = client.responses.create(
        model=model,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_text},
                    {"type": "input_image", "image_url": image_url},
                ],
            },
        ],
        timeout=timeout,
    )
    raw_text = extract_text_from_response(resp)
    parsed = _safe_parse_json(raw_text)
    parsed["usage"] = extract_usage_from_response(resp)
    return parsed


def extract_bill_lines_from_image(
    image_bytes: bytes,
    content_type: str | None = None,
    *,
    model: str | None = None,
    timeout: float = 45.0,
) -> dict[str, Any]:
    data = _vision_extract(
        image_bytes=image_bytes,
        content_type=content_type,
        system_prompt=BILL_LINES_SYSTEM_PROMPT,
        user_text=(
            "Extract bill/invoice rows from this vendor document. "
            "One row per bill with billno and amount. Return JSON only."
        ),
        model=(model or os.getenv("PAY_NOTES_AI_MODEL") or "gpt-4o-mini").strip(),
        timeout=timeout,
    )
    if data.get("error"):
        return {
            "lines": [],
            "total_amount": 0.0,
            "warnings": list(data.get("warnings") or [str(data.get("error"))]),
            "usage": data.get("usage") or {},
        }

    lines: list[dict[str, Any]] = []
    for raw in data.get("lines") or []:
        if not isinstance(raw, dict):
            continue
        billno = str(raw.get("billno") or "").strip()
        try:
            amount = round(float(raw.get("amount") or 0), 2)
        except (TypeError, ValueError):
            amount = 0.0
        lines.append({"billno": billno, "amount": amount})

    try:
        total_amount = round(float(data.get("total_amount") or 0), 2)
    except (TypeError, ValueError):
        total_amount = 0.0
    if not total_amount and lines:
        total_amount = round(sum(ln["amount"] for ln in lines), 2)

    warnings = [str(w).strip() for w in (data.get("warnings") or []) if str(w).strip()]
    return {
        "lines": lines,
        "total_amount": total_amount,
        "warnings": warnings,
        "usage": data.get("usage") or {},
    }


def verify_payment_from_image(
    image_bytes: bytes,
    content_type: str | None,
    *,
    expected_amount: float,
    model: str | None = None,
    timeout: float = 45.0,
) -> dict[str, Any]:
    data = _vision_extract(
        image_bytes=image_bytes,
        content_type=content_type,
        system_prompt=PAYMENT_VERIFY_SYSTEM_PROMPT,
        user_text=(
            "Read the transfer amount from this Thai bank payment slip. "
            "Return JSON with extracted_amount only for the amount transferred."
        ),
        model=(model or os.getenv("PAY_NOTES_AI_MODEL") or "gpt-4o-mini").strip(),
        timeout=timeout,
    )
    warnings = [str(w).strip() for w in (data.get("warnings") or []) if str(w).strip()]
    if data.get("error"):
        return {
            **compare_payment_amounts(0, expected_amount),
            "confidence": "low",
            "transfer_date": "",
            "reference": "",
            "warnings": warnings or [str(data.get("error"))],
            "usage": data.get("usage") or {},
        }

    try:
        extracted = round(float(data.get("extracted_amount") or 0), 2)
    except (TypeError, ValueError):
        extracted = 0.0

    result = compare_payment_amounts(extracted, expected_amount)
    result.update(
        {
            "confidence": "high" if extracted > 0 else "low",
            "transfer_date": str(data.get("transfer_date") or "").strip(),
            "reference": str(data.get("reference") or "").strip(),
            "warnings": warnings,
            "usage": data.get("usage") or {},
        }
    )
    return result

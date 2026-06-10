import base64
import json
import logging
import os
import re
from typing import Any

from src.ai.openai_client import extract_text_from_response, get_openai_client

logger = logging.getLogger("kcw.table_extractor")

TABLE_EXTRACT_MODEL = os.getenv("TABLE_EXTRACT_MODEL", "gpt-4o-mini").strip()
TABLE_EXTRACT_TIMEOUT_SECONDS = float(
    os.getenv("TABLE_EXTRACT_TIMEOUT_SECONDS", "60").strip()
)

SYSTEM_PROMPT = """
You extract tabular data from images for a Thai auto-parts shop.

Return JSON only. No markdown fences.

Schema:
{
  "title": string,
  "columns": [string],
  "rows": [object],
  "warnings": [string]
}

Rules:
- Preserve Thai text exactly. Do not translate.
- Detect column headers from the image when possible.
- Each row object must use the detected column names as keys.
- Prefer these columns when they appear: ลำดับ, รหัส, รายละเอียด, จำนวน, หน่วย, ราคา, หมายเหตุ
- If a cell is unreadable, use "" and add a warning.
- Do not invent values that are not visible in the image.
- If no table is found, return:
  {"error": "no_table_detected", "title": "", "columns": [], "rows": [], "warnings": ["no table detected"]}
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
        logger.exception("table_extract_json_parse_failed raw=%s", cleaned[:500])

    return {
        "error": "invalid_json",
        "title": "",
        "columns": [],
        "rows": [],
        "warnings": ["Could not parse model output as JSON"],
    }


def _normalize_result(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("error"):
        return {
            "error": str(data.get("error")),
            "title": "",
            "columns": [],
            "rows": [],
            "warnings": list(data.get("warnings") or []),
        }

    columns = [str(c).strip() for c in (data.get("columns") or []) if str(c).strip()]
    rows = []
    for row in data.get("rows") or []:
        if not isinstance(row, dict):
            continue
        normalized_row = {}
        for key, value in row.items():
            key_text = str(key).strip()
            if not key_text:
                continue
            normalized_row[key_text] = "" if value is None else str(value).strip()
        if normalized_row:
            rows.append(normalized_row)

    if not columns and rows:
        columns = list(rows[0].keys())

    warnings = [str(w).strip() for w in (data.get("warnings") or []) if str(w).strip()]

    return {
        "title": str(data.get("title") or "").strip(),
        "columns": columns,
        "rows": rows,
        "warnings": warnings,
    }


def extract_table_from_image(image_bytes: bytes, content_type: str | None = None) -> dict[str, Any]:
    if not image_bytes:
        return {
            "error": "empty_image",
            "title": "",
            "columns": [],
            "rows": [],
            "warnings": ["Image is empty"],
        }

    mime = (content_type or "image/jpeg").split(";")[0].strip() or "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode("ascii")
    image_url = f"data:{mime};base64,{b64}"

    client = get_openai_client()
    resp = client.responses.create(
        model=TABLE_EXTRACT_MODEL,
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": SYSTEM_PROMPT}],
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": "Extract the table from this image.",
                    },
                    {
                        "type": "input_image",
                        "image_url": image_url,
                    },
                ],
            },
        ],
        timeout=TABLE_EXTRACT_TIMEOUT_SECONDS,
    )

    raw_text = extract_text_from_response(resp)
    parsed = _safe_parse_json(raw_text)
    return _normalize_result(parsed)

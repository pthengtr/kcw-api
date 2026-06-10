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
from src.printout.schema import TABLE_COLUMNS, normalize_rows

logger = logging.getLogger("kcw.table_extractor")

TABLE_EXTRACT_MODEL = os.getenv("TABLE_EXTRACT_MODEL", "gpt-4o-mini").strip()
TABLE_EXTRACT_TIMEOUT_SECONDS = float(
    os.getenv("TABLE_EXTRACT_TIMEOUT_SECONDS", "60").strip()
)

_COLUMNS_JSON = json.dumps(TABLE_COLUMNS, ensure_ascii=False)

SYSTEM_PROMPT = f"""
You extract tabular data from images for a Thai auto-parts shop.

Return JSON only. No markdown fences.

Schema:
{{
  "title": string,
  "columns": {_COLUMNS_JSON},
  "rows": [object],
  "warnings": [string]
}}

Rules:
- "columns" must be exactly this list in this order: {_COLUMNS_JSON}
- Each row object must use exactly these keys: {_COLUMNS_JSON}
- Preserve Thai text exactly. Do not translate.
- รหัสสินค้า = product code / bcode
- ชื่อสินค้า = product name / description
- แบบ = model or type
- No.1 and No.2 = part numbers, OEM numbers, or reference numbers from the table (keep as shown)
- ยี่ห้อ = brand
- จำนวน = quantity
- หน่วย = unit (ชิ้น, ตัว, ชุด, etc.)
- If a cell is unreadable or missing, use "" and add a warning with row context.
- Do not invent values that are not visible in the image.
- Skip completely empty rows.
- If no table is found, return:
  {{"error": "no_table_detected", "title": "", "columns": [], "rows": [], "warnings": ["no table detected"]}}
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

    rows = normalize_rows(data.get("rows") or [])
    warnings = [str(w).strip() for w in (data.get("warnings") or []) if str(w).strip()]

    result = {
        "title": str(data.get("title") or "").strip(),
        "columns": list(TABLE_COLUMNS),
        "rows": rows,
        "warnings": warnings,
    }
    usage = data.get("usage")
    if isinstance(usage, dict) and usage.get("total_tokens"):
        result["usage"] = usage
    return result


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
                        "text": (
                            "Extract every data row from this table image. "
                            f"Use only these columns in order: {_COLUMNS_JSON}"
                        ),
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
    parsed["usage"] = extract_usage_from_response(resp)
    return _normalize_result(parsed)

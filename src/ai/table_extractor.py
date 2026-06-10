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
from src.printout.schema import EXTRACTION_COLUMNS, normalize_rows

logger = logging.getLogger("kcw.table_extractor")

TABLE_EXTRACT_MODEL = os.getenv("TABLE_EXTRACT_MODEL", "gpt-4o-mini").strip()
TABLE_EXTRACT_TIMEOUT_SECONDS = float(
    os.getenv("TABLE_EXTRACT_TIMEOUT_SECONDS", "60").strip()
)

_COLUMNS_JSON = json.dumps(EXTRACTION_COLUMNS, ensure_ascii=False)

SYSTEM_PROMPT = f"""
You extract tabular data from images for a Thai auto-parts shop.

Return JSON only. No markdown fences.

Expected input table in the image:
The image is usually a Thai auto-parts pick/order list with a table like:

| รหัสสินค้า | ชื่อสินค้า | แบบ | No.1 | No.2 | ยี่ห้อ | จำนวน | หน่วย |

Columns that MAY appear in the image but must NOT be extracted:
- ชื่อสินค้า, แบบ, No.1, No.2, ยี่ห้อ
- These will be filled later from the database using รหัสสินค้า.

Columns you MUST read from each data row:
- รหัสสินค้า — product code / BCODE (required)
- จำนวน — quantity ordered or picked (required)
- หน่วย — unit of measure such as ชิ้น, ตัว, ชุด (required)

Map image headers to output even if labels differ:
- รหัสสินค้า: may appear as รหัส, bcode, code
- จำนวน: may appear as qty, quantity
- หน่วย: may appear as unit

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
- Extract DATA ROWS ONLY.
- SKIP all document headers, titles, subtitles, page headers, and footer text.
- SKIP the table column-header row.
- NEVER include header labels as data rows.
- If the image has a document title, put it in "title" only, not in "rows".
- Preserve Thai text exactly. Do not translate.
- If a cell is unreadable or missing, use "" and add a warning with row context.
- Do not invent values that are not visible in the image.
- Keep "rows" in the exact top-to-bottom order shown in the image.
- Never sort, reorder, or group rows.
- If a row is unreadable, skip it and add a warning; do not shift other rows.
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
        "columns": list(EXTRACTION_COLUMNS),
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
                            "Extract only product/data rows from this table image. "
                            "The source table may have many columns, but read only "
                            "ลำดับ, รหัสสินค้า, จำนวน, and หน่วย from each row. "
                            "Do not extract ชื่อสินค้า, แบบ, No.1, No.2, or ยี่ห้อ. "
                            "Return rows in exact top-to-bottom image order. "
                            "Skip document headers and skip the column-header row. "
                            f"Use only these output columns in order: {_COLUMNS_JSON}"
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

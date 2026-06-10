import logging
import os
import re
from typing import Any

from sqlalchemy import bindparam, text

logger = logging.getLogger("kcw.printout.enrich")

from src.printout.schema import BLANK_OUTPUT_COLUMNS

BCODE_COLUMN = "รหัสสินค้า"
LOCATION1_COLUMN = "location1"
_SAFE_IDENT = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

TABLE_PRINTOUT_PRODUCT_TABLE = os.getenv(
    "TABLE_PRINTOUT_PRODUCT_TABLE",
    "raw_kcw.raw_hq_icmas_products",
).strip()


def _product_table_ref() -> tuple[str, str]:
    ref = TABLE_PRINTOUT_PRODUCT_TABLE
    if "." not in ref:
        raise ValueError(f"Invalid TABLE_PRINTOUT_PRODUCT_TABLE: {ref}")

    schema, table = ref.split(".", 1)
    if not _SAFE_IDENT.match(schema) or not _SAFE_IDENT.match(table):
        raise ValueError(f"Invalid TABLE_PRINTOUT_PRODUCT_TABLE: {ref}")

    return schema, table


def get_location1_by_bcodes(engine, bcodes: list[str]) -> dict[str, str]:
    cleaned = list(dict.fromkeys(b.strip() for b in bcodes if b and str(b).strip()))
    if not cleaned:
        return {}

    schema, table = _product_table_ref()
    sql = text(f"""
        SELECT DISTINCT ON (trim("BCODE"))
            trim("BCODE") AS bcode,
            nullif(trim(cast("LOCATION1" AS text)), '') AS location1
        FROM "{schema}"."{table}"
        WHERE trim("BCODE") IN :bcodes
        ORDER BY trim("BCODE"), _ingested_at DESC NULLS LAST
    """).bindparams(bindparam("bcodes", expanding=True))

    with engine.connect() as conn:
        rows = conn.execute(sql, {"bcodes": cleaned}).mappings().all()

    return {
        str(row["bcode"]): str(row["location1"] or "").strip()
        for row in rows
        if row.get("bcode")
    }


def enrich_printout_rows(engine, extracted: dict[str, Any]) -> dict[str, Any]:
    if extracted.get("error"):
        return extracted

    rows = extracted.get("rows") or []
    if not rows:
        return {**extracted, "enriched": True}

    bcodes = [
        str(row.get(BCODE_COLUMN) or "").strip()
        for row in rows
        if isinstance(row, dict)
    ]

    try:
        location_map = get_location1_by_bcodes(engine, bcodes)
    except Exception:
        logger.exception("printout_location_enrich_failed")
        warnings = list(extracted.get("warnings") or [])
        warnings.append("ไม่สามารถดึงข้อมูลที่เก็บจากระบบได้ชั่วคราว")
        return {**extracted, "warnings": warnings, "enriched": False}

    warnings = list(extracted.get("warnings") or [])
    enriched_rows = []

    for row in rows:
        if not isinstance(row, dict):
            continue

        bcode = str(row.get(BCODE_COLUMN) or "").strip()
        location1 = location_map.get(bcode, "")

        if bcode and not location1:
            warnings.append(f"ไม่พบที่เก็บสำหรับรหัสสินค้า {bcode}")

        enriched_row = dict(row)
        enriched_row[LOCATION1_COLUMN] = location1
        for col in BLANK_OUTPUT_COLUMNS:
            enriched_row[col] = ""
        enriched_rows.append(enriched_row)

    return {
        **extracted,
        "rows": enriched_rows,
        "warnings": warnings,
        "enriched": True,
    }

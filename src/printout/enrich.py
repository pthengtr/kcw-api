import logging
import os
import re
from typing import Any

from sqlalchemy import bindparam, text

logger = logging.getLogger("kcw.printout.enrich")

from src.printout.schema import BLANK_OUTPUT_COLUMNS, SEQ_COLUMN

BCODE_COLUMN = "รหัสสินค้า"
NAME_COLUMN = "ชื่อสินค้า"
MODEL_COLUMN = "แบบ"
BRAND_COLUMN = "ยี่ห้อ"
QTY_COLUMN = "จำนวน"
UNIT_COLUMN = "หน่วย"
LOCATION1_COLUMN = "location1"
LOCATION2_COLUMN = "location2"
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


def get_products_by_bcodes(engine, bcodes: list[str]) -> dict[str, dict[str, str]]:
    cleaned = list(dict.fromkeys(b.strip() for b in bcodes if b and str(b).strip()))
    if not cleaned:
        return {}

    schema, table = _product_table_ref()
    sql = text(f"""
        SELECT DISTINCT ON (trim("BCODE"))
            trim("BCODE") AS bcode,
            nullif(trim(cast("DESCR" AS text)), '') AS descr,
            nullif(trim(cast("MODEL" AS text)), '') AS model,
            nullif(trim(cast("BRAND" AS text)), '') AS brand,
            nullif(trim(cast("LOCATION1" AS text)), '') AS location1,
            nullif(trim(cast("LOCATION2" AS text)), '') AS location2
        FROM "{schema}"."{table}"
        WHERE trim("BCODE") IN :bcodes
        ORDER BY trim("BCODE"), _ingested_at DESC NULLS LAST
    """).bindparams(bindparam("bcodes", expanding=True))

    with engine.connect() as conn:
        rows = conn.execute(sql, {"bcodes": cleaned}).mappings().all()

    result: dict[str, dict[str, str]] = {}
    for row in rows:
        bcode = str(row.get("bcode") or "").strip()
        if not bcode:
            continue
        result[bcode] = {
            NAME_COLUMN: str(row.get("descr") or "").strip(),
            MODEL_COLUMN: str(row.get("model") or "").strip(),
            BRAND_COLUMN: str(row.get("brand") or "").strip(),
            LOCATION1_COLUMN: str(row.get("location1") or "").strip(),
            LOCATION2_COLUMN: str(row.get("location2") or "").strip(),
        }
    return result


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
        product_map = get_products_by_bcodes(engine, bcodes)
    except Exception:
        logger.exception("printout_product_enrich_failed")
        warnings = list(extracted.get("warnings") or [])
        warnings.append("ไม่สามารถดึงข้อมูลสินค้าจากระบบได้ชั่วคราว")
        return {**extracted, "warnings": warnings, "enriched": False}

    warnings = list(extracted.get("warnings") or [])
    enriched_rows = []

    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue

        seq = str(row.get(SEQ_COLUMN) or "").strip() or str(index)
        bcode = str(row.get(BCODE_COLUMN) or "").strip()
        qty = str(row.get(QTY_COLUMN) or "").strip()
        unit = str(row.get(UNIT_COLUMN) or "").strip()
        product = product_map.get(bcode, {})

        if bcode and bcode not in product_map:
            warnings.append(f"ไม่พบข้อมูลสินค้าสำหรับรหัสสินค้า {bcode}")

        location1 = product.get(LOCATION1_COLUMN, "")
        location2 = product.get(LOCATION2_COLUMN, "")
        if bcode and bcode in product_map and not location1 and not location2:
            warnings.append(f"ไม่พบที่เก็บสำหรับรหัสสินค้า {bcode}")

        enriched_row = {
            SEQ_COLUMN: seq,
            BCODE_COLUMN: bcode,
            NAME_COLUMN: product.get(NAME_COLUMN, ""),
            MODEL_COLUMN: product.get(MODEL_COLUMN, ""),
            BRAND_COLUMN: product.get(BRAND_COLUMN, ""),
            QTY_COLUMN: qty,
            UNIT_COLUMN: unit,
            LOCATION1_COLUMN: location1,
            LOCATION2_COLUMN: location2,
        }
        for col in BLANK_OUTPUT_COLUMNS:
            enriched_row[col] = ""
        enriched_rows.append(enriched_row)

    return {
        **extracted,
        "rows": enriched_rows,
        "warnings": warnings,
        "enriched": True,
    }

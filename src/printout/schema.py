TABLE_COLUMNS = [
    "รหัสสินค้า",
    "ชื่อสินค้า",
    "แบบ",
    "No.1",
    "No.2",
    "ยี่ห้อ",
    "จำนวน",
    "หน่วย",
]

ENRICHMENT_COLUMNS = [
    "location1",
]

PRINTOUT_COLUMNS = TABLE_COLUMNS + ENRICHMENT_COLUMNS

PRINTOUT_COLUMN_LABELS = {
    "location1": "ที่เก็บ",
}

# Alternate header labels seen in source images → canonical column
COLUMN_ALIASES: dict[str, list[str]] = {
    "รหัสสินค้า": ["รหัสสินค้า", "รหัส", "bcode", "code", "รหัสสินค้า "],
    "ชื่อสินค้า": ["ชื่อสินค้า", "ชื่อ", "รายละเอียด", "สินค้า", "ชื่อสินค้า "],
    "แบบ": ["แบบ", "model", "รุ่น"],
    "No.1": ["No.1", "No. 1", "NO.1", "no.1", "No1", "หมายเลข 1"],
    "No.2": ["No.2", "No. 2", "NO.2", "no.2", "No2", "หมายเลข 2"],
    "ยี่ห้อ": ["ยี่ห้อ", "brand", "ยี่ห้อ "],
    "จำนวน": ["จำนวน", "qty", "quantity", "จำนวน "],
    "หน่วย": ["หน่วย", "unit", "หน่วย "],
}


def normalize_row(row: dict) -> dict[str, str]:
    if not isinstance(row, dict):
        return {col: "" for col in TABLE_COLUMNS}

    stripped = {
        str(key).strip(): "" if value is None else str(value).strip()
        for key, value in row.items()
        if str(key).strip()
    }

    normalized: dict[str, str] = {}
    for col in TABLE_COLUMNS:
        value = stripped.get(col, "")
        if not value:
            for alias in COLUMN_ALIASES.get(col, [col]):
                if alias in stripped and stripped[alias]:
                    value = stripped[alias]
                    break
        normalized[col] = value

    return normalized


def normalize_rows(rows: list) -> list[dict[str, str]]:
    result = []
    for row in rows or []:
        normalized = normalize_row(row)
        if any(normalized.values()):
            result.append(normalized)
    return result

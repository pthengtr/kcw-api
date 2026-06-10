SEQ_COLUMN = "ลำดับ"

# Columns read from the scanned image only
EXTRACTION_COLUMNS = [
    SEQ_COLUMN,
    "รหัสสินค้า",
    "จำนวน",
    "หน่วย",
]

# Full data columns shown on the printout (some filled from DB)
PRINTOUT_DATA_COLUMNS = [
    SEQ_COLUMN,
    "รหัสสินค้า",
    "ชื่อสินค้า",
    "แบบ",
    "ยี่ห้อ",
    "จำนวน",
    "หน่วย",
]

ENRICHMENT_COLUMNS = [
    "location1",
    "location2",
]

OUTPUT_ONLY_COLUMNS = [
    "picked",
]

PRINTOUT_COLUMNS = PRINTOUT_DATA_COLUMNS + ENRICHMENT_COLUMNS + OUTPUT_ONLY_COLUMNS

PRINTOUT_COLUMN_LABELS = {
    "location1": "ที่เก็บ 1",
    "location2": "ที่เก็บ 2",
    "picked": "จัดของแล้ว",
}

BLANK_OUTPUT_COLUMNS = {
    "picked",
}

EXTRACTION_COLUMN_ALIASES: dict[str, list[str]] = {
    SEQ_COLUMN: [SEQ_COLUMN, "ลำดับที่", "no.", "no", "#"],
    "รหัสสินค้า": ["รหัสสินค้า", "รหัส", "bcode", "code"],
    "จำนวน": ["จำนวน", "qty", "quantity"],
    "หน่วย": ["หน่วย", "unit"],
}

# Header labels that may appear in source images but are not extracted
SOURCE_HEADER_LABELS = [
    SEQ_COLUMN,
    "ลำดับที่",
    "no.",
    "no",
    "ชื่อสินค้า",
    "ชื่อ",
    "รายละเอียด",
    "สินค้า",
    "แบบ",
    "model",
    "รุ่น",
    "No.1",
    "No. 1",
    "NO.1",
    "no.1",
    "No1",
    "No.2",
    "No. 2",
    "NO.2",
    "no.2",
    "No2",
    "ยี่ห้อ",
    "brand",
]


def normalize_row(row: dict) -> dict[str, str]:
    if not isinstance(row, dict):
        return {col: "" for col in EXTRACTION_COLUMNS}

    stripped = {
        str(key).strip(): "" if value is None else str(value).strip()
        for key, value in row.items()
        if str(key).strip()
    }

    normalized: dict[str, str] = {}
    for col in EXTRACTION_COLUMNS:
        value = stripped.get(col, "")
        if not value:
            for alias in EXTRACTION_COLUMN_ALIASES.get(col, [col]):
                if alias in stripped and stripped[alias]:
                    value = stripped[alias]
                    break
        normalized[col] = value

    return normalized


def header_label_set() -> set[str]:
    labels = set(EXTRACTION_COLUMNS)
    labels.update(SOURCE_HEADER_LABELS)
    for aliases in EXTRACTION_COLUMN_ALIASES.values():
        labels.update(aliases)
    return {label.strip().casefold() for label in labels if label.strip()}


def is_header_or_column_row(row: dict[str, str]) -> bool:
    values = [
        str(value).strip().casefold()
        for value in row.values()
        if value is not None and str(value).strip()
    ]
    if not values:
        return False

    labels = header_label_set()
    seq = str(row.get(SEQ_COLUMN) or "").strip().casefold()
    if seq in labels:
        return True

    bcode = str(row.get("รหัสสินค้า") or "").strip().casefold()
    if bcode in labels:
        return True

    header_matches = sum(1 for value in values if value in labels)
    if header_matches >= 2:
        return True
    if header_matches == len(values):
        return True

    return False


def assign_row_sequence(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    sequenced = []
    for index, row in enumerate(rows, start=1):
        seq = str(row.get(SEQ_COLUMN) or "").strip() or str(index)
        ordered = {SEQ_COLUMN: seq}
        ordered.update({key: value for key, value in row.items() if key != SEQ_COLUMN})
        sequenced.append(ordered)
    return sequenced


def normalize_rows(rows: list) -> list[dict[str, str]]:
    result = []
    for row in rows or []:
        normalized = normalize_row(row)
        if not any(normalized.values()):
            continue
        if is_header_or_column_row(normalized):
            continue
        result.append(normalized)
    return assign_row_sequence(result)

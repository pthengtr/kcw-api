import re
import pandas as pd
from sqlalchemy import text

SEARCH_COLS = [
    "BCODE",
    "XCODE",
    "MCODE",
    "PCODE",
    "ACODE",
    "DESCR",
    "MODEL",
    "BRAND",
]

CODE1_KEYWORD_MAP = {
    "A": ["ถ่าน"],
    "C": ["ซีล"],
    "D": ["บูช", "บู๊ช", "บู๊ซ", "บู็ช", "บู็ซ"],
    "E": ["ลูกปืนเข็ม", "ลูกปืนกรงนก", "เข็ม", "กรงนก"],
    "F": ["ไส้กรองอากาศ", "กรองอากาศ"],
    "G": ["ยอยกากบาท", "ยอย"],
    "I": ["ลูกปืนตลับ", "ลูกปืน"],
    "K": ["จานคลัช", "คลัช"],
    "L": ["สายอ่อน"],
    "O": ["โอริง"],
    "P": ["ไส้กรองน้ำมันเครื่อง", "กรองน้ำมัน"],
    "Q": ["ลูกหมาก"],
    "R": ["ลูกยาง"],
}


def _normalize_text(text_value: str) -> str:
    s = str(text_value or "").strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s


def _extract_code1_and_remaining_tokens(query: str) -> tuple[str | None, list[str]]:
    raw = str(query or "").strip()
    if not raw:
        return None, []

    text_upper = _normalize_text(raw)
    text_lower = raw.lower()

    detected_code1 = None
    matched_keyword = None

    # 1) explicit CODE1: I, CODE1 I, CODE1:I
    m = re.search(r'(?<![A-Z0-9])CODE1\s*[:=]?\s*([A-Z])(?![A-Z0-9])', text_upper)
    if m:
        detected_code1 = m.group(1)

    # 2) bare single-letter prefix like "I 6201" or "O 35 3"
    if not detected_code1:
        m = re.match(r'^\s*([A-Z])\b', text_upper)
        if m and m.group(1) in CODE1_KEYWORD_MAP:
            detected_code1 = m.group(1)

    # 3) keyword detection — longest keyword first
    if not detected_code1:
        keyword_rows = []
        for code1, keywords in CODE1_KEYWORD_MAP.items():
            for kw in keywords:
                keyword_rows.append((kw, code1))

        keyword_rows.sort(key=lambda x: len(x[0]), reverse=True)

        for kw, code1 in keyword_rows:
            if kw.lower() in text_lower:
                detected_code1 = code1
                matched_keyword = kw
                break

    cleaned = raw

    # remove only the actually matched keyword, not all synonyms
    if matched_keyword:
        cleaned = re.sub(re.escape(matched_keyword), " ", cleaned, flags=re.IGNORECASE)

    # remove explicit CODE1 notation if present
    cleaned = re.sub(
        r'(?<![A-Za-z0-9])CODE1\s*[:=]?\s*[A-Za-z](?![A-Za-z0-9])',
        ' ',
        cleaned,
        flags=re.IGNORECASE,
    )

    # remove bare leading code1 if present, e.g. "I 6201"
    if detected_code1:
        cleaned = re.sub(
            rf'^\s*{re.escape(detected_code1)}\b',
            ' ',
            cleaned,
            flags=re.IGNORECASE,
        )

    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    tokens = [tk.strip().lower() for tk in cleaned.split() if tk.strip()]
    return detected_code1, tokens

def _extract_size_filters(query: str) -> tuple[dict[str, str], str]:
    raw = str(query or "").strip()
    if not raw:
        return {}, raw

    m = re.search(
        r"(?:^|\s)(ขนาด)\s+([^\s]+)(?:\s+([^\s]+))?(?:\s+([^\s]+))?",
        raw,
        flags=re.IGNORECASE,
    )
    if not m:
        return {}, raw

    slots = [m.group(2), m.group(3), m.group(4)]
    size_filters = {}

    for idx, value in enumerate(slots, start=1):
        if value is None:
            continue
        value = value.strip()
        if value == "-":
            continue
        size_filters[f"SIZE{idx}"] = value

    cleaned_query = (raw[:m.start()] + " " + raw[m.end():]).strip()
    cleaned_query = re.sub(r"\s+", " ", cleaned_query)
    return size_filters, cleaned_query


def _extract_bcode_category_prefix(query: str) -> tuple[str | None, str]:
    """
    Detect leading 2-digit BCODE category search.

    Examples:
    - "12" -> category 12, remaining ""
    - "12 ลูกปืน 6207" -> category 12, remaining "ลูกปืน 6207"
    - "22010585" -> no category, keep as normal BCODE search
    """
    raw = str(query or "").strip()
    if not raw:
        return None, raw

    m = re.match(r"^\s*(\d{2})(?=\s|$)", raw)
    if not m:
        return None, raw

    category_prefix = m.group(1)
    cleaned = (raw[:m.start()] + " " + raw[m.end():]).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)

    return category_prefix, cleaned

def simple_and_search_sql(
    engine,
    query: str,
    schema: str = "raw_kcw",
    table_name: str = "raw_hq_icmas_products",  # kept for compatibility, not used now
    limit: int = 5,
) -> dict:
    if not query or not str(query).strip():
        return {
            "items": pd.DataFrame(),
            "total": 0,
            "bcode_category_prefix": None,
        }

    bcode_category_prefix, query_wo_category = _extract_bcode_category_prefix(query)
    size_filters, query_wo_size = _extract_size_filters(query_wo_category)
    detected_code1, tokens = _extract_code1_and_remaining_tokens(query_wo_size)

    where_parts = []
    params = {}

    if bcode_category_prefix:
        where_parts.append('LEFT(TRIM(CAST(p."BCODE" AS TEXT)), 2) = :bcode_category_prefix')
        params["bcode_category_prefix"] = bcode_category_prefix

    if detected_code1:
        where_parts.append('UPPER(TRIM(COALESCE(p."CODE1", \'\'))) = :code1')
        params["code1"] = detected_code1

    for col, value in size_filters.items():
        param_key = col.lower()
        where_parts.append(f'TRIM(COALESCE(CAST(p."{col}" AS TEXT), \'\')) = :{param_key}')
        params[param_key] = str(value)

    for i, tk in enumerate(tokens):
        key = f"tk{i}"
        params[key] = f"%{tk}%"
        col_parts = [f'LOWER(CAST(p."{col}" AS TEXT)) LIKE :{key}' for col in SEARCH_COLS]
        where_parts.append("(" + " OR ".join(col_parts) + ")")

    if not where_parts:
        return {
            "items": pd.DataFrame(),
            "total": 0,
            "bcode_category_prefix": bcode_category_prefix,
        }

    where_sql = " AND ".join(where_parts)

    sql = f"""
    WITH hq_products AS (
        SELECT *
        FROM "{schema}"."raw_hq_icmas_products"
    ),
    syp_products AS (
        SELECT *
        FROM "{schema}"."raw_syp_icmas_products"
    ),
    merged_products AS (
        SELECT
            COALESCE(hq."BCODE", syp."BCODE") AS "BCODE",
            COALESCE(NULLIF(TRIM(hq."XCODE"), ''), NULLIF(TRIM(syp."XCODE"), '')) AS "XCODE",
            COALESCE(NULLIF(TRIM(hq."MCODE"), ''), NULLIF(TRIM(syp."MCODE"), '')) AS "MCODE",
            COALESCE(NULLIF(TRIM(hq."PCODE"), ''), NULLIF(TRIM(syp."PCODE"), '')) AS "PCODE",
            COALESCE(NULLIF(TRIM(hq."ACODE"), ''), NULLIF(TRIM(syp."ACODE"), '')) AS "ACODE",
            COALESCE(NULLIF(TRIM(hq."DESCR"), ''), NULLIF(TRIM(syp."DESCR"), '')) AS "DESCR",
            COALESCE(NULLIF(TRIM(hq."MODEL"), ''), NULLIF(TRIM(syp."MODEL"), '')) AS "MODEL",
            COALESCE(NULLIF(TRIM(hq."BRAND"), ''), NULLIF(TRIM(syp."BRAND"), '')) AS "BRAND",
            COALESCE(NULLIF(TRIM(hq."CODE1"), ''), NULLIF(TRIM(syp."CODE1"), '')) AS "CODE1",
            COALESCE(hq."SIZE1", syp."SIZE1") AS "SIZE1",
            COALESCE(hq."SIZE2", syp."SIZE2") AS "SIZE2",
            COALESCE(hq."SIZE3", syp."SIZE3") AS "SIZE3",
            COALESCE(hq."UI1", syp."UI1") AS "UI1",
            COALESCE(hq."UI2", syp."UI2") AS "UI2",
            COALESCE(hq."PRICE1", syp."PRICE1") AS "PRICE1",
            COALESCE(hq."PRICE2", syp."PRICE2") AS "PRICE2",
            COALESCE(hq."PRICE3", syp."PRICE3") AS "PRICE3",
            COALESCE(hq."PRICEM1", syp."PRICEM1") AS "PRICEM1",
            COALESCE(hq."COSTNET", syp."COSTNET") AS "COSTNET",
            NULLIF(TRIM(CAST(hq."LOCATION1" AS TEXT)), '') AS "location1_hq",
            NULLIF(TRIM(CAST(hq."LOCATION2" AS TEXT)), '') AS "location2_hq",
            NULLIF(TRIM(CAST(syp."LOCATION1" AS TEXT)), '') AS "location1_syp",
            NULLIF(TRIM(CAST(syp."LOCATION2" AS TEXT)), '') AS "location2_syp",
            GREATEST(
                COALESCE(hq._ingested_at, '1900-01-01'::timestamptz),
                COALESCE(syp._ingested_at, '1900-01-01'::timestamptz)
            ) AS _ingested_at
        FROM hq_products hq
        FULL OUTER JOIN syp_products syp
            ON hq."BCODE" = syp."BCODE"
    )
    SELECT * FROM (
        SELECT
            p.*,
            COALESCE(hq.qty, 0) AS qty_hq,
            COALESCE(syp.qty, 0) AS qty_syp,
            COALESCE(hq.qty, 0) + COALESCE(syp.qty, 0) AS qty_total,
            hq.updated_at AS updated_at_hq,
            syp.updated_at AS updated_at_syp,
            GREATEST(
                COALESCE(hq.updated_at, '1900-01-01'::timestamptz),
                COALESCE(syp.updated_at, '1900-01-01'::timestamptz)
            ) AS inventory_updated_at,
            COUNT(*) OVER() AS total_count
        FROM merged_products p
        LEFT JOIN curated_kcw.inventory_qty_latest hq
            ON p."BCODE" = hq.bcode AND hq.branch = 'HQ'
        LEFT JOIN curated_kcw.inventory_qty_latest syp
            ON p."BCODE" = syp.bcode AND syp.branch = 'SYP'
        WHERE {where_sql}
    ) t
    ORDER BY
        qty_total DESC,
        qty_hq DESC,
        qty_syp DESC,
        "BCODE" ASC
    LIMIT :limit
    """

    params["limit"] = limit

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.fetchall()
        cols = result.keys()

    df = pd.DataFrame(rows, columns=cols)

    total = 0
    if not df.empty and "total_count" in df.columns:
        total = int(df["total_count"].iloc[0])

    df = df.drop(columns=["total_count"], errors="ignore")
    return {"items": df, "total": total}
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

    explicit_codes = re.findall(r"(?<![A-Z0-9])([ACDEFGIKLOPQR])(?![A-Z0-9])", text_upper)
    if explicit_codes:
        detected_code1 = explicit_codes[0]

    if not detected_code1:
        for code1, keywords in CODE1_KEYWORD_MAP.items():
            for kw in keywords:
                if kw and kw.lower() in text_lower:
                    detected_code1 = code1
                    break
            if detected_code1:
                break

    cleaned_query = raw

    if detected_code1:
        cleaned_query = re.sub(
            rf"(?<![A-Za-z0-9]){re.escape(detected_code1)}(?![A-Za-z0-9])",
            " ",
            cleaned_query,
            flags=re.IGNORECASE,
        )
        for kw in CODE1_KEYWORD_MAP.get(detected_code1, []):
            cleaned_query = re.sub(re.escape(kw), " ", cleaned_query, flags=re.IGNORECASE)

    cleaned_query = re.sub(r"\s+", " ", cleaned_query).strip()
    tokens = cleaned_query.lower().split() if cleaned_query else []
    return detected_code1, tokens


def _extract_size_filters(query: str) -> tuple[dict[str, str], str]:
    """
    Examples:
      ขนาด 1 2 3   -> SIZE1=1, SIZE2=2, SIZE3=3
      ขนาด 1 2     -> SIZE1=1, SIZE2=2
      ขนาด - 2 3   -> SIZE2=2, SIZE3=3
      ขนาด - - 3   -> SIZE3=3
      ขนาด 1       -> SIZE1=1
    Returns:
      ({'SIZE1': '1', ...}, cleaned_query_without_size_part)
    """
    raw = str(query or "").strip()
    if not raw:
        return {}, raw

    # match "ขนาด" followed by 1-3 slots, each slot = number/word or "-"
    # stops after max 3 slots
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

    # remove the whole matched size phrase from free-text query
    cleaned_query = (raw[:m.start()] + " " + raw[m.end():]).strip()
    cleaned_query = re.sub(r"\s+", " ", cleaned_query)

    return size_filters, cleaned_query


def simple_and_search_sql(
    engine,
    query: str,
    schema: str = "raw_kcw",
    table_name: str = "raw_hq_icmas_products",
    limit: int = 5,
) -> dict:
    if not query or not str(query).strip():
        return {"items": pd.DataFrame(), "total": 0}

    # 1) extract size first
    size_filters, query_wo_size = _extract_size_filters(query)

    # 2) then extract CODE1 + remaining free-text
    detected_code1, tokens = _extract_code1_and_remaining_tokens(query_wo_size)

    where_parts = []
    params = {}

    if detected_code1:
        where_parts.append('UPPER(TRIM(COALESCE(p."CODE1", \'\'))) = :code1')
        params["code1"] = detected_code1

    # exact size filters
    for col, value in size_filters.items():
        param_key = col.lower()
        where_parts.append(f'TRIM(COALESCE(CAST(p."{col}" AS TEXT), \'\')) = :{param_key}')
        params[param_key] = str(value)

    # normal AND token search
    for i, tk in enumerate(tokens):
        key = f"tk{i}"
        params[key] = f"%{tk}%"
        col_parts = [
            f'LOWER(CAST(p."{col}" AS TEXT)) LIKE :{key}'
            for col in SEARCH_COLS
        ]
        where_parts.append("(" + " OR ".join(col_parts) + ")")

    if not where_parts:
        return {"items": pd.DataFrame(), "total": 0}

    where_sql = " AND ".join(where_parts)

    sql = f"""
    SELECT *
    FROM (
        SELECT
            p.*,
            COALESCE(hq.qty, 0) AS qty_hq,
            COALESCE(syp.qty, 0) AS qty_syp,
            hq.updated_at AS updated_at_hq,
            syp.updated_at AS updated_at_syp,
            GREATEST(
                COALESCE(hq.updated_at, '1900-01-01'::timestamptz),
                COALESCE(syp.updated_at, '1900-01-01'::timestamptz)
            ) AS inventory_updated_at,
            COUNT(*) OVER() AS total_count
        FROM "{schema}"."{table_name}" p
        LEFT JOIN curated_kcw.inventory_qty_latest hq
            ON p."BCODE" = hq.bcode AND hq.branch = 'HQ'
        LEFT JOIN curated_kcw.inventory_qty_latest syp
            ON p."BCODE" = syp.bcode AND syp.branch = 'SYP'
        WHERE {where_sql}
    ) t
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

    return {
        "items": df,
        "total": total,
    }
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

# รหัสคุม -> รายการ
CODE1_KEYWORD_MAP = {
    "A": ["ถ่าน"],
    "C": ["ซีล"],
    "D": ["บูช","บู๊ช","บู๊ซ","บู็ช","บู็ซ"],
    "E": ["ลูกปืนเข็ม", "ลูกปืนกรงนก", "เข็ม", "กรงนก"],
    "F": ["ไส้กรองอากาศ","กรองอากาศ"],
    "G": ["ยอยกากบาท","ยอย"],
    "I": ["ลูกปืนตลับ","ลูกปืน"],
    "K": ["จานคลัช","คลัช"],
    "L": ["สายอ่อน"],
    "O": ["โอริง"],
    "P": ["ไส้กรองน้ำมันเครื่อง","กรองน้ำมัน"],
    "Q": ["ลูกหมาก"],
    "R": ["ลูกยาง"],
}

VALID_CODE1 = set(CODE1_KEYWORD_MAP.keys())


def _normalize_text(text_value: str) -> str:
    s = str(text_value or "").strip().upper()
    s = re.sub(r"\s+", " ", s)
    return s


def _extract_code1_and_remaining_tokens(query: str) -> tuple[str | None, list[str]]:
    """
    Return:
      detected_code1: exact CODE1 to filter, or None
      remaining_tokens: tokens for normal free-text search
    Priority:
      1) explicit code in user text
      2) keyword match from รายการ table
    """
    raw = str(query or "").strip()
    if not raw:
        return None, []

    text_upper = _normalize_text(raw)
    text_lower = raw.lower()

    detected_code1 = None

    # 1) explicit control code in free text
    # match standalone single-letter code only
    explicit_codes = re.findall(r"(?<![A-Z0-9])([ACDEFGIKLOPQR])(?![A-Z0-9])", text_upper)
    if explicit_codes:
        detected_code1 = explicit_codes[0]

    # 2) keyword-based mapping from รายการ
    if not detected_code1:
        for code1, keywords in CODE1_KEYWORD_MAP.items():
            for kw in keywords:
                if kw and kw.lower() in text_lower:
                    detected_code1 = code1
                    break
            if detected_code1:
                break

    cleaned_query = raw

    # remove explicit code token from normal token search
    if detected_code1:
        cleaned_query = re.sub(
            rf"(?<![A-Za-z0-9]){re.escape(detected_code1)}(?![A-Za-z0-9])",
            " ",
            cleaned_query,
            flags=re.IGNORECASE,
        )

        # remove matched Thai keywords too, so they don't become noisy LIKE tokens
        for kw in CODE1_KEYWORD_MAP.get(detected_code1, []):
            cleaned_query = re.sub(re.escape(kw), " ", cleaned_query, flags=re.IGNORECASE)

    cleaned_query = re.sub(r"\s+", " ", cleaned_query).strip()
    tokens = cleaned_query.lower().split() if cleaned_query else []

    return detected_code1, tokens


def simple_and_search_sql(
    engine,
    query: str,
    schema: str = "raw_kcw",
    table_name: str = "raw_hq_icmas_products",
    limit: int = 5,
) -> dict:
    """
    AND search across SEARCH_COLS,
    optionally with CODE1 exact-match filter.
    Returns:
    {
      "items": DataFrame,
      "total": int
    }
    """
    if not query or not str(query).strip():
        return {"items": pd.DataFrame(), "total": 0}

    detected_code1, tokens = _extract_code1_and_remaining_tokens(query)

    where_parts = []
    params = {}

    # CODE1 exact match
    if detected_code1:
        where_parts.append('UPPER(TRIM(COALESCE(p."CODE1", \'\'))) = :code1')
        params["code1"] = detected_code1

    # normal AND token search
    for i, tk in enumerate(tokens):
        key = f"tk{i}"
        params[key] = f"%{tk}%"
        col_parts = [
            f'LOWER(CAST(p."{col}" AS TEXT)) LIKE :{key}'
            for col in SEARCH_COLS
        ]
        where_parts.append("(" + " OR ".join(col_parts) + ")")

    # if query was only a CODE1/รายการ keyword, still allow search by CODE1 alone
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
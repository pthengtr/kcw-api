import pandas as pd
from sqlalchemy import text

SEARCH_COLS = [
    "BCODE", "XCODE", "MCODE", "PCODE", "ACODE",
    "DESCR", "MODEL", "BRAND"
]


def simple_and_search_sql(
    engine,
    query: str,
    schema: str = "raw_kcw",
    table_name: str = "raw_hq_icmas_products",
    limit: int = 5,
) -> dict:
    """
    AND search across SEARCH_COLS.
    Returns:
    {
        "items": DataFrame,
        "total": int
    }
    """
    if not query or not str(query).strip():
        return {"items": pd.DataFrame(), "total": 0}

    tokens = str(query).strip().lower().split()

    where_parts = []
    params = {}

    for i, tk in enumerate(tokens):
        key = f"tk{i}"
        params[key] = f"%{tk}%"

        col_parts = [
            f'LOWER(CAST("{col}" AS TEXT)) LIKE :{key}'
            for col in SEARCH_COLS
        ]
        where_parts.append("(" + " OR ".join(col_parts) + ")")

    where_sql = " AND ".join(where_parts)

    sql = f"""
        SELECT *
        FROM (
            SELECT
                *,
                COUNT(*) OVER() AS total_count
            FROM "{schema}"."{table_name}"
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
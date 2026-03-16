from sqlalchemy import text
import pandas as pd

SEARCH_COLS = [
    "BCODE", "XCODE", "MCODE", "PCODE", "ACODE",
    "DESCR", "MODEL", "BRAND"
]

def simple_and_search_sql(
    engine,
    query: str,
    schema: str = "raw_kcw",
    table_name: str = "raw_hq_icmas_products",
    limit: int = 50,
):
    if not query or not str(query).strip():
        return pd.DataFrame()

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

    sql = f'''
        SELECT *
        FROM "{schema}"."{table_name}"
        WHERE {where_sql}
        LIMIT :limit
    '''

    params["limit"] = limit

    with engine.connect() as conn:
        result = conn.execute(text(sql), params)
        rows = result.fetchall()
        cols = result.keys()

    return pd.DataFrame(rows, columns=cols)
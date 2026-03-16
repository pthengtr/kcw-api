from pathlib import Path
import pandas as pd

def query_product_by_bcode(engine, bcode: str):
    sql = """
    select
        trim("BCODE") as "BCODE",
        trim("DESCR") as "DESCR",
        trim("MODEL") as "MODEL",
        trim("BRAND") as "BRAND",
        "PRICE1"
    from raw_kcw.raw_hq_icmas_products
    where trim("BCODE") = %(bcode)s
    """

    return pd.read_sql(sql, engine, params={"bcode": bcode.strip()})

def query_product_exact(engine, q: str):
    q = q.strip()

    sql = """
    select
        trim("BCODE") as "BCODE",
        trim("XCODE") as "XCODE",
        trim("MCODE") as "MCODE",
        trim("PCODE") as "PCODE",
        trim("ACODE") as "ACODE",
        trim("DESCR") as "DESCR",
        trim("MODEL") as "MODEL",
        trim("BRAND") as "BRAND",
        "PRICE1",
        case
            when trim("BCODE") = %(q)s then 'BCODE'
            when trim("XCODE") = %(q)s then 'XCODE'
            when trim("MCODE") = %(q)s then 'MCODE'
            when trim("PCODE") = %(q)s then 'PCODE'
            when trim("ACODE") = %(q)s then 'ACODE'
            else null
        end as matched_column,
        'exact' as match_type,
        case
            when trim("BCODE") = %(q)s then 100
            when trim("XCODE") = %(q)s then 95
            when trim("MCODE") = %(q)s then 95
            when trim("PCODE") = %(q)s then 95
            when trim("ACODE") = %(q)s then 95
            else 0
        end as score
    from raw_kcw.raw_hq_icmas_products
    where
        trim("BCODE") = %(q)s
        or trim("XCODE") = %(q)s
        or trim("MCODE") = %(q)s
        or trim("PCODE") = %(q)s
        or trim("ACODE") = %(q)s
    order by score desc, "BCODE"
    """

    return pd.read_sql(sql, engine, params={"q": q})

def query_product_code_partial(engine, q: str, limit: int = 20):
    q = q.strip()

    sql = """
    select
        trim("BCODE") as "BCODE",
        trim("XCODE") as "XCODE",
        trim("MCODE") as "MCODE",
        trim("PCODE") as "PCODE",
        trim("ACODE") as "ACODE",
        trim("DESCR") as "DESCR",
        trim("MODEL") as "MODEL",
        trim("BRAND") as "BRAND",
        "PRICE1",
        case
            when trim("BCODE") ilike %(q_like)s then 'BCODE'
            when trim("XCODE") ilike %(q_like)s then 'XCODE'
            when trim("MCODE") ilike %(q_like)s then 'MCODE'
            when trim("PCODE") ilike %(q_like)s then 'PCODE'
            when trim("ACODE") ilike %(q_like)s then 'ACODE'
            else null
        end as matched_column,
        'partial_code' as match_type,
        case
            when trim("BCODE") = %(q)s then 100
            when trim("XCODE") = %(q)s then 95
            when trim("MCODE") = %(q)s then 95
            when trim("PCODE") = %(q)s then 95
            when trim("ACODE") = %(q)s then 95
            when trim("BCODE") ilike %(q_prefix)s then 80
            when trim("XCODE") ilike %(q_prefix)s then 75
            when trim("MCODE") ilike %(q_prefix)s then 75
            when trim("PCODE") ilike %(q_prefix)s then 75
            when trim("ACODE") ilike %(q_prefix)s then 75
            when trim("BCODE") ilike %(q_like)s then 60
            when trim("XCODE") ilike %(q_like)s then 55
            when trim("MCODE") ilike %(q_like)s then 55
            when trim("PCODE") ilike %(q_like)s then 55
            when trim("ACODE") ilike %(q_like)s then 55
            else 0
        end as score
    from raw_kcw.raw_hq_icmas_products
    where
        trim("BCODE") ilike %(q_like)s
        or trim("XCODE") ilike %(q_like)s
        or trim("MCODE") ilike %(q_like)s
        or trim("PCODE") ilike %(q_like)s
        or trim("ACODE") ilike %(q_like)s
    order by score desc, "BCODE"
    limit %(limit)s
    """

    params = {
        "q": q,
        "q_like": f"%{q}%",
        "q_prefix": f"{q}%",
        "limit": limit,
    }

    return pd.read_sql(sql, engine, params=params)

def query_product_text_partial(engine, q: str, limit: int = 20):
    q = q.strip()

    sql = """
    select
        trim("BCODE") as "BCODE",
        trim("XCODE") as "XCODE",
        trim("MCODE") as "MCODE",
        trim("PCODE") as "PCODE",
        trim("ACODE") as "ACODE",
        trim("DESCR") as "DESCR",
        trim("MODEL") as "MODEL",
        trim("BRAND") as "BRAND",
        "PRICE1",
        case
            when trim("BRAND") ilike %(q_exact)s then 'BRAND'
            when trim("MODEL") ilike %(q_exact)s then 'MODEL'
            when trim("DESCR") ilike %(q_exact)s then 'DESCR'
            when trim("BRAND") ilike %(q_prefix)s then 'BRAND'
            when trim("MODEL") ilike %(q_prefix)s then 'MODEL'
            when trim("DESCR") ilike %(q_prefix)s then 'DESCR'
            when trim("BRAND") ilike %(q_like)s then 'BRAND'
            when trim("MODEL") ilike %(q_like)s then 'MODEL'
            when trim("DESCR") ilike %(q_like)s then 'DESCR'
            else null
        end as matched_column,
        'partial_text' as match_type,
        case
            when trim("BRAND") ilike %(q_exact)s then 70
            when trim("MODEL") ilike %(q_exact)s then 65
            when trim("DESCR") ilike %(q_exact)s then 60
            when trim("BRAND") ilike %(q_prefix)s then 55
            when trim("MODEL") ilike %(q_prefix)s then 50
            when trim("DESCR") ilike %(q_prefix)s then 45
            when trim("BRAND") ilike %(q_like)s then 40
            when trim("MODEL") ilike %(q_like)s then 35
            when trim("DESCR") ilike %(q_like)s then 30
            else 0
        end as score
    from raw_kcw.raw_hq_icmas_products
    where
        trim("DESCR") ilike %(q_like)s
        or trim("MODEL") ilike %(q_like)s
        or trim("BRAND") ilike %(q_like)s
    order by score desc, "BCODE"
    limit %(limit)s
    """

    params = {
        "q_exact": q,
        "q_prefix": f"{q}%",
        "q_like": f"%{q}%",
        "limit": limit,
    }

    return pd.read_sql(sql, engine, params=params)

def split_query_terms(q: str) -> list[str]:
    q = (q or "").strip()
    if not q:
        return []

    # simple first pass
    terms = [x.strip() for x in q.split() if x.strip()]

    # optional: ignore 1-char tokens for now
    terms = [x for x in terms if len(x) >= 2]

    return terms

def query_product_search_v1_multi(engine, q: str, limit: int = 20):
    q = (q or "").strip()
    terms = split_query_terms(q)

    if not q:
        return pd.DataFrame(
            columns=[
                "BCODE", "XCODE", "MCODE", "PCODE", "ACODE",
                "DESCR", "MODEL", "BRAND", "PRICE1",
                "matched_column", "match_type", "matched_terms", "score"
            ]
        )

    params = {
        "q": q,
        "q_exact": q,
        "q_prefix": f"{q}%",
        "q_like": f"%{q}%",
        "limit": limit,
    }

    token_where_parts = []
    token_score_parts = []
    token_match_count_parts = []

    for i, term in enumerate(terms):
        like_key = f"term_like_{i}"
        prefix_key = f"term_prefix_{i}"
        exact_key = f"term_exact_{i}"

        params[like_key] = f"%{term}%"
        params[prefix_key] = f"{term}%"
        params[exact_key] = term

        # each token can match code OR text fields
        token_where_parts.append(f"""
            trim("BCODE") ilike %({like_key})s
            or trim("XCODE") ilike %({like_key})s
            or trim("MCODE") ilike %({like_key})s
            or trim("PCODE") ilike %({like_key})s
            or trim("ACODE") ilike %({like_key})s
            or trim("DESCR") ilike %({like_key})s
            or trim("MODEL") ilike %({like_key})s
            or trim("BRAND") ilike %({like_key})s
        """)

        # weighted mixed scoring per token
        token_score_parts.append(f"""
            (
                case when trim("BCODE") = %({exact_key})s then 35 else 0 end +
                case when trim("XCODE") = %({exact_key})s then 32 else 0 end +
                case when trim("MCODE") = %({exact_key})s then 32 else 0 end +
                case when trim("PCODE") = %({exact_key})s then 32 else 0 end +
                case when trim("ACODE") = %({exact_key})s then 32 else 0 end +

                case when trim("BCODE") ilike %({prefix_key})s then 28 else 0 end +
                case when trim("XCODE") ilike %({prefix_key})s then 26 else 0 end +
                case when trim("MCODE") ilike %({prefix_key})s then 26 else 0 end +
                case when trim("PCODE") ilike %({prefix_key})s then 26 else 0 end +
                case when trim("ACODE") ilike %({prefix_key})s then 26 else 0 end +

                case when trim("BCODE") ilike %({like_key})s then 22 else 0 end +
                case when trim("XCODE") ilike %({like_key})s then 20 else 0 end +
                case when trim("MCODE") ilike %({like_key})s then 20 else 0 end +
                case when trim("PCODE") ilike %({like_key})s then 20 else 0 end +
                case when trim("ACODE") ilike %({like_key})s then 20 else 0 end +

                case when trim("BRAND") ilike %({exact_key})s then 18 else 0 end +
                case when trim("MODEL") ilike %({exact_key})s then 16 else 0 end +
                case when trim("DESCR") ilike %({exact_key})s then 14 else 0 end +

                case when trim("BRAND") ilike %({prefix_key})s then 12 else 0 end +
                case when trim("MODEL") ilike %({prefix_key})s then 10 else 0 end +
                case when trim("DESCR") ilike %({prefix_key})s then 8 else 0 end +

                case when trim("BRAND") ilike %({like_key})s then 7 else 0 end +
                case when trim("MODEL") ilike %({like_key})s then 6 else 0 end +
                case when trim("DESCR") ilike %({like_key})s then 5 else 0 end
            )
        """)

        # count matched tokens once per token, no matter how many cols it hits
        token_match_count_parts.append(f"""
            (
                case
                    when trim("BCODE") ilike %({like_key})s
                      or trim("XCODE") ilike %({like_key})s
                      or trim("MCODE") ilike %({like_key})s
                      or trim("PCODE") ilike %({like_key})s
                      or trim("ACODE") ilike %({like_key})s
                      or trim("DESCR") ilike %({like_key})s
                      or trim("MODEL") ilike %({like_key})s
                      or trim("BRAND") ilike %({like_key})s
                    then 1 else 0
                end
            )
        """)

    token_where_sql = " or ".join(f"({x})" for x in token_where_parts) if token_where_parts else "false"
    token_score_sql = " + ".join(f"({x})" for x in token_score_parts) if token_score_parts else "0"
    token_match_count_sql = " + ".join(f"({x})" for x in token_match_count_parts) if token_match_count_parts else "0"

    sql = f"""
    with candidates as (

        -- 1) exact whole-query code match
        select
            trim("BCODE") as "BCODE",
            trim("XCODE") as "XCODE",
            trim("MCODE") as "MCODE",
            trim("PCODE") as "PCODE",
            trim("ACODE") as "ACODE",
            trim("DESCR") as "DESCR",
            trim("MODEL") as "MODEL",
            trim("BRAND") as "BRAND",
            "PRICE1",
            case
                when trim("BCODE") = %(q)s then 'BCODE'
                when trim("XCODE") = %(q)s then 'XCODE'
                when trim("MCODE") = %(q)s then 'MCODE'
                when trim("PCODE") = %(q)s then 'PCODE'
                when trim("ACODE") = %(q)s then 'ACODE'
            end as matched_column,
            'exact_code' as match_type,
            {max(len(terms), 1)} as matched_terms,
            case
                when trim("BCODE") = %(q)s then 100
                when trim("XCODE") = %(q)s then 95
                when trim("MCODE") = %(q)s then 95
                when trim("PCODE") = %(q)s then 95
                when trim("ACODE") = %(q)s then 95
                else 0
            end as score
        from raw_kcw.raw_hq_icmas_products
        where
            trim("BCODE") = %(q)s
            or trim("XCODE") = %(q)s
            or trim("MCODE") = %(q)s
            or trim("PCODE") = %(q)s
            or trim("ACODE") = %(q)s

        union all

        -- 2) partial whole-query code match
        select
            trim("BCODE") as "BCODE",
            trim("XCODE") as "XCODE",
            trim("MCODE") as "MCODE",
            trim("PCODE") as "PCODE",
            trim("ACODE") as "ACODE",
            trim("DESCR") as "DESCR",
            trim("MODEL") as "MODEL",
            trim("BRAND") as "BRAND",
            "PRICE1",
            case
                when trim("BCODE") ilike %(q_like)s then 'BCODE'
                when trim("XCODE") ilike %(q_like)s then 'XCODE'
                when trim("MCODE") ilike %(q_like)s then 'MCODE'
                when trim("PCODE") ilike %(q_like)s then 'PCODE'
                when trim("ACODE") ilike %(q_like)s then 'ACODE'
            end as matched_column,
            'partial_code' as match_type,
            1 as matched_terms,
            case
                when trim("BCODE") ilike %(q_prefix)s then 80
                when trim("XCODE") ilike %(q_prefix)s then 75
                when trim("MCODE") ilike %(q_prefix)s then 75
                when trim("PCODE") ilike %(q_prefix)s then 75
                when trim("ACODE") ilike %(q_prefix)s then 75
                when trim("BCODE") ilike %(q_like)s then 60
                when trim("XCODE") ilike %(q_like)s then 55
                when trim("MCODE") ilike %(q_like)s then 55
                when trim("PCODE") ilike %(q_like)s then 55
                when trim("ACODE") ilike %(q_like)s then 55
                else 0
            end as score
        from raw_kcw.raw_hq_icmas_products
        where
            trim("BCODE") ilike %(q_like)s
            or trim("XCODE") ilike %(q_like)s
            or trim("MCODE") ilike %(q_like)s
            or trim("PCODE") ilike %(q_like)s
            or trim("ACODE") ilike %(q_like)s

        union all

        -- 3) whole-query phrase text match
        select
            trim("BCODE") as "BCODE",
            trim("XCODE") as "XCODE",
            trim("MCODE") as "MCODE",
            trim("PCODE") as "PCODE",
            trim("ACODE") as "ACODE",
            trim("DESCR") as "DESCR",
            trim("MODEL") as "MODEL",
            trim("BRAND") as "BRAND",
            "PRICE1",
            case
                when trim("BRAND") ilike %(q_exact)s then 'BRAND'
                when trim("MODEL") ilike %(q_exact)s then 'MODEL'
                when trim("DESCR") ilike %(q_exact)s then 'DESCR'
                when trim("BRAND") ilike %(q_prefix)s then 'BRAND'
                when trim("MODEL") ilike %(q_prefix)s then 'MODEL'
                when trim("DESCR") ilike %(q_prefix)s then 'DESCR'
                when trim("BRAND") ilike %(q_like)s then 'BRAND'
                when trim("MODEL") ilike %(q_like)s then 'MODEL'
                when trim("DESCR") ilike %(q_like)s then 'DESCR'
            end as matched_column,
            'phrase_text' as match_type,
            1 as matched_terms,
            case
                when trim("BRAND") ilike %(q_exact)s then 70
                when trim("MODEL") ilike %(q_exact)s then 65
                when trim("DESCR") ilike %(q_exact)s then 60
                when trim("BRAND") ilike %(q_prefix)s then 55
                when trim("MODEL") ilike %(q_prefix)s then 50
                when trim("DESCR") ilike %(q_prefix)s then 45
                when trim("BRAND") ilike %(q_like)s then 40
                when trim("MODEL") ilike %(q_like)s then 35
                when trim("DESCR") ilike %(q_like)s then 30
                else 0
            end as score
        from raw_kcw.raw_hq_icmas_products
        where
            trim("DESCR") ilike %(q_like)s
            or trim("MODEL") ilike %(q_like)s
            or trim("BRAND") ilike %(q_like)s

        union all

        -- 4) mixed token search: each token can hit code OR text fields
        select
            trim("BCODE") as "BCODE",
            trim("XCODE") as "XCODE",
            trim("MCODE") as "MCODE",
            trim("PCODE") as "PCODE",
            trim("ACODE") as "ACODE",
            trim("DESCR") as "DESCR",
            trim("MODEL") as "MODEL",
            trim("BRAND") as "BRAND",
            "PRICE1",
            case
                when trim("BCODE") ilike %(q_like)s then 'BCODE'
                when trim("XCODE") ilike %(q_like)s then 'XCODE'
                when trim("MCODE") ilike %(q_like)s then 'MCODE'
                when trim("PCODE") ilike %(q_like)s then 'PCODE'
                when trim("ACODE") ilike %(q_like)s then 'ACODE'
                when trim("BRAND") ilike %(q_like)s then 'BRAND'
                when trim("MODEL") ilike %(q_like)s then 'MODEL'
                when trim("DESCR") ilike %(q_like)s then 'DESCR'
                else 'MIXED'
            end as matched_column,
            'token_mixed' as match_type,
            ({token_match_count_sql}) as matched_terms,
            ({token_score_sql}) as score
        from raw_kcw.raw_hq_icmas_products
        where {token_where_sql}
    ),

    ranked as (
        select *,
               row_number() over (
                   partition by "BCODE"
                   order by matched_terms desc, score desc, match_type
               ) as rn
        from candidates
    )

    select
        "BCODE",
        "XCODE",
        "MCODE",
        "PCODE",
        "ACODE",
        "DESCR",
        "MODEL",
        "BRAND",
        "PRICE1",
        matched_column,
        match_type,
        matched_terms,
        score
    from ranked
    where rn = 1
    order by matched_terms desc, score desc, "BCODE"
    limit %(limit)s
    """

    return pd.read_sql(sql, engine, params=params)


def query_product_search_v1(engine, q: str, limit: int = 20):
    q = q.strip()

    sql = """
    with candidates as (

        -- 1) exact code match
        select
            trim("BCODE") as "BCODE",
            trim("XCODE") as "XCODE",
            trim("MCODE") as "MCODE",
            trim("PCODE") as "PCODE",
            trim("ACODE") as "ACODE",
            trim("DESCR") as "DESCR",
            trim("MODEL") as "MODEL",
            trim("BRAND") as "BRAND",
            "PRICE1",
            case
                when trim("BCODE") = %(q)s then 'BCODE'
                when trim("XCODE") = %(q)s then 'XCODE'
                when trim("MCODE") = %(q)s then 'MCODE'
                when trim("PCODE") = %(q)s then 'PCODE'
                when trim("ACODE") = %(q)s then 'ACODE'
            end as matched_column,
            'exact_code' as match_type,
            case
                when trim("BCODE") = %(q)s then 100
                when trim("XCODE") = %(q)s then 95
                when trim("MCODE") = %(q)s then 95
                when trim("PCODE") = %(q)s then 95
                when trim("ACODE") = %(q)s then 95
                else 0
            end as score
        from raw_kcw.raw_hq_icmas_products
        where
            trim("BCODE") = %(q)s
            or trim("XCODE") = %(q)s
            or trim("MCODE") = %(q)s
            or trim("PCODE") = %(q)s
            or trim("ACODE") = %(q)s

        union all

        -- 2) partial code match
        select
            trim("BCODE") as "BCODE",
            trim("XCODE") as "XCODE",
            trim("MCODE") as "MCODE",
            trim("PCODE") as "PCODE",
            trim("ACODE") as "ACODE",
            trim("DESCR") as "DESCR",
            trim("MODEL") as "MODEL",
            trim("BRAND") as "BRAND",
            "PRICE1",
            case
                when trim("BCODE") ilike %(q_like)s then 'BCODE'
                when trim("XCODE") ilike %(q_like)s then 'XCODE'
                when trim("MCODE") ilike %(q_like)s then 'MCODE'
                when trim("PCODE") ilike %(q_like)s then 'PCODE'
                when trim("ACODE") ilike %(q_like)s then 'ACODE'
            end as matched_column,
            'partial_code' as match_type,
            case
                when trim("BCODE") ilike %(q_prefix)s then 80
                when trim("XCODE") ilike %(q_prefix)s then 75
                when trim("MCODE") ilike %(q_prefix)s then 75
                when trim("PCODE") ilike %(q_prefix)s then 75
                when trim("ACODE") ilike %(q_prefix)s then 75
                when trim("BCODE") ilike %(q_like)s then 60
                when trim("XCODE") ilike %(q_like)s then 55
                when trim("MCODE") ilike %(q_like)s then 55
                when trim("PCODE") ilike %(q_like)s then 55
                when trim("ACODE") ilike %(q_like)s then 55
                else 0
            end as score
        from raw_kcw.raw_hq_icmas_products
        where
            trim("BCODE") ilike %(q_like)s
            or trim("XCODE") ilike %(q_like)s
            or trim("MCODE") ilike %(q_like)s
            or trim("PCODE") ilike %(q_like)s
            or trim("ACODE") ilike %(q_like)s

        union all

        -- 3) partial text match
        select
            trim("BCODE") as "BCODE",
            trim("XCODE") as "XCODE",
            trim("MCODE") as "MCODE",
            trim("PCODE") as "PCODE",
            trim("ACODE") as "ACODE",
            trim("DESCR") as "DESCR",
            trim("MODEL") as "MODEL",
            trim("BRAND") as "BRAND",
            "PRICE1",
            case
                when trim("BRAND") ilike %(q_exact)s then 'BRAND'
                when trim("MODEL") ilike %(q_exact)s then 'MODEL'
                when trim("DESCR") ilike %(q_exact)s then 'DESCR'
                when trim("BRAND") ilike %(q_prefix)s then 'BRAND'
                when trim("MODEL") ilike %(q_prefix)s then 'MODEL'
                when trim("DESCR") ilike %(q_prefix)s then 'DESCR'
                when trim("BRAND") ilike %(q_like)s then 'BRAND'
                when trim("MODEL") ilike %(q_like)s then 'MODEL'
                when trim("DESCR") ilike %(q_like)s then 'DESCR'
            end as matched_column,
            'partial_text' as match_type,
            case
                when trim("BRAND") ilike %(q_exact)s then 70
                when trim("MODEL") ilike %(q_exact)s then 65
                when trim("DESCR") ilike %(q_exact)s then 60
                when trim("BRAND") ilike %(q_prefix)s then 55
                when trim("MODEL") ilike %(q_prefix)s then 50
                when trim("DESCR") ilike %(q_prefix)s then 45
                when trim("BRAND") ilike %(q_like)s then 40
                when trim("MODEL") ilike %(q_like)s then 35
                when trim("DESCR") ilike %(q_like)s then 30
                else 0
            end as score
        from raw_kcw.raw_hq_icmas_products
        where
            trim("DESCR") ilike %(q_like)s
            or trim("MODEL") ilike %(q_like)s
            or trim("BRAND") ilike %(q_like)s
    ),

    ranked as (
        select *,
               row_number() over (
                   partition by "BCODE"
                   order by score desc, match_type
               ) as rn
        from candidates
    )

    select
        "BCODE",
        "XCODE",
        "MCODE",
        "PCODE",
        "ACODE",
        "DESCR",
        "MODEL",
        "BRAND",
        "PRICE1",
        matched_column,
        match_type,
        score
    from ranked
    where rn = 1
    order by score desc, "BCODE"
    limit %(limit)s
    """

    params = {
        "q": q,
        "q_exact": q,
        "q_prefix": f"{q}%",
        "q_like": f"%{q}%",
        "limit": limit,
    }

    return pd.read_sql(sql, engine, params=params)

def refresh_raw_hq_icmas_products_via_staging(conn, csv_path: str | Path) -> dict:
    """
    Load CSV into staging table, validate, then replace main table from staging.
    """
    csv_path = Path(csv_path)

    df = pd.read_csv(csv_path, dtype="string", nrows=0)
    cols = df.columns.tolist()
    quoted_cols = ", ".join([f'"{c}"' for c in cols])

    staging_table = "raw_kcw.raw_hq_icmas_products_stg"
    main_table = "raw_kcw.raw_hq_icmas_products"

    copy_sql = f"""
    COPY {staging_table} ({quoted_cols})
    FROM STDIN WITH CSV HEADER
    """

    with conn.cursor() as cur:
        # ensure staging exists
        cur.execute(f"""
        create table if not exists {staging_table}
        (like {main_table} including all)
        """)

        # clear staging only
        cur.execute(f"delete from {staging_table}")

        # load staging
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            with cur.copy(copy_sql) as copy:
                while data := f.read(1024 * 1024):
                    copy.write(data)

        # set source file on staging
        cur.execute(
            f"""
            update {staging_table}
            set _source_file = %s
            where _source_file is null
            """,
            (csv_path.name,)
        )

        # validate staging count
        cur.execute(f"select count(*) from {staging_table}")
        staging_count = cur.fetchone()[0]

        if staging_count == 0:
            raise ValueError("Staging load produced 0 rows. Main table not touched.")

        # replace main from staging
        cur.execute(f"delete from {main_table}")
        cur.execute(f"""
            insert into {main_table}
            select * from {staging_table}
        """)

        cur.execute(f"select count(*) from {main_table}")
        main_count = cur.fetchone()[0]

    conn.commit()

    return {
        "status": "ok",
        "staging_rows": staging_count,
        "main_rows": main_count,
        "source_file": csv_path.name,
    }
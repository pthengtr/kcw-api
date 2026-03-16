from pathlib import Path
import pandas as pd

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


    q = (q or "").strip()
    terms = split_query_terms(q)

    empty_cols = [
        "BCODE", "XCODE", "MCODE", "PCODE", "ACODE",
        "DESCR", "MODEL", "BRAND", "PRICE1",
        "matched_column", "match_type", "matched_terms", "score",
    ]

    if not q:
        return pd.DataFrame(columns=empty_cols)

    params = {
        "q": q,
        "q_exact": q,
        "q_prefix": f"{q}%",
        "q_like": f"%{q}%",
        "limit": limit,
    }

    token_where_sql, token_score_sql, token_match_count_sql = build_token_sql_parts(
        terms, params
    )

    candidate_blocks = [
        build_exact_code_block(len(terms)),
        build_partial_code_block(),
        build_phrase_text_block(),
        build_token_mixed_block(
            token_where_sql=token_where_sql,
            token_score_sql=token_score_sql,
            token_match_count_sql=token_match_count_sql,
        ),
    ]

    candidates_sql = "\nunion all\n".join(candidate_blocks)

    sql = f"""
    with candidates as (
        {candidates_sql}
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
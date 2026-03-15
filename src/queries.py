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
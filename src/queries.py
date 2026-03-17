from sqlalchemy import text


def get_daily_sales_summary(
    engine,
    target_date: str | None = None,
    table_name: str = "raw_kcw.fact_sales_all",
) -> dict:
    """
    Daily sales summary.

    If target_date is None:
        use latest BILLDATE in table.
    """

    with engine.connect() as conn:

        # ⭐ auto resolve latest date
        if not target_date:
            sql_max = text(f"""
                select max("BILLDATE")
                from {table_name}
            """)
            target_date = conn.execute(sql_max).scalar()

            if not target_date:
                return {
                    "date": None,
                    "HQ": 0.0,
                    "SYP": 0.0,
                    "BOTH": 0.0,
                }

        # ⭐ main aggregation
        sql = text(f"""
            with filtered as (
                select
                    "BRANCH",
                    case
                        when "TAXIC" = 'Y'
                            then cast(replace(coalesce("AMOUNT",'0'), ',', '') as numeric) / 1.07
                        else cast(replace(coalesce("AMOUNT",'0'), ',', '') as numeric)
                    end as sale_net
                from {table_name}
                where
                    "BILLDATE" = :target_date
                    and coalesce("JOURMODE",'') <> '0'
                    and coalesce("BILLTYPE_STD",'') not in ('DN','TAR','TF','TFV')
            )
            select "BRANCH", sum(sale_net)
            from filtered
            group by "BRANCH"

            union all

            select 'BOTH', sum(sale_net)
            from filtered
        """)

        rows = conn.execute(sql, {"target_date": target_date}).fetchall()

    result = {
        "date": target_date,
        "HQ": 0.0,
        "SYP": 0.0,
        "BOTH": 0.0,
    }

    for branch, value in rows:
        if branch in result:
            result[branch] = float(value or 0)

    return result
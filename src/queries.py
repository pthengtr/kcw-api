from sqlalchemy import text

def get_daily_sales_summary(engine, target_date: str):
    sql = text("""
        with filtered as (
            select
                "BRANCH",
                case
                    when "TAXIC" = 'Y'
                        then cast(replace(coalesce("AMOUNT", '0'), ',', '') as numeric) / 1.07
                    else cast(replace(coalesce("AMOUNT", '0'), ',', '') as numeric)
                end as sale_net
            from raw_kcw.fact_sales_all
            where
                "BILLDATE" = :target_date
                and coalesce("JOURMODE", '') <> '0'
                and coalesce("BILLTYPE_STD", '') not in ('DN', 'TAR', 'TF', 'TFV')
        )
        select coalesce("BRANCH", 'UNKNOWN') as branch, sum(sale_net) as net_sales
        from filtered
        group by "BRANCH"

        union all

        select 'BOTH' as branch, sum(sale_net) as net_sales
        from filtered
    """)

    result = {"date": target_date, "HQ": 0.0, "SYP": 0.0, "BOTH": 0.0}

    with engine.connect() as conn:
        rows = conn.execute(sql, {"target_date": target_date}).fetchall()

    for branch, net_sales in rows:
        if branch in result:
            result[branch] = float(net_sales or 0)

    return result
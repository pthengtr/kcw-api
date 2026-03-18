from sqlalchemy import text
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


def get_daily_sales_summary(
    engine,
    target_date: str | date | None = None,
    table_name: str = "curated_kcw.fact_sales_all",
) -> dict:
    """
    Daily sales summary.

    If target_date is None:
    - before 7 PM Bangkok time -> use yesterday
    - from 7 PM onward        -> use today
    """

    # resolve target_date
    if not target_date:
        bangkok_now = datetime.now(ZoneInfo("Asia/Bangkok"))
        if bangkok_now.hour < 19:
            target_date = (bangkok_now - timedelta(days=1)).date()
        else:
            target_date = bangkok_now.date()
    elif isinstance(target_date, str):
        target_date = datetime.strptime(target_date, "%Y-%m-%d").date()

    with engine.connect() as conn:
        sql = text(f"""
            with filtered as (
                select
                    coalesce(trim("BRANCH"), '') as "BRANCH",
                    case
                        when coalesce("TAXIC", '') = 'Y'
                            then cast(replace(coalesce("AMOUNT", '0'), ',', '') as numeric) / 1.07
                        else cast(replace(coalesce("AMOUNT", '0'), ',', '') as numeric)
                    end as sale_net
                from {table_name}
                where
                    "BILLDATE" = :target_date
                    and coalesce("JOURMODE", '') <> '0'
                    and coalesce("BILLTYPE_STD", '') not in ('DN', 'TAR', 'TF', 'TFV')
            )
            select "BRANCH", sum(sale_net) as total_sale
            from filtered
            group by "BRANCH"

            union all

            select 'BOTH' as "BRANCH", sum(sale_net) as total_sale
            from filtered
        """)

        rows = conn.execute(sql, {"target_date": target_date}).fetchall()

    result = {
        "date": str(target_date),
        "HQ": 0.0,
        "SYP": 0.0,
        "BOTH": 0.0,
    }

    for branch, value in rows:
        branch = (branch or "").strip()
        if branch in result:
            result[branch] = float(value or 0)

    return result
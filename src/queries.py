from sqlalchemy import text
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo


def _to_num_sql(column_name: str) -> str:
    return f"""
        case
            when trim(coalesce({column_name}, '')) = '' then 0
            else cast(replace(coalesce({column_name}, '0'), ',', '') as numeric)
        end
    """

def get_purchase_history_by_bcode(
    engine,
    bcode: str,
    limit: int = 3,
) -> dict:
    """
    Purchase history from HQ purchase lines only.
    """
    sql = text(f"""
        with purchase_rows as (
            select
                _ingested_at,
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("BILLNO", '')) as "BILLNO",
                trim(coalesce("BILLDATE", '')) as "BILLDATE",
                trim(coalesce("DETAIL", '')) as "DETAIL",
                trim(coalesce("TAXIC", '')) as "TAXIC",
                trim(coalesce("ACCTNO", '')) as "ACCTNO",
                {_to_num_sql('"QTY"')} as "QTY_NUM",
                {_to_num_sql('"AMOUNT"')} as "AMOUNT_NUM"
            from raw_kcw.raw_hq_pidet_purchase_lines
            where trim(coalesce("BCODE", '')) = :bcode
              and coalesce(trim("CANCELED"), '') <> 'Y'
        ),
        ranked as (
            select
                *,
                case
                    when "QTY_NUM" = 0 then 0
                    else "AMOUNT_NUM" / "QTY_NUM"
                end as "UNIT_AMOUNT",
                row_number() over (
                    order by "BILLDATE" desc, "BILLNO" desc
                ) as rn,
                count(*) over () as total_found
            from purchase_rows
        )
        select
            _ingested_at,
            "BCODE",
            "BILLNO",
            "BILLDATE",
            "DETAIL",
            "TAXIC",
            "ACCTNO",
            "QTY_NUM" as "QTY",
            "AMOUNT_NUM" as "AMOUNT",
            "UNIT_AMOUNT",
            total_found as "TOTAL_FOUND"
        from ranked
        where rn <= :limit
        order by rn
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"bcode": bcode.strip(), "limit": limit},
        ).mappings().all()

    rows = [dict(r) for r in rows]

    total_found = int(rows[0]["TOTAL_FOUND"]) if rows else 0
    product_name = rows[0]["DETAIL"] if rows else None

    latest_summary = None
    if rows:
        latest_summary = {
            "billdate": rows[0]["BILLDATE"],
            "billno": rows[0]["BILLNO"],
            "qty": float(rows[0]["QTY"] or 0),
            "amount": float(rows[0]["AMOUNT"] or 0),
            "unit_amount": float(rows[0]["UNIT_AMOUNT"] or 0),
        }

    for r in rows:
        r.pop("TOTAL_FOUND", None)

    latest_ingested = None
    if rows:
        latest_ingested = max(r["_ingested_at"] for r in rows if r.get("_ingested_at"))

    return {
        "product_name": product_name,
        "rows": rows,
        "latest_summary": latest_summary,
        "total_found": total_found,
        "latest_ingested_at": latest_ingested,
    }

def get_sales_history_by_bcode(
    engine,
    bcode: str,
    limit: int = 3,
) -> dict:
    """
    Sales history from curated_kcw.fact_sales_all.
    """
    sql = text(f"""
        with sales_rows as (
            select
                _ingested_at,
                trim(coalesce("BRANCH", '')) as "BRANCH",
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("BILLNO", '')) as "BILLNO",
                trim(coalesce("BILLDATE", '')) as "BILLDATE",
                trim(coalesce("DETAIL", '')) as "DETAIL",
                trim(coalesce("TAXIC", '')) as "TAXIC",
                trim(coalesce("ACCTNO", '')) as "ACCTNO",
                trim(coalesce("JOURMODE", '')) as "JOURMODE",
                trim(coalesce("BILLTYPE_STD", '')) as "BILLTYPE_STD",
                trim(coalesce("CANCELED", '')) as "CANCELED",
                {_to_num_sql('"QTY"')} as "QTY_NUM",
                case
                    when {_to_num_sql('"AMOUNT_NUM"')} <> 0
                        then {_to_num_sql('"AMOUNT_NUM"')}
                    else {_to_num_sql('"AMOUNT"')}
                end as "AMOUNT_NUM"
            from curated_kcw.fact_sales_all
            where trim(coalesce("BCODE", '')) = :bcode
        ),
        filtered as (
            select *
            from sales_rows
            where coalesce("CANCELED", '') <> 'Y'
              and coalesce("JOURMODE", '') <> '0'
              and coalesce("BILLTYPE_STD", '') not in ('DN', 'TAR', 'TF', 'TFV')
        ),
        ranked as (
            select
                *,
                case
                    when "QTY_NUM" = 0 then 0
                    else "AMOUNT_NUM" / "QTY_NUM"
                end as "UNIT_AMOUNT",
                row_number() over (
                    order by "BILLDATE" desc, "BILLNO" desc, "BRANCH" asc
                ) as rn,
                count(*) over () as total_found
            from filtered
        )
        select
            _ingested_at,
            "BRANCH",
            "BCODE",
            "BILLNO",
            "BILLDATE",
            "DETAIL",
            "TAXIC",
            "ACCTNO",
            "QTY_NUM" as "QTY",
            "AMOUNT_NUM" as "AMOUNT",
            "UNIT_AMOUNT",
            total_found as "TOTAL_FOUND"
        from ranked
        where rn <= :limit
        order by rn
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {"bcode": bcode.strip(), "limit": limit},
        ).mappings().all()

    rows = [dict(r) for r in rows]

    total_found = int(rows[0]["TOTAL_FOUND"]) if rows else 0
    product_name = rows[0]["DETAIL"] if rows else None

    latest_summary = None
    if rows:
        latest_summary = {
            "billdate": rows[0]["BILLDATE"],
            "billno": rows[0]["BILLNO"],
            "qty": float(rows[0]["QTY"] or 0),
            "amount": float(rows[0]["AMOUNT"] or 0),
            "unit_amount": float(rows[0]["UNIT_AMOUNT"] or 0),
        }

    for r in rows:
        r.pop("TOTAL_FOUND", None)

    latest_ingested = None
    if rows:
        latest_ingested = max(r["_ingested_at"] for r in rows if r.get("_ingested_at"))

    return {
        "product_name": product_name,
        "rows": rows,
        "latest_summary": latest_summary,
        "total_found": total_found,
        "latest_ingested_at": latest_ingested,
    }

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
                    "BILLDATE"::date = :target_date
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
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

def get_latest_purchase_by_bcode(engine, bcode: str) -> dict | None:
    sql = text(f"""
        with purchase_rows as (
            select
                _ingested_at,
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("BILLNO", '')) as "BILLNO",
                trim(coalesce("BILLDATE", '')) as "BILLDATE",
                trim(coalesce("DETAIL", '')) as "DETAIL",
                trim(coalesce("ACCTNO", '')) as "ACCTNO",
                {_to_num_sql('"QTY"')} as "QTY_NUM",
                {_to_num_sql('"AMOUNT"')} as "AMOUNT_NUM"
            from raw_kcw.raw_hq_pidet_purchase_lines
            where trim(coalesce("BCODE", '')) = :bcode
              and coalesce(trim("CANCELED"), '') <> 'Y'
        )
        select
            _ingested_at,
            "BCODE",
            "BILLNO",
            "BILLDATE",
            "DETAIL",
            "ACCTNO",
            "QTY_NUM" as "QTY",
            "AMOUNT_NUM" as "AMOUNT",
            case
                when "QTY_NUM" = 0 then 0
                else "AMOUNT_NUM" / "QTY_NUM"
            end as "UNIT_AMOUNT"
        from purchase_rows
        order by "BILLDATE" desc, "BILLNO" desc
        limit 1
    """)

    with engine.connect() as conn:
        row = conn.execute(sql, {"bcode": bcode.strip()}).mappings().first()

    return dict(row) if row else None

def get_latest_sale_by_bcode(engine, bcode: str) -> dict | None:
    sql = text(f"""
        with sales_rows as (
            select
                _ingested_at,
                trim(coalesce("BRANCH", '')) as "BRANCH",
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("BILLNO", '')) as "BILLNO",
                trim(coalesce("BILLDATE", '')) as "BILLDATE",
                trim(coalesce("DETAIL", '')) as "DETAIL",
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
        )
        select
            _ingested_at,
            "BRANCH",
            "BCODE",
            "BILLNO",
            "BILLDATE",
            "DETAIL",
            "ACCTNO",
            "QTY_NUM" as "QTY",
            "AMOUNT_NUM" as "AMOUNT",
            case
                when "QTY_NUM" = 0 then 0
                else "AMOUNT_NUM" / "QTY_NUM"
            end as "UNIT_AMOUNT"
        from sales_rows
        where coalesce("CANCELED", '') <> 'Y'
          and coalesce("JOURMODE", '') <> '0'
          and coalesce("BILLTYPE_STD", '') not in ('DN', 'TAR', 'TF', 'TFV')
        order by "BILLDATE" desc, "BILLNO" desc, "BRANCH" asc
        limit 1
    """)

    with engine.connect() as conn:
        row = conn.execute(sql, {"bcode": bcode.strip()}).mappings().first()

    return dict(row) if row else None

def get_stock_snapshot_by_bcode(engine, bcode: str) -> dict | None:
    sql = text("""
        select
            trim(coalesce(bcode, '')) as "BCODE",
            max(updated_at) as "_ingested_at",
            sum(coalesce(qty, 0)) as "QTY_TOTAL",
            sum(
                case
                    when upper(trim(coalesce(branch, ''))) = 'HQ'
                        then coalesce(qty, 0)
                    else 0
                end
            ) as "QTY_HQ",
            sum(
                case
                    when upper(trim(coalesce(branch, ''))) = 'SYP'
                        then coalesce(qty, 0)
                    else 0
                end
            ) as "QTY_SYP"
        from curated_kcw.inventory_qty_latest
        where trim(coalesce(bcode, '')) = :bcode
        group by trim(coalesce(bcode, ''))
    """)

    with engine.connect() as conn:
        row = conn.execute(sql, {"bcode": bcode.strip()}).mappings().first()

    return dict(row) if row else None

def get_product_snapshot_by_bcode(engine, bcode: str) -> dict | None:
    stock = get_stock_snapshot_by_bcode(engine, bcode)
    purchase = get_latest_purchase_by_bcode(engine, bcode)
    sale = get_latest_sale_by_bcode(engine, bcode)

    if not stock and not purchase and not sale:
        return None

    product_name = None
    for candidate in (purchase, sale, stock):
        if candidate and candidate.get("DETAIL"):
            product_name = candidate["DETAIL"]
            break

    latest_ingested_candidates = []
    for candidate in (stock, purchase, sale):
        if candidate and candidate.get("_ingested_at"):
            latest_ingested_candidates.append(candidate["_ingested_at"])

    latest_ingested_at = max(latest_ingested_candidates) if latest_ingested_candidates else None

    return {
        "bcode": bcode,
        "product_name": product_name or "-",
        "stock_total": float(stock.get("QTY_TOTAL") or 0) if stock else 0,
        "stock_hq": float(stock.get("QTY_HQ") or 0) if stock else 0,
        "stock_syp": float(stock.get("QTY_SYP") or 0) if stock else 0,
        "last_purchase": {
            "billdate": purchase.get("BILLDATE"),
            "billno": purchase.get("BILLNO"),
            "qty": float(purchase.get("QTY") or 0),
            "amount": float(purchase.get("AMOUNT") or 0),
            "unit_amount": float(purchase.get("UNIT_AMOUNT") or 0),
            "acct": purchase.get("ACCTNO"),
        } if purchase else None,
        "last_sale": {
            "branch": sale.get("BRANCH"),
            "billdate": sale.get("BILLDATE"),
            "billno": sale.get("BILLNO"),
            "qty": float(sale.get("QTY") or 0),
            "amount": float(sale.get("AMOUNT") or 0),
            "unit_amount": float(sale.get("UNIT_AMOUNT") or 0),
            "acct": sale.get("ACCTNO"),
        } if sale else None,
        "latest_ingested_at": latest_ingested_at,
    }

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
    branch: str | None = None,
    limit: int = 3,
) -> dict:
    sql = text(f"""
        with sales_rows as (
            select
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
                _ingested_at,
                {_to_num_sql('"QTY"')} as "QTY_NUM",
                case
                    when {_to_num_sql('"AMOUNT_NUM"')} <> 0
                        then {_to_num_sql('"AMOUNT_NUM"')}
                    else {_to_num_sql('"AMOUNT"')}
                end as "AMOUNT_NUM"
            from curated_kcw.fact_sales_all
            where trim(coalesce("BCODE", '')) = :bcode
              and (
                    cast(:branch as text) is null
                    or trim(coalesce("BRANCH", '')) = cast(:branch as text)
              )
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
            "BRANCH",
            "BCODE",
            "BILLNO",
            "BILLDATE",
            "DETAIL",
            "TAXIC",
            "ACCTNO",
            "_ingested_at",
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
            {
                "bcode": bcode.strip(),
                "branch": branch,
                "limit": limit,
            },
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

    latest_ingested = None
    if rows:
        ingested_values = [r["_ingested_at"] for r in rows if r.get("_ingested_at")]
        latest_ingested = max(ingested_values) if ingested_values else None

    for r in rows:
        r.pop("TOTAL_FOUND", None)

    return {
        "product_name": product_name,
        "rows": rows,
        "latest_summary": latest_summary,
        "total_found": total_found,
        "latest_ingested_at": latest_ingested,
        "branch": branch,
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

def get_top_matched_locations_with_products(
    engine,
    branch: str,
    location_keyword: str,
    max_locations: int = 3,
    max_products_per_location: int = 100,
) -> list[dict]:
    branch = (branch or "").strip().upper()
    location_keyword = (location_keyword or "").strip()

    if branch not in {"HQ", "SYP"}:
        raise ValueError("branch must be HQ or SYP")

    if branch == "HQ":
        product_table = 'raw_kcw.raw_hq_icmas_products'
    else:
        product_table = 'raw_kcw.raw_syp_icmas_products'

    sql = text(f"""
        WITH all_locations AS (
            SELECT DISTINCT TRIM(CAST("LOCATION1" AS TEXT)) AS location_name
            FROM {product_table}
            WHERE NULLIF(TRIM(CAST("LOCATION1" AS TEXT)), '') IS NOT NULL

            UNION

            SELECT DISTINCT TRIM(CAST("LOCATION2" AS TEXT)) AS location_name
            FROM {product_table}
            WHERE NULLIF(TRIM(CAST("LOCATION2" AS TEXT)), '') IS NOT NULL
        ),
        matched_locations AS (
            SELECT
                location_name,
                CASE
                    WHEN UPPER(location_name) = UPPER(:keyword) THEN 0
                    WHEN UPPER(location_name) LIKE UPPER(:prefix_kw) THEN 1
                    ELSE 2
                END AS match_rank,
                LENGTH(location_name) AS name_len
            FROM all_locations
            WHERE UPPER(location_name) LIKE UPPER(:contains_kw)
        ),
        matched_location_count AS (
            SELECT COUNT(*) AS total_location_matches
            FROM matched_locations
        ),
        top_locations AS (
            SELECT location_name
            FROM matched_locations
            ORDER BY
                match_rank ASC,
                name_len ASC,
                location_name ASC
            LIMIT :max_locations
        ),
        products_in_top_locations AS (
            SELECT
                tl.location_name AS matched_location,
                TRIM(COALESCE(p."BCODE", '')) AS "BCODE",
                TRIM(COALESCE(p."DESCR", '')) AS "DESCR"
            FROM top_locations tl
            JOIN {product_table} p
              ON TRIM(COALESCE(CAST(p."LOCATION1" AS TEXT), '')) = tl.location_name
              OR TRIM(COALESCE(CAST(p."LOCATION2" AS TEXT), '')) = tl.location_name
        )
        SELECT
            x.matched_location AS "MATCHED_LOCATION",
            x."BCODE",
            x."DESCR",
            COALESCE(i.qty, 0) AS "QTY",
            i.updated_at AS "UPDATED_AT",
            c.total_location_matches AS "TOTAL_LOCATION_MATCHES"
        FROM products_in_top_locations x
        CROSS JOIN matched_location_count c
        LEFT JOIN curated_kcw.inventory_qty_latest i
          ON x."BCODE" = i.bcode
         AND UPPER(TRIM(COALESCE(i.branch, ''))) = :branch
        ORDER BY
            x.matched_location ASC,
            COALESCE(i.qty, 0) DESC,
            x."BCODE" ASC
        LIMIT :final_limit
    """)

    with engine.connect() as conn:
        rows = conn.execute(
            sql,
            {
                "branch": branch,
                "keyword": location_keyword,
                "prefix_kw": f"{location_keyword}%",
                "contains_kw": f"%{location_keyword}%",
                "max_locations": max_locations,
                "final_limit": max_locations * max_products_per_location,
            },
        ).mappings().all()

    return [dict(r) for r in rows]

def get_product_brief_by_bcode(engine, bcode: str) -> dict | None:
    sql = text("""
        with candidates as (
            select
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("DESCR", '')) as "DESCR",
                trim(coalesce("BRAND", '')) as "BRAND",
                trim(coalesce("MODEL", '')) as "MODEL"
            from raw_kcw.raw_hq_icmas_products
            where trim(coalesce("BCODE", '')) = :bcode

            union all

            select
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("DESCR", '')) as "DESCR",
                trim(coalesce("BRAND", '')) as "BRAND",
                trim(coalesce("MODEL", '')) as "MODEL"
            from raw_kcw.raw_syp_icmas_products
            where trim(coalesce("BCODE", '')) = :bcode
        )
        select
            :bcode as "BCODE",
            max(nullif("DESCR", '')) as "DESCR",
            max(nullif("BRAND", '')) as "BRAND",
            max(nullif("MODEL", '')) as "MODEL"
        from candidates
    """)

    with engine.connect() as conn:
        row = conn.execute(sql, {"bcode": bcode.strip()}).mappings().first()

    if not row:
        return None

    data = dict(row)
    if not any(data.get(k) for k in ("DESCR", "BRAND", "MODEL")):
        return None

    return data

def get_recent_purchase_signal_by_bcode(engine, bcode: str, months: int = 6) -> dict:
    sql = text(f"""
        with purchase_rows as (
            select
                _ingested_at,
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("BILLNO", '')) as "BILLNO",
                trim(coalesce("BILLDATE", '')) as "BILLDATE",
                trim(coalesce("DETAIL", '')) as "DETAIL",
                trim(coalesce("ACCTNO", '')) as "ACCTNO",
                case
                    when trim(coalesce("BILLDATE", '')) ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
                        then cast(trim(coalesce("BILLDATE", '')) as date)
                    else null
                end as "BILLDATE_DT"
            from raw_kcw.raw_hq_pidet_purchase_lines
            where trim(coalesce("BCODE", '')) = :bcode
              and coalesce(trim("CANCELED"), '') <> 'Y'
        ),
        filtered as (
            select *
            from purchase_rows
            where "BILLDATE_DT" >= current_date - (:months || ' months')::interval
        ),
        latest_row as (
            select *
            from filtered
            order by "BILLDATE_DT" desc, "BILLNO" desc
            limit 1
        )
        select
            coalesce((select count(*) from filtered), 0) as "PURCHASE_COUNT",
            l._ingested_at,
            l."BILLNO",
            l."BILLDATE",
            l."DETAIL",
            l."ACCTNO"
        from (select 1) seed
        left join latest_row l on true
    """)

    with engine.connect() as conn:
        row = conn.execute(sql, {"bcode": bcode.strip(), "months": int(months)}).mappings().first()

    row = dict(row) if row else {}
    return {
        "count": int(row.get("PURCHASE_COUNT") or 0),
        "last_purchase": {
            "billdate": row.get("BILLDATE"),
            "billno": row.get("BILLNO"),
            "detail": row.get("DETAIL"),
            "acct": row.get("ACCTNO"),
        } if row.get("BILLDATE") else None,
        "latest_ingested_at": row.get("_ingested_at"),
    }

def get_recent_sale_signal_by_bcode(engine, bcode: str, months: int = 6) -> dict:
    sql = text(f"""
        with sales_rows as (
            select
                _ingested_at,
                trim(coalesce("BRANCH", '')) as "BRANCH",
                trim(coalesce("BCODE", '')) as "BCODE",
                trim(coalesce("BILLNO", '')) as "BILLNO",
                trim(coalesce("BILLDATE", '')) as "BILLDATE",
                trim(coalesce("DETAIL", '')) as "DETAIL",
                trim(coalesce("ACCTNO", '')) as "ACCTNO",
                trim(coalesce("JOURMODE", '')) as "JOURMODE",
                trim(coalesce("BILLTYPE_STD", '')) as "BILLTYPE_STD",
                trim(coalesce("CANCELED", '')) as "CANCELED",
                case
                    when trim(coalesce("BILLDATE", '')) ~ '^[0-9]{{4}}-[0-9]{{2}}-[0-9]{{2}}$'
                        then cast(trim(coalesce("BILLDATE", '')) as date)
                    else null
                end as "BILLDATE_DT"
            from curated_kcw.fact_sales_all
            where trim(coalesce("BCODE", '')) = :bcode
        ),
        filtered as (
            select *
            from sales_rows
            where coalesce("CANCELED", '') <> 'Y'
              and coalesce("JOURMODE", '') <> '0'
              and coalesce("BILLTYPE_STD", '') not in ('DN', 'TAR', 'TF', 'TFV')
              and "BILLDATE_DT" >= current_date - (:months || ' months')::interval
        ),
        latest_row as (
            select *
            from filtered
            order by "BILLDATE_DT" desc, "BILLNO" desc, "BRANCH" asc
            limit 1
        )
        select
            coalesce((select count(*) from filtered), 0) as "SALE_COUNT",
            l._ingested_at,
            l."BRANCH",
            l."BILLNO",
            l."BILLDATE",
            l."DETAIL",
            l."ACCTNO"
        from (select 1) seed
        left join latest_row l on true
    """)

    with engine.connect() as conn:
        row = conn.execute(sql, {"bcode": bcode.strip(), "months": int(months)}).mappings().first()

    row = dict(row) if row else {}
    return {
        "count": int(row.get("SALE_COUNT") or 0),
        "last_sale": {
            "branch": row.get("BRANCH"),
            "billdate": row.get("BILLDATE"),
            "billno": row.get("BILLNO"),
            "detail": row.get("DETAIL"),
            "acct": row.get("ACCTNO"),
        } if row.get("BILLDATE") else None,
        "latest_ingested_at": row.get("_ingested_at"),
    }

def get_quick_order_check_by_bcode(engine, bcode: str, months: int = 6) -> dict | None:
    product = get_product_brief_by_bcode(engine, bcode)
    stock = get_stock_snapshot_by_bcode(engine, bcode)
    purchase_signal = get_recent_purchase_signal_by_bcode(engine, bcode, months=months)
    sale_signal = get_recent_sale_signal_by_bcode(engine, bcode, months=months)

    if not product and not stock and not purchase_signal.get("count") and not sale_signal.get("count"):
        return None

    product_name = None
    if product and product.get("DESCR"):
        product_name = product.get("DESCR")
    elif purchase_signal.get("last_purchase") and purchase_signal["last_purchase"].get("detail"):
        product_name = purchase_signal["last_purchase"].get("detail")
    elif sale_signal.get("last_sale") and sale_signal["last_sale"].get("detail"):
        product_name = sale_signal["last_sale"].get("detail")

    has_sale = (sale_signal.get("count") or 0) > 0
    has_purchase = (purchase_signal.get("count") or 0) > 0

    if has_sale:
        status_key = "green"
        status_label = "สั่งได้"
        status_reason = f"พบการขายใน {months} เดือนล่าสุด"
    elif has_purchase:
        status_key = "orange"
        status_label = "เช็กอีกที"
        status_reason = (
            f"ไม่พบการขายใน {months} เดือนล่าสุด\n"
            f"แต่พบการซื้อเข้าใน {months} เดือนล่าสุด"
        )
    else:
        status_key = "red"
        status_label = "หยุดก่อน"
        status_reason = f"ไม่พบการขายและไม่พบการซื้อเข้าใน {months} เดือนล่าสุด"

    latest_ingested_candidates = []
    if stock and stock.get("_ingested_at"):
        latest_ingested_candidates.append(stock.get("_ingested_at"))
    if purchase_signal.get("latest_ingested_at"):
        latest_ingested_candidates.append(purchase_signal.get("latest_ingested_at"))
    if sale_signal.get("latest_ingested_at"):
        latest_ingested_candidates.append(sale_signal.get("latest_ingested_at"))

    latest_ingested_at = max(latest_ingested_candidates) if latest_ingested_candidates else None

    return {
        "bcode": bcode.strip(),
        "product_name": product_name or "-",
        "brand": (product or {}).get("BRAND"),
        "model": (product or {}).get("MODEL"),
        "stock_total": float(stock.get("QTY_TOTAL") or 0) if stock else 0,
        "stock_hq": float(stock.get("QTY_HQ") or 0) if stock else 0,
        "stock_syp": float(stock.get("QTY_SYP") or 0) if stock else 0,
        "has_sale_recent": has_sale,
        "has_purchase_recent": has_purchase,
        "recent_sale_count": int(sale_signal.get("count") or 0),
        "recent_purchase_count": int(purchase_signal.get("count") or 0),
        "last_sale": sale_signal.get("last_sale"),
        "last_purchase": purchase_signal.get("last_purchase"),
        "status_key": status_key,
        "status_label": status_label,
        "status_reason": status_reason,
        "latest_ingested_at": latest_ingested_at,
        "months_window": int(months),
    }


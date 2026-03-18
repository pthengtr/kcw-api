create schema if not exists curated_kcw;

create table if not exists curated_kcw.stg_fact_sales_all (
    _ingested_at timestamptz not null default now(),
    _source_file text,

    "BILLDATE" text,
    "BILLTYPE" text,
    "JOURMODE" text,
    "BILLNO" text,
    "BCODE" text,
    "DETAIL" text,
    "STATUS" text,
    "TAXIC" text,
    "ISVAT" text,
    "QTY" text,
    "UI" text,
    "MTP" text,
    "PRICE" text,
    "XPRICE" text,
    "DISCNT1" text,
    "DISCNT2" text,
    "DISCNT3" text,
    "DISCNT4" text,
    "DED" text,
    "VAT" text,
    "AMOUNT" text,
    "ACCTNO" text,
    "PAID" text,
    "ACCT_NO" text,
    "DONE" text,
    "CANCELED" text,
    "PRICE_NUM" text,
    "AMOUNT_NUM" text,
    "IS_VALID" text,
    "INVALID_REASON" text,
    "ROW_ID" text,
    "LAST_PURCHASE_DATE" text,
    "LAST_PURCHASE_COST" text,
    "COST_STATUS" text,
    "BRANCH" text,
    "BRANCH_BILLNO" text,
    "BILLTYPE_STD" text
);

create table if not exists curated_kcw.fact_sales_all_stg
(
    like raw_kcw.fact_sales_all including all
);

drop table raw_kcw.fact_sales_all;
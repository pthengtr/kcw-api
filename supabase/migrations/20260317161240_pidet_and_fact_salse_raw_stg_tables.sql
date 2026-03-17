create schema if not exists raw_kcw;

-- =========================================================
-- 1) FACT SALES ALL
-- =========================================================
create table if not exists raw_kcw.fact_sales_all (
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

create table if not exists raw_kcw.fact_sales_all_stg
(
    like raw_kcw.fact_sales_all including all
);

-- =========================================================
-- 2) RAW HQ PIDET PURCHASE LINES
-- =========================================================
create table if not exists raw_kcw.raw_hq_pidet_purchase_lines (
    _ingested_at timestamptz not null default now(),
    _source_file text,

    "ID" text,
    "JOURMODE" text,
    "JOURTYPE" text,
    "JOURDATE" text,
    "BILLTYPE" text,
    "BILLDATE" text,
    "BILLNO" text,
    "LINE" text,
    "ITEMNO" text,
    "BCODE" text,
    "PCODE" text,
    "MCODE" text,
    "DETAIL" text,
    "WHNUMBER" text,
    "LOCATION1" text,
    "STATUS" text,
    "SERIAL" text,
    "TAXIC" text,
    "EXMPT" text,
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
    "CHGAMT" text,
    "ACCTNO" text,
    "PAID" text,
    "SALEDATE" text,
    "SALENO" text,
    "SALEPRICE" text,
    "ACCT_NO" text,
    "CANCELED" text,
    "DONE" text
);

create table if not exists raw_kcw.raw_hq_pidet_purchase_lines_stg
(
    like raw_kcw.raw_hq_pidet_purchase_lines including all
);
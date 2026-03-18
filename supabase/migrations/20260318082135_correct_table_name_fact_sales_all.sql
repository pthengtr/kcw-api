create table if not exists curated_kcw.fact_sales_all
(
    like curated_kcw.fact_sales_all_stg including all
);

drop table curated_kcw.stg_fact_sales_all;
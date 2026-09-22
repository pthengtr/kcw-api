-- Persist device api/cash_box inventory alongside Open API hopper (payment/cash).

alter table tiger_pay.cash_snapshot
    add column if not exists cash_box_items jsonb not null default '[]'::jsonb,
    add column if not exists cash_box_total_baht numeric(14, 2) not null default 0;

alter table tiger_pay.cash_snapshot
    drop constraint if exists cash_snapshot_cash_box_items_array;
alter table tiger_pay.cash_snapshot
    add constraint cash_snapshot_cash_box_items_array
        check (jsonb_typeof(cash_box_items) = 'array');

alter table tiger_pay.cash_snapshot
    drop constraint if exists cash_snapshot_cash_box_total_non_negative;
alter table tiger_pay.cash_snapshot
    add constraint cash_snapshot_cash_box_total_non_negative
        check (cash_box_total_baht >= 0);

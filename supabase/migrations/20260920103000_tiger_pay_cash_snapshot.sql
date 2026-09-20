-- Hopper inventory snapshots + KCW till-close (Z-report) + v2 command queue.
-- Additive only: payment ingest tables are unchanged.

create schema if not exists tiger_pay;
create extension if not exists pgcrypto;

create table if not exists tiger_pay.cash_snapshot (
    id uuid primary key default gen_random_uuid(),
    captured_at timestamptz not null default now(),
    biz_day date not null,
    trigger text not null,
    tiger_payment_id bigint null,
    payment_no text null,
    payment_status text null,
    change_ready boolean null,
    change_level text not null,
    change_reasons jsonb not null default '[]'::jsonb,
    items jsonb not null default '[]'::jsonb,
    total_baht numeric(14, 2) not null default 0,
    shop_code text not null default '1',
    constraint cash_snapshot_trigger_check
        check (trigger in ('webhook', 'startup', 'eod', 'manual')),
    constraint cash_snapshot_level_check
        check (change_level in ('green', 'orange', 'red')),
    constraint cash_snapshot_total_non_negative
        check (total_baht >= 0),
    constraint cash_snapshot_items_array
        check (jsonb_typeof(items) = 'array'),
    constraint cash_snapshot_reasons_array
        check (jsonb_typeof(change_reasons) = 'array')
);

create index if not exists cash_snapshot_shop_captured_idx
    on tiger_pay.cash_snapshot (shop_code, captured_at desc);

create index if not exists cash_snapshot_shop_biz_day_idx
    on tiger_pay.cash_snapshot (shop_code, biz_day, captured_at desc);

create index if not exists cash_snapshot_payment_idx
    on tiger_pay.cash_snapshot (tiger_payment_id, payment_status, captured_at desc)
    where tiger_payment_id is not null;

create table if not exists tiger_pay.daily_close (
    biz_day date not null,
    shop_code text not null default '1',
    closed_at timestamptz not null default now(),
    trigger text not null,
    opening_snapshot_id uuid null
        references tiger_pay.cash_snapshot (id) on delete restrict,
    closing_snapshot_id uuid not null
        references tiger_pay.cash_snapshot (id) on delete restrict,
    report jsonb not null default '{}'::jsonb,
    locked boolean not null default true,
    primary key (biz_day, shop_code),
    constraint daily_close_trigger_check
        check (trigger in ('eod_auto', 'manual')),
    constraint daily_close_report_object
        check (jsonb_typeof(report) = 'object')
);

create table if not exists tiger_pay.cash_command (
    id uuid primary key default gen_random_uuid(),
    command text not null,
    shop_code text not null default '1',
    biz_day date null,
    status text not null default 'pending',
    requested_at timestamptz not null default now(),
    started_at timestamptz null,
    finished_at timestamptz null,
    error text null,
    snapshot_id uuid null
        references tiger_pay.cash_snapshot (id) on delete restrict,
    requested_by text null,
    constraint cash_command_type_check
        check (command in ('refresh', 'close')),
    constraint cash_command_status_check
        check (status in ('pending', 'running', 'done', 'failed'))
);

create index if not exists cash_command_pending_idx
    on tiger_pay.cash_command (requested_at)
    where status = 'pending';

grant usage on schema tiger_pay to service_role, authenticated;
grant all on table tiger_pay.cash_snapshot to service_role;
grant all on table tiger_pay.daily_close to service_role;
grant all on table tiger_pay.cash_command to service_role;
grant select on table tiger_pay.cash_snapshot to authenticated;
grant select on table tiger_pay.daily_close to authenticated;
grant select, insert, update on table tiger_pay.cash_command to authenticated;

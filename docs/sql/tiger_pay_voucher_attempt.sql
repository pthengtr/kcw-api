-- Tiger Pay companion voucher attempt tables (CN cash-return)
-- Paste into Supabase Dashboard → SQL Editor and run once.

create schema if not exists tiger_pay;

create table if not exists tiger_pay.voucher_attempt (
    id text primary key,
    pos_bill_id text not null,
    pos_bill_number text not null,
    amount numeric(18, 2) not null,
    voucher_num text null,
    ref_num text null,
    status text not null,
    raw_status text null,
    raw_create_response jsonb null,
    raw_last_show jsonb null,
    error_message text null,
    submitted_by text null,
    submitted_by_name text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_polled_at timestamptz null,
    constraint voucher_attempt_amount_non_negative check (amount >= 0),
    constraint voucher_attempt_id_max_len check (char_length(id) <= 20)
);

create unique index if not exists voucher_attempt_one_active_per_bill_idx
    on tiger_pay.voucher_attempt (pos_bill_id)
    where status in ('creating', 'pending');

create index if not exists voucher_attempt_pos_bill_id_idx
    on tiger_pay.voucher_attempt (pos_bill_id);

create index if not exists voucher_attempt_voucher_num_idx
    on tiger_pay.voucher_attempt (voucher_num);

create index if not exists voucher_attempt_status_idx
    on tiger_pay.voucher_attempt (status);

create index if not exists voucher_attempt_submitted_by_idx
    on tiger_pay.voucher_attempt (submitted_by);

create table if not exists tiger_pay.voucher_event (
    id bigserial primary key,
    voucher_attempt_id text not null
        references tiger_pay.voucher_attempt (id) on delete cascade,
    source text not null,
    status text not null,
    payload jsonb not null default '{}'::jsonb,
    event_key text null,
    created_at timestamptz not null default now(),
    constraint voucher_event_source_check
        check (source in ('api', 'polling'))
);

create unique index if not exists voucher_event_attempt_event_key_idx
    on tiger_pay.voucher_event (voucher_attempt_id, event_key)
    where event_key is not null;

create index if not exists voucher_event_attempt_id_created_at_idx
    on tiger_pay.voucher_event (voucher_attempt_id, created_at);

create unique index if not exists voucher_attempt_one_blocking_per_bill_idx
    on tiger_pay.voucher_attempt (pos_bill_id)
    where status in ('creating', 'pending', 'used');

create unique index if not exists voucher_attempt_one_used_per_bill_idx
    on tiger_pay.voucher_attempt (pos_bill_id)
    where status = 'used';

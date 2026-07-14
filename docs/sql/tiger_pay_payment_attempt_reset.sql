-- Tiger Pay companion tables — RESET for RefNo2 <= 20
-- Paste into Supabase SQL Editor and run once.
-- WARNING: deletes existing payment_attempt / payment_event rows (Phase 1 OK).

create schema if not exists tiger_pay;

drop table if exists tiger_pay.payment_event cascade;
drop table if exists tiger_pay.payment_attempt cascade;

create table tiger_pay.payment_attempt (
    id text primary key,
    pos_bill_id text not null,
    pos_bill_number text not null,
    amount numeric(18, 2) not null,
    tiger_payment_id bigint null,
    tiger_payment_no text null,
    status text not null,
    raw_status text null,
    raw_create_response jsonb null,
    error_message text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_polled_at timestamptz null,
    constraint payment_attempt_amount_non_negative check (amount >= 0),
    constraint payment_attempt_id_max_len check (char_length(id) <= 20)
);

create unique index payment_attempt_one_active_per_bill_idx
    on tiger_pay.payment_attempt (pos_bill_id)
    where status in ('sending', 'pending', 'paying', 'changing', 'cancelling');

create index payment_attempt_tiger_payment_id_idx
    on tiger_pay.payment_attempt (tiger_payment_id);

create index payment_attempt_pos_bill_id_idx
    on tiger_pay.payment_attempt (pos_bill_id);

create index payment_attempt_status_idx
    on tiger_pay.payment_attempt (status);

create table tiger_pay.payment_event (
    id bigserial primary key,
    payment_attempt_id text not null
        references tiger_pay.payment_attempt (id) on delete cascade,
    source text not null,
    status text not null,
    payload jsonb not null default '{}'::jsonb,
    event_key text null,
    created_at timestamptz not null default now(),
    constraint payment_event_source_check
        check (source in ('api', 'webhook', 'polling'))
);

create unique index payment_event_attempt_event_key_idx
    on tiger_pay.payment_event (payment_attempt_id, event_key)
    where event_key is not null;

create index payment_event_attempt_id_created_at_idx
    on tiger_pay.payment_event (payment_attempt_id, created_at);

-- Tiger Pay companion payment attempt tables
-- Paste into Supabase Dashboard → SQL Editor and run once.
--
-- If you still see: invalid input syntax for type uuid
-- run the hard reset instead:
--   docs/sql/tiger_pay_payment_attempt_reset.sql

create schema if not exists tiger_pay;

create table if not exists tiger_pay.payment_attempt (
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

create unique index if not exists payment_attempt_one_active_per_bill_idx
    on tiger_pay.payment_attempt (pos_bill_id)
    where status in ('sending', 'pending', 'paying', 'changing', 'cancelling');

create index if not exists payment_attempt_tiger_payment_id_idx
    on tiger_pay.payment_attempt (tiger_payment_id);

create index if not exists payment_attempt_pos_bill_id_idx
    on tiger_pay.payment_attempt (pos_bill_id);

create index if not exists payment_attempt_status_idx
    on tiger_pay.payment_attempt (status);

create table if not exists tiger_pay.payment_event (
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

create unique index if not exists payment_event_attempt_event_key_idx
    on tiger_pay.payment_event (payment_attempt_id, event_key)
    where event_key is not null;

create index if not exists payment_event_attempt_id_created_at_idx
    on tiger_pay.payment_event (payment_attempt_id, created_at);

-- Force-convert earlier uuid PK installs to text.
do $$
declare
    id_type text;
begin
    select data_type into id_type
    from information_schema.columns
    where table_schema = 'tiger_pay'
      and table_name = 'payment_attempt'
      and column_name = 'id';

    if id_type = 'uuid' then
        alter table tiger_pay.payment_event
            drop constraint if exists payment_event_payment_attempt_id_fkey;

        -- Clear old attempt rows so length<=20 check can apply cleanly.
        truncate table tiger_pay.payment_event, tiger_pay.payment_attempt cascade;

        alter table tiger_pay.payment_attempt
            alter column id type text using id::text;

        alter table tiger_pay.payment_event
            alter column payment_attempt_id type text using payment_attempt_id::text;

        alter table tiger_pay.payment_event
            add constraint payment_event_payment_attempt_id_fkey
            foreign key (payment_attempt_id)
            references tiger_pay.payment_attempt (id)
            on delete cascade;
    end if;

    begin
        alter table tiger_pay.payment_attempt
            add constraint payment_attempt_id_max_len
            check (char_length(id) <= 20);
    exception
        when duplicate_object then null;
    end;
end $$;

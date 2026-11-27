-- Tiger Pay cloud QR (BackOffice KBANK) — separate from box Open API payments.
-- Mirror of supabase/migrations/20261118190000_tiger_pay_cloud_qr_payment.sql
-- Paste into Supabase Dashboard → SQL Editor if applying manually.

create schema if not exists tiger_pay;

create table if not exists tiger_pay.cloud_qr_payment (
    id text primary key,
    pos_bill_id text not null,
    pos_bill_number text not null,
    amount numeric(18, 2) not null,
    uuid text null,
    ref1 text null,
    ref2 text null,
    qr_raw_data text null,
    qr_image text null,
    status text not null,
    payer_name text null,
    payer_account_number text null,
    sending_bank_code text null,
    paid_amount numeric(18, 2) null,
    raw_create_response jsonb null,
    raw_status_response jsonb null,
    error_message text null,
    submitted_by text null,
    submitted_by_name text null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    last_polled_at timestamptz null,
    paid_at timestamptz null,
    announced_at timestamptz null,
    announced_by text null,
    constraint cloud_qr_payment_amount_non_negative check (amount >= 0),
    constraint cloud_qr_payment_id_max_len check (char_length(id) <= 20)
);

create unique index if not exists cloud_qr_payment_one_active_per_bill_idx
    on tiger_pay.cloud_qr_payment (pos_bill_id)
    where status in ('sending', 'I');

create unique index if not exists cloud_qr_payment_one_blocking_per_bill_idx
    on tiger_pay.cloud_qr_payment (pos_bill_id)
    where status in ('sending', 'I', 'C');

create unique index if not exists cloud_qr_payment_one_success_per_bill_idx
    on tiger_pay.cloud_qr_payment (pos_bill_id)
    where status = 'C';

create unique index if not exists cloud_qr_payment_uuid_uidx
    on tiger_pay.cloud_qr_payment (uuid)
    where uuid is not null;

create index if not exists cloud_qr_payment_pos_bill_id_idx
    on tiger_pay.cloud_qr_payment (pos_bill_id);

create index if not exists cloud_qr_payment_status_idx
    on tiger_pay.cloud_qr_payment (status);

create index if not exists cloud_qr_payment_created_at_idx
    on tiger_pay.cloud_qr_payment (created_at);

create index if not exists cloud_qr_payment_paid_at_idx
    on tiger_pay.cloud_qr_payment (paid_at);

create index if not exists cloud_qr_payment_announce_pending_idx
    on tiger_pay.cloud_qr_payment (paid_at asc nulls last)
    where status = 'C' and announced_at is null;

grant usage on schema tiger_pay to service_role, authenticated;
grant all on table tiger_pay.cloud_qr_payment to service_role;
grant select on table tiger_pay.cloud_qr_payment to authenticated;

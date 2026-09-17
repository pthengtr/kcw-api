-- Record who submitted a Tiger Pay companion payment / voucher attempt.
-- LINE users store their line_user_id + display name.
-- Tailscale access stores submitted_by = 'tailscale'.

alter table tiger_pay.payment_attempt
    add column if not exists submitted_by text null,
    add column if not exists submitted_by_name text null;

alter table tiger_pay.voucher_attempt
    add column if not exists submitted_by text null,
    add column if not exists submitted_by_name text null;

create index if not exists payment_attempt_submitted_by_idx
    on tiger_pay.payment_attempt (submitted_by);

create index if not exists voucher_attempt_submitted_by_idx
    on tiger_pay.voucher_attempt (submitted_by);

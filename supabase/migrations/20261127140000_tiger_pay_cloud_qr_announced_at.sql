-- Cloud QR till announce worker: claim paid rows once, speak near the cashbox PC.
-- Companion browser TTS stays separate; this is for a speaker-equipped till/box PC.

alter table tiger_pay.cloud_qr_payment
    add column if not exists announced_at timestamptz null;

alter table tiger_pay.cloud_qr_payment
    add column if not exists announced_by text null;

comment on column tiger_pay.cloud_qr_payment.announced_at is
    'When a till announce worker claimed/spoke this paid cloud QR (null = not yet).';

comment on column tiger_pay.cloud_qr_payment.announced_by is
    'Announce worker id/hostname that claimed the row.';

-- Do not re-announce historical paid rows when the worker first starts.
update tiger_pay.cloud_qr_payment
set announced_at = coalesce(paid_at, updated_at, now())
where status = 'C'
  and announced_at is null;

create index if not exists cloud_qr_payment_announce_pending_idx
    on tiger_pay.cloud_qr_payment (paid_at asc nulls last)
    where status = 'C' and announced_at is null;

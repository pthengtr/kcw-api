-- Audit trail when an await-proof payment voucher is canceled so the note
-- can return to รอชำระ and be paid again without recreating the bill note.

create table if not exists pay_note.payment_cancel (
  id uuid primary key default gen_random_uuid(),
  acctno text not null,
  noteno text not null,
  voucno text not null,
  reason text not null,
  canceled_by text null,
  canceled_at timestamptz not null default now(),
  snapshot jsonb not null default '{}'::jsonb
);

create index if not exists pay_note_payment_cancel_note_idx
  on pay_note.payment_cancel (acctno, noteno, canceled_at desc);

create index if not exists pay_note_payment_cancel_voucno_idx
  on pay_note.payment_cancel (voucno, canceled_at desc);

comment on table pay_note.payment_cancel is
  'History of canceled await-proof payment vouchers (KSS BPDET soft-canceled; note returned to pending)';

-- Audit trail for post-voucher receive-meta edits (date / remark / bank only).

create table if not exists receive_note.receipt_edit_audit (
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid null references receive_note.receipt (id) on delete set null,
  acctno text not null,
  noteno text null,
  voucno text not null,
  edited_by text null,
  edited_at timestamptz not null default now(),
  accounting_reviewed boolean not null default false,
  gate_reasons text[] not null default '{}',
  old_values jsonb not null default '{}'::jsonb,
  new_values jsonb not null default '{}'::jsonb
);

create index if not exists receive_note_receipt_edit_audit_voucno_idx
  on receive_note.receipt_edit_audit (voucno, edited_at desc);

create index if not exists receive_note_receipt_edit_audit_receipt_idx
  on receive_note.receipt_edit_audit (receipt_id, edited_at desc);

comment on table receive_note.receipt_edit_audit is
  'History of post-voucher edits to received_at / remark / receive bank (no amount or Tiger changes)';

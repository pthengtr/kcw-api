-- Receive notes ops overlay (KSS holds ledger; this schema = receipts / notes / proof / tiger)

create schema if not exists receive_note;

create table if not exists receive_note.note (
  acctno text not null,
  noteno text not null,
  jourmode text not null,
  due_date date null,
  remark text null,
  status text not null default 'open',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by text null,
  primary key (acctno, noteno),
  constraint receive_note_note_status_check
    check (status in ('open', 'received', 'canceled'))
);

create index if not exists receive_note_note_status_idx on receive_note.note (status);
create index if not exists receive_note_note_due_idx on receive_note.note (due_date);

create table if not exists receive_note.receipt (
  id uuid primary key default gen_random_uuid(),
  acctno text not null,
  acctname text null,
  noteno text null,
  voucno text null,
  jourmode text not null,
  received_at date not null default (timezone('Asia/Bangkok', now()))::date,
  received_by text null,
  remark text null,
  billamt numeric(18, 2) not null default 0,
  discount numeric(18, 2) not null default 0,
  netamt numeric(18, 2) not null default 0,
  cash_amt numeric(18, 2) not null default 0,
  transfer_amt numeric(18, 2) not null default 0,
  cheque_amt numeric(18, 2) not null default 0,
  workflow_status text not null default 'pending',
  proof_status text not null default 'none',
  kss_sync_status text not null default 'pending',
  kss_sync_error text null,
  tiger_attempt_id text null,
  tiger_payment_id bigint null,
  tiger_payment_no text null,
  cash_mode text null,
  cash_manual_reason text null,
  money_confirmed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint receive_note_receipt_workflow_check
    check (workflow_status in (
      'pending', 'awaiting_tiger', 'awaiting_proof', 'review', 'done', 'failed'
    )),
  constraint receive_note_receipt_proof_check
    check (proof_status in ('none', 'awaiting', 'attached', 'tiger_auto')),
  constraint receive_note_receipt_sync_check
    check (kss_sync_status in ('pending', 'synced', 'failed', 'orphan_overlay')),
  constraint receive_note_receipt_cash_mode_check
    check (cash_mode is null or cash_mode in ('tiger', 'manual'))
);

create unique index if not exists receive_note_receipt_voucno_uidx
  on receive_note.receipt (voucno)
  where voucno is not null;

create index if not exists receive_note_receipt_acct_idx on receive_note.receipt (acctno);
create index if not exists receive_note_receipt_received_at_idx
  on receive_note.receipt (received_at desc);
create index if not exists receive_note_receipt_workflow_idx
  on receive_note.receipt (workflow_status);
create index if not exists receive_note_receipt_tiger_attempt_idx
  on receive_note.receipt (tiger_attempt_id);

create table if not exists receive_note.receipt_bill (
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null references receive_note.receipt (id) on delete cascade,
  billno text not null,
  aftertax numeric(18, 2) not null,
  allocate_amt numeric(18, 2) not null,
  fully_paid boolean not null default false,
  created_at timestamptz not null default now(),
  unique (receipt_id, billno)
);

create index if not exists receive_note_receipt_bill_billno_idx
  on receive_note.receipt_bill (billno);

create table if not exists receive_note.receipt_channel (
  id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null references receive_note.receipt (id) on delete cascade,
  settle_method text not null,
  amount numeric(18, 2) not null,
  chkno text null,
  chkdate date null,
  receive_bank_key text null,
  bankname text null,
  bank_gl text null,
  tiger_payment_no text null,
  created_at timestamptz not null default now(),
  constraint receive_note_channel_method_check
    check (settle_method in ('transfer', 'cheque', 'cash'))
);

create index if not exists receive_note_channel_receipt_idx
  on receive_note.receipt_channel (receipt_id);

-- Worker heartbeat URLs for receive-notes LAN service (port 8797)
alter table ops.worker_heartbeat
  add column if not exists receive_notes_public_base_url text,
  add column if not exists receive_notes_tailscale_base_url text;

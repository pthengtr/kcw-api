-- HQ vendor goods receipt overlay. PARTS9 PIMAS/PIDET are written by kcw-hq-receive
-- when HQ_RECEIVE_PIMAS_WRITE_ENABLED=true. ICLOW RECEIVED/RCVDNO stamped on confirm.

create schema if not exists hq_receive;

create table if not exists hq_receive.receipts (
  receipt_id uuid primary key default gen_random_uuid(),
  short_id text not null,
  status text not null default 'draft',
  vendor_acctno text not null default '',
  vendor_name text null,
  vendor_billno text null,
  vendor_bill_date date null,
  receive_date date null,
  pay_method text not null default 'credit',
  receiver text null,
  po_docnos jsonb not null default '[]'::jsonb,
  kcw_billno text null,
  pimas_billno text null,
  subtotal numeric not null default 0,
  discount numeric not null default 0,
  vat numeric not null default 0,
  net numeric not null default 0,
  notes text null,
  created_by text null,
  updated_by text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  confirmed_at timestamptz null,
  constraint hq_receive_receipts_short_id_key unique (short_id),
  constraint hq_receive_receipts_status_check
    check (status in ('draft', 'dry_run', 'confirmed', 'canceled'))
);

create index if not exists hq_receive_receipts_status_idx on hq_receive.receipts (status);
create index if not exists hq_receive_receipts_vendor_idx on hq_receive.receipts (vendor_acctno);
create index if not exists hq_receive_receipts_updated_idx on hq_receive.receipts (updated_at desc);

create table if not exists hq_receive.lines (
  line_id uuid primary key default gen_random_uuid(),
  receipt_id uuid not null references hq_receive.receipts (receipt_id) on delete cascade,
  line_no int not null,
  iclow_id bigint null,
  bcode text not null,
  descr text null,
  qty numeric not null check (qty > 0),
  ui text null,
  cost numeric not null default 0,
  discount numeric not null default 0,
  amount numeric not null default 0,
  po_docno text null,
  status text not null default 'ok',
  hold_reason text null,
  created_at timestamptz not null default now(),
  constraint hq_receive_lines_status_check
    check (status in ('ok', 'hold', 'mismatch'))
);

create index if not exists hq_receive_lines_receipt_idx on hq_receive.lines (receipt_id);
create index if not exists hq_receive_lines_iclow_idx on hq_receive.lines (iclow_id);
create index if not exists hq_receive_lines_bcode_idx on hq_receive.lines (bcode);

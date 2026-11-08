-- Purchase credit notes created from HQ goods receive (KCCN / 7KCCN).
-- Tracks VAT temp docs awaiting the real vendor credit-note number + date.

alter table hq_receive.lines
  add column if not exists bill_qty numeric null,
  add column if not exists received_qty numeric null,
  add column if not exists variance_action text null;

alter table hq_receive.lines
  drop constraint if exists hq_receive_lines_variance_action_check;

alter table hq_receive.lines
  add constraint hq_receive_lines_variance_action_check
    check (
      variance_action is null
      or variance_action in ('credit_note', 'wait_rest', 'change_product')
    );

create table if not exists hq_receive.credit_notes (
  credit_note_id uuid primary key default gen_random_uuid(),
  receipt_id uuid null references hq_receive.receipts (receipt_id) on delete set null,
  source_pimas_billno text not null,
  cn_billno text not null,
  vendor_acctno text not null default '',
  vendor_name text null,
  is_vat boolean not null default false,
  status text not null default 'awaiting_vendor_doc',
  vendor_cn_no text null,
  vendor_cn_date date null,
  beforetax numeric not null default 0,
  tax numeric not null default 0,
  aftertax numeric not null default 0,
  lines jsonb not null default '[]'::jsonb,
  created_by text null,
  updated_by text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  completed_at timestamptz null,
  constraint hq_receive_credit_notes_status_check
    check (status in ('awaiting_vendor_doc', 'completed', 'canceled')),
  constraint hq_receive_credit_notes_cn_billno_key unique (cn_billno)
);

create index if not exists hq_receive_credit_notes_status_idx
  on hq_receive.credit_notes (status);
create index if not exists hq_receive_credit_notes_source_idx
  on hq_receive.credit_notes (source_pimas_billno);
create index if not exists hq_receive_credit_notes_vendor_idx
  on hq_receive.credit_notes (vendor_acctno);
create index if not exists hq_receive_credit_notes_receipt_idx
  on hq_receive.credit_notes (receipt_id);
create index if not exists hq_receive_credit_notes_updated_idx
  on hq_receive.credit_notes (updated_at desc);

-- One non-canceled CN per source purchase bill (prevents duplicate credit notes).
create unique index if not exists hq_receive_credit_notes_active_source_uidx
  on hq_receive.credit_notes (source_pimas_billno)
  where status <> 'canceled';

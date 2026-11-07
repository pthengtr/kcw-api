-- Invoice AI extractions, discrepancy tracking, and barcode print jobs for hq_receive.

create table if not exists hq_receive.invoice_extractions (
  extraction_id uuid primary key default gen_random_uuid(),
  vendor_acctno text null,
  file_name text null,
  content_type text null,
  file_sha256 text null,
  raw_text text null,
  structured jsonb not null default '{}'::jsonb,
  confidence numeric null,
  created_by text null,
  created_at timestamptz not null default now()
);

create index if not exists hq_receive_invoice_extractions_vendor_idx
  on hq_receive.invoice_extractions (vendor_acctno);
create index if not exists hq_receive_invoice_extractions_created_idx
  on hq_receive.invoice_extractions (created_at desc);

create table if not exists hq_receive.invoice_extraction_lines (
  line_id uuid primary key default gen_random_uuid(),
  extraction_id uuid not null references hq_receive.invoice_extractions (extraction_id) on delete cascade,
  line_no int not null,
  raw_code text null,
  raw_name text null,
  brand text null,
  model text null,
  qty numeric null,
  ui text null,
  cost numeric null,
  discount numeric null,
  amount numeric null,
  confidence numeric null,
  created_at timestamptz not null default now()
);

create index if not exists hq_receive_invoice_extraction_lines_ext_idx
  on hq_receive.invoice_extraction_lines (extraction_id);

create table if not exists hq_receive.discrepancies (
  discrepancy_id uuid primary key default gen_random_uuid(),
  receipt_id uuid null references hq_receive.receipts (receipt_id) on delete set null,
  extraction_id uuid null references hq_receive.invoice_extractions (extraction_id) on delete set null,
  iclow_id bigint null,
  bcode text null,
  kind text not null,
  detail jsonb not null default '{}'::jsonb,
  status text not null default 'open',
  created_by text null,
  resolved_by text null,
  created_at timestamptz not null default now(),
  resolved_at timestamptz null,
  constraint hq_receive_discrepancies_kind_check
    check (kind in (
      'qty_mismatch', 'cost_mismatch', 'unknown_product',
      'over_po', 'under_po', 'wrong_brand', 'total_mismatch', 'other'
    )),
  constraint hq_receive_discrepancies_status_check
    check (status in ('open', 'held', 'resolved', 'ignored'))
);

create index if not exists hq_receive_discrepancies_status_idx
  on hq_receive.discrepancies (status);
create index if not exists hq_receive_discrepancies_receipt_idx
  on hq_receive.discrepancies (receipt_id);

create table if not exists hq_receive.barcode_print_jobs (
  job_id uuid primary key default gen_random_uuid(),
  receipt_id uuid null references hq_receive.receipts (receipt_id) on delete set null,
  pimas_billno text null,
  printer_model text null,
  printer_host text null,
  action text not null default 'download',
  copies int not null default 0,
  lines jsonb not null default '[]'::jsonb,
  created_by text null,
  created_at timestamptz not null default now()
);

create index if not exists hq_receive_barcode_jobs_receipt_idx
  on hq_receive.barcode_print_jobs (receipt_id);
create index if not exists hq_receive_barcode_jobs_created_idx
  on hq_receive.barcode_print_jobs (created_at desc);

alter table hq_receive.receipts
  add column if not exists extraction_id uuid null
    references hq_receive.invoice_extractions (extraction_id) on delete set null;

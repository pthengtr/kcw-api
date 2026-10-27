-- Full tax invoice (TO) overlay for one HQ TAD bill.
-- PARTS9 SIMAS/SIDET are read live and are not written.
-- The number series is gapless per issue-month. Drafts have no number.
-- Void keeps the number. A new draft for that TAD may be issued later.

create schema if not exists to_bill;

create table if not exists to_bill.counters (
  yymm text primary key,
  last_seq integer not null default 0 check (last_seq >= 0)
);

create table if not exists to_bill.invoices (
  invoice_id uuid primary key default gen_random_uuid(),
  docno text null,
  tad_billno text not null,
  status text not null default 'draft',
  bill_date date null,
  acctno text null,
  acctname_kss text null,
  online_po text null,
  beforetax numeric not null default 0,
  tax numeric not null default 0,
  aftertax numeric not null default 0,
  discount numeric not null default 0,
  kss_canceled boolean not null default false,
  source_read_at timestamptz null,
  customer_name text null,
  address text null,
  phone text null,
  tax_id text null,
  branch_label text not null default 'สำนักงานใหญ่',
  email text null,
  issued_at timestamptz null,
  issued_by text null,
  voided_at timestamptz null,
  void_reason text null,
  voided_by text null,
  created_by text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint to_bill_invoices_docno_key unique (docno),
  constraint to_bill_invoices_status_check check (status in ('draft', 'issued', 'void')),
  constraint to_bill_invoices_docno_status_check check (
    (status = 'draft' and docno is null)
    or (status in ('issued', 'void') and docno is not null)
  )
);

-- One open document per TAD. Void releases the slot.
create unique index if not exists to_bill_invoices_open_tad_idx
  on to_bill.invoices (tad_billno)
  where status in ('draft', 'issued');

create index if not exists to_bill_invoices_status_idx on to_bill.invoices (status);
create index if not exists to_bill_invoices_updated_idx on to_bill.invoices (updated_at desc);
create index if not exists to_bill_invoices_issued_tax_idx
  on to_bill.invoices (tax_id)
  where status = 'issued';

create table if not exists to_bill.lines (
  line_id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references to_bill.invoices (invoice_id) on delete cascade,
  line_no integer not null,
  bcode text null,
  detail text null,
  qty numeric not null default 0,
  ui text null,
  price numeric not null default 0,
  amount numeric not null default 0,
  constraint to_bill_lines_invoice_line_key unique (invoice_id, line_no)
);

create index if not exists to_bill_lines_invoice_idx on to_bill.lines (invoice_id);

create table if not exists to_bill.events (
  event_id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references to_bill.invoices (invoice_id) on delete cascade,
  action text not null,
  actor text null,
  note text null,
  created_at timestamptz not null default now(),
  constraint to_bill_events_action_check check (
    action in ('created', 'refreshed', 'issued', 'voided', 'printed')
  )
);

create index if not exists to_bill_events_invoice_idx on to_bill.events (invoice_id, created_at);

-- Internal staff see drafts and voids. Portal users see issued rows only.
-- A user with role external and without admin is a portal user.
create or replace function to_bill.caller_sees_internal()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select
    auth.uid() is not null
    and (
      exists (
        select 1
        from public.kcw_user_roles r
        where r.user_id = auth.uid()
          and r.role_key = 'admin'
      )
      or (
        exists (
          select 1
          from public.kcw_user_roles r
          where r.user_id = auth.uid()
            and r.role_key <> 'external'
        )
        and not exists (
          select 1
          from public.kcw_user_roles r
          where r.user_id = auth.uid()
            and r.role_key = 'external'
        )
      )
    );
$$;

alter table to_bill.invoices enable row level security;
alter table to_bill.lines enable row level security;
alter table to_bill.events enable row level security;
alter table to_bill.counters enable row level security;

drop policy if exists to_bill_invoices_select on to_bill.invoices;
create policy to_bill_invoices_select
  on to_bill.invoices
  for select
  to authenticated
  using (status = 'issued' or to_bill.caller_sees_internal());

drop policy if exists to_bill_lines_select on to_bill.lines;
create policy to_bill_lines_select
  on to_bill.lines
  for select
  to authenticated
  using (
    exists (
      select 1
      from to_bill.invoices i
      where i.invoice_id = lines.invoice_id
        and (i.status = 'issued' or to_bill.caller_sees_internal())
    )
  );

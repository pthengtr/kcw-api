-- Shared waiting-list drafts for catalog / peer lines that have no ICLOW id yet.
-- Same idea as waiting_drafts (qty / unit / vendor, shared across staff), keyed by bcode.

create table if not exists hq_po.waiting_extra_drafts (
  bcode text primary key,
  qty numeric not null check (qty > 0),
  ui text null,
  vendor_acctno text not null default '',
  vendor_name text null,
  source text not null default 'catalog'
    check (source in ('catalog', 'peer', 'history')),
  updated_by text null,
  updated_at timestamptz not null default now()
);

create index if not exists hq_po_waiting_extra_drafts_updated_at_idx
  on hq_po.waiting_extra_drafts (updated_at desc);

grant all on hq_po.waiting_extra_drafts to anon, authenticated, service_role;

notify pgrst, 'reload schema';

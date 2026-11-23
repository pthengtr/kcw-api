-- Shared waiting-list drafts: qty / vendor edits persist across refresh and devices.
-- Drafts are not orders; confirm still creates the real PO and then clears them.

create table if not exists hq_po.waiting_drafts (
  iclow_id bigint primary key,
  bcode text not null,
  qty numeric not null check (qty > 0),
  ui text null,
  vendor_acctno text not null default '',
  vendor_name text null,
  base_qty numeric null,
  base_vendor text null,
  base_descr text null,
  updated_by text null,
  updated_at timestamptz not null default now()
);

create index if not exists hq_po_waiting_drafts_bcode_idx
  on hq_po.waiting_drafts (bcode);

create index if not exists hq_po_waiting_drafts_updated_at_idx
  on hq_po.waiting_drafts (updated_at desc);

grant all on hq_po.waiting_drafts to anon, authenticated, service_role;

notify pgrst, 'reload schema';

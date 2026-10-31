-- A product this HQ vendor does not currently supply.
-- Clearing a tag keeps the row so the history stays.

create table if not exists hq_po.product_vendor_blocks (
  block_id bigint generated always as identity primary key,
  bcode text not null,
  acctno text not null,
  reason text not null default '',
  marked_by text null,
  created_at timestamptz not null default now(),
  cleared_at timestamptz null
);

create unique index if not exists hq_po_product_vendor_blocks_active_idx
  on hq_po.product_vendor_blocks (bcode, acctno)
  where cleared_at is null;

create index if not exists hq_po_product_vendor_blocks_bcode_idx
  on hq_po.product_vendor_blocks (bcode)
  where cleared_at is null;

grant all on hq_po.product_vendor_blocks to anon, authenticated, service_role;

notify pgrst, 'reload schema';

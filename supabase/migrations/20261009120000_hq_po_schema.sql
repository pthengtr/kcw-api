-- HQ supplier PO overlay. PARTS9 POMAS/PODET are not written.
-- ICLOW ORDERED/DOCNO/DOCDATE is stamped from the app; RECEIVED stays with PIMAS.

create schema if not exists hq_po;

create table if not exists hq_po.orders (
  order_id uuid primary key default gen_random_uuid(),
  short_id text not null,
  docno text not null,
  vendor_acctno text not null default '',
  vendor_name text null,
  status text not null default 'ordered',
  ordered_by text null,
  ordered_at timestamptz not null default now(),
  canceled_at timestamptz null,
  cancel_reason text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint hq_po_orders_short_id_key unique (short_id),
  constraint hq_po_orders_docno_key unique (docno),
  constraint hq_po_orders_status_check check (status in ('ordered', 'canceled'))
);

create index if not exists hq_po_orders_status_idx on hq_po.orders (status);
create index if not exists hq_po_orders_ordered_at_idx on hq_po.orders (ordered_at desc);
create index if not exists hq_po_orders_vendor_idx on hq_po.orders (vendor_acctno);

create table if not exists hq_po.lines (
  line_id uuid primary key default gen_random_uuid(),
  order_id uuid not null references hq_po.orders (order_id) on delete cascade,
  iclow_id bigint not null,
  bcode text not null,
  descr text null,
  qty numeric not null check (qty > 0),
  ui text null,
  propose_meta jsonb null,
  canceled_at timestamptz null,
  created_at timestamptz not null default now(),
  constraint hq_po_lines_order_iclow_key unique (order_id, iclow_id)
);

-- One open PO line per ICLOW row. Cancel sets canceled_at so the row can be ordered again.
create unique index if not exists hq_po_lines_open_iclow_idx
  on hq_po.lines (iclow_id)
  where canceled_at is null;

create index if not exists hq_po_lines_order_id_idx on hq_po.lines (order_id);

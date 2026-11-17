-- Online sale order drafts (pre-TAD pick list).
-- No PARTS9 write until confirmed as TAD.

create schema if not exists online_sale;

create table if not exists online_sale.drafts (
  draft_id uuid primary key default gen_random_uuid(),
  status text not null default 'open',
  platform text null,
  acctno text not null,
  acctname text null,
  shop_name text null,
  online_po text not null,
  aftertax numeric not null default 0,
  lines jsonb not null default '[]'::jsonb,
  pick_printed_at timestamptz null,
  sold_billno text null,
  sold_at timestamptz null,
  canceled_at timestamptz null,
  canceled_by text null,
  created_by text null,
  updated_by text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint online_sale_drafts_status_check
    check (status in ('open', 'printed', 'canceled', 'sold')),
  constraint online_sale_drafts_po_len_check
    check (char_length(btrim(online_po)) > 0 and char_length(online_po) <= 15)
);

-- One active draft per shop + order id.
create unique index if not exists online_sale_drafts_open_po_idx
  on online_sale.drafts (acctno, online_po)
  where status in ('open', 'printed');

create index if not exists online_sale_drafts_status_idx
  on online_sale.drafts (status);

create index if not exists online_sale_drafts_updated_idx
  on online_sale.drafts (updated_at desc);

create index if not exists online_sale_drafts_po_idx
  on online_sale.drafts (online_po);

grant usage on schema online_sale to authenticated, service_role;
grant select on online_sale.drafts to authenticated;
grant all on all tables in schema online_sale to service_role;
alter default privileges for role postgres in schema online_sale
  grant select on tables to authenticated;
alter default privileges for role postgres in schema online_sale
  grant all on tables to service_role;

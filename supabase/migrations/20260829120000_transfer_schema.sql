-- HQ↔SYP transfer workflow overlay (PARTS9 commits TF + receive; this schema = state)

create schema if not exists transfer;

create table if not exists transfer.requests (
  transfer_id uuid primary key default gen_random_uuid(),
  short_id text not null,
  status text not null default 'draft',
  site text not null default 'SYP',
  requested_by text null,
  requested_at timestamptz null,
  notes text null,
  cancelled_at timestamptz null,
  cancel_reason text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint transfer_requests_short_id_key unique (short_id)
);

create index if not exists transfer_requests_status_idx on transfer.requests (status);
create index if not exists transfer_requests_requested_at_idx on transfer.requests (requested_at desc nulls last);

create table if not exists transfer.lines (
  line_id uuid primary key default gen_random_uuid(),
  transfer_id uuid not null references transfer.requests (transfer_id) on delete cascade,
  bcode text not null,
  descr text null,
  qty_requested numeric not null check (qty_requested > 0),
  qty_prepared numeric not null default 0 check (qty_prepared >= 0),
  qty_received numeric not null default 0 check (qty_received >= 0),
  line_status text not null default 'open',
  iclow_id bigint null,
  cancelled_at timestamptz null,
  cancel_reason text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint transfer_lines_transfer_bcode_key unique (transfer_id, bcode)
);

create index if not exists transfer_lines_transfer_id_idx on transfer.lines (transfer_id);
create index if not exists transfer_lines_bcode_idx on transfer.lines (bcode);

create table if not exists transfer.need_list (
  need_id uuid primary key default gen_random_uuid(),
  bcode text not null,
  descr text null,
  suggest_qty numeric not null default 0,
  qty numeric not null check (qty > 0),
  hq_qtyoh2 numeric null,
  added_by text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint transfer_need_list_bcode_key unique (bcode)
);

create table if not exists transfer.shipments (
  shipment_id uuid primary key default gen_random_uuid(),
  transfer_id uuid not null references transfer.requests (transfer_id) on delete cascade,
  tf_billno text null,
  posted_at timestamptz null,
  posted_by text null,
  client_token text null,
  created_at timestamptz not null default now(),
  constraint transfer_shipments_client_token_key unique (client_token)
);

create index if not exists transfer_shipments_transfer_id_idx on transfer.shipments (transfer_id);

create table if not exists transfer.shipment_lines (
  shipment_line_id uuid primary key default gen_random_uuid(),
  shipment_id uuid not null references transfer.shipments (shipment_id) on delete cascade,
  line_id uuid not null references transfer.lines (line_id) on delete cascade,
  bcode text not null,
  qty_shipped numeric not null check (qty_shipped > 0),
  qty_received numeric not null default 0 check (qty_received >= 0)
);

create index if not exists transfer_shipment_lines_shipment_id_idx on transfer.shipment_lines (shipment_id);

create table if not exists transfer.events (
  event_id uuid primary key default gen_random_uuid(),
  transfer_id uuid null references transfer.requests (transfer_id) on delete set null,
  event_type text not null,
  payload jsonb not null default '{}'::jsonb,
  actor text null,
  created_at timestamptz not null default now()
);

create index if not exists transfer_events_transfer_id_idx on transfer.events (transfer_id, created_at desc);

alter table ops.worker_heartbeat
  add column if not exists transfer_public_base_url text,
  add column if not exists transfer_tailscale_base_url text;

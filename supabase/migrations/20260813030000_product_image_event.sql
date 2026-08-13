-- Per-operator product picture mutations (upload / replace / delete) for kcw-v2 KPI.
create schema if not exists ops;

create table if not exists ops.product_image_event (
  id uuid primary key default gen_random_uuid(),
  line_user_id text not null,
  display_name text not null default '',
  event_type text not null,
  bcode text not null,
  storage_path text,
  bucket text not null default 'pictures',
  source text not null default 'line_bot',
  created_at timestamptz not null default now()
);

create index if not exists product_image_event_user_created_idx
  on ops.product_image_event (line_user_id, created_at desc);

create index if not exists product_image_event_created_idx
  on ops.product_image_event (created_at desc);

create index if not exists product_image_event_bcode_created_idx
  on ops.product_image_event (bcode, created_at desc);

create or replace view ops.product_image_kpi_daily as
select
  (created_at at time zone 'Asia/Bangkok')::date as work_date,
  line_user_id,
  max(display_name) as display_name,
  count(*) filter (where event_type = 'image_upload') as uploads,
  count(*) filter (where event_type = 'image_replace') as replaces,
  count(*) filter (where event_type = 'image_delete') as deletes,
  count(*) as total_actions,
  count(distinct bcode) as unique_products
from ops.product_image_event
group by 1, line_user_id;

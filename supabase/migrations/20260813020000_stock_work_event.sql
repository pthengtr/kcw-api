-- Per-operator stock-check work events (counting + auditing KPI).
create schema if not exists stock;

create table if not exists stock.work_event (
  id text primary key,
  branch text not null,
  line_user_id text not null,
  display_name text not null,
  event_type text not null,
  bcode text,
  draft_id text,
  variance double precision,
  source text,
  created_at timestamptz not null default now()
);

create index if not exists work_event_branch_user_created_idx
  on stock.work_event (branch, line_user_id, created_at desc);

create index if not exists work_event_branch_created_idx
  on stock.work_event (branch, created_at desc);

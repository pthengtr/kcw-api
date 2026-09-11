-- Product substitute groups (สินค้าทดแทน) — mutual peer SKUs by BCODE

create schema if not exists catalog;

create table if not exists catalog.substitute_groups (
  group_id uuid primary key default gen_random_uuid(),
  name text null,
  note text null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by text null
);

create table if not exists catalog.substitute_members (
  group_id uuid not null references catalog.substitute_groups (group_id) on delete cascade,
  bcode text not null,
  sort_rank int not null default 0,
  note text null,
  primary key (group_id, bcode),
  constraint substitute_members_bcode_key unique (bcode)
);

create index if not exists substitute_members_bcode_idx
  on catalog.substitute_members (bcode);

create index if not exists substitute_members_group_id_idx
  on catalog.substitute_members (group_id);

grant usage on schema catalog to anon, authenticated, service_role;

grant all on all tables in schema catalog to anon, authenticated, service_role;
grant all on all sequences in schema catalog to anon, authenticated, service_role;
grant all on all routines in schema catalog to anon, authenticated, service_role;

alter default privileges for role postgres in schema catalog
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema catalog
  grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema catalog
  grant all on routines to anon, authenticated, service_role;

alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note, transfer, catalog';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

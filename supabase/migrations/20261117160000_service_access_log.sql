-- Audit who opened / switched / left staff web services (LINE + in-app launcher).

create table if not exists ops.service_access_log (
  id bigserial primary key,
  line_user_id text not null,
  display_name text null,
  branch text null,
  service_id text not null,
  source text not null default 'direct',
  action text not null default 'open',
  path text null,
  at timestamptz not null default now(),
  constraint ops_service_access_log_source_check
    check (source in ('line', 'launcher', 'direct')),
  constraint ops_service_access_log_action_check
    check (action in ('open', 'switch', 'logout'))
);

create index if not exists ops_service_access_log_at_idx
  on ops.service_access_log (at desc);

create index if not exists ops_service_access_log_user_idx
  on ops.service_access_log (line_user_id, at desc);

create index if not exists ops_service_access_log_service_idx
  on ops.service_access_log (service_id, at desc);

grant select on ops.service_access_log to authenticated;
grant all on ops.service_access_log to service_role;
grant usage, select on sequence ops.service_access_log_id_seq to service_role;

-- Per-user per-service menu/command usage counts (Phase 2 personalized menu).

create table if not exists ops.service_menu_usage (
  line_user_id text not null,
  service_id text not null,
  click_count bigint not null default 0,
  last_clicked_at timestamptz not null default now(),
  primary key (line_user_id, service_id),
  constraint ops_service_menu_usage_click_count_check
    check (click_count >= 0)
);

create index if not exists ops_service_menu_usage_user_count_idx
  on ops.service_menu_usage (line_user_id, click_count desc);

create index if not exists ops_service_menu_usage_service_idx
  on ops.service_menu_usage (service_id, click_count desc);

grant select on ops.service_menu_usage to authenticated;
grant all on ops.service_menu_usage to service_role;

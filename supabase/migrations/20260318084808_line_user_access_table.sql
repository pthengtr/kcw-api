create schema if not exists ops;

create table if not exists ops.line_access (
    line_user_id text primary key,
    display_name text,
    access_group text not null default 'guest',
    is_allowed boolean not null default false,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);
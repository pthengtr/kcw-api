create schema if not exists ops;

create table if not exists ops.worker_heartbeat (
    worker_name text primary key,
    last_seen timestamptz not null default now(),
    hostname text,
    status text,
    updated_at timestamptz not null default now()
);
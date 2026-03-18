create schema if not exists ops;

create table if not exists ops.job_queue (
    id bigint generated always as identity primary key,
    job_type text not null,
    payload jsonb not null default '{}'::jsonb,
    status text not null default 'pending',
    requested_by text,
    source text,
    requested_at timestamptz not null default now(),
    started_at timestamptz,
    finished_at timestamptz,
    worker_name text,
    result_message text,
    error_message text
);

create index if not exists idx_job_queue_status_requested_at
on ops.job_queue (status, requested_at);
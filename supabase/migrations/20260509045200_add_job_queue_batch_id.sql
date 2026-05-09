alter table ops.job_queue
add column if not exists batch_id uuid;

create index if not exists idx_job_queue_batch_id
on ops.job_queue (batch_id);


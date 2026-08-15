alter table ops.worker_heartbeat
  add column if not exists explorer_public_base_url text;

-- Register reachable stock-check URL on branch workers for LINE deep links.
alter table ops.worker_heartbeat
  add column if not exists public_base_url text;

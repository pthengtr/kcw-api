-- LINE companion links (Tiger Pay) use a separate LAN URL from stock-check.
alter table ops.worker_heartbeat
  add column if not exists companion_public_base_url text;

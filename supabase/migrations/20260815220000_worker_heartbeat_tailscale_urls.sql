alter table ops.worker_heartbeat
  add column if not exists tailscale_public_base_url text,
  add column if not exists companion_tailscale_base_url text,
  add column if not exists explorer_tailscale_base_url text;

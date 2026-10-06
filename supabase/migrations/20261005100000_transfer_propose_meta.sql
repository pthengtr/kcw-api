-- AI recommendation shown beside a transfer line. Does not change qty or status.

alter table transfer.need_list
  add column if not exists propose_meta jsonb null;

alter table transfer.lines
  add column if not exists propose_meta jsonb null;

notify pgrst, 'reload schema';

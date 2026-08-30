-- Bidirectional transfer: from_branch / to_branch on requests

alter table transfer.requests
  add column if not exists from_branch text not null default 'HQ',
  add column if not exists to_branch text not null default 'SYP';

update transfer.requests
set from_branch = 'HQ', to_branch = 'SYP'
where from_branch is null or to_branch is null;

create index if not exists transfer_requests_from_branch_status_idx
  on transfer.requests (from_branch, status);

create index if not exists transfer_requests_to_branch_status_idx
  on transfer.requests (to_branch, status);

-- Optional alias column for ship bill (keep tf_billno for compat)
alter table transfer.shipments
  add column if not exists ship_billno text;

update transfer.shipments
set ship_billno = tf_billno
where ship_billno is null and tf_billno is not null;

-- Billing note: optional company bank account shown to customer (not settle method).

alter table receive_note.note
  add column if not exists receive_bank_key text null;

comment on column receive_note.note.receive_bank_key is
  'Optional HQ receive bank key for billing note print (customer transfer target)';

comment on column receive_note.note.settle_method is
  'Legacy intended method at create; prefer receive_bank_key on notes. Actual settle at voucher.';

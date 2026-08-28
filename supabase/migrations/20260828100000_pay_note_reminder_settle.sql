-- Store payment method + company payout account on reminder after voucher is recorded.
alter table pay_note.reminder
  add column if not exists settle_method text,
  add column if not exists pay_bank text;

comment on column pay_note.reminder.settle_method is 'transfer | cheque | cash — set when voucher is recorded';
comment on column pay_note.reminder.pay_bank is 'Company payout account key (ktb_44244 | kbank_72355)';

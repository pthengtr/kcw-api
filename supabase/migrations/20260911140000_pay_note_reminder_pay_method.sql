-- Intended payment method is chosen when creating a billing note
-- (transfer | cheque). Confirmed / may change when the voucher is recorded
-- (transfer | cheque | cash). Existing nulls stay null (UI treats as transfer).

alter table pay_note.reminder
  alter column settle_method set default 'transfer';

comment on column pay_note.reminder.settle_method is
  'transfer | cheque | cash — intended at note create; confirmed when voucher is recorded';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'reminder_settle_method_chk'
  ) then
    alter table pay_note.reminder
      add constraint reminder_settle_method_chk
      check (settle_method is null or settle_method in ('transfer', 'cheque', 'cash'));
  end if;
end $$;

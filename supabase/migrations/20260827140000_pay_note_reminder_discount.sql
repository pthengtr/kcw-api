-- Discount is captured on the note (reminder), applied when voucher is posted.

alter table pay_note.reminder
  add column if not exists discount_mode text not null default 'amount',
  add column if not exists discount_input numeric(18, 4) not null default 0,
  add column if not exists discount_amount numeric(18, 4) not null default 0;

comment on column pay_note.reminder.discount_mode is 'amount = baht input; percent = %% of selected bill total';
comment on column pay_note.reminder.discount_input is 'raw user input (baht or percent)';
comment on column pay_note.reminder.discount_amount is 'resolved baht discount stored at note create';

do $$
begin
  if not exists (
    select 1 from pg_constraint
    where conname = 'reminder_discount_mode_chk'
  ) then
    alter table pay_note.reminder
      add constraint reminder_discount_mode_chk
      check (discount_mode in ('amount', 'percent'));
  end if;
end $$;

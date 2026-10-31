-- Receipt payment channel. Tax invoices leave this empty.
-- platform: marketplace collected the money. cod: cash on delivery.

alter table to_bill.invoices
  add column if not exists pay_via text null;

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'to_bill_invoices_pay_via_check'
  ) then
    alter table to_bill.invoices
      add constraint to_bill_invoices_pay_via_check
      check (pay_via is null or pay_via in ('platform', 'cod'));
  end if;
end $$;

notify pgrst, 'reload schema';

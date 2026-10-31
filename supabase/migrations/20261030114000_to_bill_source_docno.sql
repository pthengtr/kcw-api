-- A receipt records the tax invoice it was created from.

alter table to_bill.invoices
  add column if not exists source_docno text null;

notify pgrst, 'reload schema';

-- One open tax invoice (TO) and one open receipt (RVO) per TAD.
-- They are different documents. Void releases only that kind.

drop index if exists to_bill.to_bill_invoices_open_tad_idx;

create unique index if not exists to_bill_invoices_open_tad_kind_idx
  on to_bill.invoices (tad_billno, doc_kind)
  where status in ('draft', 'issued');

notify pgrst, 'reload schema';

-- Optional Low Stock (L / ICMAS.QTYMIN) override on shared waiting drafts.
-- Null means staff did not edit L; confirm keeps the live PARTS9 value.

alter table hq_po.waiting_drafts
  add column if not exists qtymin numeric null;

alter table hq_po.waiting_extra_drafts
  add column if not exists qtymin numeric null;

alter table hq_po.waiting_drafts
  drop constraint if exists hq_po_waiting_drafts_qtymin_pos;
alter table hq_po.waiting_drafts
  add constraint hq_po_waiting_drafts_qtymin_pos
  check (qtymin is null or qtymin > 0);

alter table hq_po.waiting_extra_drafts
  drop constraint if exists hq_po_waiting_extra_drafts_qtymin_pos;
alter table hq_po.waiting_extra_drafts
  add constraint hq_po_waiting_extra_drafts_qtymin_pos
  check (qtymin is null or qtymin > 0);

notify pgrst, 'reload schema';

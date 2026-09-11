-- Phase 3b: track original request BCODE when shipment ships a substitute (ส่งแทน)

alter table transfer.shipment_lines
  add column if not exists requested_bcode text null;

comment on column transfer.shipment_lines.requested_bcode is
  'Request-line BCODE when shipment line bcode is a substitute peer (ส่งแทน); null = same as bcode';

update transfer.shipment_lines
set requested_bcode = bcode
where requested_bcode is null;

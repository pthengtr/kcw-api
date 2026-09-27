-- Collapse transfer statuses to requested / prepared / received.
-- draft and cancelled headers are left as stored.
-- A short ship whose prepared qty is already in becomes received.

update transfer.lines
set line_status = case
  when cancelled_at is not null and qty_prepared <= 0 then 'cancelled'
  when qty_prepared > 0 and qty_received >= qty_prepared then 'received'
  when qty_prepared > 0 then 'prepared'
  else 'open'
end;

update transfer.requests r
set status = s.next_status
from (
  select
    r2.transfer_id,
    case
      when not exists (
        select 1
        from transfer.lines l
        where l.transfer_id = r2.transfer_id
          and not (l.cancelled_at is not null and l.qty_prepared <= 0)
      ) and exists (
        select 1 from transfer.lines l where l.transfer_id = r2.transfer_id
      ) then 'cancelled'
      when exists (
        select 1
        from transfer.lines l
        where l.transfer_id = r2.transfer_id
          and l.qty_prepared > l.qty_received
          and not (l.cancelled_at is not null and l.qty_prepared <= 0)
      ) then 'prepared'
      when exists (
        select 1
        from transfer.lines l
        where l.transfer_id = r2.transfer_id
          and l.qty_prepared > 0
          and l.qty_received >= l.qty_prepared
      ) then 'received'
      when exists (
        select 1 from transfer.shipments s where s.transfer_id = r2.transfer_id
      ) then 'prepared'
      else 'requested'
    end as next_status
  from transfer.requests r2
  where r2.status not in ('draft', 'cancelled')
) s
where r.transfer_id = s.transfer_id
  and r.status is distinct from s.next_status;

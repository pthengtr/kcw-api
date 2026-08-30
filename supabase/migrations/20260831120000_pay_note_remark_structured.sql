-- Structured remark: bill month + optional extra; remark remains composed display string.

alter table pay_note.reminder
  add column if not exists bill_month date,
  add column if not exists remark_extra text not null default '';

comment on column pay_note.reminder.bill_month is
  'Bill month (first day of month) for board filter; not written to KSS';
comment on column pay_note.reminder.remark_extra is
  'Optional suffix after standard {acctno}-บิลเดือน mm/yyyy pattern';

-- Backfill from existing composed remark text.
update pay_note.reminder r
set
  bill_month = to_date(
    (sub.m)[3] || '-' || lpad((sub.m)[2], 2, '0') || '-01',
    'YYYY-MM-DD'
  ),
  remark_extra = coalesce(trim((sub.m)[4]), '')
from (
  select
    acctno,
    noteno,
    regexp_match(
      remark,
      '^(.+?)-บิลเดือน\s+(\d{1,2})/(\d{4})(?:\s*/\s*(.+))?$'
    ) as m
  from pay_note.reminder
  where remark <> ''
) sub
where r.acctno = sub.acctno
  and r.noteno = sub.noteno
  and sub.m is not null;

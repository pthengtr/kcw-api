-- Optional KBIZ transfer reminder on pay_note.reminder (column may exist from initial schema).

alter table pay_note.reminder
  add column if not exists kbiz_datetime timestamptz null;

comment on column pay_note.reminder.kbiz_datetime is
  'Optional scheduled KBIZ transfer datetime (operator reminder; not written to KSS).';

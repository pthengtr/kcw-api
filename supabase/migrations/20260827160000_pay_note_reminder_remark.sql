-- Free-text remark for the pay board (PVMAS has no remark column).

alter table pay_note.reminder
  add column if not exists remark text not null default '';

comment on column pay_note.reminder.remark is 'operator note shown on pending board; not written to KSS PVMAS';

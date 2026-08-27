-- due_date is a calendar day (Bangkok business date), not a timestamp.
-- timestamptz midnight +07 was stored as previous-day UTC and UI .slice(0,10) showed -1 day.

alter table pay_note.reminder
  alter column due_date type date
  using ((due_date at time zone 'Asia/Bangkok')::date);

-- Header choice on a full invoice: tax invoice (TO) or receipt (RVO).
-- Each series has its own gapless monthly counter. Existing counters are TO.

alter table to_bill.invoices
  add column if not exists doc_kind text not null default 'to';

update to_bill.invoices
set doc_kind = 'rvo'
where coalesce(docno, '') like 'RVO%'
  and doc_kind <> 'rvo';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'to_bill_invoices_doc_kind_check'
  ) then
    alter table to_bill.invoices
      add constraint to_bill_invoices_doc_kind_check
      check (doc_kind in ('to', 'rvo'));
  end if;
end $$;

alter table to_bill.counters
  add column if not exists series text not null default 'TO';

do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'to_bill_counters_series_check'
  ) then
    alter table to_bill.counters
      add constraint to_bill_counters_series_check
      check (series in ('TO', 'RVO'));
  end if;
end $$;

do $$
declare
  key_count int;
begin
  select count(*)
  into key_count
  from pg_constraint c
  join pg_class t on t.oid = c.conrelid
  join pg_namespace n on n.oid = t.relnamespace
  join lateral unnest(c.conkey) as att(attnum) on true
  where n.nspname = 'to_bill'
    and t.relname = 'counters'
    and c.contype = 'p';

  if key_count = 1 then
    alter table to_bill.counters drop constraint counters_pkey;
    alter table to_bill.counters
      add constraint counters_pkey primary key (series, yymm);
  end if;
end $$;

notify pgrst, 'reload schema';

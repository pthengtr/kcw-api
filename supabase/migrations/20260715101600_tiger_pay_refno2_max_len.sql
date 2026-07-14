-- Convert payment_attempt ids from uuid to text so Tiger RefNo2 (<=20 chars) can
-- use the same id. Safe to re-run only when the uuid->text repair is needed.

do $$
begin
    if exists (
        select 1
        from information_schema.columns
        where table_schema = 'tiger_pay'
          and table_name = 'payment_attempt'
          and column_name = 'id'
          and data_type = 'uuid'
    ) then
        alter table tiger_pay.payment_event
            drop constraint if exists payment_event_payment_attempt_id_fkey;

        alter table tiger_pay.payment_attempt
            alter column id type text using id::text;

        alter table tiger_pay.payment_event
            alter column payment_attempt_id type text using payment_attempt_id::text;

        alter table tiger_pay.payment_event
            add constraint payment_event_payment_attempt_id_fkey
            foreign key (payment_attempt_id)
            references tiger_pay.payment_attempt (id)
            on delete cascade;
    end if;

    begin
        alter table tiger_pay.payment_attempt
            add constraint payment_attempt_id_max_len
            check (char_length(id) <= 20);
    exception
        when duplicate_object then null;
        when undefined_table then null;
    end;
end $$;

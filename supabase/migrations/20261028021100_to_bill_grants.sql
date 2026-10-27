-- Read access for signed-in kcw-v2 users. Writes stay on the kcw-api database role.
-- anon is not granted.

grant usage on schema to_bill to authenticated, service_role;

grant select on to_bill.invoices, to_bill.lines to authenticated;
grant all on all tables in schema to_bill to service_role;
grant all on all sequences in schema to_bill to service_role;
grant execute on function to_bill.caller_sees_internal() to authenticated, service_role;

revoke all on function to_bill.caller_sees_internal() from public;

alter default privileges for role postgres in schema to_bill
  grant select on tables to authenticated;
alter default privileges for role postgres in schema to_bill
  grant all on tables to service_role;
alter default privileges for role postgres in schema to_bill
  grant all on sequences to service_role;

alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note, transfer, catalog, ops, hq_po, to_bill';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

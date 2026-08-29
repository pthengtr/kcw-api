grant usage on schema transfer to anon, authenticated, service_role;

grant all on all tables in schema transfer to anon, authenticated, service_role;
grant all on all sequences in schema transfer to anon, authenticated, service_role;
grant all on all routines in schema transfer to anon, authenticated, service_role;

alter default privileges for role postgres in schema transfer
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema transfer
  grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema transfer
  grant all on routines to anon, authenticated, service_role;

alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note, transfer';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

grant usage on schema hq_po to anon, authenticated, service_role;

grant all on all tables in schema hq_po to anon, authenticated, service_role;
grant all on all sequences in schema hq_po to anon, authenticated, service_role;
grant all on all routines in schema hq_po to anon, authenticated, service_role;

alter default privileges for role postgres in schema hq_po
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema hq_po
  grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema hq_po
  grant all on routines to anon, authenticated, service_role;

alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note, transfer, catalog, ops, hq_po';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

grant usage on schema receive_note to anon, authenticated, service_role;

grant all on all tables in schema receive_note to anon, authenticated, service_role;
grant all on all sequences in schema receive_note to anon, authenticated, service_role;
grant all on all routines in schema receive_note to anon, authenticated, service_role;

alter default privileges for role postgres in schema receive_note
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema receive_note
  grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema receive_note
  grant all on routines to anon, authenticated, service_role;

alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note, receive_note';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

-- Expose pay_note on PostgREST (same pattern as tiger_pay / bank / kb).
-- Fixes PGRST106: "The schema must be one of the following: ..."

grant usage on schema pay_note to anon, authenticated, service_role;

grant all on all tables in schema pay_note to anon, authenticated, service_role;
grant all on all sequences in schema pay_note to anon, authenticated, service_role;
grant all on all routines in schema pay_note to anon, authenticated, service_role;

alter default privileges for role postgres in schema pay_note
  grant all on tables to anon, authenticated, service_role;
alter default privileges for role postgres in schema pay_note
  grant all on sequences to anon, authenticated, service_role;
alter default privileges for role postgres in schema pay_note
  grant all on routines to anon, authenticated, service_role;

-- Include every schema already exposed on this project, plus pay_note.
alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

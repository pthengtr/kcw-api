-- Expose pay_note to service_role via grants (CRUD uses SQLAlchemy on HQ box).
-- Also prepare PostgREST if schema is later added to dashboard Exposed schemas.

grant usage on schema pay_note to postgres, service_role;
grant all on all tables in schema pay_note to service_role;
grant all on all sequences in schema pay_note to service_role;
alter default privileges in schema pay_note
  grant all on tables to service_role;
alter default privileges in schema pay_note
  grant all on sequences to service_role;

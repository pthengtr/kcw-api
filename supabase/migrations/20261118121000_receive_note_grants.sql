grant usage on schema receive_note to postgres, service_role;
grant all on all tables in schema receive_note to service_role;
grant all on all sequences in schema receive_note to service_role;
alter default privileges in schema receive_note
  grant all on tables to service_role;
alter default privileges in schema receive_note
  grant all on sequences to service_role;

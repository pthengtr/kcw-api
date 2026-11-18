-- receive_note_expose_postgrest (20261118122000) overwrote pgrst.db_schemas and
-- dropped transfer (+ catalog, ops, hq_po, hq_receive, to_bill). Transfer UI then
-- 500s with PGRST106 on /transfer/api/counts.

alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note, transfer, catalog, ops, hq_po, hq_receive, to_bill, receive_note';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

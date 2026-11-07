-- hq_receive grants accidentally dropped to_bill from PostgREST schemas.
-- VAT register and to-bills pages need schema("to_bill") via service_role.

alter role authenticator set pgrst.db_schemas =
  'public, graphql_public, kb, bank, tiger_pay, curated_kcw, raw_kcw, pay_note, transfer, catalog, ops, hq_po, hq_receive, to_bill';

notify pgrst, 'reload config';
notify pgrst, 'reload schema';

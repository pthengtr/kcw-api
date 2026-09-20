-- kcw-v2 daily status reads POS submitter / voucher counts through PostgREST.
-- Companion uses SQLAlchemy as the DB owner, so these tables were never granted
-- to service_role. Missing SELECT made /api/bank/tiger-pay/daily 500.

grant usage on schema tiger_pay to service_role, authenticated;

grant select on table tiger_pay.payment_attempt to service_role;
grant select on table tiger_pay.voucher_attempt to service_role;
grant select on table tiger_pay.payment_event to service_role;
grant select on table tiger_pay.voucher_event to service_role;

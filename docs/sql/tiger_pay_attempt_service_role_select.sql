-- Mirror of supabase/migrations/20260920104500_tiger_pay_attempt_service_role_select.sql
grant usage on schema tiger_pay to service_role, authenticated;

grant select on table tiger_pay.payment_attempt to service_role;
grant select on table tiger_pay.voucher_attempt to service_role;
grant select on table tiger_pay.payment_event to service_role;
grant select on table tiger_pay.voucher_event to service_role;

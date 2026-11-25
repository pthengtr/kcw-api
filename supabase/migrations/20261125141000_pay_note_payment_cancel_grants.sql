-- Expose payment_cancel to PostgREST / service_role after create.

grant all on table pay_note.payment_cancel to anon, authenticated, service_role;

notify pgrst, 'reload schema';

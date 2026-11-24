-- Ensure receipt_edit_audit is granted and visible to PostgREST after create.
-- Missing schema-cache reload caused detail/"ดู" and PATCH /api/vouchers/meta
-- to 500 with PGRST205 (table not in schema cache).

grant all on table receive_note.receipt_edit_audit to anon, authenticated, service_role;

notify pgrst, 'reload schema';

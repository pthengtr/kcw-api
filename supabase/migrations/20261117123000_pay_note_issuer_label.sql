-- Snapshotted printable preparer name for pay-note / payment-voucher sheets.
alter table pay_note.reminder
  add column if not exists issuer_label text null;

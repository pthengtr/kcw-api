-- Align receive_note.note with pay_note.reminder fields used by AP-like pending UX.
-- Skip vendor_bank / kbiz / bank_id (AR create has no vendor-bank book).

alter table receive_note.note
  add column if not exists discount_mode text not null default 'amount',
  add column if not exists discount_input numeric(18, 4) not null default 0,
  add column if not exists discount_amount numeric(18, 4) not null default 0,
  add column if not exists settle_method text null,
  add column if not exists bill_month date null,
  add column if not exists remark_extra text not null default '',
  add column if not exists issuer_label text null;

alter table receive_note.note
  drop constraint if exists receive_note_note_discount_mode_check;

alter table receive_note.note
  add constraint receive_note_note_discount_mode_check
  check (discount_mode in ('amount', 'percent'));

alter table receive_note.note
  drop constraint if exists receive_note_note_settle_method_check;

alter table receive_note.note
  add constraint receive_note_note_settle_method_check
  check (
    settle_method is null
    or settle_method in ('transfer', 'cheque', 'cash')
  );

comment on column receive_note.note.discount_amount is
  'Resolved baht discount from create/edit; shown on receive modal to prevent double discount';
comment on column receive_note.note.settle_method is
  'Intended method at create (transfer|cheque); cash confirmed at voucher';

-- Central staff legal names keyed by LINE user id (not display name).
-- Shared by all services; edit rows without redeploying code.
-- Document print uses a snapshotted issuer_label written at issue time.

create table if not exists ops.staff_profiles (
  line_user_id text primary key,
  full_name text not null,
  nickname text not null,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint ops_staff_profiles_full_name_check
    check (char_length(btrim(full_name)) > 0),
  constraint ops_staff_profiles_nickname_check
    check (char_length(btrim(nickname)) > 0)
);

create index if not exists ops_staff_profiles_active_idx
  on ops.staff_profiles (is_active)
  where is_active;

grant select on ops.staff_profiles to authenticated;
grant all on ops.staff_profiles to service_role;

-- Snapshotted print name for PARTS9 bills (TAD / CNTAD).
-- SALE on SIMAS stays LINE display; print reads issuer_label here.
create table if not exists online_sale.doc_issuers (
  billno text primary key,
  line_user_id text null,
  line_display_name text null,
  issuer_label text not null,
  created_at timestamptz not null default now(),
  constraint online_sale_doc_issuers_label_check
    check (char_length(btrim(issuer_label)) > 0)
);

create index if not exists online_sale_doc_issuers_line_idx
  on online_sale.doc_issuers (line_user_id);

grant select on online_sale.doc_issuers to authenticated;
grant all on online_sale.doc_issuers to service_role;

-- Snapshotted print labels for TO/RVO signature blocks.
alter table to_bill.invoices
  add column if not exists issuer_label text null,
  add column if not exists approver_label text null;

-- Seed from known LINE user ids in ops.line_access (matched at migration time).
insert into ops.staff_profiles (line_user_id, full_name, nickname)
values
  ('U7fa69960556c92b529db58541ed7b1e2', 'พรอนันต์ มานะ', 'เจี๊ยบ'),
  ('U88f0e18f1d4bf865eb360db0e5f7c839', 'ปิยะนุช นันตาบุตร', 'เมย์'),
  ('Ub11401984b737ca3079621aae9aefbfd', 'สราวุฒิ พิกุลแกม', 'พี่นก'),
  ('U19a6a2d22a54ef435deb6571c0178efd', 'ณัชชา นึกแจ้ง', 'มิ้น'),
  ('Ufbe823c2e35aa9c51614bcb7204e9d2f', 'ฉัตรชัย สุวรรณกูล', 'หนุ่ย'),
  ('Ua542a4e8651997f5d051cbe60b80ad63', 'จิดาภา กระจาย', 'การ์ตูน'),
  ('Ue782dd6253d75c3049c21a12b66bae18', 'รณชัย พงษ์ปาน', 'อ้น'),
  ('U6b2a50661a87b047a8652fb5391f8715', 'ธนวรรณ เดชกุญชร', 'มะเหมี่ยว'),
  ('Uf9d92568307ce2e787cd002305c5402a', 'ธิติ จันทร์พราหมณ์', 'ช๊อปเปอร์'),
  ('Ue6f27097d21e4879ab753b9b6c5ff360', 'ศุภิสรา เดชกุญชร', 'เบ้นซ์'),
  ('U351ac819b4232949ef6a4d29c3a8d0cf', 'อาทิตยา หมื่นไสยาสน์', 'พลอย'),
  ('U8bff25336fcdf7bae3deec954f3e0337', 'สุริยะ โกศัลยกุล', 'บอส'),
  ('Uf7a2090c68f42106241864e4d62b8301', 'วัจน์กร นาคทอง', 'เบลล์'),
  ('Ub3ed60592564bb10ac037435f98e1727', 'กัญญาวีร์ ปิ่นทอง', 'กวาง'),
  ('U007c09fef7b54544199fc76ce39b46ad', 'มัญชุนันท์ คำลา', 'อ้อน'),
  ('U67bbcdc95de1d693bcdabfade4b5e59d', 'อานนท์ ชูสวัสดิ์', 'นุ'),
  ('Ub1bf1f0f92a343b8681127fbfc3dd127', 'จิตติมา ทิมเทศ', 'อุ้ม'),
  ('Ua0b1c6ab2fe34cbcf1e4cc2272440419', 'ญดาพร นิมวรรณ์', 'อุ๋มอิ๋ม'),
  ('Uaf623e21e67d58d061ad0d8f8178187a', 'นพดล โกศัลยกุล', 'บูม')
on conflict (line_user_id) do update
set
  full_name = excluded.full_name,
  nickname = excluded.nickname,
  is_active = true,
  updated_at = now();

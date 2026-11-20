-- Add legal names for peung / PHU / January Ice (document issuer print).

insert into ops.staff_profiles (line_user_id, full_name, nickname)
values
  ('U7ad4da99b4438917dbe13684f2d9aafb', 'นฤมล วิทยผโลทัย', 'ผึ้ง'),
  ('U3357ce0387b5355980d710e3f9feed0e', 'ณัฐพล วิทยผโลทัย', 'ภู่'),
  ('Ua994bb2f6f93dd003276d6b17196b6c1', 'มกรา มณีกุล', 'ไอซ์')
on conflict (line_user_id) do update
set
  full_name = excluded.full_name,
  nickname = excluded.nickname,
  is_active = true,
  updated_at = now();

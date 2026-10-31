-- Remember why a ค้างรับ line was sent back to รอสั่ง.

create table if not exists hq_po.release_marks (
  iclow_id bigint primary key,
  bcode text not null,
  kind text not null,
  previous_vendor text not null default '',
  previous_vendor_name text null,
  previous_docno text null,
  created_at timestamptz not null default now(),
  constraint hq_po_release_marks_kind_check check (kind in ('switch', 'reorder'))
);

grant all on hq_po.release_marks to anon, authenticated, service_role;

notify pgrst, 'reload schema';

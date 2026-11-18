-- Snapshotted TAD/CNTAD print HTML from ขายออนไลน์ for the VAT register.
-- Same sheet staff print from online-sale; VAT embeds it instead of uploads.

create table if not exists online_sale.bill_sheets (
  billno text primary key,
  kind text not null,
  html text not null,
  updated_at timestamptz not null default now(),
  constraint online_sale_bill_sheets_kind_check
    check (kind in ('tad', 'cntad')),
  constraint online_sale_bill_sheets_html_check
    check (char_length(btrim(html)) > 0)
);

create index if not exists online_sale_bill_sheets_kind_idx
  on online_sale.bill_sheets (kind);

grant select on online_sale.bill_sheets to authenticated;
grant all on online_sale.bill_sheets to service_role;

-- Let the VAT register load snapshotted online-sale TAD/CNTAD HTML without
-- exposing the whole online_sale schema to PostgREST.
create or replace function public.fn_vat_online_bill_html(p_billno text)
returns text
language sql
stable
security definer
set search_path = online_sale, public, pg_temp
as $$
  select s.html
  from online_sale.bill_sheets s
  where s.billno = upper(btrim(coalesce(p_billno, '')))
  limit 1;
$$;

comment on function public.fn_vat_online_bill_html(text) is
  'Return snapshotted TAD/CNTAD print HTML from online_sale.bill_sheets for the VAT register.';

grant execute on function public.fn_vat_online_bill_html(text) to authenticated, service_role;

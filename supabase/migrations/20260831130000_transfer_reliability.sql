-- Transfer reliability: receive idempotency + atomic quantity bumps

create table if not exists transfer.receipts (
  receipt_id uuid primary key default gen_random_uuid(),
  shipment_id uuid not null references transfer.shipments (shipment_id) on delete cascade,
  client_token text not null,
  receive_billno text not null,
  created_at timestamptz not null default now(),
  constraint transfer_receipts_client_token_key unique (client_token)
);

create index if not exists transfer_receipts_shipment_id_idx on transfer.receipts (shipment_id);

grant all on transfer.receipts to anon, authenticated, service_role;

create or replace function transfer.bump_line_prepared(p_line_id uuid, p_qty numeric)
returns transfer.lines
language plpgsql
as $$
declare
  result transfer.lines;
begin
  update transfer.lines
  set qty_prepared = qty_prepared + p_qty,
      updated_at = now()
  where line_id = p_line_id
    and qty_prepared + p_qty <= qty_requested
  returning * into result;
  if not found then
    raise exception 'bump_line_prepared_failed';
  end if;
  return result;
end;
$$;

create or replace function transfer.bump_line_received(p_line_id uuid, p_qty numeric)
returns transfer.lines
language plpgsql
as $$
declare
  result transfer.lines;
begin
  update transfer.lines
  set qty_received = qty_received + p_qty,
      updated_at = now()
  where line_id = p_line_id
    and qty_received + p_qty <= qty_prepared
  returning * into result;
  if not found then
    raise exception 'bump_line_received_failed';
  end if;
  return result;
end;
$$;

create or replace function transfer.bump_shipment_line_received(
  p_shipment_line_id uuid,
  p_qty numeric
)
returns transfer.shipment_lines
language plpgsql
as $$
declare
  result transfer.shipment_lines;
begin
  update transfer.shipment_lines
  set qty_received = qty_received + p_qty
  where shipment_line_id = p_shipment_line_id
    and qty_received + p_qty <= qty_shipped
  returning * into result;
  if not found then
    raise exception 'bump_shipment_line_received_failed';
  end if;
  return result;
end;
$$;

grant execute on function transfer.bump_line_prepared(uuid, numeric) to anon, authenticated, service_role;
grant execute on function transfer.bump_line_received(uuid, numeric) to anon, authenticated, service_role;
grant execute on function transfer.bump_shipment_line_received(uuid, numeric) to anon, authenticated, service_role;

alter default privileges for role postgres in schema transfer
  grant all on tables to anon, authenticated, service_role;

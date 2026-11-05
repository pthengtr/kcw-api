-- Evidence photos of goods prepared for a transfer bill.

create table if not exists transfer.shipment_photos (
  photo_id uuid primary key default gen_random_uuid(),
  transfer_id uuid not null references transfer.requests (transfer_id) on delete cascade,
  shipment_id uuid null references transfer.shipments (shipment_id) on delete cascade,
  storage_path text not null,
  created_by text null,
  created_at timestamptz not null default now()
);

create index if not exists transfer_shipment_photos_transfer_id_idx
  on transfer.shipment_photos (transfer_id);

create index if not exists transfer_shipment_photos_shipment_id_idx
  on transfer.shipment_photos (shipment_id);

grant all on table transfer.shipment_photos to anon, authenticated, service_role;

notify pgrst, 'reload schema';

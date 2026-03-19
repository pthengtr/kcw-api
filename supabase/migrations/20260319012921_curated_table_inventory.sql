create table if not exists curated_kcw.inventory_qty_latest (
    branch text not null,
    bcode text not null,
    qty numeric,
    updated_at timestamptz not null default now(),
    primary key (branch, bcode)
);

create index if not exists idx_inventory_qty_latest_bcode
on curated_kcw.inventory_qty_latest (bcode);
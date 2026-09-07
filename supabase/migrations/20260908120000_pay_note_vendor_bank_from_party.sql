-- One-time copy of public.party_bank_info into pay_note.vendor_bank.
-- Public is the up-to-date source for this migration only. Pay-notes does not
-- read or write public.party_bank_info at runtime after this. Do not drop public.

alter table pay_note.vendor_bank
  add column if not exists legacy_bank_info_uuid uuid;

create unique index if not exists vendor_bank_legacy_bank_info_uuid_uidx
  on pay_note.vendor_bank (legacy_bank_info_uuid)
  where legacy_bank_info_uuid is not null;

comment on column pay_note.vendor_bank.legacy_bank_info_uuid is
  'One-time copy key from public.party_bank_info.bank_info_uuid. Not kept in sync after this migration.';

-- Link already-seeded rows (acctno + account number) and overwrite from public.
with candidates as (
  select
    vb.bank_id,
    b.bank_info_uuid
  from public.party_bank_info b
  join public.party p on p.party_uuid = b.party_uuid
  join pay_note.vendor_bank vb
    on vb.acctno = trim(p.party_code)
   and trim(vb.bank_account_number) = trim(b.bank_account_number)
  where p.party_code is not null
    and trim(p.party_code) <> ''
    and coalesce(trim(b.bank_name), '') <> ''
    and coalesce(trim(b.bank_account_name), '') <> ''
    and coalesce(trim(b.bank_account_number), '') <> ''
    and vb.legacy_bank_info_uuid is null
    and not exists (
      select 1
      from pay_note.vendor_bank taken
      where taken.legacy_bank_info_uuid = b.bank_info_uuid
    )
),
picked_uuid as (
  select distinct on (bank_info_uuid)
    bank_id,
    bank_info_uuid
  from candidates
  order by bank_info_uuid, bank_id
),
picked as (
  select distinct on (bank_id)
    bank_id,
    bank_info_uuid
  from picked_uuid
  order by bank_id, bank_info_uuid
)
update pay_note.vendor_bank vb
set legacy_bank_info_uuid = picked.bank_info_uuid
from picked
where vb.bank_id = picked.bank_id
  and vb.legacy_bank_info_uuid is null;

-- Public wins for every linked row (including rows linked above).
update pay_note.vendor_bank vb
set
  acctno = trim(p.party_code),
  bank_name = trim(b.bank_name),
  bank_account_name = trim(b.bank_account_name),
  bank_account_number = trim(b.bank_account_number),
  bank_branch = nullif(trim(coalesce(b.bank_branch, '')), ''),
  account_type = case
    when upper(trim(b.account_type::text)) in ('CHECKING', 'SAVINGS', 'OTHER')
      then upper(trim(b.account_type::text))
    else 'OTHER'
  end,
  is_default = coalesce(b.is_default, false),
  updated_at = now()
from public.party_bank_info b
join public.party p on p.party_uuid = b.party_uuid
where vb.legacy_bank_info_uuid = b.bank_info_uuid
  and p.party_code is not null
  and trim(p.party_code) <> ''
  and coalesce(trim(b.bank_name), '') <> ''
  and coalesce(trim(b.bank_account_name), '') <> ''
  and coalesce(trim(b.bank_account_number), '') <> '';

-- Insert public banks that were never copied (or whose account number changed).
insert into pay_note.vendor_bank (
  acctno,
  bank_name,
  bank_account_name,
  bank_account_number,
  bank_branch,
  account_type,
  is_default,
  legacy_bank_info_uuid
)
select
  trim(p.party_code),
  trim(b.bank_name),
  trim(b.bank_account_name),
  trim(b.bank_account_number),
  nullif(trim(coalesce(b.bank_branch, '')), ''),
  case
    when upper(trim(b.account_type::text)) in ('CHECKING', 'SAVINGS', 'OTHER')
      then upper(trim(b.account_type::text))
    else 'OTHER'
  end,
  coalesce(b.is_default, false),
  b.bank_info_uuid
from public.party_bank_info b
join public.party p on p.party_uuid = b.party_uuid
where p.party_code is not null
  and trim(p.party_code) <> ''
  and coalesce(trim(b.bank_name), '') <> ''
  and coalesce(trim(b.bank_account_name), '') <> ''
  and coalesce(trim(b.bank_account_number), '') <> ''
  and not exists (
    select 1
    from pay_note.vendor_bank vb
    where vb.legacy_bank_info_uuid = b.bank_info_uuid
  );

-- One default per AP. Prefer a public-linked default, then stable uuid.
with ranked as (
  select
    bank_id,
    row_number() over (
      partition by acctno
      order by
        is_default desc,
        (legacy_bank_info_uuid is null),
        legacy_bank_info_uuid,
        bank_id
    ) as rn
  from pay_note.vendor_bank
  where is_default
)
update pay_note.vendor_bank vb
set
  is_default = false,
  updated_at = now()
from ranked
where vb.bank_id = ranked.bank_id
  and ranked.rn > 1;

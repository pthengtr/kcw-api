-- Pay notes ops overlay (KSS holds ledger; this schema = reminder + vendor banks)

create schema if not exists pay_note;

create table if not exists pay_note.vendor_bank (
  bank_id uuid primary key default gen_random_uuid(),
  acctno text not null,
  bank_name text not null,
  bank_account_name text not null,
  bank_account_number text not null,
  bank_branch text null,
  account_type text not null default 'OTHER',
  is_default boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists vendor_bank_acctno_idx on pay_note.vendor_bank (acctno);

create table if not exists pay_note.reminder (
  acctno text not null,
  noteno text not null,
  due_date timestamptz not null,
  bank_id uuid not null references pay_note.vendor_bank (bank_id),
  kbiz_datetime timestamptz null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  created_by text null,
  primary key (acctno, noteno)
);

create index if not exists reminder_due_date_idx on pay_note.reminder (due_date);

-- Seed vendor banks from legacy party master (party_code = APMAS ACCTNO)
insert into pay_note.vendor_bank (
  acctno,
  bank_name,
  bank_account_name,
  bank_account_number,
  bank_branch,
  account_type,
  is_default
)
select
  trim(p.party_code),
  b.bank_name,
  b.bank_account_name,
  b.bank_account_number,
  b.bank_branch,
  coalesce(nullif(trim(b.account_type::text), ''), 'OTHER'),
  coalesce(b.is_default, false)
from public.party_bank_info b
join public.party p on p.party_uuid = b.party_uuid
where p.party_code is not null
  and trim(p.party_code) <> ''
  and not exists (
    select 1
    from pay_note.vendor_bank vb
    where vb.acctno = trim(p.party_code)
      and vb.bank_account_number = b.bank_account_number
  );

-- Worker heartbeat URLs for pay-notes LAN service (port 8791)
alter table ops.worker_heartbeat
  add column if not exists pay_notes_public_base_url text,
  add column if not exists pay_notes_tailscale_base_url text;

-- Allow marketplace order ids up to TikTok's 18 chars (was hard-capped at 15).
-- App enforces exact lengths: TikTok 18 / Lazada 16 / Shopee 14.

alter table online_sale.drafts
  drop constraint if exists online_sale_drafts_po_len_check;

alter table online_sale.drafts
  add constraint online_sale_drafts_po_len_check
  check (
    char_length(btrim(online_po)) > 0
    and char_length(online_po) <= 30
  );

-- Allow many drafts / TADs to share one online order number (many-to-one).
-- Duplicate PO is a soft UI warning only — no longer a unique constraint.

drop index if exists online_sale.online_sale_drafts_open_po_idx;

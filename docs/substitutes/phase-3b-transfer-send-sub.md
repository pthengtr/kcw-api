# Phase 3b — Transfer prepare ส่งแทน (write path)

**Cursor Auto handoff.** Requires Phase 3a hints. See [plan.md](plan.md). Highest-risk phase — keep scope tight.

## Domain lock

```
PROJECT: kcw-api / kcw-transfer (:8792)
DOMAIN: Preparer ships a substitute peer BCODE against an original request line (ส่งแทน)
NOT THIS:
  - Explorer group management (Phase 2)
  - Changing QTYMIN
  - Bank transfer / pay-notes
  - Auto-substitute without preparer action
THAI: ส่งแทน = ship peer; จัดแล้ว = prepare+TF; รับแล้ว = receive
```

## Goal

End-to-end: prepare can choose a group peer, TF ships that peer’s `BCODE`, request line fulfillment counts against the original line, receive/stickers work for shipped SKU.

## Out of scope / FORBIDDEN

- Silent auto-pick of substitute without UI confirmation
- Multi-substitute partial splits beyond what existing partial prepare already allows (one ship_as per line per wave is enough)
- Redesigning full transfer UI

## Read first

- Phase 3a substitute JSON on suggest/prepare
- `app/routers/transfer.py` prepare endpoint body
- `src/transfer/db.py` shipment_lines create
- `src/transfer/writers/ship_simas.py` (what BCODE goes to SIDET)
- `supabase/migrations/20260829120000_transfer_schema.sql` — `unique(transfer_id, bcode)` on lines
- Receive + sticker paths keyed by shipped bcode
- `src/transfer/state.py` can_action rules

## Work checklist

1. **API contract:** prepare line item gains optional `ship_as_bcode`.
   - Default: null → ship request line `bcode` (today’s behavior).
   - If set: must be same substitute group as line `bcode`; must exist on ship-from ICMAS; `QTYOH2` checks use **ship_as** stock.
2. **Clash rule:** if `ship_as_bcode` is already another **request line** on the same transfer, reject with clear error **or** documented merge behavior (pick one; prefer reject in v1).
3. **Persistence:**
   - `shipment_lines.bcode` = shipped SKU
   - Store `requested_bcode` on shipment line **or** rely on `line_id` + event payload — prefer explicit column if migration is cheap
   - Event `substitute_ship` `{line_id, from_bcode, to_bcode, qty}`
4. **Writer:** SIDET/TF uses shipped BCODE + descr from that SKU.
5. **UI prepare:** peer picker (from Phase 3a list) → sets `ship_as_bcode`; show “ส่งแทน: {bcode}” before confirm.
6. **Receive/stickers:** confirm they use shipment line bcode; add UI note when substituted.
7. **Tests:** validation (not in group → 400); writer called with alt bcode; clash reject; non-substitute prepare unchanged.

## Acceptance gate

```bash
cd /home/hqadmin/projects/kcw-api && .venv/bin/python -m pytest tests/test_transfer.py tests/test_substitutes.py -q
```

Manual / staged check:

- [ ] Prepare with `ship_as_bcode` creates TF for alt SKU (needs live PARTS9 + writers on — ops staged)
- [ ] Original request line prepared qty increases
- [ ] Receive against shipment succeeds for alt SKU
- [x] Prepare without substitute still works (unit/regression)
- [x] pytest green
- [x] Migrations applied on Supabase (`catalog_substitutes`, `transfer_shipment_requested_bcode`)

## Delivered (Phase 3b)

| Piece | Where |
|-------|--------|
| Migration | `supabase/migrations/20260910130000_transfer_shipment_requested_bcode.sql` |
| Validation | `src/substitutes/ship_as.py` — `resolve_ship_as` |
| Prepare API | `api_prepare` resolves `ship_as_bcode` → writer `bcode` + `requested_bcode` |
| Persist | `add_shipment_lines` writes `requested_bcode`; event `substitute_ship` |
| Writer | unchanged — uses resolved `lines[].bcode` (alt SKU) |
| UI prepare | peer `<select>` + confirm “ส่งแทน: …” |
| UI receive | `substituted` / `requested_bcode` note via `fmtSubstitutedRecv` |

## Stop here

Next: [phase-4-docs-ops.md](phase-4-docs-ops.md).

## Handoff to Phase 4

### API (prepare line)

| Field | Meaning |
|-------|---------|
| `line_id` | Request line (fulfillment still bumps this line) |
| `qty_ship` | Qty on this wave |
| `ship_as_bcode` | Optional peer BCODE; omit/null/same-as-request = no substitute |
| (resolved) `bcode` | Shipped SKU sent to TF/SIDET + `shipment_lines.bcode` |
| (resolved) `requested_bcode` | Original request BCODE on shipment line |

### Clash rule (v1)

**Reject** if `ship_as_bcode` equals another request line’s `bcode` on the same transfer (`unique(transfer_id, bcode)`).

### Operator steps (ส่งแทน)

1. Seed peer group in Explorer (`/parts9/substitutes`).
2. On prepare (ship-from), open a line that shows **ทดแทนแนะนำ**.
3. Choose **ส่งแทน {peer}** in the dropdown; set qty; confirm — UI shows **ส่งแทน: {peer}**.
4. TF/SIDET deducts peer stock; request line `qty_prepared` increases.
5. Receive sees shipped peer BCODE with note “ส่งแทนจากคำขอ …”.

Apply migration before staging E2E.

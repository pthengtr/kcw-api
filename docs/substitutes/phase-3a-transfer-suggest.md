# Phase 3a — Transfer suggest peers (read-only)

**Cursor Auto handoff.** Requires Phase 1 lookup API/helper. Phase 2 nice-to-have for ops seeding. See [plan.md](plan.md).

## Domain lock

```
PROJECT: kcw-api / kcw-transfer (:8792)
DOMAIN: Show substitute peers on transfer suggest / prepare UI when ship-from is L-1 or weak stock
NOT THIS:
  - Shipping a different BCODE (Phase 3b)
  - Changing request line bcode uniqueness behavior yet
  - Pay-notes / โอนเงิน
THAI: ทดแทนแนะนำ = hint only; ส่งแทน = Phase 3b
```

## Goal

When HQ (or ship-from) has `QTYMIN < 0` or insufficient `QTYOH2`, surface ranked substitute peers with dual stock so operators see options. **Still ship original BCODE only.**

## Out of scope / FORBIDDEN

- `ship_as_bcode` on prepare payload
- TF writer changes
- Auto-replacing lines on draft submit

## Read first

- `src/transfer/parts9.py` (`suggest_transfer_skus`, enrich, `hq_no_stock` / blocked)
- `src/transfer/ui.py` (suggest list + prepare stock cells / ไม่สต็อก badge)
- Shared substitute lookup from Phase 1/2 (`src/substitutes/…`)
- `tests/test_transfer.py`

## Work checklist

1. **Enrich helper:** given list of bcodes → map to peers (exclude self), sorted by `sort_rank`, with stock fields.
2. **Suggest API / enrich:** attach `substitutes: [...]` (or similar) when:
   - ship-from `QTYMIN < 0`, or
   - ship-from `QTYOH2` below requested/suggested qty (simple threshold OK)
3. **UI:** compact peer line under the SKU (BCODE, DESCR short, HQ/SYP qty, L-1 badge). No “send as” control yet.
4. **Prepare queue:** same hint when viewing a line that is L-1 at ship-from.
5. **Tests:** enrich attaches peers; no writer assertions changed.

## Acceptance gate

```bash
cd /home/hqadmin/projects/kcw-api && .venv/bin/python -m pytest tests/test_transfer.py tests/test_substitutes.py -q
```

- [x] Suggest/prepare UI shows peers for a seeded L-1 SKU with group members (`fmtSubsHint` / `substitutes[]`)
- [x] Prepare still only posts original `bcode` + `qty_ship` (no `ship_as_bcode`)
- [x] No migration changing `shipment_lines` yet
- [x] pytest green (transfer + substitutes)

## Delivered (Phase 3a)

| Piece | Where |
|-------|--------|
| Hint helper | `src/substitutes/peers.py` — `needs_substitute_hint`, `attach_substitute_hints`, `enriched_peers_for_bcodes` |
| Bulk peers | `db.bulk_peers` / `MemorySubstitutes.bulk_peers` |
| Suggest enrich | `suggest_transfer_skus` → ship-from = other branch |
| Prepare enrich | `enrich_transfer_lines` → ship-from = `from_branch` |
| UI | `fmtSubsHint` under descr on suggest + prepare (via `fmtDescr`) |

Trigger: ship-from `QTYMIN < 0` / `hq_no_stock`, or ship-from `QTYOH2` &lt; need qty (`suggest_qty` / open prepare).

## Stop here

Next: [phase-3b-transfer-send-sub.md](phase-3b-transfer-send-sub.md).

## Handoff to Phase 3b

### `substitutes[]` JSON (suggest item + prepare line)

Attached only when the hint trigger fires; otherwise `[]`. Sorted by `sort_rank`, then `bcode`. Self excluded.

```json
"substitutes": [
  {
    "bcode": "01050082",
    "descr": "…",
    "hq_qtyoh2": 10.0,
    "hq_qtymin": 1.0,
    "syp_qtyoh2": 2.0,
    "syp_qtymin": 1.0,
    "sort_rank": 0,
    "hq_l1": false,
    "syp_l1": false
  }
]
```

### Clash case for ส่งแทน

`transfer.lines` (or equivalent) has `unique(transfer_id, bcode)`. If preparer sets `ship_as_bcode` to a BCODE that is already another **request line** on the same transfer, Phase 3b should **reject** (v1 preference) with a clear error — do not silently merge.
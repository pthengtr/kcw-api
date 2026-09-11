# Phase 4 — Docs & ops runbooks

**Cursor Auto handoff.** Requires Phase 3b behavior stable. See [plan.md](plan.md).

## Domain lock

```
PROJECT: kcw-docs + kcw-api docs
DOMAIN: Operator and engineer documentation for สินค้าทดแทน
NOT THIS:
  - New features or schema changes (unless doc-only fixes)
  - Rewriting unrelated transfer history
```

## Goal

Anyone can find: what L-1 means, how to manage substitute groups, how ส่งแทน works on prepare.

## Out of scope / FORBIDDEN

- Implementing new substitute behavior
- OpenCode prompts

## Read first

- [plan.md](plan.md) + all phase docs as built
- Final API routes and UI labels from Phases 1–3b
- `kcw-docs/ops/transfer.md`
- `kcw-docs/dictionaries/kcw-icmas-data-dictionary.md`
- `kcw-api/docs/transfer.md`

## Work checklist

1. **New** `kcw-docs/ops/product-substitutes.md` — glossary, manage in Explorer, seed review process, ส่งแทน steps, non-goals.
2. **Update** `kcw-docs/ops/transfer.md` — short section + link for L-1 + ส่งแทน.
3. **Update** ICMAS dictionary — REMARKS not substitute registry; cross-link to product-substitutes ops; reinforce `QTYMIN < 0`.
4. **Update** `kcw-api/docs/transfer.md` — prepare `ship_as_bcode` contract.
5. **Pointer** from `docs/substitutes/plan.md` “Phase index” status notes if useful (mark phases done).
6. **ops/README.md** — link new ops page if that index lists runbooks.

## Acceptance gate

- [x] `kcw-docs/ops/product-substitutes.md` exists and matches shipped behavior
- [x] Transfer ops + API docs mention ส่งแทน
- [x] Dictionary does not claim REMARKS is the substitute system
- [x] No code behavior changes (doc-only diff preferred)

## Stop here

Feature v1 complete from a process perspective. Later optional: stock-check integration, multi-group membership, better seed mining, staged live PARTS9 E2E for ส่งแทน, approved seed import.

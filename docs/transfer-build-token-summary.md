# KCW Transfer Build — Token Summary

*Build session: Aug 2026 · HQ↔SYP `kcw-transfer` (:8792)*

## Executive summary

| | Cloud (Cursor) | Local (Spark) |
|--|----------------|---------------|
| **Estimated total** | **~55k–70k tokens** (~$0.55–$0.85) | **$0** (spark-3583) |
| **If done entirely in cloud** | **~180k–220k tokens** (~$1.80–$3.00) | — |
| **Rough savings** | **~65–70%** | Electricity only |

---

## Line items

| Phase | Who | Cloud tokens (est.) | Outcome |
|-------|-----|---------------------|---------|
| Planning + plan iterations | Cursor | ~12k | Domain lock, UI spec, LINE menu |
| Spark run #1 — “transfer” misread as โอนเงิน | Spark | ~4k orchestration | Failed — ambiguous prompt |
| Phase 1 — app, LINE, UI shell | Cursor | ~25k–30k | Shipped |
| Spark Phase 1b — ICLOW stamp | Spark | ~3k orchestration | OK; Cursor fixed integration bugs |
| Spark Phase 2+3 — HQ TF + SYP receive | Spark | ~4k orchestration | Code in; 4 tests red at handoff |
| Test fixes + writer integration | Cursor | ~8k–10k | **31/31 pytest green** |
| Status / delegation docs | Cursor | ~5k | This file + checklist |

---

## Deliverables

- **`kcw-transfer`** on port 8792 (pay-notes-style UI)
- LINE: `โอนสินค้า` entry, rich menu cell, `menu`/`เมนู` services Flex card
- Flow: SYP select → HQ prepare (TF) → SYP receive
- ICLOW stamp for parallel operation with legacy `/po`
- Writers: `hq_tf.py`, `syp_receive.py`, `syp_iclow_stamp.py`
- **31 automated tests** (`tests/test_transfer_*.py`, etc.)

---

## What went wrong (run #1) and fix

Spark `qwen3-coder:30b` interpreted “transfer” as **bank transfer**, not inventory transfer. Root cause: **Cursor prompt ambiguity**, not missing model.

**Fix:** [opencode-delegation-checklist.md](./opencode-delegation-checklist.md) — domain lock, scope fence, `pytest` gate, Cursor review.

---

## Cost control going forward

| Delegate to Spark | Keep in Cursor |
|-------------------|----------------|
| Bulk writers, migrations, test scaffolding | Architecture, UI polish, integration fixes |
| One phase per prompt (see `opencode-transfer-phase23-prompt.md`) | Live KSS/kss-pc testing, SQL grants |
| Must pass `pytest` before reporting done | Operator UX (“wife test”) |

**Acceptance gate:**

```bash
cd ~/projects/kcw-api && .venv/bin/python -m pytest \
  tests/test_transfer_state.py tests/test_transfer.py tests/test_services_menu.py \
  tests/test_transfer_iclow_stamp.py tests/test_transfer_hq_tf.py \
  tests/test_transfer_syp_receive.py tests/test_line_rich_menu.py -q
```

---

## ROI one-liner

> **~$0.70 cloud + $0 Spark ≈ same deliverable that would’ve been ~$2.50 all-cloud** — delegation works when Cursor writes an unambiguous spec and reviews the handoff; not when it says “build transfer” and hopes.

---

## Related docs

- [transfer.md](./transfer.md) — operator runbook
- [opencode-delegation-checklist.md](./opencode-delegation-checklist.md) — Spark prompt template
- Plan: `~/.cursor/plans/HQ-SYP Transfer Service-b590dfca.plan.md`

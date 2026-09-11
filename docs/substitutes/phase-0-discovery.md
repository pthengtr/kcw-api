# Phase 0 — Discovery → initial substitute candidate list

**Cursor Auto handoff.** Read [plan.md](plan.md) first.

## Domain lock

```
PROJECT: kcw-api / product substitutes
DOMAIN: Discover candidate substitute (สินค้าทดแทน) groups from existing ICMAS signals
NOT THIS:
  - Creating Supabase schema or APIs (Phase 1)
  - Explorer/Transfer UI (Phases 2–3)
  - Changing QTYMIN / L-1 meaning
  - Writing into ICMAS.REMARKS or PARTS9
  - Bank transfer / pay-notes
THAI: ทดแทน = peer SKUs; L-1 / ไม่สั่งซ้ำ = QTYMIN < 0 (not OOS)
```

## Goal

Explore live and/or mirrored ICMAS data and produce a **human-reviewable initial list** of proposed substitute groups.

## Out of scope / FORBIDDEN

- `CREATE TABLE`, migrations, app routes, UI changes
- Auto-inserting groups into any DB
- Treating REMARKS or PCODE twins as confirmed substitutes without labeling confidence

## Read first

- [plan.md](plan.md) glossary
- `kcw-docs/dictionaries/kcw-icmas-data-dictionary.md` (§4 PCODE/MCODE, §6 QTYMIN, REMARKS if documented)
- `kcw-docs/ops/icmas-master-sync.md` (what is master vs branch-local)
- `kcw-api/supabase/migrations/20260315143028_create_raw_kcw_icmas.sql` (column names on mirrors)
- How Explorer connects: `src/parts9_explorer/db.py`, `search.py` (for live query patterns if used)

## Data sources (prefer in order)

1. Supabase `raw_kcw.raw_hq_icmas_products` / `raw_syp_icmas_products` (safe read)
2. Live PARTS9 via existing explorer/transfer engines **read-only** if mirrors are stale/incomplete

## Work checklist

1. **Glossary note** at top of the output file: qtylo → `QTYMIN`; L-1 ≠ `QTYOH2=0`.
2. **REMARKS pass (HQ master preferred):** find non-empty `REMARKS` matching substitute-like patterns (`แทน`, `ใช้แทน`, `ทดแทน`, embedded BCODE-like tokens). Capture `BCODE`, `DESCR`, `REMARKS`, site.
3. **PCODE clusters:** same non-empty `PCODE` → multiple distinct `BCODE`s (exclude dirty PCODE noise where obvious). Rank by cluster size / both sites present.
4. **MCODE clusters:** same as PCODE for `MCODE`.
5. **L-1 need signal (high value):** HQ `QTYMIN < 0` where SYP still has recent usefulness (e.g. SYP `QTYOH2 > 0` or appears in transfer/ICLOW if easy). List these as “needs substitute” even if no peer found yet.
6. **Optional soft peers:** same `CODE1` + matching `SIZE1–3` only as `confidence: low` suggestions; do not flood the report.
7. **Dedupe & propose groups:** merge overlapping evidence into candidate groups. Each group: members (`BCODE` + short DESCR), evidence type(s), confidence `high|med|low`, notes for reviewer.
8. Write deliverables below. Do not load into catalog.

## Deliverables

| File | Content |
|------|---------|
| `docs/substitutes/initial-seed-candidates.md` | Human-readable groups + evidence + confidence + open questions |
| `docs/substitutes/initial-seed-candidates.csv` (optional) | Columns: `proposed_group_id`, `bcode`, `descr`, `evidence`, `confidence`, `hq_qtymin`, `hq_qtyoh2`, `syp_qtyoh2`, `notes` |
| Short summary in chat | Counts: remarks hits, PCODE clusters, MCODE clusters, L-1-need orphans |

### Suggested markdown section shape

```markdown
## Candidate group G001
- Confidence: med
- Evidence: same PCODE=...; REMARKS on 08xxxx mentions 08yyyy
- Members:
  - 08xxxx — DESCR… (HQ QTYMIN=-1, HQ QTYOH2=…, SYP QTYOH2=…)
  - 08yyyy — …
- Reviewer action: approve / reject / edit members
```

## Acceptance gate

- [x] `initial-seed-candidates.md` exists under `docs/substitutes/`
- [x] Glossary locked at top of that file
- [x] At least one of: REMARKS hits, PCODE clusters, MCODE clusters, or L-1-need list with clear empty-peer callouts
- [x] Every proposed group has confidence + evidence
- [x] No schema/API/UI changes in this phase
- [x] Chat summary with counts for human review

**Follow-up (ops, not blocking code):** human approve/reject groups before `load_substitute_seed.py --apply`.

## Stop here

**Human reviews the seed list** (approve/edit/reject). Next agent starts Phase 1 using [phase-1-schema-api.md](phase-1-schema-api.md). Seed import into Supabase is Phase 1 optional follow-up after approval — not automatic.

## Handoff to Phase 1

Pass: path to approved candidates (or “skip seed, empty catalog”). Phase 1 builds empty CRUD first; import script only loads **approved** rows.

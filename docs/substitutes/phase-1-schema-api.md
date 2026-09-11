# Phase 1 — Schema + API

**Cursor Auto handoff.** Requires [plan.md](plan.md). Phase 0 review preferred but not required for empty CRUD.

## Domain lock

```
PROJECT: kcw-api / product substitutes
DOMAIN: Supabase catalog tables + CRUD/lookup APIs for mutual substitute groups
NOT THIS:
  - Explorer HTML manage UI (Phase 2)
  - Transfer suggest / ส่งแทน (Phases 3a/3b)
  - PARTS9 writes / ICMAS.REMARKS updates
  - Changing QTYMIN semantics
THAI: กลุ่มทดแทน = substitute_groups; สมาชิก = members by BCODE
```

## Goal

Create `catalog.substitute_groups` / `catalog.substitute_members` and a small Python API used later by Explorer and Transfer.

## Out of scope / FORBIDDEN

- Full Explorer manage page (Phase 2)
- Transfer prepare payload changes
- Multi-group membership per BCODE
- Auto-loading unreviewed Phase 0 dump

## Read first

- [plan.md](plan.md) data model
- `supabase/migrations/20260829120000_transfer_schema.sql` (schema/grants style)
- `src/transfer/db.py` (Supabase client patterns)
- `app/parts9_explorer_app.py`, `app/routers/parts9_explorer.py` (where to mount routes)
- `tests/test_transfer.py` or similar for mock patterns
- Approved seed file if any: `docs/substitutes/initial-seed-candidates.md`

## Work checklist

1. **Migration** `supabase/migrations/YYYYMMDDHHMMSS_catalog_substitutes.sql`:
   - `create schema if not exists catalog;`
   - tables per plan.md; indexes on `bcode`; grants like transfer (anon/authenticated/service_role as used elsewhere)
   - `unique (bcode)` on members
2. **Module** `src/substitutes/`:
   - `db.py` — list/get group, create group, delete group, add/remove member, get_by_bcode, list peers
   - Enforce: adding a BCODE already in another group → clear error
   - `models.py` / typed dicts as fits repo style
3. **Router** mount under Explorer app, e.g. `/parts9/api/substitutes/...` (keep path prefix consistent with explorer):
   - `GET /by-bcode/{bcode}` → group + members (bcodes only is OK; enrichment with stock can wait for Phase 2)
   - `POST /groups` create
   - `DELETE /groups/{group_id}`
   - `POST /groups/{group_id}/members` `{bcode, sort_rank?, note?}`
   - `DELETE /groups/{group_id}/members/{bcode}`
   - `GET /groups` optional list/search
4. **Auth:** same LINE/cookie pattern as other explorer APIs (do not invent a new auth stack).
5. **Tests** `tests/test_substitutes.py` — mock Supabase; cover unique bcode conflict, add/remove, by-bcode.
6. **Optional seed script** `scripts/load_substitute_seed.py` — reads an **approved** CSV/markdown subset only; dry-run flag; never run against prod without human OK.

## Acceptance gate

```bash
cd /home/hqadmin/projects/kcw-api && .venv/bin/python -m pytest tests/test_substitutes.py -q
```

Also:

- [x] Migration file present and matches plan model
- [x] Routes importable from explorer app
- [x] No Transfer UI/writer changes
- [x] Document endpoint list briefly at bottom of this file or in `plan.md` if paths differ

## Stop here

Next: [phase-2-explorer-ui.md](phase-2-explorer-ui.md).

## Endpoints (Explorer app `:8788`)

Auth: same LINE cookie / Tailscale gate as other `/parts9/api/*` routes.

| Method | Path | Notes |
|--------|------|-------|
| GET | `/parts9/api/substitutes/by-bcode/{bcode}` | `{ group, peers }` (`group` null if none) |
| GET | `/parts9/api/substitutes/groups?q=&limit=` | List / search by bcode or name |
| GET | `/parts9/api/substitutes/groups/{group_id}` | One group + members |
| POST | `/parts9/api/substitutes/groups` | Body: `{ name?, note?, members: [{bcode, sort_rank?, note?}] }` |
| PATCH | `/parts9/api/substitutes/groups/{group_id}` | Body: `{ name?, note? }` |
| DELETE | `/parts9/api/substitutes/groups/{group_id}` | Cascade members |
| POST | `/parts9/api/substitutes/groups/{group_id}/members` | Body: `{ bcode, sort_rank?, note? }` — **409** if bcode already in another group |
| DELETE | `/parts9/api/substitutes/groups/{group_id}/members/{bcode}` | |

Optional seed (approved CSV only, dry-run default):

```bash
.venv/bin/python scripts/load_substitute_seed.py docs/substitutes/approved-seed.csv
.venv/bin/python scripts/load_substitute_seed.py docs/substitutes/approved-seed.csv --apply
```

## Handoff to Phase 2

API base: `/parts9/api/substitutes`. Catalog empty until human-approved seed import (or manual create). Call `GET .../by-bcode/{bcode}` for peer list.

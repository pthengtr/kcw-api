# Phase 2 — Explorer UI (manage + display)

**Cursor Auto handoff.** Requires Phase 1 API green. See [plan.md](plan.md).

## Domain lock

```
PROJECT: kcw-api / parts9_explorer (:8788)
DOMAIN: Manage substitute groups and show peers on product search/detail
NOT THIS:
  - Transfer suggest or ส่งแทน (Phases 3a/3b)
  - PARTS9 master edits / QTYMIN changes
  - Full redesign of Explorer chrome
THAI: กลุ่มทดแทน / ทดแทนในกลุ่ม; L-1 badge stays QTYMIN-based
```

## Goal

Operators can add/remove SKUs in a substitute group from Explorer, and see peers when viewing a product.

## Out of scope / FORBIDDEN

- Transfer prepare `ship_as_bcode`
- Changing default L-1 hide behavior except showing peers even when the viewed SKU is L-1
- Cards-heavy redesign; match existing Explorer HTML/JS style in `src/parts9_explorer/ui.py`

## Read first

- Phase 1 routes in `src/substitutes/` + explorer router
- `src/parts9_explorer/ui.py`, `search.py`
- `app/routers/parts9_explorer.py`
- How product detail loads dual HQ/SYP qty today

## Work checklist

1. **Manage page** (new route under `/parts9/`, e.g. substitutes manage):
   - Search/load by BCODE → show current group or “create group”
   - Add peer by BCODE (validate exists in ICMAS on at least one site)
   - Remove peer; optional group note
   - Show dual `QTYOH2` + L-1 (`QTYMIN < 0`) badges per member
2. **Wire APIs** from page JS to Phase 1 endpoints (same auth cookie as explorer).
3. **Product detail / search results:**
   - If `by-bcode` returns peers → panel **ทดแทนในกลุ่ม** listing peers + stock
   - Link to manage page for that group/BCODE
4. **Enrichment:** prefer server-side enrich (ICMAS dual stock) in substitute lookup used by UI — extend Phase 1 lookup if needed rather than N+1 from browser.
5. **Tests:** extend `tests/test_parts9_explorer.py` and/or `tests/test_substitutes.py` for serialize/enrich helpers; UI can stay smoke-level if that matches repo norms.

## Acceptance gate

- [x] Can create a group and add ≥2 BCODEs via Explorer manage UI
- [x] Product detail for a member shows peers
- [x] L-1 products still show peers when opened (include_skip / direct BCODE as today)
- [x] `pytest` for substitute + explorer-related tests still green:

```bash
cd /home/hqadmin/projects/kcw-api && .venv/bin/python -m pytest tests/test_substitutes.py tests/test_parts9_explorer.py -q
```

## Delivered (Phase 2)

| Piece | Where |
|-------|--------|
| Manage UI | `GET /parts9/substitutes` (`substitutes_manage_page` in `ui.py`) |
| Peers panel | Product detail → **ทดแทนในกลุ่ม** via `loadSubsPeers` |
| Enrichment | `src/substitutes/enrich.py` — `fetch_dual_stock` / `enrich_member_rows` / `enrich_group` |
| BCODE validate | Add/create rejects unknown ICMAS codes (`UnknownBcodeError` → 400) |
| Group meta | `PATCH /parts9/api/substitutes/groups/{group_id}` `{name?, note?}` |

## Stop here

Next: [phase-3a-transfer-suggest.md](phase-3a-transfer-suggest.md).

## Handoff to Phase 3a

Shared lookup: `from src.substitutes.enrich import enrich_member_rows, fetch_dual_stock`  
(or `GET /parts9/api/substitutes/by-bcode/{bcode}` → `peers`).

Enrich fields on each peer/member:

`bcode`, `descr`, `hq_qtyoh2`, `hq_qtymin`, `syp_qtyoh2`, `syp_qtymin`, `sort_rank`  
(+ UI helpers `hq_l1` / `syp_l1` when `qtymin < 0`).

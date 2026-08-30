# OpenCode prompt: kcw-transfer Phase 2+3 (full writer flow)

Use this file as the delegation spec. Do not paraphrase.

## DOMAIN LOCK

```
PROJECT: kcw-api / kcw-transfer (:8792)
DOMAIN: HQ↔SYP INVENTORY stock transfer (โอนสินค้า). SYP requests → HQ prepares TF bill (stock OUT KSS) → SYP receives (stock IN kss-pc).
NOT THIS:
  - bank transfer / โอนเงิน / send money / fund transfer
  - pay-notes AP / PVMAS / payment vouchers
  - POMAS / SYP PO creation (new path skips PO)
  - src/handlers/transfer.py (use transfer_entry.py only)
THAI: จัดแล้ว = HQ prepare+TF; รับแล้ว = SYP receive; โอนสินค้า = this app
COMMANDS: โอนสินค้า, โอน, transfer (stock only)
```

## EXISTING CODE (read before writing)

- src/transfer/writers/syp_iclow_stamp.py — ICLOW stamp (Phase 1b, done)
- src/stock_check/sa_writer.py — SIMAS+SIDET insert pattern, billno seq, writer engine
- src/pay_notes/writer.py — writer error mapping, transaction pattern
- src/ops/tf_prepare.py — read TF/TFV bills (BILLNO like TF%, REMARKS links docno)
- app/routers/transfer.py — api_prepare/api_receive are 501 stubs
- src/transfer/db.py — needs shipment helpers
- src/transfer/state.py — can_action rules
- kcw-docs/dictionaries/kcw-iclow-pending-receive-data-dictionary.md — ICLOW.ID not ICLOW_ID

## TASK — Phase 2: HQ TF writer

Create `src/transfer/writers/hq_tf.py` + `src/transfer/writers/_engine.py`:

- `_writer_engine_hq()` using get_site_engine("hq") with POS_MSSQL_WRITER_* from transfer config (add writer username/password fields to config if missing, mirror pay_notes)
- `post_transfer_tf(*, transfer_id, short_id, lines: list[{line_id,bcode,qty_ship,descr}], operator, client_token)`:
  - One multi-line TF bill per call (BILLNO prefix `TF` + YYMM seq like sa_writer)
  - SIMAS.REMARKS = `TRF-{short_id}` or transfer_id uuid (nvarchar 30 max — truncate)
  - SIDET one row per line with qty_ship
  - BILLTYPE: use same as existing HQ TF bills — query one recent TF SIMAS row for template OR use BILLTYPE from ops reads; document choice in comment
  - Stock OUT (HQ QTYOH2 decreases) — follow sa_writer BILLTYPE 1 pattern if TF is outbound
  - Idempotent: if client_token already in transfer.shipments, return existing tf_billno
  - Raise `TransferWriteError` with codes

Extend `src/transfer/db.py`:
- `create_shipment`, `get_shipment_by_token`, `list_shipments`, `add_shipment_lines`
- `bump_line_prepared`, `bump_line_received`, `cancel_request` (supabase status)
- Recompute header status after prepare/receive

Wire `POST /api/requests/{transfer_id}/prepare`:
- Body: `{client_token, lines: [{line_id, qty_ship}]}`
- Gate: TRANSFER_HQ_WRITE_ENABLED + site HQ
- can_action hq_prepare per line
- Call post_transfer_tf then save shipment + update lines
- Return `{tf_billno, shipment_id}`

## TASK — Phase 3: SYP receive writer

Create `src/transfer/writers/syp_receive.py`:

- `post_transfer_receive(*, shipment, lines_to_receive, operator, client_token)` on kss-pc (get_site_engine("syp"))
- Validate qty against shipment_lines and HQ TF SIDET (read-only query on HQ engine for tf_billno)
- Stock IN on SYP — mirror sa_writer positive variance / BILLTYPE 2 OR ICLOW receive-only if that's all that's needed; prefer minimal SIMAS+SIDET receive bill if PARTS9 requires it
- If line has iclow_id and TRANSFER_ICLOW_STAMP_ENABLED: call mark_received from syp_iclow_stamp
- Idempotent client_token
- bump_line_received in Supabase

Wire `POST /api/shipments/{shipment_id}/receive`:
- Body: `{client_token, lines: [{shipment_line_id, qty_receive}]}`
- Gate: TRANSFER_SYP_RECEIVE_ENABLED + site SYP

## TASK — Fix cancel endpoint

- can_action cancel_request (no shipments)
- Revert ICLOW stamps (existing)
- cancel_request in db (status=cancelled)

## TASK — UI (minimal, functional)

Update `src/transfer/ui.py` JS only (no full redesign):
- HQ tab รอจัด: button จัดแล้ว → POST prepare with selected qtys
- SYP tab รอรับ: button รับแล้ว → POST receive
- Show tf_billno when present
- Busy overlay already exists

## TASK — SQL + docs

- `scripts/sql/grant_transfer_writer.sql` — template grants for SIMAS/SIDET/ICMAS UPDATE on HQ and SYP
- Update `docs/transfer.md` with writer flags and flow

## TESTS (mocked DB, no live SQL)

- `tests/test_transfer_hq_tf.py` — billno gen, idempotent token, multi-line, deny over-prepare
- `tests/test_transfer_syp_receive.py` — receive qty validation, iclow mark_received called
- Keep all existing tests passing

## FORBIDDEN

- Do NOT create src/handlers/transfer.py
- Do NOT add โอนเงิน / money transfer strings
- Do NOT use ICLOW_ID (use ID)
- Do NOT call get_site_engine(server, database) — use get_site_engine("hq") or ("syp")
- Do NOT implement POMAS writes

## ACCEPTANCE GATE

```bash
cd /home/hqadmin/projects/kcw-api && .venv/bin/python -m pytest \
  tests/test_transfer_state.py tests/test_transfer.py tests/test_services_menu.py \
  tests/test_transfer_iclow_stamp.py tests/test_transfer_hq_tf.py \
  tests/test_transfer_syp_receive.py tests/test_line_rich_menu.py -q
```

All must pass. Fix failures before reporting done.

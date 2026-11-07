# HQ vendor goods receive (`kcw-hq-receive`)

Standalone **HQ-only** app on port **8795**, sibling to `kcw-hq-po` (`:8793`). LINE command: `รับสินค้า`.

Closes the loop that HQ PO leaves open: ordered ICLOW rows → vendor receive → `PIMAS` / `PIDET` + `ICLOW.RECEIVED` / `RCVDNO`.

## Scope

- Deploy and run on **`hq-ubuntu-server` only** (not SYP).
- Reads / writes **HQ `KSS` PARTS9** only.
- Transfer HQ↔SYP receive stays in `kcw-transfer`.

## Operator flow

1. Choose a vendor that still has ค้างรับ (`ICLOW` `ORDERED='Y'`, not received).
2. Optional: upload vendor bill photo → **AI อ่านบิล** → **AI Match ค้างรับ**.
3. Or pick open ICLOW lines manually (partial receive supported).
4. Check qty / brand / cost / bill totals; hold mismatch lines.
5. **บันทึกร่าง** then **ยืนยันรับเข้า**.
6. Print / reprint barcode stickers (TSPL `.prn`) from confirmed lines or history.

AI prefills only. The operator must confirm before PARTS9 writes.

## Business rules

See also `src/hq_receive/rules.py` (`RULES_SUMMARY`).

| Rule | Behavior |
|------|----------|
| Confirm required | No PARTS9 write without operator confirm |
| Partial receive | Allowed; remaining qty stays on ICLOW |
| Hold lines | Skipped on confirm (not written to PIMAS) |
| Mismatch lines | Block confirm unless held (or future `force_ok`) |
| Cost tolerance | Default ±2% (`HQ_RECEIVE_COST_TOLERANCE_PCT`) |
| Qty tolerance | Default ~0 (`HQ_RECEIVE_QTY_TOLERANCE`) |
| Total tolerance | Default 1 baht (`HQ_RECEIVE_TOTAL_TOLERANCE`) |
| Write flag | `HQ_RECEIVE_PIMAS_WRITE_ENABLED` (software default false; enable on HQ after grants) |
| Stickers | Only from checked receive lines / history reprint |
| Site | HQ `KSS` only — never SYP |

## API (`/hq-receive`)

- `GET /` UI
- `GET /api/meta`
- `GET /api/vendors?q=`
- `GET /api/open-lines?acctno=`
- `POST /api/invoices/extract` (multipart image)
- `POST /api/invoices/{id}/match`
- `GET /api/discrepancies`
- `POST|PUT|GET /api/receipts[/{id}]`
- `POST /api/receipts/{id}/confirm`
- `GET /api/history` (alias `/api/receipts/history`)
- `GET /api/stickers/config`
- `POST /api/stickers/preview`
- `POST /api/stickers/print` (`action=download|print`)
- `GET /api/stickers/jobs?receipt_id=`

## Data (`hq_receive` schema)

- `receipts` / `lines` — drafts and confirmed GR
- `invoice_extractions` / `invoice_extraction_lines` — AI bill parse
- `discrepancies` — qty/cost/unknown-product follow-ups
- `barcode_print_jobs` — sticker print/download history

Migrations:

- `20261107120000_hq_receive_schema.sql`
- `20261107120100_hq_receive_grants.sql`
- `20261107123000_hq_receive_ai_stickers.sql`

Until migrations are applied, the service keeps drafts / extractions / jobs in process memory.

## PARTS9 write

When the flag is on, `writers/receive_pimas.py`:

1. Allocates next `BN` + Buddhist YYMM billno on HQ `PIMAS`
2. Inserts `PIMAS` + `PIDET` (vendor invoice → `NOTENO`, HQ PO → `PO`)
3. Bumps `ICMAS.QTYOH2`
4. Stamps matched `ICLOW` rows `RECEIVED='Y'`, `RCVDNO=billno`

Enable:

1. Run [`scripts/sql/grant_hq_receive_writer.sql`](../scripts/sql/grant_hq_receive_writer.sql) on HQ `KSS`
2. Apply Supabase migrations
3. Set `HQ_RECEIVE_PIMAS_WRITE_ENABLED=true` and restart

```bash
systemctl --user enable --now kcw-hq-receive.service
curl -s http://127.0.0.1:8795/health
```

Optional: `HQ_RECEIVE_PUBLIC_BASE_URL`, `HQ_RECEIVE_TAILSCALE_BASE_URL`, `HQ_RECEIVE_AI_MODEL`, `HQ_RECEIVE_STICKER_PRINTER_*`.

## Firewall

`scripts/hq-linux-firewall.sh` includes LAN TCP **8795**. Or:

```bash
sudo bash scripts/hq-open-port-8795.sh
```

# HQ↔SYP Transfer (`kcw-transfer`)

LAN + Tailscale UI for HQ→SYP stock transfers. Port **8792**, routes under `/transfer/`.

**Operator runbook:** [kcw-docs ops/transfer.md](https://github.com/pthengtr/kcw-docs/blob/main/ops/transfer.md).

LINE command: `โอนสินค้า` (aliases: `โอน`, `transfer`).

## Operator flow

1. **SYP** — select what's needed → submit transfer request
2. **HQ** — pick list → mark prepared (**TF bill** on KSS — stock out)
3. **SYP** — mark received against TF (**receive** on kss-pc — stock in)

Supabase `transfer.*` owns workflow; PARTS9 owns inventory at TF + receive only.

Runs on **both** HQ and SYP boxes (`TRANSFER_SITE=HQ` or `SYP`).

## Enable

```env
TRANSFER_ENABLED=true
TRANSFER_SITE=HQ   # or SYP on syp box
TRANSFER_LISTEN_PORT=8792
STOCK_CHECK_TOKEN_SECRET=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
```

Writers (off in Phase 1 until validated):

```env
TRANSFER_HQ_WRITE_ENABLED=false
TRANSFER_SYP_RECEIVE_ENABLED=false
TRANSFER_ICLOW_STAMP_ENABLED=false
```

## Writer Database Credentials

To enable write to PARTS9 databases, set the following SQL Server credentials. For the writer user account, you must grant INSERT on SIMAS/SIDET and UPDATE on ICMAS:

```env
POS_MSSQL_WRITER_USERNAME=...
POS_MSSQL_WRITER_PASSWORD=...
```

Note: If these are not set, connections will still work for read operations but writes to PARTS9 will fail.

systemd: `scripts/systemd/kcw-transfer.service` on both `hq-ubuntu-server` and `syp-ubuntu-server`.

```bash
systemctl --user enable --now kcw-transfer
curl -s http://127.0.0.1:8792/health
```

## LINE

- Rich menu cell: **โอนสินค้า**
- Text: `menu` / `เมนู` / `services` → Flex services menu card
- Legacy PO status: `สถานะใบสั่งซื้อ` (kcw-ops)

## Parallel with old `/po`

When using this app, ICLOW is stamped on submit (Phase 1b) so old ICLOW/PO UI does not double-order. Old path remains available by operator choice.

## ICLOW Stamping

When `TRANSFER_ICLOW_STAMP_ENABLED=true` and `TRANSFER_SITE=SYP`, the transfer workflow will:
- **On Submit**: Find open ICLOW record for each BCODE (`ORDERED=N`, `RECEIVED=N`, `CANCELED=N`) and set:
  - `ORDERED = 'Y'`
  - `DOCNO = TRF-{short_id}` 
  - `DOCDATE = today`
- **On Cancel**: If no shipments have occurred, reset ICLOW:
  - `ORDERED = 'N'` 
  - `DOCNO = ''` (cleared)
- **On Receive**: Mark ICLOW as received:
  - `RECEIVED = 'Y'`
  - `RCVDNO = left12(tf_billno)`
  - `RCVDDATE = today`

This behavior only applies to SYP-site transfers.

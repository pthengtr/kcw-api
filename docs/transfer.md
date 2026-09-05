# HQ↔SYP Transfer (`kcw-transfer`)

LAN + Tailscale UI for **bidirectional** HQ↔SYP stock transfers. Port **8792**, routes under `/transfer/`.

**Operator runbook:** [kcw-docs ops/transfer.md](https://github.com/pthengtr/kcw-docs/blob/main/ops/transfer.md).

**PARTS9 ledger (four legs):** [transfer-ledger.md](./transfer-ledger.md).

**SYP box one-time setup:** [kcw-docs ops/syp-linux-transfer-setup.md](https://github.com/pthengtr/kcw-docs/blob/main/ops/syp-linux-transfer-setup.md).

LINE command: `โอนสินค้า` (aliases: `โอน`, `transfer`).

## Operator flow (bidirectional)

Requester is always **`to_branch`** (branch that needs stock). Shipper is **`from_branch`**.

| Direction | Requester submits at | Shipper prepares at | Receiver receives at |
|-----------|---------------------|---------------------|----------------------|
| **HQ → SYP** | SYP | HQ (TF SIMAS on KSS) | SYP (TF PIMAS on kss-pc) |
| **SYP → HQ** | HQ | SYP (3TF SIMAS on kss-pc) | HQ (3TF PIMAS on KSS) |

1. **Requester** — draft with direction picker → submit
2. **Shipper** (`from_branch`) — prepare queue → one click = one ship bill (partial prepare allowed)
3. **Receiver** (`to_branch`) — receive against shipment → PIMAS bill (stock in)

Supabase `transfer.*` owns workflow; PARTS9 owns inventory at ship (SIMAS) + receive (PIMAS).

Runs on **both** HQ and SYP boxes (`TRANSFER_SITE=HQ` or `SYP`). Same tab set on both sites.

## Enable

```env
TRANSFER_ENABLED=true
TRANSFER_SITE=HQ   # or SYP on syp box
TRANSFER_LISTEN_PORT=8792
STOCK_CHECK_TOKEN_SECRET=...
SUPABASE_URL=...
SUPABASE_SERVICE_ROLE_KEY=...
# Dual stock: SYP cannot reach HQ KSS (LAN-only). Peer over Tailscale when POS_MSSQL
# and PARTS9_SYP both point at kss-pc (default MagicDNS: hq-ubuntu-server / syp-ubuntu-server).
# TRANSFER_PEER_BASE_URL=http://hq-ubuntu-server:8792   # on SYP
```

Writers (off until validated on live PARTS9):

```env
TRANSFER_HQ_SHIP_WRITE_ENABLED=false      # SIMAS on KSS (TF)
TRANSFER_SYP_SHIP_WRITE_ENABLED=false   # SIMAS on kss-pc (3TF)
TRANSFER_HQ_RECEIVE_WRITE_ENABLED=false   # PIMAS on KSS (3TF)
TRANSFER_SYP_RECEIVE_WRITE_ENABLED=false# PIMAS on kss-pc (TF)
TRANSFER_ICLOW_STAMP_ENABLED=false
```

Legacy aliases (one release): `TRANSFER_HQ_WRITE_ENABLED` → HQ ship; `TRANSFER_SYP_RECEIVE_ENABLED` → SYP receive.

## Dual stock (คงเหลือ HQ / สาขา)

Live `ICMAS.QTYOH2` from each branch. On **HQ**, both SQL hosts are reachable (`POS_MSSQL_*` → KSS, `PARTS9_SYP_*` → kss-pc). On **SYP**, `POS_MSSQL_*` is also kss-pc — so `get_site_engine("hq")` would wrongly return shop stock. Transfer detects that host collision and loads HQ stock via peer `GET /transfer/api/local-icmas` on the other box (Tailscale CGNAT auth).

## Inter-branch AP (ACCTNO)

Ship (SIMAS) and receive (PIMAS) bills set `ACCTNO`/`ACCTNAME` from APMAS like manual TF:

| Writing site | Counterparty | ACCTNO |
|--------------|--------------|--------|
| HQ | SYP | `KCW1` |
| SYP | HQ | `KCW` |

## Cancel + print

- Cancel: requester (`to_branch`) while status is `requested` and no ship bill yet (`POST /transfer/api/requests/{id}/cancel`).
- Print: **พิมพ์ใบคำขอ** on request detail / status list — browser print of TRF lines + AP labels.
- Barcode stickers: after **ยืนยันรับเข้า**, or later from **ตรวจสอบสถานะ** (history) / request detail. Operators pick which received SKUs to print (one sticker per received unit). Primary output is a **TSPL `.prn` download** for shop TSC printers (TE310 / 244 Pro) — send the file raw to the printer (e.g. port 9100). Optional LAN send if `TRANSFER_STICKER_PRINTER_HOST` is set. Browser print is not used for stickers.

```env
TRANSFER_STICKER_PRINTER_MODEL=te310   # or ttp244pro (2-across); both invert BITMAP
TRANSFER_STICKER_PRINTER_HOST=192.168.1.50
TRANSFER_STICKER_PRINTER_PORT=9100
```

Sticker fields come from the receiving site's ICMAS (ที่เก็บ, ยี่ห้อ, หน่วย, ชื่อย่อ, บริษัท, รุ่น, เบอร์โรงงาน, รหัสสินค้า, ชื่อสินค้า, รหัสราคาทุน/ขาย, เบอร์แท้). Price letters: M0 P1 T2 N3 L4 B5 V6 S7 R8 C9 — `O` = cost, `X` = sell (270/420 → `OTSMXLTM`).

## Writer Database Credentials

Grant INSERT on **SIMAS/SIDET** and **PIMAS/PIDET**, UPDATE on **ICMAS** — see `scripts/sql/grant_transfer_writer.sql`.

```env
POS_MSSQL_WRITER_USERNAME=...
POS_MSSQL_WRITER_PASSWORD=...
```

systemd: `scripts/systemd/kcw-transfer.service` on both `hq-ubuntu-server` and `syp-ubuntu-server`.

```bash
systemctl --user enable --now kcw-transfer
curl -s http://127.0.0.1:8792/health
```

## API (direction)

- `POST /transfer/api/requests/draft` — body `{direction: "to_syp"|"to_hq", lines: [...]}`
- `POST /transfer/api/submit` — only at `to_branch`
- `POST /transfer/api/prepare` — only at `from_branch`
- `POST /transfer/api/receive` — only at `to_branch` (response includes `lines` for sticker print)
- `POST /transfer/api/stickers/preview` — ICMAS-backed 5×3.5 cm preview + resolved fields
- `POST /transfer/api/stickers/print` — `action=print` (LAN :9100) or `action=download` (.prn)
- `GET /transfer/api/requests?role=prepare|receive|mine`
- `GET /transfer/api/suggest` — pick list + live HQ/SYP `QTYOH2` + `LOCATION*` (ที่เก็บ)
- `GET /transfer/api/product?bcode=` — one SKU dual stock + dual location
- `GET /transfer/api/local-icmas?bcodes=a,b` — this site’s ICMAS only (peer)

## Schema

Migrations: `20260829120000_transfer_schema.sql`, `20260830120000_transfer_direction.sql` (`from_branch`, `to_branch`, `ship_billno`).

## LINE

- Rich menu cell: **โอนสินค้า**
- Text: `menu` / `เมนู` / `services` → Flex services menu card
- Legacy PO status: `สถานะใบสั่งซื้อ` (kcw-ops)

## Parallel with old `/po`

When using this app, ICLOW is stamped on submit at SYP when `to_branch=SYP` (Phase 1b) so old ICLOW/PO UI does not double-order. Old path remains available by operator choice.

## ICLOW Stamping

When `TRANSFER_ICLOW_STAMP_ENABLED=true` and submit happens at SYP (`to_branch=SYP`):

- **On Submit**: stamp open ICLOW (`ORDERED=Y`, `DOCNO=TRF-{short_id}`)
- **On Cancel**: revert if no shipments
- **On Receive**: `RECEIVED=Y`, `RCVDNO=left12(ship_billno)`

SYP→HQ requests (submit at HQ) do not stamp SYP ICLOW.

# Online sale (ขายออนไลน์)

Local HQ LAN/Tailscale service that replaces opening **TAD** bills in legacy PARTS9 POS.

| Item | Value |
|------|--------|
| Port | `8796` |
| App | `app.online_sale_app:app` |
| UI | `/online-sale/` |
| Merged TO | `/to-bill/` on the same process (was `:8794`) |
| LINE | `ขายออนไลน์` · `ใบเต็มออนไลน์` opens TO tab |

## What it writes

| Doc | `BOOKNO` | `BILLTYPE` | Stock | Notes |
|-----|----------|------------|-------|-------|
| `TAD{YYMM}-{###}` | `2` | `1` | `QTYOH2 -= qty` | Credit (`CASHED=N`), VAT inclusive (`TAXIC=Y`), `PO`=order id |
| `CNTAD{YYMM}-{###}` | `7` | `2` | `QTYOH2 += qty` | `PO`=original TAD; negative line qty/amount |

`JOURMODE=1` for both. Platform `REMARKS`: Lazada `##…1`, TikTok `##…2`, Shopee `##…3`, Line `##…4`.

Full tax invoice **TO** still uses Supabase `to_bill.*` only (no PARTS9 rewrite).

## Draft → pick → TAD flow

Staff pack before posting TAD:

1. **ขาย** → `บันทึกฉบับร่าง` (Supabase `online_sale.drafts` — no TAD number, no stock cut, no sales)
2. **ค้นหา** (filter ฉบับร่าง) → select drafts → `พิมพ์ใบจัดสินค้ารวม` (refs = order ids)
3. Pack / substitute on the floor
4. Open draft → edit lines → `ยืนยันขาย (ออก TAD)` (re-checks duplicate PO + stock)

Duplicate order id is checked against both active drafts and posted TAD. Printed drafts show status **พิมพ์ใบจัดแล้ว**. Pick sheets are not generated from TAD anymore.

## Enable writes

1. Run [`scripts/sql/grant_online_sale_writer.sql`](../scripts/sql/grant_online_sale_writer.sql) on KSS as admin.
2. Set `ONLINE_SALE_WRITE_ENABLED=true` in `.env`.
3. Restart `kcw-online-sale.service`.

## Deploy

```bash
systemctl --user daemon-reload
systemctl --user enable --now kcw-online-sale.service
# After verify, stop the old standalone TO process:
systemctl --user disable --now kcw-to-bill.service
```

Copy unit from `scripts/systemd/kcw-online-sale.service` into `~/.config/systemd/user/` if needed.

## Firewall (LAN)

`scripts/hq-linux-firewall.sh` includes LAN TCP **8796**. Or add only this port:

```bash
sudo bash scripts/hq-open-port-8796.sh
```

## Auth

Same pattern as hq-receive: LINE HMAC token (`APP=kcw-online-sale`) or private LAN / Tailscale. Opening the UI also sets the `kcw_to_bill` cookie so the embedded TO iframe works.

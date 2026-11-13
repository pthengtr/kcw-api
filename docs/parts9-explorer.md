# PARTS9 Explorer

Search / detail UI on `:8788` (`kcw-parts9-explorer`). Product discovery is read-mostly; write surfaces below edit **HQ (KSS)** only so waiting rows show up in hq-po.

## Read

- `GET /parts9/` — search UI
- `GET /parts9/api/search` — products / docs / ICLOW summary
- `GET /parts9/api/product/{bcode}` — detail + movement + insight + open **รอสั่ง** (`waiting`)
- Substitutes manage under `/parts9/substitutes`

## Writes (product detail / + สินค้าใหม่)

| Action | Route | Backend | Flag |
|--------|-------|---------|------|
| Create ICMAS | `POST /parts9/api/products` | `hq_receive.icmas_create.create_product` | `HQ_RECEIVE_PIMAS_WRITE_ENABLED` |
| Update master | `PUT /parts9/api/products/{bcode}` | `update_product` | same |
| Edit L | `POST /parts9/api/products/{bcode}/qtymin` | `hq_po.update_qtymin` | `HQ_PO_ICLOW_STAMP_ENABLED` |
| Edit QTYGET | `POST /parts9/api/products/{bcode}/qtyget` | Explorer writer | stamp |
| Put in รอสั่ง | `POST /parts9/api/products/{bcode}/waiting` | `force_insert_waiting_iclow` → ICLOW `ORDERED='N'` | stamp |
| Edit waiting qty | `PATCH /parts9/api/waiting/{iclow_id}` | ICLOW.QTY (รอสั่ง only) | stamp |
| Upload / delete photos | `POST` / `DELETE .../images` | LINE image helpers (Supabase `pictures`) | Supabase creds |

**ใส่รอสั่งซื้อ** inserts a waiting ICLOW row immediately (even if on-hand is still above L). It does **not** stamp `ORDERED='Y'` — confirming an order stays on hq-po. If an unreceived ICLOW row already exists, the API returns `409 already_open` with `iclow_id`.

Default waiting qty: body `qty` → else `QTYGET` if set (> 0) → else `max(L − QTYOH2, 1)` → else `1`.

## Auth

Same LINE / Tailscale cookie as the rest of Explorer. Writes use the same `_require` gate.

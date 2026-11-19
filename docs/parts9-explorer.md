# PARTS9 Explorer

Search / detail UI on `:8788` (`kcw-parts9-explorer`). Product discovery is read-mostly; write surfaces below edit **HQ (KSS)** only so waiting rows show up in hq-po.

## Product detail layout

- Search cards: photo, code, name, model/brand, PCODE/MCODE, PRICE1, HQ·SYP stock+bin on one line (omit empty fields)
- Header above tabs: labeled facts (brand/model/company/OEM แท้|ไม่แท้), prices, **สต็อกคงเหลือ** with bin under HQ/SYP, existing photos only — category/CODE1 live in **จัดการสินค้า**
- Tabs: **Insight** (default) · ประวัติซื้อ · ประวัติขาย · การสั่งซื้อ · ต้นทุน (admin)
- Insight / buy / sell match hq-po hist UX, including **HQ / SYP** site toggle (kept when switching tabs)
- **จัดการสินค้า** opens edit + photo upload; L / ล็อต / ใส่รอสั่ง live under การสั่งซื้อ
- Branch labels are **HQ / SYP** (same as hq-po), not Thai long names

## Read

- `GET /parts9/` — search UI
- `GET /parts9/api/search` — products / docs / ICLOW summary
- `GET /parts9/api/product/{bcode}` — detail + movement + insight + open **รอสั่ง** (`waiting`)
- `GET /parts9/api/history/{bcode}/purchases|sales` — ประวัติซื้อ/ขาย (same payload as hq-po)
- `GET /parts9/api/history/bills/{kind}/{billno}` — รายละเอียดบิล
- Substitutes manage under `/parts9/substitutes`

## Writes (จัดการสินค้า / + สินค้าใหม่ / tab การสั่งซื้อ)

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

# HQ purchase order (`kcw-hq-po`)

Standalone app on port **8793**, separate from transfer (`:8792`). LINE command: `สั่งซื้อ`.

Supabase `hq_po` is the purchase order. PARTS9 `POMAS` / `PODET` are not written.

## Flow

1. The list reads HQ `dbo.ICLOW` rows still waiting to order (`ORDERED <> 'Y'`, not canceled).
2. Default layout is **ตามเจ้าหนี้**. **ตามสินค้า** is the same rows, flat.
3. AI safe stock comes from `product_insight.product_insights` (`site=hq`): company `safe_holding_qty` (else `suggested_order_qty`) minus live HQ+SYP `QTYOH2` and ค้างรับ qty (`ORDERED='Y'`, not received, not canceled), pack-rounded. An AI line can be confirmed when it has a vendor. Confirm inserts one ICLOW row already ordered.
4. Each line shows the PARTS9 reorder qty (`QTYGET`, otherwise `QTYMIN − QTYOH2`) and the AI qty. The order qty is editable and starts from the ICLOW qty, or from the AI qty when there is no ICLOW row. Tapping a recommendation copies it into the order qty.
5. **ดูใบส่งเจ้าหนี้** opens the sheet for the vendor’s salesperson. **แบบย่อ** is the goods list (รหัส, ชื่อ, แบบ, NO.1, NO.2, ยี่ห้อ, จำนวน, หน่วย, ราคา/หน่วย) plus the supplier block: name, account, address, phone, tax id, contact, and credit term. **แบบเต็ม** is the purchase order with the same supplier block, ship-to HQ, line amounts, 7% VAT, and signature lines. **พิมพ์** and **คัดลอกส่งฝ่ายขาย** use the selected form. Unit price is filled from last cost (`COSTLAST`, else `COSTNET`) when that figure exists. The printed sheet does not label it as cost. **บันทึกว่าสั่งแล้ว** is the step that writes ICLOW. Confirm creates one Supabase PO per vendor (`HP` + Buddhist `YYMM` + 4 hex chars, e.g. `HP6910-A1B2`) and writes the edited qty. An existing ICLOW row is stamped `ORDERED='Y'`, `DOCNO`, `DOCDATE`. An AI-only product gets a new ICLOW row with those fields set. Cancel of a stamped row clears the stamp. Cancel of a row this app inserted sets `CANCELED='Y'`. A saved order can be printed or copied again from **สั่งแล้ว**.
6. Receive is not written here. The ordered screen reads `RECEIVED` / `RCVDNO` and resolves `RCVDNO` to `PIMAS`. PARTS9 receive is what sets those fields.

Cancel is allowed only while every line is still unreceived and `DOCNO` is still ours. It sets `ORDERED='N'`, clears `DOCNO` / `DOCDATE`, and marks the Supabase order canceled.

## Enable the stamp

Listing works with the stamp flag off. Confirm and cancel refuse until both of these are done:

1. Run [`scripts/sql/grant_hq_po_writer.sql`](../scripts/sql/grant_hq_po_writer.sql) on HQ `KSS` as a SQL admin.
2. Set `HQ_PO_ICLOW_STAMP_ENABLED=true` in `.env` and restart `kcw-hq-po`.

```bash
systemctl --user enable --now kcw-hq-po.service
```

Optional URLs for the LINE button: `HQ_PO_PUBLIC_BASE_URL`, `HQ_PO_TAILSCALE_BASE_URL`. If unset, the bot rewrites the HQ explorer heartbeat onto port 8793.

Apply the Supabase migrations `20261009120000_hq_po_schema.sql` and `20261009120100_hq_po_grants.sql` before confirming an order.

## Known limit

If the PARTS9 receive screen only flips ICLOW rows that belong to a real `POMAS`, rows stamped by this app stay ค้างรับ until that is checked on one test SKU. This service will not set `RECEIVED` itself.

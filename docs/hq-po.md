# HQ purchase order (`kcw-hq-po`)

Standalone app on port **8793**, separate from transfer (`:8792`). LINE command: `สั่งซื้อ`.

Supabase `hq_po` is the purchase order. PARTS9 `POMAS` / `PODET` are not written.

## Flow

1. The list reads HQ `dbo.ICLOW` rows still waiting to order (`ORDERED <> 'Y'`, not canceled).
2. The waiting list opens as **ตามสินค้า**. Search matches the product code, description, model, genuine number, factory number, brand, and the vendor already on the line (account and name). **เปลี่ยนเจ้าหนี้** loads, for that one product, the HQ purchase accounts (`PIDET.ACCTNO`) plus the catalog vendor (`ICMAS.VENDOR`). Choosing an account updates the line immediately. **เลือกเจ้าหนี้ใหม่** searches live PARTS9 `APMAS` accounts and can set one that has never supplied this product. Saving the order writes that account onto `ICLOW.VENDOR`. **เพิ่มสินค้า**, beside the search box, searches `ICMAS` for a code that is not already on the list. A waiting line with no product code is left off the list. From a vendor, the new line is checked on that vendor's order. The line is written to ICLOW only on confirm, the same way as a substitute. **สินค้าแทน** looks up, on click, the confirmed replacement group plus other codes with the same clean เบอร์แท้ (`PCODE`) or เบอร์โรงงาน (`MCODE`). A peer already on the waiting list is scrolled into view. A peer that is not waiting is added as its own line and inserted into ICLOW on confirm. **สั่งกับเจ้าหนี้นี้** on a product opens that vendor with the waiting lines and that vendor's AI lines. **ดูสินค้าที่เคยสั่งจากเจ้าหนี้นี้** loads products purchased from that vendor which are not already waiting. Searching a short name that is not on the waiting list, such as `RR`, shows only that button. **ตามบริษัท** lists each vendor with a count of its products. Opening a vendor shows only that vendor’s lines, with checkboxes. **ดูใบส่งเจ้าหนี้** is available there and includes only the checked lines. Unchecked lines stay on the waiting list. When the product has both a small unit (`UI1`) and a large pack (`UI2`, `MTP2` > 1), the line can be ordered in either unit. A large-pack line stores `MTP = MTP2`. A small-unit line stores `MTP = 1`.
3. AI safe stock comes from `product_insight.product_insights` (`site=hq`): company `safe_holding_qty` (else `suggested_order_qty`) minus live HQ+SYP `QTYOH2` and ค้างรับ qty (`ORDERED='Y'`, not received, not canceled), pack-rounded. The waiting list reads stored `ICMAS.QTYOH2` and does not wait for a ledger scan. A background rebuild still runs (`QTYOH2_SYNC_ON_READ`) and the next load within two minutes sees it. A vendor's AI lines, a product opened for ordering, and purchase history still rebuild HQ and SYP on-hand before they show a number. The waiting list loads a policy only for those waiting products. Opening **AI** loads the other recommended products and rebuilds on-hand for the lines it is about to show. A peer lookup and a confirm do the same. On HQ, `trg_PIDET_sync_icmas_qtyoh2` also recomputes on-hand when a purchase line is posted, so the stored quantity does not wait for a screen to open. An AI line can be confirmed when it has a vendor. Confirm inserts one ICLOW row already ordered.
4. Each line shows ชื่อรุ่น, เบอร์แท้ (`PCODE`), เบอร์โรงงาน (`MCODE`), ยี่ห้อ, ราคา (`PRICE1`), and ค่า (`COSTLAST`, otherwise `COSTNET`), the HQ low-stock point **L** (`ICMAS.QTYMIN`), plus the PARTS9 reorder qty (`QTYGET`, otherwise `QTYMIN − QTYOH2`) and the AI qty. When the stamp is on, L is editable on the waiting line and must stay **positive**; writing it updates HQ `ICMAS.QTYMIN` without touching ICLOW. Zero / negative values are refused — setting `QTYMIN = -1` stays on **นำออก**. The order qty is editable and starts from the ICLOW qty, or from the AI qty when there is no ICLOW row. Tapping a recommendation copies it into the order qty.
5. From the open vendor, **ดูใบส่งเจ้าหนี้** opens the sheet for that vendor’s salesperson, using the checked lines only. **แบบย่อ** is the goods list (รหัส, ชื่อ, แบบ, NO.1, NO.2, ยี่ห้อ, จำนวน, หน่วย, ราคา/หน่วย) plus the supplier code and name only. **แบบเต็ม** is the purchase order with the full supplier block (name, account, address, phone, tax id, contact, and credit term), ship-to HQ, line amounts, 7% VAT, and signature lines. Each line shows the product’s first public photo when one exists; a missing picture is left blank. **พิมพ์** and **คัดลอกส่งฝ่ายขาย** use the selected form. The copied text includes the photo URL. Unit price is filled from last cost (`COSTLAST`, else `COSTNET`) when that figure exists. The printed sheet does not label it as cost. **บันทึกว่าสั่งแล้ว** is the step that writes ICLOW. Confirm creates one Supabase PO per vendor (`HP` + Buddhist `YYMM` + 4 hex chars, e.g. `HP6910-A1B2`) and writes the edited qty. An existing ICLOW row is stamped `ORDERED='Y'`, `DOCNO`, `DOCDATE`. An AI-only product gets a new ICLOW row with those fields set. Cancel of a stamped row clears the stamp. Cancel of a row this app inserted sets `CANCELED='Y'`. A saved order can be printed or copied again from **สั่งแล้ว**.
6. Receive is not written here. The ordered screen reads `RECEIVED` / `RCVDNO` and resolves `RCVDNO` to `PIMAS`. PARTS9 receive is what sets those fields. **สั่งแล้ว** filters by vendor (name or account) and product code. Both filters apply together. A product-code filter shows only the matching lines on each order. Print and cancel still use the whole order.

**ไม่เอาแล้ว** on **สั่งแล้ว → ตามสินค้า** drops that one ค้างรับ row. It sets `CANCELED='Y'` on that `ICLOW` id and closes the open purchase-order line when this app has one. The row leaves ค้างรับ and does not return to รอสั่ง. `QTYMIN` is left alone, so a later low-stock pass can open a new waiting row. **เปลี่ยนเจ้าสั่ง** and **สั่งย้ำเจ้าเดิม** still send the row back to รอสั่ง with a status.

**ยกเลิกบรรทัด** is for one product the vendor cannot supply. It is allowed while that line is still unreceived and `DOCNO` is still ours. It sets `ORDERED='N'`, clears `DOCNO` / `DOCDATE`, and marks that Supabase line canceled, so the row returns to the waiting list — including a row this app inserted. When that was the last open line, the order is canceled too.

Cancel of the whole order is allowed only while every line is still unreceived and `DOCNO` is still ours. A row that was already on ICLOW returns to the waiting list. A row this app inserted is marked `CANCELED='Y'` and does not return.

**นำออก** on a รอสั่ง line asks for confirmation, then sets HQ `ICMAS.QTYMIN` to `-1` (the legacy qtylo do-not-order mark) and sets `CANCELED='Y'` on that product's unordered, unreceived ICLOW rows. ค้างรับ rows stay. The product leaves this list and the legacy รอสั่งซื้อ list, and a later low-stock insert does not recreate it.

## Enable the stamp

Listing works with the stamp flag off. Confirm and cancel refuse until both of these are done:

1. Run [`scripts/sql/grant_hq_po_writer.sql`](../scripts/sql/grant_hq_po_writer.sql) on HQ `KSS` as a SQL admin.
2. Set `HQ_PO_ICLOW_STAMP_ENABLED=true` in `.env` and restart `kcw-hq-po`.

```bash
systemctl --user enable --now kcw-hq-po.service
```

Optional URLs for the LINE button: `HQ_PO_PUBLIC_BASE_URL`, `HQ_PO_TAILSCALE_BASE_URL`. If unset, the bot rewrites the HQ explorer heartbeat onto port 8793.

Apply the Supabase migrations `20261009120000_hq_po_schema.sql`, `20261009120100_hq_po_grants.sql`, `20261031170000_hq_po_release_marks.sql`, and `20261031183000_hq_po_product_vendor_blocks.sql` before confirming an order. A product marked not available from a vendor is stored in `hq_po.product_vendor_blocks`.

## Known limit

If the PARTS9 receive screen only flips ICLOW rows that belong to a real `POMAS`, rows stamped by this app stay ค้างรับ until that is checked on one test SKU. This service will not set `RECEIVED` itself.

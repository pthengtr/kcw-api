from __future__ import annotations

from src.online_sale.issuers import resolve_print_issuer
from src.online_sale.sheets.common import (
    COMPANY,
    CSS,
    esc,
    line_rows_html,
    meta_row,
    thai_date,
    totals_block,
)
from src.online_sale.shops import channel_label, customer_name_without_shop


def render_tad_sheet(bill: dict) -> str:
    lines = bill.get("lines") or []
    amounts = [ln.get("amount") for ln in lines]
    seller_name = (
        str(bill.get("issuer_label") or "").strip() or resolve_print_issuer(bill)
    )

    raw_name = bill.get("customer_name") or bill.get("acctname") or ""
    customer_name = customer_name_without_shop(str(raw_name))
    customer_address = bill.get("customer_address") or bill.get("address") or ""
    customer_tax_id = bill.get("customer_tax_id") or bill.get("tax_id") or ""
    shop = bill.get("shop_name") or ""
    channel = bill.get("channel") or channel_label(bill.get("platform"), shop)

    left = (
        "<div class='side'>"
        + meta_row("ลูกค้า", esc(customer_name))
        + meta_row("ที่อยู่", esc(customer_address))
        + meta_row("เลขประจำตัวผู้เสียภาษี", esc(customer_tax_id))
        + "</div>"
    )
    right = (
        "<div class='side'>"
        + meta_row("เลขที่", esc(bill.get("billno")))
        + meta_row("วันที่", thai_date(bill.get("bill_date")))
        + meta_row("ช่องทาง", esc(channel))
        + meta_row("เลขคำสั่งซื้อ", esc(bill.get("online_po")))
        + "</div>"
    )
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<title></title>
<style>{CSS}</style></head><body>
<div class="rcp">
  <div class="co">{esc(COMPANY['name'])}</div>
  <div class="addr">{esc(COMPANY['address'])}<br>{esc(COMPANY['phone'])}<br>{esc(COMPANY['tax'])}</div>
  <div class="title">ใบกำกับภาษีอย่างย่อ/ใบส่งสินค้า</div>
  <div class="meta">{left}{right}</div>
  <table>
    <thead><tr>
      <th class="ctr">#</th><th>รหัสสินค้า</th><th>รายการ</th>
      <th class="num">ราคา/หน่วย</th><th class="num">จำนวน</th><th class="ctr">หน่วย</th>
      <th class="num">รวมยอดเงิน</th>
    </tr></thead>
    <tbody>{line_rows_html(lines)}</tbody>
  </table>
  {totals_block(amounts)}
  <div class="foot">พนักงานขาย: <b>{esc(seller_name)}</b></div>
</div>
<script>
window.onload=function(){{
  document.title="";
  setTimeout(function(){{ window.print(); }}, 200);
}};
</script>
</body></html>"""

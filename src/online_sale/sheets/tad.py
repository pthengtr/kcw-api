from __future__ import annotations

from src.online_sale.sheets.common import (
    COMPANY,
    CSS,
    esc,
    fmt_money,
    line_rows_html,
    platform_label,
    thai_date,
    totals_block,
)


def render_tad_sheet(bill: dict) -> str:
    lines = bill.get("lines") or []
    amounts = [ln.get("amount") for ln in lines]
    meta = (
        f"<div><b>เลขที่</b> {esc(bill.get('billno'))}</div>"
        f"<div><b>วันที่</b> {thai_date(bill.get('bill_date'))}</div>"
        f"<div><b>แพลตฟอร์ม</b> {esc(platform_label(bill.get('platform') or ''))}</div>"
        f"<div><b>ร้านค้า</b> {esc(bill.get('shop_name') or bill.get('acctname'))}</div>"
        f"<div><b>เลขคำสั่งซื้อ</b> {esc(bill.get('online_po'))}</div>"
        f"<div><b>ลูกค้า</b> {esc(bill.get('acctname'))}</div>"
    )
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<title></title>
<style>{CSS}</style></head><body>
<div class="rcp">
  <div class="co">{esc(COMPANY['name'])}</div>
  <div class="addr">{esc(COMPANY['address'])}<br>{esc(COMPANY['phone'])}<br>{esc(COMPANY['tax'])}</div>
  <div class="title">ใบกำกับภาษีอย่างย่อ/ใบส่งสินค้า</div>
  <div class="meta">{meta}</div>
  <table>
    <thead><tr>
      <th class="ctr">#</th><th>รหัสสินค้า</th><th>รายการ</th>
      <th class="num">ราคา/หน่วย</th><th class="num">จำนวน</th><th class="ctr">หน่วย</th>
      <th class="num">รวมยอดเงิน</th>
    </tr></thead>
    <tbody>{line_rows_html(lines)}</tbody>
  </table>
  {totals_block(amounts)}
  <div class="foot">พนักงานขาย: <b>{esc(bill.get('sale') or '')}</b></div>
</div>
<script>
window.onload=function(){{
  document.title="";
  setTimeout(function(){{ window.print(); }}, 200);
}};
</script>
</body></html>"""

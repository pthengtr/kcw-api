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
from src.online_sale.vat import money


def render_cntad_sheet(bill: dict, *, original: dict | None = None, reason: str = "") -> str:
    lines = bill.get("lines") or []
    amounts = [abs(float(ln.get("amount") or 0)) for ln in lines]
    orig_after = money((original or {}).get("aftertax") or 0)
    credit_after = money(abs(float(bill.get("aftertax") or sum(amounts))))
    correct_after = orig_after - credit_after
    credit_tax = money(abs(float(bill.get("tax") or 0)))
    if credit_tax == 0 and amounts:
        from src.online_sale.vat import totals_from_amounts

        credit_tax = totals_from_amounts(amounts)["tax"]

    reason_text = reason or bill.get("reason") or ""
    meta = (
        f"<div><b>เลขที่</b> {esc(bill.get('billno'))}</div>"
        f"<div><b>วันที่</b> {thai_date(bill.get('bill_date'))}</div>"
        f"<div><b>อ้างอิง</b> {esc(bill.get('online_po') or bill.get('tad_billno'))}</div>"
        f"<div><b>แพลตฟอร์ม</b> {esc(platform_label(bill.get('platform') or ''))}</div>"
        f"<div><b>ร้านค้า</b> {esc(bill.get('shop_name') or bill.get('acctname'))}</div>"
        f"<div><b>ลูกค้า</b> {esc(bill.get('acctname'))}</div>"
    )
    cn_box = (
        "<div class='cn-box'>"
        f"<div class='row'><span>เหตุผลที่ออกใบลดหนี้</span><span>{esc(reason_text)}</span></div>"
        f"<div class='row'><span>มูลค่าตามใบกำกับภาษีเดิม</span><span>{fmt_money(orig_after)}</span></div>"
        f"<div class='row'><span>มูลค่าที่ถูกต้อง</span><span>{fmt_money(correct_after)}</span></div>"
        f"<div class='row'><span>ผลต่างที่ลดหนี้</span><span>{fmt_money(credit_after)}</span></div>"
        f"<div class='row'><span>VAT ของยอดลดหนี้</span><span>{fmt_money(credit_tax)}</span></div>"
        f"<div class='row'><b>รวมยอดลดหนี้ (รวม VAT)</b><b>{fmt_money(credit_after)}</b></div>"
        "</div>"
    )
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<title>{esc(bill.get('billno'))}</title>
<style>{CSS}</style></head><body>
<div class="rcp">
  <div class="co">{esc(COMPANY['name'])}</div>
  <div class="addr">{esc(COMPANY['address'])}<br>{esc(COMPANY['phone'])}<br>{esc(COMPANY['tax'])}</div>
  <div class="title">ใบลดหนี้/ใบกำกับภาษี</div>
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
  {cn_box}
  <div class="foot">พนักงานขาย: <b>{esc(bill.get('sale') or '')}</b></div>
</div>
<script>window.onload=()=>setTimeout(()=>window.print(),200)</script>
</body></html>"""

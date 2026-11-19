from __future__ import annotations

from decimal import Decimal

from src.online_sale.sheets.common import (
    COMPANY,
    CSS,
    esc,
    fmt_money,
    line_rows_html,
    meta_row,
    thai_date,
)
from src.online_sale.shops import channel_label, customer_name_without_shop
from src.online_sale.issuers import resolve_print_issuer
from src.online_sale.vat import money, totals_from_amounts


def _signature(title: str, *, name: str = "", signed_on: str = "") -> str:
    name_cell = esc(name) if name else ""
    date_cell = esc(signed_on) if signed_on else ""
    return f"""
    <section>
      <h3>{esc(title)}</h3>
      <div class="hand"></div>
      <div class="sig-fields">
        <span>ลายมือชื่อ</span><span class="line"></span>
        <span>ชื่อ</span><span class="line">{name_cell}</span>
        <span>วันที่</span><span class="line">{date_cell}</span>
      </div>
    </section>"""


def credit_note_summary(bill: dict, original: dict | None = None) -> dict[str, Decimal]:
    """Pre-VAT original / correct / credit, plus VAT and inclusive credit total.

    Full return: credit_before == original_before → correct_before == 0.
    Partial return: correct_before == original_before − credit_before.
    Line amounts on TAD/CNTAD are VAT-inclusive; header beforetax is the source of truth.
    """
    lines = bill.get("lines") or []
    amounts = [abs(float(ln.get("amount") or 0)) for ln in lines]
    from_lines = totals_from_amounts(amounts) if amounts else None

    orig_before = money(abs(float((original or {}).get("beforetax") or 0)))
    credit_before = money(abs(float(bill.get("beforetax") or 0)))
    credit_tax = money(abs(float(bill.get("tax") or 0)))
    credit_after = money(abs(float(bill.get("aftertax") or 0)))

    if credit_after == 0 and from_lines:
        credit_before = from_lines["beforetax"]
        credit_tax = from_lines["tax"]
        credit_after = from_lines["aftertax"]
    elif credit_before == 0 and from_lines and from_lines["beforetax"]:
        credit_before = from_lines["beforetax"]
        if credit_tax == 0:
            credit_tax = from_lines["tax"]
        if credit_after == 0:
            credit_after = from_lines["aftertax"]

    correct_before = money(orig_before - credit_before)
    return {
        "original_before": orig_before,
        "correct_before": correct_before,
        "credit_before": credit_before,
        "credit_tax": credit_tax,
        "credit_after": credit_after,
    }


def render_cntad_sheet(bill: dict, *, original: dict | None = None, reason: str = "") -> str:
    lines = bill.get("lines") or []
    summary = credit_note_summary(bill, original)
    reason_text = reason or bill.get("reason") or ""
    issuer_name = str(bill.get("issuer_label") or "").strip() or resolve_print_issuer(bill)
    signed_on = thai_date(bill.get("bill_date"))

    raw_name = bill.get("customer_name") or bill.get("acctname") or ""
    customer_name = customer_name_without_shop(str(raw_name))
    customer_address = bill.get("customer_address") or bill.get("address") or ""
    customer_tax_id = bill.get("customer_tax_id") or bill.get("tax_id") or ""

    tad_billno = bill.get("tad_billno") or bill.get("online_po") or ""
    tad_date = (
        bill.get("tad_bill_date")
        or (original or {}).get("bill_date")
        or ""
    )
    order_id = (
        bill.get("order_id")
        or (original or {}).get("online_po")
        or ""
    )
    shop = bill.get("shop_name") or ""
    if not shop and (original or {}).get("shop_name"):
        shop = original.get("shop_name")  # type: ignore[union-attr]
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
        + meta_row("อ้างอิง", esc(tad_billno))
        + meta_row("วันที่บิลอ้างอิง", thai_date(tad_date))
        + meta_row("ช่องทาง", esc(channel))
        + meta_row("เลขคำสั่งซื้อ", esc(order_id))
        + "</div>"
    )
    cn_box = (
        "<div class='cn-box'>"
        f"<div class='reason'><span class='k'>เหตุผลที่ออกใบลดหนี้</span>"
        f"<span class='v'>{esc(reason_text) or '—'}</span></div>"
        f"<div class='row'><span>มูลค่าตามใบกำกับภาษีเดิม (ก่อน VAT)</span>"
        f"<span>{fmt_money(summary['original_before'])}</span></div>"
        f"<div class='row'><span>มูลค่าที่ถูกต้อง (ก่อน VAT)</span>"
        f"<span>{fmt_money(summary['correct_before'])}</span></div>"
        f"<div class='row'><span>ผลต่างที่ลดหนี้ (ก่อน VAT)</span>"
        f"<span>{fmt_money(summary['credit_before'])}</span></div>"
        f"<div class='row'><span>VAT 7%</span>"
        f"<span>{fmt_money(summary['credit_tax'])}</span></div>"
        f"<div class='row net'><span>รวมยอดลดหนี้ (รวม VAT)</span>"
        f"<span>{fmt_money(summary['credit_after'])}</span></div>"
        "</div>"
    )
    signs = "".join(
        (
            _signature("ผู้ออกเอกสาร", name=issuer_name, signed_on=signed_on),
            _signature("ผู้อนุมัติเอกสาร", signed_on=signed_on),
            _signature("ผู้รับเอกสาร"),
        )
    )
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<title></title>
<style>{CSS}</style></head><body>
<div class="rcp">
  <div class="co">{esc(COMPANY['name'])}</div>
  <div class="addr">{esc(COMPANY['address'])}<br>{esc(COMPANY['phone'])}<br>{esc(COMPANY['tax'])}</div>
  <div class="title">ใบลดหนี้/ใบกำกับภาษี</div>
  <div class="meta">{left}{right}</div>
  <table>
    <thead><tr>
      <th class="ctr">#</th><th>รหัสสินค้า</th><th>รายการ</th>
      <th class="num">ราคา/หน่วย</th><th class="num">จำนวน</th><th class="ctr">หน่วย</th>
      <th class="num">รวมยอดเงิน</th>
    </tr></thead>
    <tbody>{line_rows_html(lines)}</tbody>
  </table>
  {cn_box}
  <div class="sign">{signs}</div>
</div>
<script>
window.onload=function(){{
  document.title="";
  setTimeout(function(){{ window.print(); }}, 200);
}};
</script>
</body></html>"""

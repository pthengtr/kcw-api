"""Printable full tax invoice. Amounts are the frozen TAD snapshot."""

from __future__ import annotations

import html
from datetime import date, datetime
from decimal import Decimal

from src.hq_po.sheet import COMPANY_ADDRESS, COMPANY_BRANCH, COMPANY_NAME, COMPANY_PHONE
from src.pay_notes.baht_text import baht_text

_MONTHS = (
    "มกราคม",
    "กุมภาพันธ์",
    "มีนาคม",
    "เมษายน",
    "พฤษภาคม",
    "มิถุนายน",
    "กรกฎาคม",
    "สิงหาคม",
    "กันยายน",
    "ตุลาคม",
    "พฤศจิกายน",
    "ธันวาคม",
)


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _money(value) -> str:
    amount = Decimal(str(value or 0)).quantize(Decimal("0.01"))
    return f"{amount:,.2f}"


def _qty(value) -> str:
    amount = Decimal(str(value or 0))
    text = f"{amount:,.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _day(value) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = str(value or "").strip()
    if len(text) < 10:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def _thai_date(value) -> str:
    day = _day(value)
    if not day:
        return "—"
    return f"{day.day} {_MONTHS[day.month - 1]} {day.year + 543}"


def build_sheet(invoice: dict, *, seller_tax_id: str) -> str:
    voided = invoice.get("status") == "void"
    lines = invoice.get("lines") or []
    body = []
    for index, line in enumerate(lines, start=1):
        body.append(
            "<tr>"
            f"<td class='ctr'>{index}</td>"
            f"<td class='mono'>{_esc(line.get('bcode'))}</td>"
            f"<td>{_esc(line.get('detail'))}</td>"
            f"<td class='num'>{_esc(_qty(line.get('qty')))} {_esc(line.get('ui'))}</td>"
            f"<td class='num'>{_money(line.get('price'))}</td>"
            f"<td class='num'>{_money(line.get('amount'))}</td>"
            "</tr>"
        )
    if not body:
        body.append("<tr><td colspan='6'>ไม่มีรายการ</td></tr>")
    discount = Decimal(str(invoice.get("discount") or 0))
    discount_row = ""
    if discount:
        discount_row = (
            f"<div class='row'><span>ส่วนลด</span><span>{_money(discount)}</span></div>"
        )
    email = str(invoice.get("email") or "").strip()
    phone = str(invoice.get("phone") or "").strip()
    extra = ""
    if phone:
        extra += f"<div><span class='k'>โทร</span> {_esc(phone)}</div>"
    if email:
        extra += f"<div><span class='k'>อีเมล</span> {_esc(email)}</div>"
    watermark = "<div class='void'>ยกเลิก</div>" if voided else ""
    reason = ""
    if voided and invoice.get("void_reason"):
        reason = f"<p class='reason'>เหตุผลที่ยกเลิก: {_esc(invoice.get('void_reason'))}</p>"
    order = str(invoice.get("online_po") or "").strip()
    order_line = f"<div><span class='k'>เลขออเดอร์</span> {_esc(order)}</div>" if order else ""
    return f"""
<article class="tof">
  {watermark}
  <div class="top">
    <div>
      <div class="logo">KCW</div>
      <div class="co">{_esc(COMPANY_NAME)}</div>
      <div class="addr">{_esc(COMPANY_ADDRESS)}<br>โทร {_esc(COMPANY_PHONE)} · {_esc(COMPANY_BRANCH)}</div>
      <div class="addr">เลขประจำตัวผู้เสียภาษี {_esc(seller_tax_id)}</div>
    </div>
    <div class="doc">
      <h1>ใบกำกับภาษีเต็มรูป</h1>
      <p class="en">FULL TAX INVOICE</p>
      <p class="no">{_esc(invoice.get("docno"))}</p>
    </div>
  </div>
  <div class="rule"></div>
  <div class="boxes">
    <div class="box">
      <h2>ผู้ซื้อ</h2>
      <div class="name">{_esc(invoice.get("customer_name"))}</div>
      <div>{_esc(invoice.get("address"))}</div>
      <div><span class="k">เลขประจำตัวผู้เสียภาษี</span> {_esc(invoice.get("tax_id"))}</div>
      <div><span class="k">สาขา</span> {_esc(invoice.get("branch_label"))}</div>
      {extra}
    </div>
    <div class="box">
      <h2>เอกสาร</h2>
      <div><span class="k">วันที่</span> {_esc(_thai_date(invoice.get("bill_date")))}</div>
      <div><span class="k">อ้างอิง</span> {_esc(invoice.get("tad_billno"))}</div>
      {order_line}
      <div><span class="k">ออกเอกสาร</span> {_esc(_thai_date(invoice.get("issued_at")))}</div>
    </div>
  </div>
  <table>
    <thead>
      <tr>
        <th class="ctr">#</th><th>รหัส</th><th>รายละเอียด</th>
        <th class="num">จำนวน</th><th class="num">ราคา</th><th class="num">จำนวนเงิน</th>
      </tr>
    </thead>
    <tbody>
      {''.join(body)}
    </tbody>
  </table>
  <div class="foot">
    <div class="note">
      เอกสารนี้เป็นใบกำกับภาษีเต็มรูปของ {_esc(invoice.get("tad_billno"))}
      รายการและยอดเงินคัดลอกจากบิลนั้น
    </div>
    <div class="tot">
      {discount_row}
      <div class="row"><span>ก่อนภาษี</span><span>{_money(invoice.get("beforetax"))}</span></div>
      <div class="row"><span>ภาษีมูลค่าเพิ่ม</span><span>{_money(invoice.get("tax"))}</span></div>
      <div class="row net"><span>รวมทั้งสิ้น</span><span>{_money(invoice.get("aftertax"))}</span></div>
      <div class="words">({_esc(baht_text(invoice.get("aftertax")))})</div>
    </div>
  </div>
  {reason}
  <div class="sign">
    <div>ผู้รับสินค้า<div class="line"></div></div>
    <div>ผู้ขาย<div class="line"></div></div>
  </div>
</article>
"""

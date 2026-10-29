"""Printable full tax invoice. Amounts are the frozen TAD snapshot."""

from __future__ import annotations

import html
from datetime import date, datetime
from decimal import Decimal

from src.hq_po.sheet import COMPANY_ADDRESS, COMPANY_BRANCH, COMPANY_NAME, COMPANY_PHONE
from src.pay_notes.baht_text import baht_text
from src.to_bill.buyers import shop_label

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


def _slash_date(value) -> str:
    day = _day(value)
    if not day:
        return "—"
    return f"{day.day:02d}/{day.month:02d}/{day.year + 543}"


def _field(label: str, value: str, *, value_class: str = "", span: bool = False) -> str:
    if span:
        return (
            f"<div class='wide'><span class='k'>{_esc(label)}</span>"
            f"<span class='wide-v'>{value}</span></div>"
        )
    klass = f" class='{_esc(value_class)}'" if value_class else ""
    return f"<div class='k'>{_esc(label)}</div><div{klass}>{value}</div>"


def _signature(title: str) -> str:
    return f"""
    <section>
      <h3>{_esc(title)}</h3>
      <div class="hand"></div>
      <div class="sig-fields">
        <span>ลายมือชื่อ</span><span class="line"></span>
        <span>ชื่อ</span><span class="line"></span>
        <span>วันที่</span><span class="line"></span>
      </div>
    </section>"""


def build_sheet(invoice: dict, *, seller_tax_id: str) -> str:
    return "\n".join(
        _article(invoice, seller_tax_id=seller_tax_id, copy_label=label)
        for label in ("ต้นฉบับ", "สำเนา")
    )


def _article(invoice: dict, *, seller_tax_id: str, copy_label: str) -> str:
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
    buyer_head = [
        _field("ลูกค้า", f"<span class='name'>{_esc(invoice.get('customer_name'))}</span>"),
        _field("ที่อยู่", _esc(invoice.get("address")), value_class="pre"),
    ]
    buyer = [
        _field("เลขประจำตัวผู้เสียภาษี", f"<span class='wide-v'>{_esc(invoice.get('tax_id'))}</span>"),
        _field("สาขา", _esc(invoice.get("branch_label"))),
    ]
    phone = str(invoice.get("phone") or "").strip()
    email = str(invoice.get("email") or "").strip()
    if phone:
        buyer.append(_field("โทร", _esc(phone)))
    if email:
        buyer.append(_field("อีเมล", _esc(email)))
    document = [
        _field("เลขที่เอกสาร", f"<span class='no'>{_esc(invoice.get('docno'))}</span>"),
        _field("วันที่", _esc(_thai_date(invoice.get("bill_date")))),
    ]
    order = str(invoice.get("online_po") or "").strip()
    if order:
        document.append(_field("เลขคำสั่งซื้อ", _esc(order)))
    document.append(_field("อ้างอิง", _esc(invoice.get("tad_billno"))))
    shop = shop_label(invoice.get("acctname_kss"), invoice.get("acctno"))
    if shop:
        document.append(_field("ร้านค้า", _esc(shop)))
    document.append(_field("ออกเอกสาร", _esc(_thai_date(invoice.get("issued_at")))))
    watermark = "<div class='void'>ยกเลิก</div>" if voided else ""
    reason = ""
    if voided and invoice.get("void_reason"):
        reason = f"<p class='reason'>เหตุผลที่ยกเลิก: {_esc(invoice.get('void_reason'))}</p>"
    note = (
        f"<span class='keep'>ออกแทนใบกำกับภาษีอย่างย่อ {_esc(invoice.get('tad_billno'))}</span> "
        f"<span class='keep'>วันที่ {_esc(_slash_date(invoice.get('bill_date')))} ซึ่งยกเลิกแล้ว</span>"
    )
    signs = "".join(
        _signature(title)
        for title in (
            "ผู้ออกเอกสาร (ผู้ขาย)",
            "ผู้อนุมัติเอกสาร (ผู้ขาย)",
            "ผู้รับเอกสาร (ลูกค้า)",
        )
    )
    return f"""
<article class="tof">
  {watermark}
  <div class="top">
    <div class="brand">
      <div class="logo">KCW</div>
      <div class="co">{_esc(COMPANY_NAME)}</div>
      <div class="addr">{_esc(COMPANY_ADDRESS)}<br>โทร {_esc(COMPANY_PHONE)} · {_esc(COMPANY_BRANCH)}</div>
      <div class="addr">เลขประจำตัวผู้เสียภาษี {_esc(seller_tax_id)}</div>
    </div>
    <div class="doc">
      <h1>ใบกำกับภาษี/ใบเสร็จรับเงิน</h1>
      <p class="mark">({_esc(copy_label)})</p>
    </div>
  </div>
  <div class="rule"></div>
  <div class="boxes">
    <div class="box">
      <div class="who">{''.join(buyer_head)}</div>
      <div class="fields">{''.join(buyer)}</div>
    </div>
    <div class="box"><div class="fields">{''.join(document)}</div></div>
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
    <div class="note">{note}</div>
    <div class="tot">
      {discount_row}
      <div class="row"><span>ก่อนภาษี</span><span>{_money(invoice.get("beforetax"))}</span></div>
      <div class="row"><span>ภาษีมูลค่าเพิ่ม</span><span>{_money(invoice.get("tax"))}</span></div>
      <div class="row net"><span>รวมทั้งสิ้น</span><span>{_money(invoice.get("aftertax"))}</span></div>
      <div class="words">({_esc(baht_text(invoice.get("aftertax")))})</div>
    </div>
  </div>
  {reason}
  <div class="sign">{signs}
  </div>
</article>
"""

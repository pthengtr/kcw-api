"""Simplified and full purchase-order sheets sent to a vendor salesperson."""

from __future__ import annotations

import html
import logging
from datetime import date, datetime
from decimal import Decimal, ROUND_HALF_UP
from typing import Any
from zoneinfo import ZoneInfo

from src.hq_po.guards import HqPoError
from src.pay_notes.baht_text import baht_text

logger = logging.getLogger(__name__)

BKK = ZoneInfo("Asia/Bangkok")

COMPANY_SHORT = "เกียรติชัยอะไหล่ยนต์ (วังจันทร์)"
COMPANY_NAME = "บริษัท เกียรติชัยอะไหล่ยนต์ 2007 จำกัด"
COMPANY_ADDRESS = "305 ม.1 ต.ชุมแสง อ.วังจันทร์ จ.ระยอง 21210"
COMPANY_PHONE = "038-666078"
COMPANY_BRANCH = "สำนักงานใหญ่"

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

_SIMPLE_STYLE = """
<style>
.pos{font-family:Prompt,"Noto Sans Thai",sans-serif;color:#111;background:#fff;padding:16px 14px 20px;max-width:1100px;margin:0 auto 16px;border:1px solid #d0d5dd}
.pos-head{display:flex;justify-content:space-between;gap:12px;align-items:flex-start;border-bottom:2px solid #111;padding-bottom:8px}
.pos-co{font-weight:700;font-size:16px}
.pos-title{text-align:center;flex:1}
.pos-title h1{margin:0;font-size:18px;font-weight:700}
.pos-title p{margin:2px 0 0;font-size:13px}
.pos-page{font-size:12px;white-space:nowrap}
.pos-vendor{margin:10px 0 12px;border:1px solid #111;padding:8px 10px}
.pos-vendor h2{margin:0 0 6px;font-size:13px;letter-spacing:.02em}
.pos-vendor .grid{display:grid;grid-template-columns:11.5rem 1fr;gap:2px 8px;font-size:13px}
.pos-vendor .k{color:#333}
.pos-vendor .v{font-weight:650}
.pos table{width:100%;min-width:720px;border-collapse:collapse;font-size:12px}
.pos th,.pos td{border-bottom:1px solid #bbb;padding:5px 4px;text-align:left;vertical-align:top}
.pos th{border-bottom:1.5px solid #111;font-size:11px;white-space:nowrap}
.pos td.num,.pos th.num{text-align:right;white-space:nowrap}
.pos-sign{display:flex;justify-content:space-between;gap:24px;margin-top:28px;font-size:13px}
.pos-sign span{display:inline-block;min-width:9rem;border-bottom:1px solid #111;margin-left:6px}
@page pos { size: A4 landscape; margin: 8mm; }
.pos{page:pos}
@media (max-width:640px){
  .pos-head{flex-direction:column}
  .pos-vendor .grid{grid-template-columns:1fr}
  .pos-title{text-align:left}
}
@media print{
  .pos{border:0;max-width:none;padding:0}
  .pos + .pos{page-break-before:always}
}
</style>
"""

_FULL_STYLE = """
<style>
.pof{font-family:Prompt,"Noto Sans Thai",sans-serif;color:#111;background:#fff;padding:18px 16px 22px;max-width:860px;margin:0 auto 16px}
.pof-top{display:flex;justify-content:space-between;gap:16px;align-items:flex-start}
.pof-logo{font-weight:800;font-size:34px;color:#9b1c2c;letter-spacing:-.03em;line-height:.9;font-family:Impact,"Arial Black",Prompt,sans-serif}
.pof-co{font-weight:700;font-size:15px;margin-top:2px}
.pof-addr{font-size:12px;line-height:1.45;color:#222}
.pof-doc{text-align:right}
.pof-doc h1{margin:0;color:#9b1c2c;font-size:28px;font-weight:800;line-height:1}
.pof-doc .en{margin:2px 0 0;color:#667085;font-size:12px;letter-spacing:.08em}
.pof-rule{height:3px;background:#9b1c2c;margin:8px 0 12px}
.pof-boxes{display:grid;grid-template-columns:1.2fr .8fr;gap:10px}
.pof-box{border:1px solid #d0d5dd;border-radius:8px;padding:8px 10px;min-height:9rem}
.pof-box h2{margin:0 0 6px;font-size:12px;color:#344054}
.pof-box .grid{display:grid;grid-template-columns:8.2rem 1fr;gap:3px 8px;font-size:12.5px}
.pof-box .k{color:#475467}
.pof-box .v{font-weight:650}
.pof-ship{display:flex;justify-content:space-between;gap:12px;margin:10px 0;font-size:12.5px}
.pof table{width:100%;border-collapse:collapse;font-size:12px}
.pof th{background:#7a1f33;color:#fff;font-weight:650;text-align:left;padding:6px 6px;-webkit-print-color-adjust:exact;print-color-adjust:exact}
.pof td{border-bottom:1px solid #eadfe3;padding:6px;vertical-align:top}
.pof td.num,.pof th.num{text-align:right;white-space:nowrap}
.pof th.ctr,.pof td.ctr{text-align:center}
.pof .sub{display:block;color:#475467;font-size:11px;margin-top:2px}
.pof-foot{display:grid;grid-template-columns:1.2fr .8fr;gap:12px;margin-top:12px}
.pof-notes{font-size:12px;line-height:1.45}
.pof-notes h2{margin:0 0 4px;font-size:12px}
.pof-notes ol{margin:0;padding-left:1.1rem}
.pof-tot{font-size:12.5px}
.pof-tot .row{display:flex;justify-content:space-between;gap:12px;padding:2px 0}
.pof-tot .net{background:#f2f4f7;font-weight:800;font-size:15px;padding:6px 8px;margin-top:4px}
.pof-words{text-align:right;font-size:12px;margin-top:4px}
.pof-sign{display:grid;grid-template-columns:1fr 1fr 1fr;gap:16px;margin-top:28px;font-size:12px;text-align:center}
.pof-sign .line{border-bottom:1px solid #111;height:2.2rem;margin:8px 12px}
@page pof { size: A4 portrait; margin: 10mm; }
.pof{page:pof}
@media (max-width:640px){
  .pof-boxes,.pof-foot,.pof-sign{grid-template-columns:1fr}
  .pof-box .grid{grid-template-columns:1fr}
}
@media print{
  .pof{max-width:none;padding:0}
  .pof + .pof{page-break-before:always}
}
</style>
"""


def _e(value: Any) -> str:
    text = "" if value is None else str(value).strip()
    return html.escape(text or "—")


def _raw(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _num(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        number = Decimal(str(value).replace(",", "").strip())
    except Exception:
        return None
    if not number.is_finite():
        return None
    return number


def _positive_price(*values: Any) -> Decimal | None:
    for value in values:
        number = _num(value)
        if number is not None and number > 0:
            return number.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return None


def _qty_text(value: Any) -> str:
    number = _num(value)
    if number is None:
        return "—"
    if number == number.to_integral():
        return f"{int(number):,}"
    text = f"{number.normalize():f}"
    return text


def _money(amount: Decimal | None) -> str:
    if amount is None:
        return "—"
    quant = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quant:,.2f}"


def _price_simple(amount: Decimal | None) -> str:
    if amount is None:
        return ""
    quant = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    if quant == quant.to_integral():
        return f"{int(quant):,}.-"
    return f"{quant:,.2f}"


def _thai_date(day: date) -> str:
    return f"{day.day} {_MONTHS[day.month - 1]} {day.year}"


def _slash_date(day: date) -> str:
    return f"{day.day:02d}/{day.month:02d}/{day.year}"


def _parse_date(value: Any) -> date:
    raw = _raw(value)
    if not raw:
        return datetime.now(BKK).date()
    try:
        if len(raw) <= 10:
            return date.fromisoformat(raw[:10])
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=BKK)
        return parsed.astimezone(BKK).date()
    except ValueError:
        return datetime.now(BKK).date()


def _term_label(term: str) -> str:
    text = (term or "").strip()
    if not text:
        return ""
    number = _num(text)
    if number is None:
        return text
    if number == number.to_integral():
        return f"เครดิต {int(number)} วัน"
    return f"เครดิต {number.normalize():f} วัน"


def _phone(card: dict[str, str]) -> str:
    phone = _raw(card.get("phone"))
    fax = _raw(card.get("fax"))
    if phone and fax and fax != phone:
        return f"{phone}, {fax}"
    return phone or fax


def _address(card: dict[str, str]) -> str:
    parts = [_raw(card.get("addr1")), _raw(card.get("addr2"))]
    return " ".join(part for part in parts if part)


def _blank_rows(count: int, cols: int) -> str:
    if count <= 0:
        return ""
    cell = "<td>&nbsp;</td>" * cols
    return "".join(f"<tr>{cell}</tr>" for _ in range(count))


def _line_amount(qty: Decimal | None, price: Decimal | None) -> Decimal | None:
    if qty is None or price is None:
        return None
    return (qty * price).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _totals(lines: list[dict[str, Any]]) -> dict[str, Any]:
    goods = Decimal("0")
    priced = False
    for line in lines:
        amount = line.get("amount")
        if isinstance(amount, Decimal):
            goods += amount
            priced = True
    if not priced:
        return {"goods": None, "discount": None, "before": None, "tax": None, "net": None, "words": ""}
    goods = goods.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    discount = Decimal("0.00")
    before = goods - discount
    tax = (before * Decimal("0.07")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    net = before + tax
    return {
        "goods": goods,
        "discount": discount,
        "before": before,
        "tax": tax,
        "net": net,
        "words": baht_text(net),
    }


def _prepare_documents(groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    cleaned: list[dict[str, Any]] = []
    vendors: list[str] = []
    bcodes: list[str] = []
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        lines = []
        for raw in group.get("lines") or []:
            if not isinstance(raw, dict):
                continue
            qty = _num(raw.get("qty"))
            if qty is None or qty <= 0:
                continue
            bcode = _raw(raw.get("bcode"))
            lines.append(raw)
            if bcode:
                bcodes.append(bcode)
        if not lines:
            continue
        vendor = _raw(group.get("vendor"))
        if vendor:
            vendors.append(vendor)
        cleaned.append({**group, "lines": lines})
    if not cleaned:
        return []
    try:
        from src.hq_po.iclow_read import fetch_vendor_cards

        cards = fetch_vendor_cards(vendors)
    except Exception:
        logger.warning("hq po vendor card lookup failed", exc_info=True)
        cards = {}
    try:
        from src.hq_po.iclow_read import fetch_sheet_products

        products = fetch_sheet_products(bcodes)
    except Exception:
        logger.warning("hq po sheet product lookup failed", exc_info=True)
        products = {}
    documents: list[dict[str, Any]] = []
    for group in cleaned:
        vendor = _raw(group.get("vendor"))
        card = dict(cards.get(vendor) or {})
        hinted = _raw(group.get("vendor_name"))
        if hinted and not _raw(card.get("name")):
            card["name"] = hinted
        card["acctno"] = vendor or _raw(card.get("acctno"))
        lines: list[dict[str, Any]] = []
        for index, raw in enumerate(group["lines"], start=1):
            bcode = _raw(raw.get("bcode"))
            product = products.get(bcode) or {}
            qty = _num(raw.get("qty")) or Decimal("0")
            price = _positive_price(product.get("costlast"), product.get("costnet"), raw.get("price"))
            lines.append(
                {
                    "seq": index,
                    "bcode": bcode,
                    "name": _raw(product.get("descr")) or _raw(raw.get("descr")),
                    "model": _raw(product.get("model")) or _raw(raw.get("model")),
                    "no1": _raw(product.get("pcode")) or _raw(raw.get("pcode")),
                    "no2": _raw(product.get("mcode")) or _raw(raw.get("mcode")),
                    "brand": _raw(product.get("brand")) or _raw(raw.get("brand")),
                    "qty": qty,
                    "ui": _raw(raw.get("ui")) or _raw(product.get("ui")),
                    "price": price,
                    "amount": _line_amount(qty, price),
                }
            )
        documents.append(
            {
                "docno": _raw(group.get("docno")),
                "docdate": _parse_date(group.get("docdate")),
                "vendor": card,
                "lines": lines,
                "totals": _totals(lines),
            }
        )
    return documents


def _vendor_rows(card: dict[str, str]) -> list[tuple[str, str]]:
    phone = _phone(card)
    return [
        ("ผู้ขาย", _raw(card.get("name"))),
        ("รหัสเจ้าหนี้", _raw(card.get("acctno"))),
        ("ที่อยู่", _address(card)),
        ("โทรศัพท์", phone),
        ("เลขประจำตัวผู้เสียภาษี", _raw(card.get("tax_id"))),
        ("ผู้ติดต่อ", _raw(card.get("contact"))),
        ("เงื่อนไขชำระเงิน", _term_label(_raw(card.get("term")))),
    ]


def _simple_page(doc: dict[str, Any]) -> str:
    card = doc["vendor"]
    day: date = doc["docdate"]
    docno = _raw(doc.get("docno")) or "ยังไม่ออกเลข"
    vendor_html = "".join(
        f'<div class="k">{html.escape(label)}</div><div class="v">{_e(value)}</div>'
        for label, value in _vendor_rows(card)
    )
    body = []
    for line in doc["lines"]:
        body.append(
            "<tr>"
            f"<td>{_e(line['bcode'])}</td>"
            f"<td>{_e(line['name'])}</td>"
            f"<td>{_e(line['model'])}</td>"
            f"<td>{_e(line['no1'])}</td>"
            f"<td>{_e(line['no2'])}</td>"
            f"<td>{_e(line['brand'])}</td>"
            f"<td class='num'>{html.escape(_qty_text(line['qty']))}</td>"
            f"<td>{_e(line['ui'])}</td>"
            f"<td class='num'>{html.escape(_price_simple(line['price']) or '—')}</td>"
            "</tr>"
        )
    return f"""
<article class="pos">
  <header class="pos-head">
    <div class="pos-co">{html.escape(COMPANY_SHORT)}</div>
    <div class="pos-title">
      <h1>ใบสั่งซื้อ</h1>
      <p>ณ วันที่ {html.escape(_thai_date(day))}</p>
      <p>เลขที่ PO {html.escape(docno)}</p>
    </div>
    <div class="pos-page">Page 1 of 1</div>
  </header>
  <section class="pos-vendor">
    <h2>ผู้ขาย / SUPPLIER</h2>
    <div class="grid">{vendor_html}</div>
  </section>
  <table>
    <thead>
      <tr>
        <th>รหัสสินค้า</th><th>ชื่อสินค้า</th><th>แบบ</th><th>NO.1</th><th>NO.2</th>
        <th>ยี่ห้อ</th><th class="num">จำนวน</th><th>หน่วย</th><th class="num">ราคา/หน่วย</th>
      </tr>
    </thead>
    <tbody>{''.join(body)}</tbody>
  </table>
  <div class="pos-sign"><div>ลงชื่อ<span></span></div><div>ผู้ตรวจสอบ<span></span></div></div>
</article>
"""


def _simple_text(doc: dict[str, Any]) -> str:
    day: date = doc["docdate"]
    docno = _raw(doc.get("docno")) or "ยังไม่ออกเลข"
    lines = [
        COMPANY_SHORT,
        f"ใบสั่งซื้อ ณ วันที่ {_thai_date(day)}",
        f"เลขที่ PO {docno}",
        "",
        "ผู้ขาย / SUPPLIER",
    ]
    for label, value in _vendor_rows(doc["vendor"]):
        lines.append(f"{label}: {value or '—'}")
    lines.append("")
    lines.append("รหัสสินค้า\tชื่อสินค้า\tแบบ\tNO.1\tNO.2\tยี่ห้อ\tจำนวน\tหน่วย\tราคา/หน่วย")
    for line in doc["lines"]:
        lines.append(
            "\t".join(
                [
                    line["bcode"] or "—",
                    line["name"] or "—",
                    line["model"] or "—",
                    line["no1"] or "—",
                    line["no2"] or "—",
                    line["brand"] or "—",
                    _qty_text(line["qty"]),
                    line["ui"] or "—",
                    _price_simple(line["price"]) or "—",
                ]
            )
        )
    lines.extend(["", "ลงชื่อ ____________________", "ผู้ตรวจสอบ ____________________"])
    return "\n".join(lines)


def _full_page(doc: dict[str, Any]) -> str:
    card = doc["vendor"]
    day: date = doc["docdate"]
    docno = _raw(doc.get("docno")) or "ยังไม่ออกเลข"
    term = _term_label(_raw(card.get("term"))) or "………………"
    vendor_html = "".join(
        f'<div class="k">{html.escape(label)}</div><div class="v">{_e(value)}</div>'
        for label, value in _vendor_rows(card)
        if label != "เงื่อนไขชำระเงิน"
    )
    body = []
    for line in doc["lines"]:
        qty_unit = _qty_text(line["qty"])
        if line["ui"]:
            qty_unit = f"{qty_unit} {line['ui']}"
        model = line["model"] or "—"
        brand = line["brand"] or "—"
        body.append(
            "<tr>"
            f"<td class='ctr'>{line['seq']}</td>"
            f"<td><b>{_e(line['bcode'])}</b> · {_e(line['name'])}"
            f"<span class='sub'>รุ่น: {html.escape(model)} · ยี่ห้อ: {html.escape(brand)}</span></td>"
            f"<td>NO.1: {_e(line['no1'])}<span class='sub'>NO.2: {_e(line['no2'])}</span></td>"
            f"<td class='num'>{html.escape(qty_unit)}</td>"
            f"<td class='num'>{html.escape(_money(line['price']))}</td>"
            f"<td class='num'>{html.escape(_money(line['amount']))}</td>"
            "</tr>"
        )
    pad = _blank_rows(max(0, 6 - len(doc["lines"])), 6)
    totals = doc["totals"]
    return f"""
<article class="pof">
  <header class="pof-top">
    <div>
      <div class="pof-logo">KCW</div>
      <div class="pof-co">{html.escape(COMPANY_NAME)}</div>
      <div class="pof-addr">{html.escape(COMPANY_ADDRESS)}<br/>โทร. {html.escape(COMPANY_PHONE)} · สาขา: {html.escape(COMPANY_BRANCH)}</div>
    </div>
    <div class="pof-doc">
      <h1>ใบสั่งซื้อ</h1>
      <div class="en">PURCHASE ORDER</div>
    </div>
  </header>
  <div class="pof-rule"></div>
  <div class="pof-boxes">
    <section class="pof-box">
      <h2>ผู้ขาย / SUPPLIER</h2>
      <div class="grid">{vendor_html}</div>
    </section>
    <section class="pof-box">
      <h2>ข้อมูลใบสั่งซื้อ / ORDER DETAILS</h2>
      <div class="grid">
        <div class="k">เลขที่ PO</div><div class="v">{html.escape(docno)}</div>
        <div class="k">วันที่</div><div class="v">{html.escape(_slash_date(day))}</div>
        <div class="k">กำหนดส่งสินค้า</div><div class="v">………………</div>
        <div class="k">เงื่อนไขชำระเงิน</div><div class="v">{html.escape(term)}</div>
        <div class="k">อ้างอิงใบเสนอราคา</div><div class="v">………………</div>
      </div>
    </section>
  </div>
  <div class="pof-ship">
    <div>สถานที่ส่งสินค้า: HQ — {html.escape(COMPANY_ADDRESS)}</div>
    <div>ผู้รับ / โทร: ………………</div>
  </div>
  <table>
    <thead>
      <tr>
        <th class="ctr">ลำดับ</th>
        <th>รหัสสินค้า / รายละเอียดสินค้า</th>
        <th>เบอร์อะไหล่</th>
        <th class="num">จำนวน / หน่วย</th>
        <th class="num">ราคา/หน่วย</th>
        <th class="num">จำนวนเงิน</th>
      </tr>
    </thead>
    <tbody>{''.join(body)}{pad}</tbody>
  </table>
  <div class="pof-foot">
    <section class="pof-notes">
      <h2>หมายเหตุ / เงื่อนไขการจัดส่ง</h2>
      <ol>
        <li>กรุณาระบุเลขที่ PO ในใบส่งของและใบกำกับภาษี</li>
        <li>หากสินค้าไม่ครบ หรือเปลี่ยนรุ่น / ยี่ห้อ / ราคา กรุณายืนยันกับผู้สั่งซื้อก่อนจัดส่ง</li>
        <li>………………</li>
      </ol>
    </section>
    <section class="pof-tot">
      <div class="row"><span>รวมค่าสินค้า</span><span>{html.escape(_money(totals['goods']))}</span></div>
      <div class="row"><span>ส่วนลด</span><span>{html.escape(_money(totals['discount']))}</span></div>
      <div class="row"><span>ยอดก่อนภาษี</span><span>{html.escape(_money(totals['before']))}</span></div>
      <div class="row"><span>ภาษีมูลค่าเพิ่ม 7%</span><span>{html.escape(_money(totals['tax']))}</span></div>
      <div class="row net"><span>ยอดสุทธิ (บาท)</span><span>{html.escape(_money(totals['net']))}</span></div>
      <div class="pof-words">{html.escape(totals['words'])}</div>
    </section>
  </div>
  <div class="pof-sign">
    <div>ผู้จัดทำ / ผู้สั่งซื้อ<div class="line"></div>วันที่ ____/____/____</div>
    <div>ผู้อนุมัติสั่งซื้อ<div class="line"></div>วันที่ ____/____/____</div>
    <div>ผู้ขายยืนยันรับคำสั่งซื้อ<div class="line"></div>วันที่ ____/____/____</div>
  </div>
</article>
"""


def _full_text(doc: dict[str, Any]) -> str:
    day: date = doc["docdate"]
    docno = _raw(doc.get("docno")) or "ยังไม่ออกเลข"
    term = _term_label(_raw(doc["vendor"].get("term"))) or "—"
    lines = [
        "ใบสั่งซื้อ / PURCHASE ORDER",
        COMPANY_NAME,
        COMPANY_ADDRESS,
        f"โทร. {COMPANY_PHONE} · สาขา: {COMPANY_BRANCH}",
        f"เลขที่ PO: {docno}",
        f"วันที่: {_slash_date(day)}",
        "กำหนดส่งสินค้า: —",
        f"เงื่อนไขชำระเงิน: {term}",
        "อ้างอิงใบเสนอราคา: —",
        f"สถานที่ส่งสินค้า: HQ — {COMPANY_ADDRESS}",
        "",
        "ผู้ขาย / SUPPLIER",
    ]
    for label, value in _vendor_rows(doc["vendor"]):
        if label == "เงื่อนไขชำระเงิน":
            continue
        lines.append(f"{label}: {value or '—'}")
    lines.append("")
    for line in doc["lines"]:
        qty_unit = _qty_text(line["qty"])
        if line["ui"]:
            qty_unit = f"{qty_unit} {line['ui']}"
        lines.append(
            f"{line['seq']}. {line['bcode'] or '—'} {line['name'] or '—'} | รุ่น {line['model'] or '—'} | "
            f"ยี่ห้อ {line['brand'] or '—'} | NO.1 {line['no1'] or '—'} | NO.2 {line['no2'] or '—'} | "
            f"{qty_unit} | {_money(line['price'])} | {_money(line['amount'])}"
        )
    totals = doc["totals"]
    lines.extend(
        [
            "",
            f"รวมค่าสินค้า {_money(totals['goods'])}",
            f"ส่วนลด {_money(totals['discount'])}",
            f"ยอดก่อนภาษี {_money(totals['before'])}",
            f"ภาษีมูลค่าเพิ่ม 7% {_money(totals['tax'])}",
            f"ยอดสุทธิ (บาท) {_money(totals['net'])}",
            totals["words"],
            "ผู้จัดทำ / ผู้สั่งซื้อ ________",
            "ผู้อนุมัติสั่งซื้อ ________",
            "ผู้ขายยืนยันรับคำสั่งซื้อ ________",
        ]
    )
    return "\n".join(lines)


def render_forms(documents: list[dict[str, Any]]) -> dict[str, str]:
    if not documents:
        return {"simple_html": "", "full_html": "", "simple_text": "", "full_text": ""}
    return {
        "simple_html": _SIMPLE_STYLE + "".join(_simple_page(doc) for doc in documents),
        "full_html": _FULL_STYLE + "".join(_full_page(doc) for doc in documents),
        "simple_text": "\n\n".join(_simple_text(doc) for doc in documents),
        "full_text": "\n\n".join(_full_text(doc) for doc in documents),
    }


def build_sheet_forms(groups: list[dict[str, Any]]) -> dict[str, str]:
    documents = _prepare_documents(groups)
    if not documents:
        raise HqPoError("empty", "ไม่มีรายการสำหรับใบสั่งซื้อ")
    return render_forms(documents)

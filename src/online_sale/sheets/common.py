from __future__ import annotations

import html as html_lib
from datetime import date, datetime

from src.online_sale.vat import money, totals_from_amounts

COMPANY = {
    "name": "บริษัท เกียรติชัยอะไหล่ยนต์ 2007 จำกัด (สำนักงานใหญ่)",
    "address": "ที่อยู่ 305 ม.1 ต.ชุมแสง อ.วังจันทร์ จ.ระยอง 21210",
    "phone": "โทร. 038-666-078",
    "tax": "เลขประจำตัวผู้เสียภาษี 0215560000262",
}

_TH_MONTHS = [
    "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.",
    "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค.",
]

CSS = """
.rcp { font-family: THSarabunNew, "Noto Sans Thai", sans-serif; color:#111; background:#fff;
  max-width:210mm; margin:0 auto; padding:8mm 10mm; box-sizing:border-box; font-size:15px; line-height:1.35; }
.rcp .co { font-weight:700; font-size:18px; }
.rcp .addr { font-size:13px; }
.rcp .title { text-align:center; font-weight:800; font-size:20px; margin:8px 0 4px; }
.rcp .meta { display:grid; grid-template-columns:1fr 1fr; gap:4px 16px; margin:8px 0 10px; font-size:14px; }
.rcp table { width:100%; border-collapse:collapse; font-size:14px; }
.rcp th { border-top:1px solid #111; border-bottom:1px solid #111; padding:4px 3px; text-align:left; }
.rcp td { border-bottom:1px solid #ddd; padding:4px 3px; vertical-align:top; }
.rcp .num { text-align:right; white-space:nowrap; }
.rcp .ctr { text-align:center; }
.rcp .tot { margin-top:10px; width:100%; max-width:280px; margin-left:auto; font-size:14px; }
.rcp .tot .row { display:flex; justify-content:space-between; gap:12px; padding:2px 0; }
.rcp .tot .net { font-weight:800; border-top:1px solid #111; margin-top:4px; padding-top:4px; }
.rcp .foot { margin-top:18px; font-size:14px; }
.rcp .cn-box { margin-top:12px; border:1px solid #333; padding:8px 10px; font-size:14px; }
.rcp .cn-box .row { display:flex; justify-content:space-between; gap:12px; padding:2px 0; }
@media print {
  @page { size:A4; margin:10mm 12mm; }
  body { background:#fff; margin:0; }
  .noprint { display:none !important; }
  .rcp { max-width:none; padding:0; }
}
"""


def esc(value) -> str:
    return html_lib.escape("" if value is None else str(value))


def thai_date(value) -> str:
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        d = value.date()
    elif isinstance(value, date):
        d = value
    else:
        text = str(value).strip()[:10]
        try:
            d = date.fromisoformat(text)
        except ValueError:
            return esc(value)
    return f"{d.day} {_TH_MONTHS[d.month - 1]} {d.year + 543}"


def fmt_money(value) -> str:
    return f"{float(money(value)):,.2f}"


def fmt_qty(value) -> str:
    n = float(value or 0)
    if n == int(n):
        return str(int(n))
    return f"{n:,.2f}"


def line_rows_html(lines: list[dict]) -> str:
    parts = []
    for i, ln in enumerate(lines, start=1):
        parts.append(
            "<tr>"
            f"<td class='ctr'>{i}</td>"
            f"<td>{esc(ln.get('bcode'))}</td>"
            f"<td>{esc(ln.get('detail') or ln.get('descr'))}</td>"
            f"<td class='num'>{fmt_money(ln.get('price'))}</td>"
            f"<td class='num'>{fmt_qty(abs(float(ln.get('qty') or 0)))}</td>"
            f"<td class='ctr'>{esc(ln.get('ui') or '')}</td>"
            f"<td class='num'>{fmt_money(abs(float(ln.get('amount') or 0)))}</td>"
            "</tr>"
        )
    return "\n".join(parts)


def totals_block(amounts: list) -> str:
    t = totals_from_amounts([abs(float(a or 0)) for a in amounts])
    return (
        "<div class='tot'>"
        f"<div class='row'><span>ยอดก่อน VAT</span><span>{fmt_money(t['beforetax'])}</span></div>"
        f"<div class='row'><span>VAT 7%</span><span>{fmt_money(t['tax'])}</span></div>"
        f"<div class='row net'><span>รวมทั้งสิ้น</span><span>{fmt_money(t['aftertax'])}</span></div>"
        "</div>"
    )


def platform_label(platform: str) -> str:
    return {
        "shopee": "Shopee",
        "lazada": "Lazada",
        "tiktok": "TikTok",
        "line": "Line Shopping",
    }.get((platform or "").lower(), platform or "")

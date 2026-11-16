from __future__ import annotations

from src.online_sale.sheets.common import (
    CSS,
    esc,
    fmt_qty,
    platform_label,
    thai_date,
)

_PICK_CSS = (
    CSS
    + """
.rcp .thumb { width:1.5cm; height:1.5cm; object-fit:cover; border:1px solid #ccc; background:#f3f4f6; display:block; }
.rcp .chk { width:1.4cm; text-align:center; font-size:16px; }
.rcp .sig2 { display:grid; grid-template-columns:1fr 1fr; gap:28px; margin-top:32px; font-size:14px; break-inside:avoid; page-break-inside:avoid; }
.rcp .sig2 .box { border-top:1px solid #111; padding-top:8px; min-height:4.5rem; }
.rcp .sig2 .label { font-weight:700; margin-bottom:18px; }
.rcp .sig2 .line { margin-top:22px; }
"""
)


def _loc_key(ln: dict) -> tuple:
    loc = str(ln.get("location1") or ln.get("location") or "").strip()
    return (loc == "", loc.lower(), str(ln.get("bcode") or ""))


def _sorted_lines(lines: list[dict]) -> list[dict]:
    return sorted(lines or [], key=_loc_key)


def _thumb_cell(ln: dict) -> str:
    photo = str(ln.get("photo") or "").strip()
    if not photo:
        return "<td class='ctr'>—</td>"
    return (
        f"<td class='ctr'><img class='thumb' alt='' src='{esc(photo)}' "
        "onerror=\"this.replaceWith(document.createTextNode('—'))\"/></td>"
    )


def pick_rows_html(lines: list[dict]) -> str:
    parts = []
    for ln in _sorted_lines(lines):
        loc = str(ln.get("location1") or ln.get("location") or "").strip() or "—"
        parts.append(
            "<tr>"
            f"{_thumb_cell(ln)}"
            f"<td>{esc(ln.get('bcode'))}</td>"
            f"<td>{esc(ln.get('detail') or ln.get('descr') or '')}</td>"
            f"<td>{esc(loc)}</td>"
            f"<td class='num'>{fmt_qty(abs(float(ln.get('qty') or 0)))}</td>"
            f"<td class='ctr'>{esc(ln.get('ui') or '')}</td>"
            "<td class='chk'>☐</td>"
            "</tr>"
        )
    return "\n".join(parts) or "<tr><td colspan='7' class='ctr'>ไม่มีรายการ</td></tr>"


def render_pick_sheet(bill: dict) -> str:
    meta = (
        f"<div><b>เลข TAD</b> {esc(bill.get('billno'))}</div>"
        f"<div><b>วันที่</b> {thai_date(bill.get('bill_date'))}</div>"
        f"<div><b>แพลตฟอร์ม</b> {esc(platform_label(bill.get('platform') or ''))}</div>"
        f"<div><b>ร้านค้า</b> {esc(bill.get('shop_name') or bill.get('acctname'))}</div>"
        f"<div><b>เลขคำสั่งซื้อ</b> {esc(bill.get('online_po'))}</div>"
    )
    return f"""<!doctype html>
<html lang="th"><head><meta charset="utf-8">
<title></title>
<style>{_PICK_CSS}</style></head><body>
<div class="rcp">
  <div class="title">ใบจัดสินค้า</div>
  <div class="meta">{meta}</div>
  <table>
    <thead><tr>
      <th class="ctr">รูป</th><th>รหัสสินค้า</th><th>ชื่อสินค้า</th>
      <th>ที่เก็บ</th><th class="num">จำนวน</th><th class="ctr">หน่วย</th>
      <th class="chk">ตรวจ</th>
    </tr></thead>
    <tbody>{pick_rows_html(bill.get("lines") or [])}</tbody>
  </table>
  <div class="sig2">
    <div class="box"><div class="label">ผู้จัดสินค้า</div><div class="line">ชื่อ / ลายเซ็น / วันที่</div></div>
    <div class="box"><div class="label">ผู้ตรวจสินค้า</div><div class="line">ชื่อ / ลายเซ็น / วันที่</div></div>
  </div>
</div>
<script>
window.onload=function(){{
  document.title="";
  setTimeout(function(){{ window.print(); }}, 200);
}};
</script>
</body></html>"""

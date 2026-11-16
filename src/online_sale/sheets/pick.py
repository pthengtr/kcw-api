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
.rcp .bill-break { font-size:12px; color:#333; margin-top:2px; line-height:1.35; }
.rcp .sig2 { display:grid; grid-template-columns:1fr 1fr; gap:28px; margin-top:32px; font-size:14px; break-inside:avoid; page-break-inside:avoid; }
.rcp .sig2 .box { border-top:1px solid #111; padding-top:8px; min-height:4.5rem; }
.rcp .sig2 .label { font-weight:700; margin-bottom:18px; }
.rcp .sig2 .line { margin-top:22px; }
"""
)


def _loc_key(ln: dict) -> tuple:
    loc = str(ln.get("location1") or ln.get("location") or "").strip()
    return (loc == "", loc.lower(), str(ln.get("bcode") or ""), str(ln.get("ui") or ""))


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


def _bill_breakdown_html(ln: dict) -> str:
    parts = ln.get("bill_qtys") or []
    if not parts:
        billno = str(ln.get("billno") or "").strip()
        if not billno:
            return ""
        qty = abs(float(ln.get("qty") or 0))
        return (
            f"<div class='bill-break'>{esc(billno)}: {esc(fmt_qty(qty))}</div>"
        )
    bits = []
    for part in parts:
        billno = str(part.get("billno") or "").strip()
        if not billno:
            continue
        qty = abs(float(part.get("qty") or 0))
        bits.append(f"{esc(billno)}: {esc(fmt_qty(qty))}")
    if not bits:
        return ""
    return f"<div class='bill-break'>{' · '.join(bits)}</div>"


def merge_pick_lines(bills: list[dict]) -> list[dict]:
    """Merge lines across bills by (bcode, ui); keep per-bill qty for packing."""
    buckets: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for bill in bills or []:
        billno = str(bill.get("billno") or "").strip()
        for ln in bill.get("lines") or []:
            bcode = str(ln.get("bcode") or "").strip()
            ui = str(ln.get("ui") or "").strip()
            key = (bcode, ui)
            qty = abs(float(ln.get("qty") or 0))
            if qty <= 0:
                continue
            if key not in buckets:
                buckets[key] = {
                    "bcode": bcode,
                    "ui": ui,
                    "detail": ln.get("detail") or ln.get("descr") or "",
                    "location1": ln.get("location1") or ln.get("location") or "",
                    "photo": ln.get("photo") or "",
                    "qty": 0.0,
                    "bill_qtys": [],
                }
                order.append(key)
            bucket = buckets[key]
            bucket["qty"] += qty
            if not bucket.get("detail"):
                bucket["detail"] = ln.get("detail") or ln.get("descr") or ""
            if not bucket.get("location1"):
                bucket["location1"] = ln.get("location1") or ln.get("location") or ""
            if not bucket.get("photo") and ln.get("photo"):
                bucket["photo"] = ln.get("photo")
            found = next(
                (x for x in bucket["bill_qtys"] if x.get("billno") == billno),
                None,
            )
            if found:
                found["qty"] = float(found["qty"]) + qty
            elif billno:
                bucket["bill_qtys"].append({"billno": billno, "qty": qty})
    return _sorted_lines([buckets[k] for k in order])


def pick_rows_html(lines: list[dict]) -> str:
    parts = []
    for ln in _sorted_lines(lines):
        loc = str(ln.get("location1") or ln.get("location") or "").strip() or "—"
        parts.append(
            "<tr>"
            f"{_thumb_cell(ln)}"
            f"<td>{esc(ln.get('bcode'))}</td>"
            f"<td>{esc(ln.get('detail') or ln.get('descr') or '')}"
            f"{_bill_breakdown_html(ln)}</td>"
            f"<td>{esc(loc)}</td>"
            f"<td class='num'>{fmt_qty(abs(float(ln.get('qty') or 0)))}</td>"
            f"<td class='ctr'>{esc(ln.get('ui') or '')}</td>"
            "<td class='chk'>☐</td>"
            "</tr>"
        )
    return "\n".join(parts) or "<tr><td colspan='7' class='ctr'>ไม่มีรายการ</td></tr>"


def _meta_from_bills(bills: list[dict]) -> str:
    if not bills:
        return ""
    if len(bills) == 1:
        bill = bills[0]
        return (
            f"<div><b>เลข TAD</b> {esc(bill.get('billno'))}</div>"
            f"<div><b>วันที่</b> {thai_date(bill.get('bill_date'))}</div>"
            f"<div><b>แพลตฟอร์ม</b> {esc(platform_label(bill.get('platform') or ''))}</div>"
            f"<div><b>ร้านค้า</b> {esc(bill.get('shop_name') or bill.get('acctname'))}</div>"
            f"<div><b>เลขคำสั่งซื้อ</b> {esc(bill.get('online_po'))}</div>"
        )
    bill_bits = []
    for bill in bills:
        billno = esc(bill.get("billno"))
        po = str(bill.get("online_po") or "").strip()
        if po:
            bill_bits.append(f"{billno} ({esc(po)})")
        else:
            bill_bits.append(billno)
    return (
        f"<div><b>จำนวนบิล</b> {len(bills)} ใบ</div>"
        f"<div style='grid-column:1/-1'><b>เลข TAD</b> {' · '.join(bill_bits)}</div>"
    )


def render_pick_sheet(bill: dict | None = None, *, bills: list[dict] | None = None) -> str:
    docs = list(bills or [])
    if not docs and bill:
        docs = [bill]
    lines = merge_pick_lines(docs)
    meta = _meta_from_bills(docs)
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
    <tbody>{pick_rows_html(lines)}</tbody>
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

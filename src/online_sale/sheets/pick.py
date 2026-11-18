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
.rcp td.warn { color:#b91c1c; font-weight:700; }
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


def _order_ref(bill: dict | None = None, *, fallback: str = "") -> str:
    """Prefer online order id for packing (drafts); fall back to billno."""
    if bill:
        po = str(bill.get("online_po") or "").strip()
        if po:
            return po
        billno = str(bill.get("billno") or "").strip()
        if billno:
            return billno
    return str(fallback or "").strip()


def _bill_breakdown_html(ln: dict) -> str:
    parts = ln.get("bill_qtys") or []
    if not parts:
        ref = str(ln.get("billno") or ln.get("online_po") or "").strip()
        if not ref:
            return ""
        qty = abs(float(ln.get("qty") or 0))
        return (
            f"<div class='bill-break'>{esc(ref)}: {esc(fmt_qty(qty))}</div>"
        )
    bits = []
    for part in parts:
        ref = str(part.get("billno") or part.get("online_po") or "").strip()
        if not ref:
            continue
        qty = abs(float(part.get("qty") or 0))
        bits.append(f"{esc(ref)}: {esc(fmt_qty(qty))}")
    if not bits:
        return ""
    return f"<div class='bill-break'>{' · '.join(bits)}</div>"


def merge_pick_lines(bills: list[dict]) -> list[dict]:
    """Merge lines across orders by (bcode, ui); keep per-order qty for packing."""
    buckets: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    for bill in bills or []:
        ref = _order_ref(bill)
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
                    "qtyoh2": float(ln.get("qtyoh2") or 0),
                    "mtp": float(ln.get("mtp") or 1) or 1.0,
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
            # Keep the freshest / highest on-hand reading across merged drafts.
            try:
                oh = float(ln.get("qtyoh2") or 0)
            except (TypeError, ValueError):
                oh = 0.0
            if oh > float(bucket.get("qtyoh2") or 0):
                bucket["qtyoh2"] = oh
            if not bucket.get("mtp"):
                try:
                    bucket["mtp"] = float(ln.get("mtp") or 1) or 1.0
                except (TypeError, ValueError):
                    bucket["mtp"] = 1.0
            found = next(
                (x for x in bucket["bill_qtys"] if x.get("billno") == ref),
                None,
            )
            if found:
                found["qty"] = float(found["qty"]) + qty
            elif ref:
                bucket["bill_qtys"].append({"billno": ref, "qty": qty})
    return _sorted_lines([buckets[k] for k in order])


def _remain_in_line_ui(ln: dict) -> float:
    """On-hand stock converted to the pick line's unit (qtyoh2 ÷ mtp)."""
    try:
        oh = float(ln.get("qtyoh2") or 0)
    except (TypeError, ValueError):
        oh = 0.0
    try:
        mtp = float(ln.get("mtp") or 1) or 1.0
    except (TypeError, ValueError):
        mtp = 1.0
    if mtp <= 0:
        mtp = 1.0
    return oh / mtp


def pick_rows_html(lines: list[dict]) -> str:
    parts = []
    for ln in _sorted_lines(lines):
        loc = str(ln.get("location1") or ln.get("location") or "").strip() or "—"
        need = abs(float(ln.get("qty") or 0))
        remain = _remain_in_line_ui(ln)
        short = remain + 1e-9 < need
        remain_cls = "num warn" if short else "num"
        parts.append(
            "<tr>"
            f"{_thumb_cell(ln)}"
            f"<td>{esc(ln.get('bcode'))}</td>"
            f"<td>{esc(ln.get('detail') or ln.get('descr') or '')}"
            f"{_bill_breakdown_html(ln)}</td>"
            f"<td>{esc(loc)}</td>"
            f"<td class='num'>{fmt_qty(need)}</td>"
            f"<td class='{remain_cls}'>{fmt_qty(remain)}</td>"
            f"<td class='ctr'>{esc(ln.get('ui') or '')}</td>"
            "<td class='chk'>☐</td>"
            "</tr>"
        )
    return "\n".join(parts) or "<tr><td colspan='8' class='ctr'>ไม่มีรายการ</td></tr>"


def _meta_from_bills(bills: list[dict]) -> str:
    if not bills:
        return ""
    if len(bills) == 1:
        bill = bills[0]
        return (
            f"<div><b>เลขคำสั่งซื้อ</b> {esc(_order_ref(bill))}</div>"
            f"<div><b>วันที่</b> {thai_date(bill.get('bill_date'))}</div>"
            f"<div><b>แพลตฟอร์ม</b> {esc(platform_label(bill.get('platform') or ''))}</div>"
            f"<div><b>ร้านค้า</b> {esc(bill.get('shop_name') or bill.get('acctname'))}</div>"
        )
    refs = []
    for bill in bills:
        ref = _order_ref(bill)
        if ref:
            refs.append(esc(ref))
    return (
        f"<div><b>จำนวนออเดอร์</b> {len(bills)} รายการ</div>"
        f"<div style='grid-column:1/-1'><b>เลขคำสั่งซื้อ</b> {' · '.join(refs)}</div>"
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
      <th>ที่เก็บ</th><th class="num">จำนวน</th><th class="num">คงเหลือ</th>
      <th class="ctr">หน่วย</th><th class="chk">ตรวจ</th>
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

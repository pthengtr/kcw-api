from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any


def _fmt_ts(ts: float | None) -> str:
    if not ts:
        return "ไม่เคย"
    return datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")


def page(title: str, body: str, *, user: dict[str, Any] | None = None) -> str:
    who = ""
    if user:
        role = "ผู้อนุมัติ" if user.get("is_approver") else "ผู้ตรวจ"
        who = f"<div class='who'>{escape(user.get('display_name') or '')} · {role}</div>"
    return f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
  <title>{escape(title)}</title>
  <style>
    :root {{
      --bg: #f3f1ec;
      --card: #fff;
      --ink: #1c1917;
      --muted: #78716c;
      --line: #e7e5e4;
      --accent: #0f766e;
      --warn: #b45309;
      --danger: #b91c1c;
      --ok: #15803d;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0; font-family: "Segoe UI", "Sarabun", system-ui, sans-serif;
      background: linear-gradient(180deg, #ecfeff 0%, var(--bg) 40%);
      color: var(--ink); min-height: 100vh;
    }}
    header {{
      position: sticky; top: 0; z-index: 5;
      background: rgba(255,255,255,.92); backdrop-filter: blur(8px);
      border-bottom: 1px solid var(--line);
      padding: 12px 16px;
    }}
    header h1 {{ margin: 0; font-size: 1.15rem; }}
    .who {{ color: var(--muted); font-size: .9rem; margin-top: 2px; }}
    main {{ padding: 12px 14px 88px; max-width: 720px; margin: 0 auto; }}
    .card {{
      background: var(--card); border: 1px solid var(--line);
      border-radius: 14px; padding: 14px; margin-bottom: 12px;
    }}
    .row {{
      display: flex; gap: 10px; justify-content: space-between; align-items: flex-start;
    }}
    .muted {{ color: var(--muted); font-size: .92rem; }}
    .loc {{
      font-weight: 700; font-size: 1.05rem; color: var(--accent);
      letter-spacing: .02em;
    }}
    .bcode {{ font-family: ui-monospace, Consolas, monospace; font-weight: 600; }}
    a.item {{
      display: block; text-decoration: none; color: inherit;
    }}
    .btn, button, input[type=submit] {{
      appearance: none; border: 0; border-radius: 12px;
      background: var(--accent); color: #fff; font-weight: 700;
      padding: 14px 16px; font-size: 1rem; width: 100%;
      cursor: pointer;
    }}
    .btn.secondary, button.secondary {{ background: #44403c; }}
    .btn.warn, button.warn {{ background: var(--warn); }}
    .btn.danger, button.danger {{ background: var(--danger); }}
    .btn.ghost, button.ghost {{
      background: #fff; color: var(--ink); border: 1px solid var(--line);
    }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    label {{ display: block; font-size: .9rem; color: var(--muted); margin: 10px 0 4px; }}
    input[type=text], input[type=number], input[type=search] {{
      width: 100%; padding: 14px; border-radius: 12px; border: 1px solid var(--line);
      font-size: 1.05rem; background: #fff;
    }}
    nav.bottom {{
      position: fixed; left: 0; right: 0; bottom: 0;
      background: rgba(255,255,255,.96); border-top: 1px solid var(--line);
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 0;
      padding: 6px 4px calc(6px + env(safe-area-inset-bottom));
    }}
    nav.bottom a {{
      text-align: center; text-decoration: none; color: var(--muted);
      font-size: .78rem; padding: 8px 4px; font-weight: 600;
    }}
    nav.bottom a.active {{ color: var(--accent); }}
    .pill {{
      display: inline-block; padding: 2px 8px; border-radius: 999px;
      background: #ccfbf1; color: #115e59; font-size: .8rem; font-weight: 700;
    }}
    .pill.warn {{ background: #ffedd5; color: #9a3412; }}
    .flash {{
      padding: 12px 14px; border-radius: 12px; margin-bottom: 12px;
      background: #ecfdf5; color: var(--ok); font-weight: 600;
    }}
    .flash.err {{ background: #fef2f2; color: var(--danger); }}
    .qty {{ font-size: 1.4rem; font-weight: 800; }}
  </style>
</head>
<body>
  <header>
    <h1>{escape(title)}</h1>
    {who}
  </header>
  <main>{body}</main>
  <nav class="bottom">
    <a href="/stock-check/">งานวันนี้</a>
    <a href="/stock-check/ondemand">ค้นหา</a>
    <a href="/stock-check/approve">อนุมัติ</a>
    <a href="/stock-check/end">จบงาน</a>
  </nav>
</body>
</html>"""


def home_page(
    *,
    user: dict[str, Any],
    items: list[dict[str, Any]],
    flash: str | None = None,
    error: str | None = None,
) -> str:
    bits: list[str] = []
    if flash:
        bits.append(f"<div class='flash'>{escape(flash)}</div>")
    if error:
        bits.append(f"<div class='flash err'>{escape(error)}</div>")
    bits.append(
        """
        <div class="card">
          <form method="post" action="/stock-check/take">
            <label>รับงานตรวจนับ (จำนวน)</label>
            <div class="grid2">
              <input type="number" name="count" value="10" min="1" max="50"/>
              <button type="submit">รับงาน</button>
            </div>
          </form>
        </div>
        """
    )
    if not items:
        bits.append("<div class='card muted'>ยังไม่มีรายการในมือ — กดรับงาน หรือค้นหารหัส</div>")
    for item in items:
        loc = " / ".join(x for x in [item.get("location1"), item.get("location2")] if x) or "-"
        bits.append(
            f"""
            <a class="item card" href="/stock-check/product/{escape(item['bcode'])}">
              <div class="loc">{escape(loc)}</div>
              <div class="row" style="margin-top:6px">
                <div>
                  <div class="bcode">{escape(item['bcode'])}</div>
                  <div class="muted">{escape(item.get('descr') or '')}</div>
                </div>
                <div style="text-align:right">
                  <div class="qty">{item.get('qtyoh2', 0):.0f}</div>
                  <div class="muted">คงเหลือ</div>
                </div>
              </div>
              <div class="muted" style="margin-top:8px">ตรวจล่าสุด: {_fmt_ts(item.get('last_audited_at'))}</div>
            </a>
            """
        )
    return page("ตรวจนับสต็อก", "".join(bits), user=user)


def product_page(*, user: dict[str, Any], item: dict[str, Any], source: str = "batch") -> str:
    loc = " / ".join(x for x in [item.get("location1"), item.get("location2")] if x) or "-"
    body = f"""
    <div class="card">
      <div class="loc">{escape(loc)}</div>
      <div class="bcode" style="margin-top:6px">{escape(item['bcode'])}</div>
      <div class="muted">{escape(item.get('descr') or '')}</div>
      <div class="row" style="margin-top:12px">
        <div>
          <div class="muted">คงเหลือระบบ</div>
          <div class="qty">{item.get('qtyoh2', 0):.3g}</div>
        </div>
        <div style="text-align:right">
          <div class="muted">ตรวจล่าสุด</div>
          <div>{_fmt_ts(item.get('last_audited_at'))}</div>
        </div>
      </div>
    </div>
    <div class="card">
      <form method="post" action="/stock-check/product/{escape(item['bcode'])}/submit">
        <input type="hidden" name="source" value="{escape(source)}"/>
        <label>นับได้ทั้งหมด (new total)</label>
        <input type="number" step="any" name="counted_qty" inputmode="decimal" placeholder="เช่น {item.get('qtyoh2', 0):.0f}"/>
        <label>หรือส่วนต่าง (+ เพิ่ม / − ลด)</label>
        <input type="number" step="any" name="difference" inputmode="decimal" placeholder="เช่น -2"/>
        <label>หมายเหตุ</label>
        <input type="text" name="notes" maxlength="120"/>
        <div style="height:10px"></div>
        <button type="submit">บันทึก</button>
        <div style="height:8px"></div>
        <button class="secondary" type="submit" name="mark_correct" value="1">ถูกต้องตามระบบ</button>
      </form>
      <form method="post" action="/stock-check/product/{escape(item['bcode'])}/skip" style="margin-top:8px">
        <button class="ghost" type="submit">ข้าม / คืนคิว</button>
      </form>
    </div>
    """
    return page("นับสินค้า", body, user=user)


def ondemand_page(*, user: dict[str, Any], results: list[dict[str, Any]] | None = None, q: str = "") -> str:
    bits = [
        f"""
        <div class="card">
          <form method="get" action="/stock-check/ondemand">
            <label>BCODE / MCODE / PCODE</label>
            <input type="search" name="q" value="{escape(q)}" placeholder="สแกนหรือพิมพ์รหัส" autofocus/>
            <div style="height:8px"></div>
            <button type="submit">ค้นหา</button>
          </form>
          <p class="muted">สำหรับเจาะจงสินค้า — งานหลักอยู่ที่รายการที่รับไว้</p>
        </div>
        """
    ]
    for item in results or []:
        loc = " / ".join(x for x in [item.get("location1"), item.get("location2")] if x) or "-"
        flag = ""
        if item.get("leased_elsewhere"):
            flag = "<span class='pill warn'>มีคนถืออยู่</span>"
        bits.append(
            f"""
            <a class="item card" href="/stock-check/product/{escape(item['bcode'])}?source=ondemand">
              <div class="row">
                <div class="loc">{escape(loc)}</div>
                {flag}
              </div>
              <div class="bcode">{escape(item['bcode'])}</div>
              <div class="muted">{escape(item.get('descr') or '')}</div>
              <div class="muted">คงเหลือ {item.get('qtyoh2', 0):.0f}</div>
            </a>
            """
        )
    return page("ค้นหาสินค้า", "".join(bits), user=user)


def approve_page(*, user: dict[str, Any], drafts: list[dict[str, Any]], flash: str | None = None, error: str | None = None) -> str:
    bits: list[str] = []
    if flash:
        bits.append(f"<div class='flash'>{escape(flash)}</div>")
    if error:
        bits.append(f"<div class='flash err'>{escape(error)}</div>")
    if not user.get("is_approver"):
        bits.append("<div class='card muted'>บัญชีนี้ไม่มีสิทธิ์อนุมัติ</div>")
        return page("อนุมัติปรับสต็อก", "".join(bits), user=user)
    if not drafts:
        bits.append("<div class='card muted'>ไม่มีรายการรออนุมัติ</div>")
    for d in drafts:
        loc = " / ".join(x for x in [d.get("location1"), d.get("location2")] if x) or "-"
        var = float(d.get("variance") or 0)
        bits.append(
            f"""
            <div class="card">
              <div class="loc">{escape(loc)}</div>
              <div class="bcode">{escape(d['bcode'])}</div>
              <div class="muted">{escape(d.get('descr') or '')}</div>
              <div class="row" style="margin-top:8px">
                <div>ระบบ <b>{float(d['system_qty']):.3g}</b></div>
                <div>นับ <b>{float(d['counted_qty']):.3g}</b></div>
                <div>ต่าง <b>{var:+.3g}</b></div>
              </div>
              <div class="muted">โดย {escape(d.get('operator_name') or '')}</div>
              {f"<div class='flash err'>{escape(d['post_error'])}</div>" if d.get('post_error') else ''}
              <form method="post" action="/stock-check/approve/{escape(d['id'])}" style="margin-top:10px">
                <div class="grid2">
                  <button type="submit">อนุมัติ SA</button>
                  <button class="danger" formaction="/stock-check/reject/{escape(d['id'])}" type="submit">ปฏิเสธ</button>
                </div>
              </form>
            </div>
            """
        )
    return page("อนุมัติปรับสต็อก", "".join(bits), user=user)

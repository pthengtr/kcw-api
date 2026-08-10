from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any


def _fmt_ts(ts: float | None) -> str:
    if not ts:
        return "ไม่เคย"
    return datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")


def _nav_active(path: str, current: str) -> str:
    return "active" if path == current else ""


def page(
    title: str,
    body: str,
    *,
    user: dict[str, Any] | None = None,
    nav: str = "/",
    eyebrow: str | None = None,
    browser_entry_url: str | None = None,
) -> str:
    who = ""
    if user:
        role = "ผู้อนุมัติ" if user.get("is_approver") else "ผู้ตรวจ"
        who = (
            f"<div class='who'>"
            f"<span class='avatar'>{escape((user.get('display_name') or '?')[:1])}</span>"
            f"<span>{escape(user.get('display_name') or '')} · {role}</span>"
            f"</div>"
        )
    eye = f"<div class='eyebrow'>{escape(eyebrow)}</div>" if eyebrow else ""
    entry = (browser_entry_url or "").strip()
    entry_attr = escape(entry, quote=True)
    browser_foot = ""
    if entry:
        browser_foot = f"""
    <div id="open-browser" class="foot-tools" hidden data-entry-url="{entry_attr}">
      <button type="button" id="copy-entry" class="foot-link">คัดลอกลิงก์เปิดนอก LINE</button>
      <span id="copy-status" class="foot-status" aria-live="polite"></span>
    </div>
    """
    return f"""<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
  <meta name="theme-color" content="#2563eb"/>
  <title>{escape(title)} · KCW</title>
  <link rel="preconnect" href="https://fonts.googleapis.com"/>
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
  <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet"/>
  <style>
    :root {{
      --bg0: #eff4ff;
      --bg1: #f8fafc;
      --card: rgba(255,255,255,.9);
      --ink: #0f172a;
      --muted: #64748b;
      --line: rgba(15,23,42,.08);
      --accent: #2563eb;
      --accent-2: #3b82f6;
      --accent-soft: #dbeafe;
      --warn: #c45c12;
      --warn-soft: #ffedd5;
      --danger: #b42318;
      --danger-soft: #fee4e2;
      --ok: #067647;
      --ok-soft: #dcfae6;
      --shadow: 0 10px 30px rgba(37, 99, 235, .08);
      --radius: 18px;
      --nav-h: 72px;
    }}
    * {{ box-sizing: border-box; }}
    html {{ -webkit-tap-highlight-color: transparent; }}
    body {{
      margin: 0;
      font-family: "Prompt", sans-serif;
      color: var(--ink);
      min-height: 100vh;
      background:
        radial-gradient(1200px 480px at 10% -10%, #bfdbfe 0%, transparent 55%),
        radial-gradient(900px 420px at 100% 0%, #e0e7ff 0%, transparent 50%),
        linear-gradient(180deg, var(--bg0), var(--bg1) 42%, #f1f5f9);
    }}
    [hidden] {{ display: none !important; }}
    header.appbar {{
      position: sticky; top: 0; z-index: 5;
      padding: 14px 18px 12px;
      background: rgba(255,255,255,.72);
      backdrop-filter: blur(14px);
      border-bottom: 1px solid var(--line);
    }}
    .eyebrow {{
      font-size: .72rem; font-weight: 600; letter-spacing: .08em;
      text-transform: uppercase; color: var(--accent); margin-bottom: 2px;
    }}
    header h1 {{
      margin: 0; font-size: 1.35rem; font-weight: 700; letter-spacing: -.02em;
      line-height: 1.25;
    }}
    .who {{
      display: flex; align-items: center; gap: 8px;
      margin-top: 8px; color: var(--muted); font-size: .88rem; font-weight: 400;
    }}
    .avatar {{
      width: 26px; height: 26px; border-radius: 50%;
      display: inline-grid; place-items: center;
      background: var(--accent); color: #fff;
      font-size: .8rem; font-weight: 700;
    }}
    main {{
      padding: 14px 14px calc(var(--nav-h) + 18px);
      max-width: 720px; margin: 0 auto;
    }}
    .card {{
      background: var(--card);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      padding: 16px;
      margin-bottom: 12px;
      box-shadow: var(--shadow);
      backdrop-filter: blur(8px);
    }}
    .card.soft {{
      background: linear-gradient(145deg, #ffffff, #f1f5ff);
    }}
    .card.hero {{
      background: linear-gradient(135deg, #1d4ed8 0%, #2563eb 55%, #3b82f6 100%);
      color: #fff; border: 0;
    }}
    .card.hero label {{ color: rgba(255,255,255,.82); }}
    .card.hero input[type=number] {{
      border: 0; background: rgba(255,255,255,.95);
    }}
    .card.hero button {{
      background: #0f172a; color: #fff;
    }}
    .row {{
      display: flex; gap: 12px; justify-content: space-between; align-items: flex-start;
    }}
    .muted {{ color: var(--muted); font-size: .9rem; font-weight: 400; line-height: 1.45; }}
    .loc {{
      display: inline-flex; align-items: center; gap: 6px;
      font-weight: 700; font-size: 1.02rem; color: var(--accent);
      letter-spacing: .01em;
    }}
    .loc::before {{
      content: "";
      width: 8px; height: 8px; border-radius: 50%;
      background: var(--accent-2);
      box-shadow: 0 0 0 4px var(--accent-soft);
    }}
    .bcode {{
      font-family: "Prompt", ui-monospace, monospace;
      font-weight: 600; font-size: 1.05rem;
      letter-spacing: .02em;
    }}
    .descr {{
      margin-top: 2px; color: var(--muted); font-size: .92rem;
      display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    a.item {{
      display: block; text-decoration: none; color: inherit;
      transition: transform .12s ease, box-shadow .12s ease;
    }}
    a.item:active {{ transform: scale(.99); }}
    a.item.card:hover {{ box-shadow: 0 14px 34px rgba(37, 99, 235, .14); }}
    .meta-row {{
      display: flex; justify-content: space-between; gap: 8px;
      margin-top: 12px; padding-top: 10px;
      border-top: 1px dashed var(--line);
      font-size: .82rem; color: var(--muted);
    }}
    .qty-block {{ text-align: right; min-width: 72px; }}
    .qty {{
      font-size: 1.55rem; font-weight: 700; letter-spacing: -.03em;
      line-height: 1; color: var(--ink);
    }}
    .qty-label {{
      margin-top: 4px; font-size: .75rem; font-weight: 500;
      color: var(--muted); text-transform: uppercase; letter-spacing: .04em;
    }}
    button, .btn, input[type=submit] {{
      appearance: none; border: 0; border-radius: 14px;
      background: linear-gradient(180deg, var(--accent-2), var(--accent));
      color: #fff; font-family: inherit; font-weight: 600;
      padding: 14px 16px; font-size: 1rem; width: 100%;
      cursor: pointer; box-shadow: 0 6px 16px rgba(37,99,235,.28);
    }}
    button:active {{ transform: translateY(1px); }}
    button.secondary {{
      background: #1e293b; box-shadow: none;
    }}
    button.warn {{ background: var(--warn); box-shadow: none; }}
    button.danger {{
      background: linear-gradient(180deg, #d92d20, var(--danger));
      box-shadow: none;
    }}
    button.ghost {{
      background: #fff; color: var(--ink);
      border: 1px solid var(--line); box-shadow: none; font-weight: 500;
    }}
    .grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }}
    label {{
      display: block; font-size: .84rem; font-weight: 500;
      color: var(--muted); margin: 12px 0 6px;
    }}
    input[type=text], input[type=number], input[type=search], input[type=file] {{
      width: 100%; padding: 14px 14px; border-radius: 14px;
      border: 1px solid var(--line); font-size: 1.05rem;
      background: #fff; font-family: inherit; color: var(--ink);
    }}
    input[type=file] {{
      padding: 18px 14px;
      border-style: dashed; border-width: 1.5px;
      background: #f8fafc; color: var(--muted);
    }}
    input:focus {{
      outline: 2px solid rgba(37,99,235,.28);
      border-color: var(--accent);
    }}
    .hint {{ margin: 10px 0 0; font-size: .84rem; color: var(--muted); }}
    .empty {{
      text-align: center; padding: 28px 16px; color: var(--muted);
    }}
    .empty strong {{ display: block; color: var(--ink); margin-bottom: 6px; font-size: 1.05rem; }}
    .stats {{
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
      margin: 12px 0 4px;
    }}
    .stat {{
      background: #f1f5f9; border-radius: 12px; padding: 10px 8px; text-align: center;
    }}
    .stat b {{ display: block; font-size: 1.15rem; font-weight: 700; }}
    .stat span {{ font-size: .72rem; color: var(--muted); font-weight: 500; }}
    nav.bottom {{
      position: fixed; left: 0; right: 0; bottom: 0;
      height: calc(var(--nav-h) + env(safe-area-inset-bottom));
      padding: 8px 10px calc(8px + env(safe-area-inset-bottom));
      background: rgba(255,255,255,.9);
      backdrop-filter: blur(16px);
      border-top: 1px solid var(--line);
      display: grid; grid-template-columns: repeat(4, 1fr); gap: 4px;
    }}
    nav.bottom a {{
      text-align: center; text-decoration: none; color: var(--muted);
      font-size: .72rem; font-weight: 500; padding: 8px 4px;
      border-radius: 14px; display: grid; gap: 2px; place-items: center;
    }}
    nav.bottom a .ico {{
      font-size: 1.15rem; line-height: 1; font-weight: 600;
    }}
    nav.bottom a.active {{
      color: var(--accent); background: var(--accent-soft); font-weight: 600;
    }}
    .pill {{
      display: inline-block; padding: 3px 9px; border-radius: 999px;
      background: var(--accent-soft); color: var(--accent);
      font-size: .75rem; font-weight: 600;
    }}
    .pill.warn {{ background: var(--warn-soft); color: var(--warn); }}
    .flash {{
      padding: 12px 14px; border-radius: 14px; margin-bottom: 12px;
      background: var(--ok-soft); color: var(--ok); font-weight: 500;
      border: 1px solid rgba(6,118,71,.12);
    }}
    .flash.err {{
      background: var(--danger-soft); color: var(--danger);
      border-color: rgba(180,35,24,.12);
    }}
    .section-title {{
      font-size: .78rem; font-weight: 600; color: var(--muted);
      letter-spacing: .06em; text-transform: uppercase;
      margin: 8px 4px 10px;
    }}
    .foot-tools {{
      margin: 18px 4px 0;
      display: flex; align-items: center; gap: 8px;
      justify-content: center;
      flex-wrap: wrap;
    }}
    .foot-link {{
      all: unset; cursor: pointer;
      font-size: .72rem; font-weight: 500; color: var(--muted);
      text-decoration: underline; text-underline-offset: 2px;
      opacity: .65;
    }}
    .foot-link:active {{ opacity: 1; color: var(--accent); }}
    .foot-status {{ font-size: .7rem; color: var(--ok); }}
    @media (min-width: 720px) {{
      main {{ padding-top: 18px; }}
      header.appbar {{ padding-left: calc(50% - 360px + 18px); padding-right: calc(50% - 360px + 18px); }}
    }}
  </style>
</head>
<body>
  <header class="appbar">
    {eye}
    <h1>{escape(title)}</h1>
    {who}
  </header>
  <main>{body}{browser_foot}</main>
  <nav class="bottom">
    <a class="{_nav_active('/', nav)}" href="/stock-check/"><span class="ico">☰</span>งานวันนี้</a>
    <a class="{_nav_active('/ondemand', nav)}" href="/stock-check/ondemand"><span class="ico">⌕</span>ค้นหา</a>
    <a class="{_nav_active('/approve', nav)}" href="/stock-check/approve"><span class="ico">✓</span>อนุมัติ</a>
    <a class="{_nav_active('/end', nav)}" href="/stock-check/end"><span class="ico">⎋</span>จบงาน</a>
  </nav>
  <script>
  (function () {{
    var ua = navigator.userAgent || "";
    var isLine = /Line\\//i.test(ua);
    var isMobile = /Android|iPhone|iPad|iPod/i.test(ua);
    var canCapturePhoto = isMobile && !isLine;

    var cam = document.getElementById("cam-block");
    if (cam) cam.hidden = !canCapturePhoto;

    var openBrowser = document.getElementById("open-browser");
    if (openBrowser) {{
      var entryUrl = openBrowser.getAttribute("data-entry-url") || "";
      openBrowser.hidden = !(isLine && entryUrl);
      var btn = document.getElementById("copy-entry");
      var status = document.getElementById("copy-status");
      function setStatus(msg) {{ if (status) status.textContent = msg; }}
      function copyUrl() {{
        if (!entryUrl) return;
        function fallback() {{
          var ta = document.createElement("textarea");
          ta.value = entryUrl;
          ta.setAttribute("readonly", "");
          ta.style.position = "fixed";
          ta.style.left = "-9999px";
          document.body.appendChild(ta);
          ta.select();
          try {{
            document.execCommand("copy");
            setStatus("คัดลอกแล้ว");
          }} catch (e) {{
            setStatus("คัดลอกไม่สำเร็จ");
          }}
          document.body.removeChild(ta);
        }}
        if (navigator.clipboard && navigator.clipboard.writeText) {{
          navigator.clipboard.writeText(entryUrl).then(function () {{
            setStatus("คัดลอกแล้ว");
          }}).catch(fallback);
        }} else {{
          fallback();
        }}
      }}
      if (btn) btn.addEventListener("click", copyUrl);
    }}
  }})();
  </script>
</body>
</html>"""


def _product_card_html(item: dict[str, Any], *, href: str, flag: str = "") -> str:
    loc = " / ".join(x for x in [item.get("location1"), item.get("location2")] if x) or "ไม่ระบุที่เก็บ"
    return f"""
    <a class="item card" href="{href}">
      <div class="row">
        <div class="loc">{escape(loc)}</div>
        {flag}
      </div>
      <div class="row" style="margin-top:10px">
        <div style="min-width:0">
          <div class="bcode">{escape(item['bcode'])}</div>
          <div class="descr">{escape(item.get('descr') or '')}</div>
        </div>
        <div class="qty-block">
          <div class="qty">{item.get('qtyoh2', 0):.0f}</div>
          <div class="qty-label">คงเหลือ</div>
        </div>
      </div>
      <div class="meta-row">
        <span>ตรวจล่าสุด {_fmt_ts(item.get('last_audited_at'))}</span>
        <span>แตะเพื่อนับ →</span>
      </div>
    </a>
    """


def home_page(
    *,
    user: dict[str, Any],
    items: list[dict[str, Any]],
    flash: str | None = None,
    error: str | None = None,
    browser_entry_url: str | None = None,
) -> str:
    bits: list[str] = []
    if flash:
        bits.append(f"<div class='flash'>{escape(flash)}</div>")
    if error:
        bits.append(f"<div class='flash err'>{escape(error)}</div>")
    bits.append(
        f"""
        <div class="card hero">
          <div style="font-size:.9rem;opacity:.9;margin-bottom:4px">รับงานเดินคลัง</div>
          <div style="font-size:1.15rem;font-weight:600;margin-bottom:12px">
            มี {len(items)} รายการในมือ
          </div>
          <form method="post" action="/stock-check/take">
            <label>จำนวนที่ต้องการรับเพิ่ม</label>
            <div class="grid2">
              <input type="number" name="count" value="10" min="1" max="50"/>
              <button type="submit">รับงาน</button>
            </div>
          </form>
        </div>
        """
    )
    if not items:
        bits.append(
            """
            <div class="card empty">
              <strong>ยังไม่มีรายการในมือ</strong>
              กดรับงานด้านบน หรือไปที่ค้นหาเพื่อเจาะจงสินค้า
            </div>
            """
        )
    else:
        bits.append(f"<div class='section-title'>คิวของฉัน · {len(items)} รายการ</div>")
    for item in items:
        bits.append(
            _product_card_html(item, href=f"/stock-check/product/{escape(item['bcode'])}")
        )
    return page(
        "ตรวจนับสต็อก",
        "".join(bits),
        user=user,
        nav="/",
        eyebrow="KCW Stock Check",
        browser_entry_url=browser_entry_url,
    )


def product_page(
    *,
    user: dict[str, Any],
    item: dict[str, Any],
    source: str = "batch",
    browser_entry_url: str | None = None,
) -> str:
    loc = " / ".join(x for x in [item.get("location1"), item.get("location2")] if x) or "ไม่ระบุที่เก็บ"
    qty = item.get("qtyoh2", 0)
    body = f"""
    <div class="card soft">
      <div class="loc">{escape(loc)}</div>
      <div class="bcode" style="margin-top:10px;font-size:1.25rem">{escape(item['bcode'])}</div>
      <div class="descr" style="-webkit-line-clamp:4">{escape(item.get('descr') or '')}</div>
      <div class="stats">
        <div class="stat"><b>{qty:.3g}</b><span>ระบบ</span></div>
        <div class="stat"><b>{_fmt_ts(item.get('last_audited_at'))}</b><span>ตรวจล่าสุด</span></div>
        <div class="stat"><b>{escape(source)}</b><span>ที่มา</span></div>
      </div>
    </div>
    <div class="card">
      <div class="section-title" style="margin:0 0 4px">บันทึกการนับ</div>
      <form method="post" action="/stock-check/product/{escape(item['bcode'])}/submit">
        <input type="hidden" name="source" value="{escape(source)}"/>
        <label>นับได้ทั้งหมด</label>
        <input type="number" step="any" name="counted_qty" inputmode="decimal" placeholder="เช่น {qty:.0f}"/>
        <label>หรือส่วนต่าง (+เพิ่ม / −ลด)</label>
        <input type="number" step="any" name="difference" inputmode="decimal" placeholder="เช่น -2"/>
        <label>หมายเหตุ</label>
        <input type="text" name="notes" maxlength="120" placeholder="ถ้ามี"/>
        <div style="height:12px"></div>
        <button type="submit">บันทึกผลนับ</button>
        <div style="height:8px"></div>
        <button class="secondary" type="submit" name="mark_correct" value="1">ถูกต้องตามระบบ</button>
      </form>
      <form method="post" action="/stock-check/product/{escape(item['bcode'])}/skip" style="margin-top:8px">
        <button class="ghost" type="submit">ข้าม / คืนคิว</button>
      </form>
    </div>
    """
    return page(
        "นับสินค้า",
        body,
        user=user,
        nav="/",
        eyebrow=loc,
        browser_entry_url=browser_entry_url,
    )


def ondemand_page(
    *,
    user: dict[str, Any],
    results: list[dict[str, Any]] | None = None,
    q: str = "",
    flash: str | None = None,
    error: str | None = None,
    decoded: list[str] | None = None,
    browser_entry_url: str | None = None,
) -> str:
    bits: list[str] = []
    if flash:
        bits.append(f"<div class='flash'>{escape(flash)}</div>")
    if error:
        bits.append(f"<div class='flash err'>{escape(error)}</div>")
    bits.append(
        """
        <div class="card soft">
          <div class="section-title" style="margin-top:0">จากรูปบาร์โค้ด</div>
          <div id="cam-block" hidden>
            <form method="post" action="/stock-check/ondemand/upload" enctype="multipart/form-data">
              <label>ถ่ายรูปด้วยกล้อง</label>
              <input type="file" name="image" accept="image/*" capture="environment" id="cam"/>
              <div style="height:10px"></div>
              <button type="submit">ถ่ายแล้วอ่านบาร์โค้ด</button>
            </form>
            <div style="height:14px"></div>
          </div>
          <form method="post" action="/stock-check/ondemand/upload" enctype="multipart/form-data">
            <label>เลือกจากคลังรูป</label>
            <input type="file" name="image" accept="image/*" id="gallery"/>
            <div style="height:10px"></div>
            <button class="secondary" type="submit">อัปโหลดรูปแล้วอ่าน</button>
          </form>
          <p class="hint">
            ปุ่มถ่ายรูปจะโชว์เมื่อเบราว์เซอร์รองรับ (เช่น Chrome/Safari บนมือถือ)
            — ใน LINE มักใช้ได้แค่เลือกจากคลัง
          </p>
        </div>
        <div class="card">
          <div class="section-title" style="margin-top:0">พิมพ์รหัส</div>
          <form method="get" action="/stock-check/ondemand">
            <label>BCODE / MCODE / PCODE</label>
            <input type="search" name="q" value="__Q__" placeholder="พิมพ์หรือแปะรหัส" />
            <div style="height:10px"></div>
            <button class="secondary" type="submit">ค้นหา</button>
          </form>
        </div>
        """.replace("__Q__", escape(q))
    )
    if decoded:
        bits.append("<div class='section-title'>รหัสที่อ่านได้</div><div class='card'>")
        for code in decoded:
            bits.append(
                f"<a class='item' style='display:flex;justify-content:space-between;"
                f"padding:12px 0;border-bottom:1px solid var(--line);font-weight:600' "
                f"href='/stock-check/product/{escape(code)}?source=ondemand'>"
                f"<span class='bcode'>{escape(code)}</span><span class='muted'>เปิด →</span></a>"
            )
        bits.append("</div>")
    if results:
        bits.append("<div class='section-title'>ผลค้นหา</div>")
    for item in results or []:
        flag = ""
        if item.get("leased_elsewhere"):
            flag = "<span class='pill warn'>มีคนถืออยู่</span>"
        bits.append(
            _product_card_html(
                item,
                href=f"/stock-check/product/{escape(item['bcode'])}?source=ondemand",
                flag=flag,
            )
        )
    return page(
        "ค้นหาสินค้า",
        "".join(bits),
        user=user,
        nav="/ondemand",
        eyebrow="Ondemand",
        browser_entry_url=browser_entry_url,
    )

def approve_page(
    *,
    user: dict[str, Any],
    drafts: list[dict[str, Any]],
    flash: str | None = None,
    error: str | None = None,
    browser_entry_url: str | None = None,
) -> str:
    bits: list[str] = []
    if flash:
        bits.append(f"<div class='flash'>{escape(flash)}</div>")
    if error:
        bits.append(f"<div class='flash err'>{escape(error)}</div>")
    if not user.get("is_approver"):
        bits.append(
            "<div class='card empty'><strong>ไม่มีสิทธิ์อนุมัติ</strong>"
            "บัญชี LINE นี้ไม่อยู่ในรายชื่อผู้อนุมัติ</div>"
        )
        return page(
            "อนุมัติปรับสต็อก",
            "".join(bits),
            user=user,
            nav="/approve",
            browser_entry_url=browser_entry_url,
        )
    if not drafts:
        bits.append(
            "<div class='card empty'><strong>คิวว่าง</strong>ไม่มีรายการรออนุมัติตอนนี้</div>"
        )
    else:
        bits.append(f"<div class='section-title'>รออนุมัติ · {len(drafts)}</div>")
    for d in drafts:
        loc = " / ".join(x for x in [d.get("location1"), d.get("location2")] if x) or "-"
        var = float(d.get("variance") or 0)
        var_color = "var(--danger)" if var < 0 else "var(--ok)"
        bits.append(
            f"""
            <div class="card">
              <div class="loc">{escape(loc)}</div>
              <div class="bcode" style="margin-top:8px">{escape(d['bcode'])}</div>
              <div class="descr">{escape(d.get('descr') or '')}</div>
              <div class="stats">
                <div class="stat"><b>{float(d['system_qty']):.3g}</b><span>ระบบ</span></div>
                <div class="stat"><b>{float(d['counted_qty']):.3g}</b><span>นับได้</span></div>
                <div class="stat"><b style="color:{var_color}">{var:+.3g}</b><span>ส่วนต่าง</span></div>
              </div>
              <div class="muted" style="margin-top:8px">โดย {escape(d.get('operator_name') or '')}</div>
              {f"<div class='flash err' style='margin-top:10px'>{escape(d['post_error'])}</div>" if d.get('post_error') else ''}
              <form method="post" action="/stock-check/approve/{escape(d['id'])}" style="margin-top:12px">
                <div class="grid2">
                  <button type="submit">อนุมัติ SA</button>
                  <button class="danger" formaction="/stock-check/reject/{escape(d['id'])}" type="submit">ปฏิเสธ</button>
                </div>
              </form>
            </div>
            """
        )
    return page(
        "อนุมัติปรับสต็อก",
        "".join(bits),
        user=user,
        nav="/approve",
        eyebrow="Approval",
        browser_entry_url=browser_entry_url,
    )

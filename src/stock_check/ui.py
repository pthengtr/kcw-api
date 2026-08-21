from __future__ import annotations

from datetime import datetime
from html import escape
from typing import Any

from src.stock_check.daily_pick import POOL_INFO


def _fmt_ts(ts: float | None) -> str:
    if not ts:
        return "ไม่เคย"
    return datetime.fromtimestamp(ts).strftime("%d/%m %H:%M")


def _nav_active(path: str, current: str) -> str:
    return "active" if path == current else ""


def _pool_info_json() -> str:
    import json

    payload = {str(k): v for k, v in POOL_INFO.items()}
    return json.dumps(payload, ensure_ascii=False)


def _pool_badge_html(item: dict[str, Any]) -> str:
    raw = item.get("pick_priority")
    if raw is None:
        return ""
    try:
        pool = int(raw)
    except (TypeError, ValueError):
        return ""
    info = POOL_INFO.get(pool)
    if not info:
        return ""
    risk = " risk" if pool in (1, 2, 3) else ""
    label = f"{pool} · {info['short']}"
    return (
        f"<button type='button' class='pool-badge{risk}' data-pool='{pool}' "
        f"aria-label='อธิบายกลุ่ม {escape(info['title'])}'>{escape(label)}</button>"
    )


def _product_model_html(item: dict[str, Any]) -> str:
    model = str(item.get("model") or "").strip()
    if not model:
        return ""
    return f"<div class='model'>รุ่น {escape(model)}</div>"


def page(
    title: str,
    body: str,
    *,
    user: dict[str, Any] | None = None,
    nav: str = "/",
    eyebrow: str | None = None,
    browser_entry_url: str | None = None,
    lease_heartbeat: bool = False,
) -> str:
    who = ""
    if user:
        who = (
            f"<div class='who'>"
            f"<span class='avatar'>{escape((user.get('display_name') or '?')[:1])}</span>"
            f"<span>{escape(user.get('display_name') or '')} · ตรวจนับ</span>"
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
    .model {{
      margin-top: 4px; font-size: .86rem; font-weight: 500; color: var(--ink);
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
    button:disabled, .btn:disabled, input[type=submit]:disabled {{
      opacity: .55; cursor: not-allowed; transform: none;
      box-shadow: none;
    }}
    #busy-overlay {{
      position: fixed; inset: 0; z-index: 40;
      display: grid; place-items: center;
      background: rgba(15, 23, 42, .42);
      backdrop-filter: blur(2px);
      padding: 24px;
    }}
    #busy-overlay .busy-card {{
      background: #fff; border-radius: 18px;
      padding: 22px 26px; min-width: min(260px, 86vw);
      box-shadow: 0 18px 40px rgba(15,23,42,.22);
      display: grid; justify-items: center; gap: 12px;
      text-align: center;
    }}
    #busy-overlay .spinner {{
      width: 36px; height: 36px; border-radius: 50%;
      border: 3px solid var(--accent-soft);
      border-top-color: var(--accent);
      animation: spin .7s linear infinite;
    }}
    #busy-overlay .busy-text {{
      font-size: .95rem; font-weight: 600; color: var(--ink);
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    body.is-busy {{ overflow: hidden; }}
    body.is-busy nav.bottom {{ pointer-events: none; opacity: .45; }}
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
    .card.own-draft {{ opacity: .72; background: #f1f5f9; border: 1px dashed var(--line); }}
    .stats {{
      display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
      margin: 12px 0 4px;
    }}
    .stat {{
      background: #f1f5f9; border-radius: 12px; padding: 10px 8px; text-align: center;
    }}
    .stat b {{ display: block; font-size: 1.15rem; font-weight: 700; }}
    .stat span {{ font-size: .72rem; color: var(--muted); font-weight: 500; }}
    .seg {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 6px;
      padding: 4px; margin: 8px 0 4px;
      background: #e8eef7; border-radius: 14px;
    }}
    .seg button {{
      width: auto; padding: 10px 8px; font-size: .9rem; font-weight: 600;
      background: transparent; color: var(--muted); box-shadow: none;
    }}
    .seg button.active {{
      background: #fff; color: var(--accent);
      box-shadow: 0 2px 8px rgba(37,99,235,.12);
    }}
    .dir-row {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0 4px;
    }}
    .dir-row button {{
      width: auto; padding: 12px 8px; font-size: .95rem; box-shadow: none;
      background: #fff; color: var(--ink); border: 1.5px solid var(--line);
    }}
    .dir-row button.active.minus {{
      background: var(--danger-soft); color: var(--danger);
      border-color: rgba(180,35,24,.25);
    }}
    .dir-row button.active.plus {{
      background: var(--ok-soft); color: var(--ok);
      border-color: rgba(6,118,71,.25);
    }}
    .preview {{
      margin-top: 10px; padding: 10px 12px; border-radius: 12px;
      background: var(--accent-soft); color: var(--accent);
      font-size: .9rem; font-weight: 500;
    }}
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
    .pool-badge {{
      all: unset; cursor: pointer;
      display: inline-flex; align-items: center; gap: 4px;
      padding: 4px 10px; border-radius: 999px;
      background: var(--accent-soft); color: var(--accent);
      font-size: .72rem; font-weight: 700; letter-spacing: .01em;
      border: 1px solid rgba(37,99,235,.18);
    }}
    .pool-badge:active {{ transform: scale(.97); }}
    .pool-badge.risk {{
      background: var(--danger-soft); color: var(--danger);
      border-color: rgba(180,35,24,.18);
    }}
    .pool-help {{
      all: unset; cursor: pointer;
      font-size: .78rem; font-weight: 600; color: var(--accent);
      text-decoration: underline; text-underline-offset: 2px;
    }}
    #pool-dialog {{
      border: 0; border-radius: 18px; padding: 0;
      width: min(420px, calc(100vw - 28px));
      max-height: min(80vh, 640px);
      box-shadow: 0 22px 50px rgba(15,23,42,.28);
    }}
    #pool-dialog::backdrop {{ background: rgba(15,23,42,.45); }}
    #pool-dialog .dlg {{
      padding: 18px 18px 14px;
    }}
    #pool-dialog h2 {{
      margin: 0 0 6px; font-size: 1.1rem; font-weight: 700;
    }}
    #pool-dialog .dlg-body {{
      color: var(--muted); font-size: .9rem; line-height: 1.45;
      margin: 0 0 14px;
    }}
    #pool-dialog .pool-list {{
      display: grid; gap: 10px; margin: 0 0 14px;
    }}
    #pool-dialog .pool-item {{
      padding: 10px 12px; border-radius: 12px;
      background: #f8fafc; border: 1px solid var(--line);
    }}
    #pool-dialog .pool-item strong {{
      display: block; font-size: .9rem; color: var(--ink); margin-bottom: 2px;
    }}
    #pool-dialog .pool-item span {{
      font-size: .82rem; color: var(--muted); line-height: 1.4;
    }}
    #pool-dialog .dlg-close {{
      width: 100%;
    }}
    .item-wrap {{
      margin-bottom: 12px;
    }}
    .item-wrap .card {{ margin-bottom: 0; }}
    .item-top {{
      display: flex; justify-content: space-between; align-items: center;
      gap: 8px; margin-bottom: 8px; padding: 0 2px;
    }}
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
  <div id="busy-overlay" hidden aria-live="assertive" aria-busy="true">
    <div class="busy-card">
      <div class="spinner" aria-hidden="true"></div>
      <div class="busy-text">กำลังดำเนินการ…</div>
    </div>
  </div>
  <dialog id="pool-dialog">
    <div class="dlg">
      <h2 id="pool-dialog-title">กลุ่มงาน Take N</h2>
      <p class="dlg-body" id="pool-dialog-body">
        รับงานจะกระจายสล็อตตามกลุ่มด้านล่าง (4→5→6 แล้ว 1→2→3)
        กดหมายเลขกลุ่มบนการ์ดเพื่ออ่านรายละเอียด
      </p>
      <div class="pool-list" id="pool-dialog-list"></div>
      <button type="button" class="dlg-close" id="pool-dialog-close">ปิด</button>
    </div>
  </dialog>
  <script>
  (function () {{
    var busy = false;
    function showBusy() {{
      if (busy) return;
      busy = true;
      document.body.classList.add("is-busy");
      var overlay = document.getElementById("busy-overlay");
      if (overlay) overlay.hidden = false;
      setTimeout(function () {{
        document.querySelectorAll("button, input[type=submit]").forEach(function (el) {{
          if (el.id === "pool-dialog-close") return;
          el.disabled = true;
        }});
      }}, 0);
    }}
    document.addEventListener("submit", function (ev) {{
      if (ev.defaultPrevented) return;
      if (busy) {{
        ev.preventDefault();
        return;
      }}
      showBusy();
    }});

    var POOL_INFO = {_pool_info_json()};
    var dlg = document.getElementById("pool-dialog");
    var dlgTitle = document.getElementById("pool-dialog-title");
    var dlgBody = document.getElementById("pool-dialog-body");
    var dlgList = document.getElementById("pool-dialog-list");
    var dlgClose = document.getElementById("pool-dialog-close");
    function renderPoolList(focus) {{
      if (!dlgList) return;
      var html = "";
      [4,5,6,1,2,3].forEach(function (n) {{
        var info = POOL_INFO[String(n)] || POOL_INFO[n];
        if (!info) return;
        var hl = (focus && Number(focus) === n) ? " style='border-color:rgba(37,99,235,.45);background:#eff6ff'" : "";
        html += "<div class='pool-item'" + hl + "><strong>" + info.title + "</strong><span>" + info.body + "</span></div>";
      }});
      dlgList.innerHTML = html;
    }}
    function openPoolDialog(pool) {{
      if (!dlg) return;
      var info = pool ? (POOL_INFO[String(pool)] || POOL_INFO[pool]) : null;
      if (info) {{
        dlgTitle.textContent = info.title;
        dlgBody.textContent = info.body;
      }} else {{
        dlgTitle.textContent = "กลุ่มงาน Take N";
        dlgBody.textContent = "รับงานจะกระจายสล็อตตามกลุ่มด้านล่าง (4→5→6 แล้ว 1→2→3) — กดหมายเลขกลุ่มบนการ์ดเพื่อโฟกัสรายละเอียด";
      }}
      renderPoolList(pool || null);
      if (typeof dlg.showModal === "function") dlg.showModal();
      else dlg.setAttribute("open", "open");
    }}
    document.addEventListener("click", function (ev) {{
      var t = ev.target;
      if (!t) return;
      var badge = t.closest ? t.closest("[data-pool]") : null;
      if (badge) {{
        ev.preventDefault();
        ev.stopPropagation();
        openPoolDialog(badge.getAttribute("data-pool"));
        return;
      }}
      if (t.id === "pool-help-all" || (t.closest && t.closest("#pool-help-all"))) {{
        ev.preventDefault();
        openPoolDialog(null);
      }}
    }});
    if (dlgClose) dlgClose.addEventListener("click", function () {{
      if (typeof dlg.close === "function") dlg.close();
      else dlg.removeAttribute("open");
    }});

    var leaseHeartbeat = {"true" if lease_heartbeat else "false"};
    if (leaseHeartbeat) {{
      function ping() {{
        if (document.hidden) return;
        fetch("/stock-check/heartbeat", {{
          method: "POST",
          credentials: "same-origin",
          headers: {{ "Accept": "application/json" }}
        }}).catch(function () {{}});
      }}
      setInterval(ping, 60000);
      document.addEventListener("visibilitychange", function () {{
        if (!document.hidden) ping();
      }});
    }}

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
    badge = _pool_badge_html(item)
    top = ""
    if badge or flag:
        top = f"<div class='item-top'>{badge or '<span></span>'}{flag}</div>"
    abc = item.get("abc_class")
    abc_bit = ""
    if abc and abc != "N":
        days = item.get("sales_days_90")
        days_bit = f" · {days} วันขาย" if days is not None else ""
        abc_bit = (
            f"<div class='muted' style='margin-top:6px;font-size:0.78rem'>"
            f"ABC {escape(str(abc))}{escape(str(days_bit))}</div>"
        )
    return f"""
    <div class="item-wrap">
      {top}
      <a class="item card" href="{href}">
        <div class="row">
          <div class="loc">{escape(loc)}</div>
        </div>
        <div class="row" style="margin-top:10px">
          <div style="min-width:0">
            <div class="bcode">{escape(item['bcode'])}</div>
            <div class="descr">{escape(item.get('descr') or '')}</div>
            {_product_model_html(item)}
            {abc_bit}
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
    </div>
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
          <p class="hint" style="color:rgba(255,255,255,.85);margin-top:12px">
            <button type="button" class="pool-help" id="pool-help-all" style="color:#fff">กลุ่มงาน Take N คืออะไร?</button>
            · คิวค้างจะคืนอัตโนมัติถ้าไม่ทำอะไร ~5 นาที
          </p>
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
        lease_heartbeat=bool(items),
    )


def product_page(
    *,
    user: dict[str, Any],
    item: dict[str, Any],
    source: str = "batch",
    browser_entry_url: str | None = None,
) -> str:
    loc = " / ".join(x for x in [item.get("location1"), item.get("location2")] if x) or "ไม่ระบุที่เก็บ"
    qty = float(item.get("qtyoh2", 0) or 0)
    qty_disp = f"{qty:.3g}"
    badge = _pool_badge_html(item)
    badge_row = f"<div style='margin-bottom:10px'>{badge}</div>" if badge else ""
    blocked = bool(item.get("submit_blocked"))
    block_reason = item.get("block_reason") or ""
    block_banner = ""
    if blocked and block_reason:
        block_banner = f"<div class='flash err' style='margin-bottom:12px'>{escape(block_reason)}</div>"
    disabled_attr = " disabled" if blocked else ""
    body = f"""
    <div class="card soft">
      {badge_row}
      {block_banner}
      <div class="loc">{escape(loc)}</div>
      <div class="bcode" style="margin-top:10px;font-size:1.25rem">{escape(item['bcode'])}</div>
      <div class="descr" style="-webkit-line-clamp:4">{escape(item.get('descr') or '')}</div>
      {_product_model_html(item)}
      <div class="stats">
        <div class="stat"><b>{qty_disp}</b><span>ระบบ</span></div>
        <div class="stat"><b>{_fmt_ts(item.get('last_audited_at'))}</b><span>ตรวจล่าสุด</span></div>
        <div class="stat"><b>{escape(source)}</b><span>ที่มา</span></div>
      </div>
    </div>
    <div class="card" id="count-card" data-system-qty="{qty}">
      <div class="section-title" style="margin:0 0 4px">บันทึกการนับ</div>
      <p class="hint" style="margin-top:0">เลือกอย่างใดอย่างหนึ่ง — ไม่ต้องกรอกทั้งสองช่อง</p>
      <div class="seg" role="tablist">
        <button type="button" class="active" data-mode="total" id="mode-total-btn">นับได้ทั้งหมด</button>
        <button type="button" data-mode="diff" id="mode-diff-btn">ส่วนต่าง</button>
      </div>
      <form method="post" action="/stock-check/product/{escape(item['bcode'])}/submit" id="count-form">
        <input type="hidden" name="source" value="{escape(source)}"/>
        <input type="hidden" name="diff_dir" id="diff-dir" value="minus"/>
        <div id="panel-total">
          <label>นับได้กี่ชิ้น</label>
          <input type="text" name="counted_qty" id="counted-qty"
            inputmode="decimal" pattern="[0-9]*[.,]?[0-9]*"
            autocomplete="off" placeholder="เช่น {qty:.0f}"{disabled_attr}/>
          <p class="hint">พิมพ์ตัวเลขอย่างเดียว (คีย์บอร์ดโทรศัพท์ใช้ได้)</p>
        </div>
        <div id="panel-diff" hidden>
          <label>ของจริงต่างจากระบบ</label>
          <div class="dir-row">
            <button type="button" class="minus active" data-dir="minus" id="dir-minus">− ลด</button>
            <button type="button" class="plus" data-dir="plus" id="dir-plus">+ เพิ่ม</button>
          </div>
          <label>จำนวนที่ต่าง (ไม่ติดลบ)</label>
          <input type="text" name="diff_amount" id="diff-amount"
            inputmode="decimal" pattern="[0-9]*[.,]?[0-9]*"
            autocomplete="off" placeholder="เช่น 2"{disabled_attr}/>
          <div class="preview" id="diff-preview">ระบบ {qty_disp} → จะได้ …</div>
        </div>
        <label>หมายเหตุ</label>
        <input type="text" name="notes" maxlength="120" placeholder="ถ้ามี"{disabled_attr}/>
        <div style="height:12px"></div>
        <button type="submit" id="save-btn"{disabled_attr}>บันทึกผลนับ</button>
        <div style="height:8px"></div>
        <button class="secondary" type="submit" name="mark_correct" value="1"{disabled_attr}>ถูกต้องตามระบบ ({qty_disp})</button>
      </form>
      <form method="post" action="/stock-check/product/{escape(item['bcode'])}/skip" style="margin-top:8px">
        <button class="ghost" type="submit"{disabled_attr}>ข้าม / คืนคิว</button>
      </form>
    </div>
    <script>
    (function () {{
      var card = document.getElementById("count-card");
      if (!card) return;
      var systemQty = parseFloat(card.getAttribute("data-system-qty") || "0") || 0;
      var panelTotal = document.getElementById("panel-total");
      var panelDiff = document.getElementById("panel-diff");
      var counted = document.getElementById("counted-qty");
      var amount = document.getElementById("diff-amount");
      var dirInput = document.getElementById("diff-dir");
      var preview = document.getElementById("diff-preview");
      var mode = "total";
      var dir = "minus";

      function setMode(next) {{
        mode = next;
        document.getElementById("mode-total-btn").classList.toggle("active", mode === "total");
        document.getElementById("mode-diff-btn").classList.toggle("active", mode === "diff");
        panelTotal.hidden = mode !== "total";
        panelDiff.hidden = mode !== "diff";
        if (mode === "total") {{
          amount.value = "";
        }} else {{
          counted.value = "";
          updatePreview();
        }}
      }}
      function setDir(next) {{
        dir = next;
        dirInput.value = dir;
        document.getElementById("dir-minus").classList.toggle("active", dir === "minus");
        document.getElementById("dir-plus").classList.toggle("active", dir === "plus");
        updatePreview();
      }}
      function parseNum(raw) {{
        if (!raw) return null;
        var n = parseFloat(String(raw).replace(",", "."));
        return isFinite(n) ? n : null;
      }}
      function updatePreview() {{
        var abs = parseNum(amount && amount.value);
        if (abs === null || abs < 0) {{
          preview.textContent = "ระบบ " + systemQty + " → จะได้ …";
          return;
        }}
        var signed = dir === "minus" ? -abs : abs;
        var next = systemQty + signed;
        var label = dir === "minus" ? ("−" + abs) : ("+" + abs);
        preview.textContent = "ระบบ " + systemQty + " " + label + " → จะได้ " + next;
      }}

      document.getElementById("mode-total-btn").addEventListener("click", function () {{ setMode("total"); }});
      document.getElementById("mode-diff-btn").addEventListener("click", function () {{ setMode("diff"); }});
      document.getElementById("dir-minus").addEventListener("click", function () {{ setDir("minus"); }});
      document.getElementById("dir-plus").addEventListener("click", function () {{ setDir("plus"); }});
      if (amount) amount.addEventListener("input", updatePreview);

      document.getElementById("count-form").addEventListener("submit", function (ev) {{
        var mark = ev.submitter && ev.submitter.name === "mark_correct";
        if (mark) return;
        if (mode === "total") {{
          amount.value = "";
          var n = parseNum(counted.value);
          if (n === null || n < 0) {{
            ev.preventDefault();
            alert("กรอกจำนวนที่นับได้");
          }}
        }} else {{
          counted.value = "";
          var abs = parseNum(amount.value);
          if (abs === null || abs < 0) {{
            ev.preventDefault();
            alert("กรอกจำนวนส่วนต่าง (ตัวเลขบวก)");
          }}
        }}
      }});
    }})();
    </script>
    """
    return page(
        "นับสินค้า",
        body,
        user=user,
        nav="/",
        eyebrow=loc,
        browser_entry_url=browser_entry_url,
        lease_heartbeat=True,
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
            <label>BCODE / MCODE / PCODE / รุ่น</label>
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
        flags: list[str] = []
        if item.get("has_pending_draft"):
            flags.append("<span class='pill warn'>รออนุมัติ</span>")
        elif item.get("leased_elsewhere"):
            flags.append("<span class='pill warn'>มีคนถืออยู่</span>")
        flag = " ".join(flags)
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
    if not drafts:
        bits.append(
            "<div class='card empty'><strong>คิวว่าง</strong>ไม่มีรายการรออนุมัติตอนนี้</div>"
        )
    else:
        bits.append(f"<div class='section-title'>รออนุมัติ · {len(drafts)}</div>")
    uid = str(user.get("line_user_id") or "").strip()
    for d in drafts:
        loc = " / ".join(x for x in [d.get("location1"), d.get("location2")] if x) or "-"
        var = float(d.get("variance") or 0)
        var_color = "var(--danger)" if var < 0 else "var(--ok)"
        is_own = uid == str(d.get("operator_line_user_id") or "").strip()
        card_class = "card own-draft" if is_own else "card"
        actions = ""
        if is_own:
            actions = f"""
              <div class='muted' style='margin-top:10px'>รายการของคุณ — ต้องให้เพื่อนร่วมงานอนุมัติ</div>
              <div class="grid2" style="margin-top:12px">
                <a class="secondary" href="/stock-check/draft/{escape(d['id'])}/edit" style="text-align:center;padding:12px;border-radius:12px;text-decoration:none">แก้ไข</a>
                <form method="post" action="/stock-check/reject/{escape(d['id'])}">
                  <button class="ghost" type="submit">ยกเลิก</button>
                </form>
              </div>
            """
        else:
            actions = f"""
              <form method="post" action="/stock-check/approve/{escape(d['id'])}" style="margin-top:12px">
                <div class="grid2">
                  <button type="submit">อนุมัติ SA</button>
                  <button class="danger" formaction="/stock-check/reject/{escape(d['id'])}" type="submit">ปฏิเสธ</button>
                </div>
              </form>
            """
        bits.append(
            f"""
            <div class="{card_class}">
              <div class="loc">{escape(loc)}</div>
              <div class="bcode" style="margin-top:8px">{escape(d['bcode'])}</div>
              <div class="descr">{escape(d.get('descr') or '')}</div>
              {_product_model_html(d)}
              <div class="stats">
                <div class="stat"><b>{float(d['system_qty']):.3g}</b><span>ระบบ</span></div>
                <div class="stat"><b>{float(d['counted_qty']):.3g}</b><span>นับได้</span></div>
                <div class="stat"><b style="color:{var_color}">{var:+.3g}</b><span>ส่วนต่าง</span></div>
              </div>
              <div class="muted" style="margin-top:8px">โดย {escape(d.get('operator_name') or '')}</div>
              {f"<div class='flash err' style='margin-top:10px'>{escape(d['post_error'])}</div>" if d.get('post_error') else ''}
              {actions}
            </div>
            """
        )
    return page(
        "อนุมัติปรับสต็อก",
        "".join(bits),
        user=user,
        nav="/approve",
        eyebrow="Audit",
        browser_entry_url=browser_entry_url,
    )


def draft_edit_page(
    *,
    user: dict[str, Any],
    draft: dict[str, Any],
    product: dict[str, Any],
    flash: str | None = None,
    error: str | None = None,
    browser_entry_url: str | None = None,
) -> str:
    loc = " / ".join(x for x in [product.get("location1"), product.get("location2")] if x) or "ไม่ระบุที่เก็บ"
    qty = float(product.get("qtyoh2", 0) or 0)
    counted = float(draft.get("counted_qty") or 0)
    qty_disp = f"{qty:.3g}"
    counted_disp = f"{counted:.3g}"
    bits: list[str] = []
    if flash:
        bits.append(f"<div class='flash'>{escape(flash)}</div>")
    if error:
        bits.append(f"<div class='flash err'>{escape(error)}</div>")
    body = f"""
    <div class="card soft">
      <div class="loc">{escape(loc)}</div>
      <div class="bcode" style="margin-top:10px;font-size:1.25rem">{escape(product['bcode'])}</div>
      <div class="descr" style="-webkit-line-clamp:4">{escape(product.get('descr') or '')}</div>
      {_product_model_html(product)}
      <div class="stats">
        <div class="stat"><b>{qty_disp}</b><span>ระบบตอนนี้</span></div>
        <div class="stat"><b>{counted_disp}</b><span>นับเดิม</span></div>
      </div>
      <div class="muted" style="margin-top:8px">แก้ไขได้ก่อนเพื่อนร่วมงานอนุมัติ</div>
    </div>
    <div class="card" id="count-card" data-system-qty="{qty}">
      <div class="section-title" style="margin:0 0 4px">แก้ไขผลนับ</div>
      <form method="post" action="/stock-check/draft/{escape(draft['id'])}/edit" id="count-form">
        <label>นับได้กี่ชิ้น</label>
        <input type="text" name="counted_qty" id="counted-qty"
          inputmode="decimal" pattern="[0-9]*[.,]?[0-9]*"
          autocomplete="off" value="{escape(counted_disp)}"/>
        <label>หมายเหตุ</label>
        <input type="text" name="notes" maxlength="120" value="{escape(draft.get('notes') or '')}"/>
        <div style="height:12px"></div>
        <button type="submit">บันทึกการแก้ไข</button>
      </form>
      <div style="height:8px"></div>
      <a href="/stock-check/approve" class="ghost" style="display:block;text-align:center;padding:10px">กลับคิวอนุมัติ</a>
    </div>
    """
    return page(
        "แก้ไขรายการ",
        "".join(bits) + body,
        user=user,
        nav="/approve",
        eyebrow="Edit",
        browser_entry_url=browser_entry_url,
    )


def drift_review_page(
    *,
    user: dict[str, Any],
    review: dict[str, Any],
    browser_entry_url: str | None = None,
) -> str:
    draft = review["draft"]
    loc = " / ".join(x for x in [draft.get("location1"), draft.get("location2")] if x) or "-"
    sys0 = float(review["draft_system_qty"])
    live = float(review["live_qty"])
    counted = float(review["counted_qty"])
    drift = float(review["drift"])
    new_var = float(review["new_variance"])
    explained = float(review.get("explained_delta") or 0)
    unexplained = float(review.get("unexplained_delta") or 0)
    var_color = "var(--danger)" if new_var < 0 else "var(--ok)"

    bill_rows = ""
    for m in review.get("movements") or []:
        q = float(m.get("qty_delta") or 0)
        q_color = "var(--danger)" if q < 0 else "var(--ok)"
        bill_rows += (
            f"<div class='muted' style='margin:6px 0'>"
            f"{escape(m.get('billno') or '')} · {escape(m.get('kind_label') or '')} "
            f"<b style='color:{q_color}'>{q:+.3g}</b></div>"
        )
    if not bill_rows:
        bill_rows = "<div class='muted'>ไม่พบบิลในช่วงนี้</div>"

    explain_note = ""
    if review.get("drift_fully_explained"):
        explain_note = "<div class='flash' style='margin-top:10px'>สอดคล้องกับบิลขาย/ซื้อระหว่างนับกับอนุมัติ</div>"
    elif abs(drift) > 1e-6:
        explain_note = (
            f"<div class='flash err' style='margin-top:10px'>"
            f"สต็อกเปลี่ยน {drift:+.3g} · จากบิล {explained:+.3g} · คงเหลือไม่อธิบาย {unexplained:+.3g}"
            f" — ยังอนุมัติต่อได้</div>"
        )

    body = f"""
    <div class="card">
      <div class="loc">{escape(loc)}</div>
      <div class="bcode" style="margin-top:8px">{escape(draft['bcode'])}</div>
      <div class="descr">{escape(draft.get('descr') or '')}</div>
      {_product_model_html(draft)}
      <div class="stats">
        <div class="stat"><b>{sys0:.3g}</b><span>ตอนนับ</span></div>
        <div class="stat"><b>{counted:.3g}</b><span>นับได้</span></div>
        <div class="stat"><b>{live:.3g}</b><span>ระบบตอนนี้</span></div>
      </div>
      <div class="muted" style="margin-top:10px">
        สต็อกเปลี่ยน {drift:+.3g} ระหว่างนับกับอนุมัติ · SA ที่จะโพสต์ <b style="color:{var_color}">{new_var:+.3g}</b>
      </div>
      {explain_note}
      <div class="section-title" style="margin-top:14px">บิลระหว่างนับกับอนุมัติ</div>
      {bill_rows}
      <form method="post" action="/stock-check/approve/{escape(draft['id'])}" style="margin-top:14px">
        <input type="hidden" name="confirm_drift" value="1"/>
        <button type="submit">อนุมัติต่อ (ใช้สต็อกปัจจุบัน)</button>
      </form>
      <a href="/stock-check/approve" class="ghost" style="display:block;text-align:center;padding:10px;margin-top:8px">กลับ</a>
    </div>
    """
    return page(
        "ตรวจสอบสต็อกเปลี่ยน",
        body,
        user=user,
        nav="/approve",
        eyebrow="Drift review",
        browser_entry_url=browser_entry_url,
    )

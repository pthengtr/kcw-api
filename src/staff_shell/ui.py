"""Shared Google Apps–style launcher chrome injected into every staff UI."""

from __future__ import annotations

import json
from html import escape

# Idle timeout before warn+logout (ms). 4 hours — session cookie still caps overall life.
IDLE_TIMEOUT_MS = 4 * 60 * 60 * 1000
IDLE_WARN_MS = 60 * 1000
RETURN_PATH_KEY = "kcw_return_path"


def render_shell_html(
    *,
    service_id: str,
    api_base: str,
    user_name: str = "",
    branch: str = "",
) -> str:
    who = escape((user_name or "").strip() or "ผู้ใช้")
    site = escape((branch or "").strip().upper() or "")
    cfg = {
        "serviceId": service_id,
        "apiBase": api_base.rstrip("/"),
        "idleMs": IDLE_TIMEOUT_MS,
        "warnMs": IDLE_WARN_MS,
    }
    cfg_json = json.dumps(cfg, ensure_ascii=False)
    branch_chip = f'<span class="kcw-shell-branch">{site}</span>' if site else ""
    return f"""
<style id="kcw-shell-css">
/* Dedicated launcher strip — never overlays host Service controls. */
html.kcw-shell-pad{{--kcw-shell-h:56px}}
html.kcw-shell-pad body{{padding-top:var(--kcw-shell-h) !important}}
html.kcw-shell-pad header,
html.kcw-shell-pad .hdr,
html.kcw-shell-pad .appbar{{top:var(--kcw-shell-h) !important}}
/* Full-screen document viewers sit below the launcher strip so 9-dot never covers toolbar. */
html.kcw-shell-pad #sheet,
html.kcw-shell-pad #catalog,
html.kcw-shell-pad #hist,
html.kcw-shell-pad #poBox,
html.kcw-shell-pad #photo,
html.kcw-shell-pad .kcw-doc-overlay{{top:var(--kcw-shell-h) !important}}
/* Shared document chrome — compact toolbar under the shell strip. */
.kcw-doc-toolbar{{display:flex;align-items:center;gap:8px;flex-wrap:nowrap;
  padding:8px 10px;background:#fff;border-bottom:1px solid #e2e8f0;
  position:sticky;top:0;z-index:5}}
.kcw-doc-toolbar .kcw-doc-x{{flex:none;width:40px;min-width:40px;min-height:40px;padding:0;
  border:1px solid #e2e8f0;border-radius:10px;background:#fff;color:#0f172a;
  font-size:22px;line-height:1;font-weight:600;cursor:pointer}}
.kcw-doc-toolbar .kcw-doc-seg{{display:inline-flex;flex:1;min-width:0;gap:2px;padding:3px;
  border-radius:10px;background:#f1f5f9;border:1px solid #e2e8f0}}
.kcw-doc-toolbar .kcw-doc-seg button{{flex:1;min-height:36px;border:0;border-radius:8px;
  background:transparent;color:#64748b;font:inherit;font-weight:650;font-size:13px;cursor:pointer;padding:6px 8px}}
.kcw-doc-toolbar .kcw-doc-seg button.on{{background:#1d4ed8;color:#fff}}
.kcw-doc-toolbar .kcw-doc-print{{flex:none;min-height:40px;padding:0 16px;border:0;border-radius:10px;
  background:#1d4ed8;color:#fff;font:inherit;font-weight:700;font-size:14px;cursor:pointer;white-space:nowrap}}
#kcw-shell-root{{position:fixed;top:0;left:0;right:0;z-index:10050;pointer-events:none;
  font-family:Prompt,"Noto Sans Thai",system-ui,sans-serif}}
#kcw-shell-root.kcw-shell-rooted{{position:static;z-index:auto;left:auto;right:auto}}
#kcw-shell-root *{{box-sizing:border-box}}
.kcw-shell-bar{{pointer-events:auto;display:flex;align-items:center;justify-content:flex-end;gap:8px;
  width:100%;min-height:48px;
  padding:max(6px,env(safe-area-inset-top)) max(12px,env(safe-area-inset-right)) 6px 12px;
  background:rgba(248,250,252,.96);border-bottom:1px solid #e2e8f0;backdrop-filter:blur(8px);
  box-shadow:0 1px 0 rgba(15,23,42,.04)}}
.kcw-shell-who{{display:flex;flex-direction:column;align-items:flex-end;line-height:1.2;
  max-width:min(48vw,220px);color:#0f172a;padding:2px 4px}}
.kcw-shell-name{{font-size:12px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:100%}}
.kcw-shell-branch{{font-size:11px;color:#64748b}}
/* Beat host-page `button {{ background }}` resets (e.g. online-sale red buttons). */
#kcw-shell-root button.kcw-shell-btn{{
  pointer-events:auto;width:40px;height:40px;min-width:40px;min-height:40px;padding:0;
  border:0;border-radius:12px;background:#0f172a !important;color:#fff !important;
  display:grid;place-items:center;cursor:pointer;font:inherit;line-height:1;
  box-shadow:0 0 0 1px rgba(15,23,42,.12),0 4px 12px rgba(15,23,42,.18)}}
#kcw-shell-root button.kcw-shell-btn:hover,
#kcw-shell-root button.kcw-shell-btn:focus-visible{{
  background:#020617 !important;outline:2px solid #93c5fd;outline-offset:2px}}
#kcw-shell-root button.kcw-shell-btn svg{{width:20px;height:20px;display:block}}
#kcwShellSlot{{display:inline-flex;align-items:center;flex:0 0 auto}}
#kcwShellSlot button.kcw-shell-btn{{
  background:rgba(255,255,255,.18) !important;color:#fff !important;
  box-shadow:inset 0 0 0 1px rgba(255,255,255,.85),0 4px 12px rgba(0,0,0,.18)}}
#kcwShellSlot button.kcw-shell-btn:hover,
#kcwShellSlot button.kcw-shell-btn:focus-visible{{
  background:rgba(255,255,255,.28) !important}}
.kcw-shell-backdrop{{pointer-events:auto;position:fixed;inset:0;background:rgba(15,23,42,.35);
  opacity:0;visibility:hidden;transition:opacity .15s ease;z-index:10050}}
.kcw-shell-backdrop.open{{opacity:1;visibility:visible}}
.kcw-shell-panel{{pointer-events:auto;position:fixed;top:calc(var(--kcw-shell-h,56px) + 8px);
  right:max(10px,env(safe-area-inset-right));width:min(320px,calc(100vw - 20px));
  background:#fff;color:#0f172a;border-radius:16px;box-shadow:0 18px 50px rgba(15,23,42,.28);
  transform:translateY(-6px) scale(.98);opacity:0;visibility:hidden;z-index:10055;
  transition:opacity .15s ease,transform .15s ease;overflow:hidden}}
.kcw-shell-panel.open{{opacity:1;visibility:visible;transform:none}}
.kcw-shell-panel-hd{{display:flex;align-items:center;justify-content:space-between;gap:8px;
  padding:12px 14px;border-bottom:1px solid #e2e8f0}}
.kcw-shell-panel-hd strong{{font-size:14px}}
.kcw-shell-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;padding:12px}}
.kcw-shell-tile{{appearance:none;border:1px solid #e2e8f0;background:#f8fafc;border-radius:12px;
  padding:12px 8px;min-height:84px;display:flex;flex-direction:column;align-items:center;
  justify-content:center;gap:6px;cursor:pointer;font:inherit;color:inherit}}
.kcw-shell-tile:hover{{border-color:#93c5fd;background:#eff6ff}}
.kcw-shell-tile.current{{border-color:#2563eb;background:#dbeafe;box-shadow:inset 0 0 0 1px #2563eb}}
.kcw-shell-tile .ico{{width:28px;height:28px;border-radius:8px;background:#1e293b;color:#fff;
  display:grid;place-items:center;font-size:12px;font-weight:700}}
.kcw-shell-tile .lbl{{font-size:12px;font-weight:600;text-align:center;line-height:1.25}}
.kcw-shell-foot{{display:flex;gap:8px;padding:0 12px 12px}}
#kcw-shell-root .kcw-shell-foot button{{flex:1;min-height:40px;border-radius:10px;border:1px solid #e2e8f0;
  background:#fff !important;color:#0f172a !important;font:inherit;font-weight:600;cursor:pointer}}
#kcw-shell-root .kcw-shell-foot button.logout{{border-color:#fecaca;color:#b91c1c !important;background:#fef2f2 !important}}
.kcw-shell-idle{{pointer-events:auto;position:fixed;inset:0;z-index:10060;background:rgba(15,23,42,.55);
  display:none;place-items:center;padding:16px}}
.kcw-shell-idle.open{{display:grid}}
.kcw-shell-idle-card{{background:#fff;border-radius:16px;padding:18px;max-width:360px;width:100%;
  box-shadow:0 18px 50px rgba(15,23,42,.35)}}
.kcw-shell-idle-card h2{{margin:0 0 8px;font-size:16px}}
.kcw-shell-idle-card p{{margin:0 0 14px;font-size:13px;color:#475569;line-height:1.45}}
.kcw-shell-idle-card .row{{display:flex;gap:8px}}
#kcw-shell-root .kcw-shell-idle-card button{{flex:1;min-height:40px;border-radius:10px;border:0;font:inherit;font-weight:600;cursor:pointer}}
#kcw-shell-root .kcw-shell-idle-card .stay{{background:#1d4ed8 !important;color:#fff !important}}
#kcw-shell-root .kcw-shell-idle-card .out{{background:#fee2e2 !important;color:#991b1b !important}}
</style>
<div id="kcw-shell-root" data-kcw-shell="1" aria-live="polite">
  <div class="kcw-shell-bar">
    <div class="kcw-shell-who" title="ผู้ใช้ที่เข้าสู่ระบบ">
      <span class="kcw-shell-name">{who}</span>
      {branch_chip}
    </div>
    <button type="button" class="kcw-shell-btn" id="kcwShellMenuBtn" aria-label="เมนูบริการ" aria-haspopup="dialog" aria-expanded="false">
      <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="5" cy="5" r="2" fill="currentColor"/><circle cx="12" cy="5" r="2" fill="currentColor"/><circle cx="19" cy="5" r="2" fill="currentColor"/><circle cx="5" cy="12" r="2" fill="currentColor"/><circle cx="12" cy="12" r="2" fill="currentColor"/><circle cx="19" cy="12" r="2" fill="currentColor"/><circle cx="5" cy="19" r="2" fill="currentColor"/><circle cx="12" cy="19" r="2" fill="currentColor"/><circle cx="19" cy="19" r="2" fill="currentColor"/></svg>
    </button>
  </div>
  <div class="kcw-shell-backdrop" id="kcwShellBackdrop" hidden></div>
  <div class="kcw-shell-panel" id="kcwShellPanel" role="dialog" aria-label="เมนูบริการ" hidden>
    <div class="kcw-shell-panel-hd">
      <strong>บริการ</strong>
      <span style="font-size:12px;color:#64748b" id="kcwShellSiteLabel"></span>
    </div>
    <div class="kcw-shell-grid" id="kcwShellGrid"></div>
    <div class="kcw-shell-foot">
      <button type="button" id="kcwShellClose">ปิด</button>
      <button type="button" class="logout" id="kcwShellLogout">ออกจากระบบ</button>
    </div>
  </div>
  <div class="kcw-shell-idle" id="kcwShellIdle" role="alertdialog" aria-label="หมดเวลา">
    <div class="kcw-shell-idle-card">
      <h2>ใกล้หมดเวลาใช้งาน</h2>
      <p>ไม่มีการใช้งานสักครู่แล้ว จะออกจากระบบอัตโนมัติเพื่อความปลอดภัย</p>
      <div class="row">
        <button type="button" class="stay" id="kcwShellStay">ใช้งานต่อ</button>
        <button type="button" class="out" id="kcwShellIdleOut">ออกจากระบบ</button>
      </div>
    </div>
  </div>
</div>
<script>
(function(){{
  if (window.kcwShell && window.kcwShell.__booted) return;
  const CFG = {cfg_json};
  const api = (CFG.apiBase || "").replace(/\\/$/, "");
  const state = {{ open:false, services:[], dirty:false }};

  function isDirty(){{
    if (typeof window.__kcwUnsaved === "boolean") return window.__kcwUnsaved;
    if (window.kcwShell && typeof window.kcwShell._dirty === "boolean") return window.kcwShell._dirty;
    return false;
  }}
  function confirmLeave(msg){{
    if (!isDirty()) return true;
    return window.confirm(msg || "มีงานที่ยังไม่ได้บันทึก ต้องการออกจากหน้านี้หรือไม่?");
  }}

  async function apiFetch(path, opts){{
    const r = await fetch(api + path, Object.assign({{ credentials:"same-origin" }}, opts||{{}}));
    let data = null;
    try {{ data = await r.json(); }} catch (e) {{ data = null; }}
    if (!r.ok) {{
      const msg = (data && (data.message || data.error)) || ("HTTP " + r.status);
      throw new Error(msg);
    }}
    return data;
  }}

  const root = document.getElementById("kcw-shell-root");
  const btn = document.getElementById("kcwShellMenuBtn");
  const panel = document.getElementById("kcwShellPanel");
  const backdrop = document.getElementById("kcwShellBackdrop");
  const grid = document.getElementById("kcwShellGrid");
  const siteLabel = document.getElementById("kcwShellSiteLabel");
  const idle = document.getElementById("kcwShellIdle");
  const bar = root ? root.querySelector(".kcw-shell-bar") : null;
  // Pages with a colored sticky header can host the 9-dot in #kcwShellSlot
  // so it is not lost under/against the header paint.
  const slot = document.getElementById("kcwShellSlot");
  let rooted = false;
  if (slot && btn && bar) {{
    slot.appendChild(btn);
    bar.style.display = "none";
    if (root) root.classList.add("kcw-shell-rooted");
    rooted = true;
  }}

  // Reserve a dedicated top strip so the launcher never covers host controls.
  function syncShellPad(){{
    if (rooted || !bar) {{
      document.documentElement.classList.remove("kcw-shell-pad");
      document.documentElement.style.removeProperty("--kcw-shell-h");
      return;
    }}
    const h = Math.ceil(bar.getBoundingClientRect().height || bar.offsetHeight || 56);
    document.documentElement.style.setProperty("--kcw-shell-h", h + "px");
    document.documentElement.classList.add("kcw-shell-pad");
  }}
  syncShellPad();
  window.addEventListener("resize", syncShellPad, {{ passive:true }});
  if (window.visualViewport) {{
    window.visualViewport.addEventListener("resize", syncShellPad, {{ passive:true }});
  }}

  function setOpen(v){{
    state.open = !!v;
    btn.setAttribute("aria-expanded", state.open ? "true" : "false");
    panel.hidden = !state.open;
    backdrop.hidden = !state.open;
    panel.classList.toggle("open", state.open);
    backdrop.classList.toggle("open", state.open);
  }}

  function iconGlyph(icon){{
    const map = {{ stock:"SC", pay:"TP", search:"P9", transfer:"TF", po:"PO", receive:"RC", sale:"OL", notes:"AP", ar:"AR", app:"•" }};
    return map[icon] || map.app;
  }}

  function renderGrid(services){{
    grid.innerHTML = "";
    (services || []).forEach(function(svc){{
      const b = document.createElement("button");
      b.type = "button";
      b.className = "kcw-shell-tile" + (svc.current ? " current" : "");
      b.dataset.id = svc.id;
      b.innerHTML = '<span class="ico">' + iconGlyph(svc.icon) + '</span><span class="lbl"></span>';
      b.querySelector(".lbl").textContent = svc.label;
      if (svc.current) b.setAttribute("aria-current", "page");
      b.addEventListener("click", function(){{ switchTo(svc.id, !!svc.current); }});
      grid.appendChild(b);
    }});
  }}

  async function loadServices(){{
    const data = await apiFetch("/services");
    state.services = data.services || [];
    if (siteLabel) siteLabel.textContent = data.site || "";
    renderGrid(state.services);
  }}

  async function switchTo(id, same){{
    if (same) {{ setOpen(false); return; }}
    if (!confirmLeave("มีงานที่ยังไม่ได้บันทึก ต้องการเปลี่ยนบริการหรือไม่?")) return;
    try {{
      const data = await apiFetch("/switch", {{
        method:"POST",
        headers:{{"Content-Type":"application/json"}},
        body: JSON.stringify({{ service_id: id }})
      }});
      setOpen(false);
      if (data && data.url) window.location.href = data.url;
    }} catch (e) {{
      alert("เปลี่ยนบริการไม่สำเร็จ: " + (e && e.message ? e.message : e));
    }}
  }}

  const RETURN_KEY = "kcw_return_path";
  function rememberReturn(){{
    try {{
      sessionStorage.setItem(RETURN_KEY, location.pathname + location.search + location.hash);
    }} catch (e) {{ /* private mode */ }}
  }}
  function consumeReturn(){{
    try {{
      const v = sessionStorage.getItem(RETURN_KEY);
      if (!v || v.charAt(0) !== "/" || v.indexOf("//") === 0) return;
      sessionStorage.removeItem(RETURN_KEY);
      const here = location.pathname + location.search + location.hash;
      if (v === here) return;
      const base = (CFG.apiBase || "").replace(/\\/_shell\\/?$/, "");
      if (base && !(v === base || v.indexOf(base + "/") === 0)) return;
      window.location.replace(v);
    }} catch (e) {{ /* ignore */ }}
  }}

  async function doLogout(){{
    if (!confirmLeave("มีงานที่ยังไม่ได้บันทึก ต้องการออกจากระบบหรือไม่?")) return;
    rememberReturn();
    try {{
      await apiFetch("/logout", {{ method:"POST" }});
    }} catch (e) {{ /* still leave */ }}
    setOpen(false);
    document.body.innerHTML = "<main style='font-family:system-ui;padding:24px'><h1>ออกจากระบบแล้ว</h1><p>พิมพ์ชื่อบริการใน LINE แล้วเปิดลิงก์เดิมได้ — ระบบจะพากลับหน้าที่ค้างไว้ให้</p><p style='color:#64748b;font-size:13px'>ลิงก์จาก LINE ใช้ซ้ำได้จนกว่าจะออกจากระบบครบรอบ session</p></main>";
  }}
  consumeReturn();

  btn.addEventListener("click", async function(){{
    if (state.open) {{ setOpen(false); return; }}
    try {{
      await loadServices();
      setOpen(true);
    }} catch (e) {{
      alert("โหลดเมนูไม่สำเร็จ: " + (e && e.message ? e.message : e));
    }}
  }});
  backdrop.addEventListener("click", function(){{ setOpen(false); }});
  document.getElementById("kcwShellClose").addEventListener("click", function(){{ setOpen(false); }});
  document.getElementById("kcwShellLogout").addEventListener("click", doLogout);
  document.addEventListener("keydown", function(ev){{
    if (ev.key === "Escape") {{
      setOpen(false);
      idle.classList.remove("open");
    }}
  }});

  // Idle timeout
  let last = Date.now();
  let warnTimer = null;
  let logoutTimer = null;
  function bump(){{ last = Date.now(); }}
  ["pointerdown","keydown","touchstart","scroll","mousemove"].forEach(function(ev){{
    window.addEventListener(ev, bump, {{ passive:true, capture:true }});
  }});
  function armIdle(){{
    clearTimeout(warnTimer);
    clearTimeout(logoutTimer);
    const remain = Math.max(0, (CFG.idleMs || 0) - (Date.now() - last));
    warnTimer = setTimeout(function(){{
      idle.classList.add("open");
      logoutTimer = setTimeout(function(){{ doLogout(); }}, CFG.warnMs || 60000);
    }}, remain);
  }}
  document.getElementById("kcwShellStay").addEventListener("click", function(){{
    idle.classList.remove("open");
    bump();
    armIdle();
  }});
  document.getElementById("kcwShellIdleOut").addEventListener("click", doLogout);
  setInterval(function(){{
    if (Date.now() - last >= (CFG.idleMs || 0) && !idle.classList.contains("open")) armIdle();
  }}, 15000);
  armIdle();

  window.kcwShell = {{
    __booted: true,
    _dirty: false,
    isDirty: isDirty,
    setDirty: function(v){{ state.dirty = !!v; window.__kcwUnsaved = !!v; window.kcwShell._dirty = !!v; }},
    open: function(){{ btn.click(); }},
    close: function(){{ setOpen(false); }},
    logout: doLogout
  }};
}})();
</script>
"""


def inject_shell(
    html: str,
    *,
    service_id: str,
    api_base: str,
    user_name: str = "",
    branch: str = "",
) -> str:
    """Insert shell chrome before ``</body>`` (or append)."""
    if 'data-kcw-shell="1"' in html:
        return html
    snippet = render_shell_html(
        service_id=service_id,
        api_base=api_base,
        user_name=user_name,
        branch=branch,
    )
    lower = html.lower()
    idx = lower.rfind("</body>")
    if idx >= 0:
        return html[:idx] + snippet + html[idx:]
    return html + snippet

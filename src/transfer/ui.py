from __future__ import annotations

import html as html_lib
import json
import re

APP = "kcw-transfer"
SESSION_COOKIE = "kcw_transfer"


def initials(name: str) -> str:
    who = (name or "operator").strip()
    if not who:
        return "OP"
    parts = [p for p in re.split(r"\s+", who) if p]
    if len(parts) >= 2 and parts[0][0].isascii() and parts[1][0].isascii():
        return (parts[0][0] + parts[1][0]).upper()
    if who[0].isascii():
        return who[:2].upper()
    return who[:2]


def page(
    *,
    user_name: str = "",
    site: str = "HQ",
    hq_write_enabled: bool = False,
    syp_write_enabled: bool = False,
) -> str:
    who = (user_name or "operator").strip()
    site_u = (site or "HQ").upper()
    is_syp = site_u == "SYP"
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace("__IS_SYP__", "true" if is_syp else "false")
        .replace('__HQ_WRITE__ === "true"', "true" if hq_write_enabled else "false")
        .replace('__SYP_WRITE__ === "true"', "true" if syp_write_enabled else "false")
        .replace("__INITIALS__", html_lib.escape(initials(who)))
    )


_HTML = r"""<!doctype html>
<html lang="th" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light dark"/>
<meta name="theme-color" content="#f3f5f9" id="themeColor"/>
<title>โอนสินค้า · __SITE__</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--acc:#2f6bff;--ok:#15803d;--warn:#c2410c;--down:#dc2626;--card:#fff;--line:#e5e9f2;--text:#111827;--muted:#6b7280;--shadow:0 1px 2px rgba(16,24,40,.06),0 4px 12px rgba(16,24,40,.04)}
*{box-sizing:border-box}body{margin:0;font-family:Prompt,sans-serif;background:#f3f5f9;color:var(--text)}
.hdr{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);padding:.85rem 1rem;box-shadow:var(--shadow)}
.hdr h1{margin:0;font-size:1.15rem}.hdr .sub{font-size:.8rem;color:var(--muted)}
.tabs{display:flex;gap:.35rem;overflow:auto;padding:.65rem 1rem;background:#fff;border-bottom:1px solid var(--line)}
.tab{border:1px solid var(--line);background:#fff;border-radius:999px;padding:.45rem .85rem;font-size:.82rem;white-space:nowrap;cursor:pointer}
.tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.panel{display:none;padding:1rem;max-width:1120px;margin:0 auto}
.panel.on{display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem;box-shadow:var(--shadow);margin-bottom:.85rem}
.table-wrap{overflow:auto;border:1px solid var(--line;border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th,td{padding:.55rem .65rem;border-bottom:1px solid var(--line);text-align:left}
th{background:#f8fafc;position:sticky;top:0}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.72rem;font-weight:600}
.b-requested{background:#e8f0ff;color:#1d4ed8}.b-await{background:#ffedd5;color:#c2410c}.b-done{background:#dcfce7;color:#15803d}
.btn{border:0;border-radius:10px;padding:.55rem 1rem;font-family:inherit;font-weight:600;cursor:pointer}
.btn-primary{background:var(--acc);color:#fff}.btn-ghost{background:#fff;border:1px solid var(--line)}
.row-actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.75rem}
.empty{color:var(--muted);text-align:center;padding:2rem 1rem}
#busy{position:fixed;inset:0;background:rgba(255,255,255,.75);display:none;align-items:center;justify-content:center;z-index:50;font-weight:600}
body.busy #busy{display:flex}
@media(max-width:640px){.t-full{display:none}.t-short{display:inline}}
@media(min-width:641px){.t-short{display:none}}
</style>
</head>
<body>
<div id="busy">กำลังดำเนินการ…</div>
<header class="hdr">
  <h1>โอนสินค้า · __SITE__</h1>
  <div class="sub">__USER__ · เลือกสินค้า → HQ จัดแล้ว → รับแล้ว</div>
</header>
<nav class="tabs" id="tabs"></nav>
<main>
  <section class="panel on" id="panelMain"><div class="card"><div id="content" class="empty">กำลังโหลด…</div></div></section>
</main>
<script>
const SITE = "__SITE__";
const IS_SYP = __IS_SYP__;
const HQ_WRITE = __HQ_WRITE__ === "true";
const SYP_WRITE = __SYP_WRITE__ === "true";
const USER = __USER_JSON__;
const SYP_TABS = [
  {id:"suggest", label:"แนะนำโอน", short:"แนะนำ"},
  {id:"draft", label:"ขอโอน", short:"ขอโอน"},
  {id:"requested", label:"รอ HQ จัด", short:"รอจัด"},
  {id:"awaiting", label:"รอรับ", short:"รอรับ"},
  {id:"history", label:"ประวัติ", short:"ประวัติ"},
];
const HQ_TABS = [
  {id:"pick", label:"รอจัด", short:"รอจัด"},
  {id:"transit", label:"กำลังส่ง", short:"ส่ง"},
  {id:"history", label:"ประวัติ", short:"ประวัติ"},
];
let activeTab = IS_SYP ? "suggest" : "pick";
let currentTransfer = null;

function $(id){return document.getElementById(id)}
function fmtQty(n){return Number(n||0).toLocaleString("th-TH",{maximumFractionDigits:2})}
function badge(status){
  const m={draft:"b-requested",requested:"b-requested",partial_prepared:"b-await",awaiting_receive:"b-await",partial_received:"b-await",complete:"b-done"};
  const t={draft:"ร่าง",requested:"รอ HQ จัด",partial_prepared:"จัดบางส่วน",awaiting_receive:"รอรับ",partial_received:"รับบางส่วน",complete:"เสร็จสิ้น"};
  return `<span class="badge ${m[status]||"b-requested"}">${t[status]||status||"-"}</span>`;
}
function setBusy(on){document.body.classList.toggle("busy",!!on)}
async function api(path, opts){
  setBusy(true);
  try{
    const r = await fetch(path, Object.assign({headers:{"Content-Type":"application/json"}}, opts||{}));
    const j = await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(j.error||j.detail||("HTTP "+r.status));
    return j;
  } finally { setBusy(false); }
}
function renderTabs(){
  const tabs = IS_SYP ? SYP_TABS : HQ_TABS;
  $("tabs").innerHTML = tabs.map(t=>`<button class="tab ${t.id===activeTab?"on":""}" data-tab="${t.id}"><span class="t-full">${t.label}</span><span class="t-short">${t.short}</span></button>`).join("");
  $("tabs").querySelectorAll(".tab").forEach(btn=>btn.onclick=()=>{activeTab=btn.dataset.tab; renderTabs(); loadPanel();});
}
async function loadPanel(){
  const el = $("content");
  try{
    if(IS_SYP && activeTab==="suggest"){
      const rows = await api("/transfer/api/suggest");
      if(!rows.items||!rows.items.length){el.innerHTML="ไม่พบสินค้าแนะนำโอน";return;}
      el.innerHTML = `<div class="table-wrap"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>คงเหลือ</th><th>แนะนำ</th><th></th></tr></thead><tbody>`+
        rows.items.map(r=>`<tr><td><code>${r.bcode}</code></td><td>${r.descr||""}</td><td>${fmtQty(r.qtyoh2)}</td><td>${fmtQty(r.suggest_qty)}</td><td><button class="btn btn-ghost" data-add="${r.bcode}" data-qty="${r.suggest_qty}">เพิ่ม</button></td></tr>`).join("")+
        `</tbody></table></div>`;
      el.querySelectorAll("[data-add]").forEach(b=>b.onclick=async()=>{
        await api("/transfer/api/need-list",{method:"POST",body:JSON.stringify({bcode:b.dataset.add,qty:Number(b.dataset.qty),descr:""})});
        alert("เพิ่มในรายการต้องการแล้ว");
      });
      return;
    }
    const statusMap = IS_SYP ? {draft:"draft",requested:"requested",awaiting:"awaiting_receive",history:"complete"} : {pick:"requested",transit:"awaiting_receive",history:"complete"};
    const st = statusMap[activeTab];
    
    if(IS_SYP && activeTab==="requested"){
      // Special view for SYP waiting requests 
      const data = await api("/transfer/api/requests?status=requested");
      const items = data.items||[];
      if(!items.length){el.innerHTML='<div class="empty">ไม่มีรายการ</div>';return;}
      
      let html = `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>สถานะ</th><th>วันที่</th><th>รายการ</th><th></th></tr></thead><tbody>`;
      for(const r of items){
        const lines = await api("/transfer/api/requests/"+r.transfer_id+"/lines");
        html += `<tr><td><code>${r.short_id}</code></td><td>${badge(r.status)}</td><td>${(r.requested_at||r.created_at||"").slice(0,10)}</td><td>${r.line_count||0} รายการ</td>`;
        html += `<td><button class="btn btn-primary" data-action="prepare" data-id="${r.transfer_id}">จัดแล้ว</button></td></tr>`;
      }
      html += `</tbody></table></div>`;
      el.innerHTML = html;
      el.querySelectorAll("[data-action='prepare']").forEach(btn=>btn.onclick=async()=>{
        const transferId = btn.dataset.id;
        try {
          if (!confirm("ยืนยันว่า จัดสินค้าแล้ว?")) return;
          alert("กำลังจัดสินค้า โปรดรอ..."); // Placeholder
          // This would be handled by JS when implementing in a real implementation  
        } catch(e) {
          alert('Error: ' + e.message);
        }
      });
      return;
    }
    
    if(IS_SYP && activeTab==="awaiting"){
      // Special view for SYP awaiting receive 
      const data = await api("/transfer/api/requests?status=awaiting_receive");
      const items = data.items||[];
      if(!items.length){el.innerHTML='<div class="empty">ไม่มีรายการ</div>';return;}
      
      let html = `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>สถานะ</th><th>วันที่</th><th>รายการ</th><th></th></tr></thead><tbody>`;
      for(const r of items){
        html += `<tr><td><code>${r.short_id}</code></td><td>${badge(r.status)}</td><td>${(r.requested_at||r.created_at||"").slice(0,10)}</td><td>${r.line_count||0} รายการ</td>`;
        html += `<td><button class="btn btn-primary" data-action="receive" data-id="${r.transfer_id}">รับแล้ว</button></td></tr>`;
      }
      html += `</tbody></table></div>`;
      el.innerHTML = html;
      el.querySelectorAll("[data-action='receive']").forEach(btn=>btn.onclick=async()=>{
        const transferId = btn.dataset.id;
        try {
          if (!confirm("ยืนยันว่า รับสินค้าแล้ว?")) return;
          alert("กำลังรับสินค้า โปรดรอ..."); // Placeholder
          // This would be handled by JS when implementing in a real implementation  
        } catch(e) {
          alert('Error: ' + e.message);
        }
      });
      return;
    }
    
    if(!IS_SYP && activeTab==="pick"){
      // Special view for HQ waiting preparation 
      const data = await api("/transfer/api/requests?status=requested");
      const items = data.items||[];
      if(!items.length){el.innerHTML='<div class="empty">ไม่มีรายการ</div>';return;}
      
      let html = `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>สถานะ</th><th>วันที่</th><th>รายการ</th><th></th></tr></thead><tbody>`;
      for(const r of items){
        const lines = await api("/transfer/api/requests/"+r.transfer_id+"/lines");
        html += `<tr><td><code>${r.short_id}</code></td><td>${badge(r.status)}</td><td>${(r.requested_at||r.created_at||"").slice(0,10)}</td><td>${r.line_count||0} รายการ</td>`;
        html += `<td><button class="btn btn-primary" data-action="prepare" data-id="${r.transfer_id}">จัดแล้ว</button></td></tr>`;
      }
      html += `</tbody></table></div>`;
      el.innerHTML = html;
      el.querySelectorAll("[data-action='prepare']").forEach(btn=>btn.onclick=async()=>{
        const transferId = btn.dataset.id;
        try {
          if (!confirm("ยืนยันว่า จัดสินค้าแล้ว?")) return;
          alert("กรุณาระบุจำนวนที่จะจัด"); // Placeholder - this should be interactive with line items
        } catch(e) {
          alert('Error: ' + e.message);
        }
      });
      return;
    }
   
    const data = await api("/transfer/api/requests"+(st?("?status="+encodeURIComponent(st)):""));
    const items = data.items||[];
    if(!items.length){el.innerHTML='<div class="empty">ไม่มีรายการ</div>';return;}
    el.innerHTML = `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>สถานะ</th><th>วันที่</th><th>รายการ</th></tr></thead><tbody>`+
      items.map(r=>`<tr><td><code>${r.short_id}</code></td><td>${badge(r.status)}</td><td>${(r.requested_at||r.created_at||"").slice(0,10)}</td><td>${r.line_count||0} รายการ</td></tr>`).join("")+
      `</tbody></table></div>`;
  }catch(e){el.innerHTML='<div class="empty">'+String(e.message||e)+'</div>';}
}
renderTabs();
loadPanel();
</script>
</body>
</html>"""
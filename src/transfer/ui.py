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
    hq_ship_enabled: bool = False,
    syp_ship_enabled: bool = False,
    hq_receive_enabled: bool = False,
    syp_receive_enabled: bool = False,
) -> str:
    who = (user_name or "operator").strip()
    site_u = (site or "HQ").upper()
    ship_on = syp_ship_enabled if site_u == "SYP" else hq_ship_enabled
    recv_on = syp_receive_enabled if site_u == "SYP" else hq_receive_enabled
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace('__SHIP_WRITE__ === "true"', "true" if ship_on else "false")
        .replace('__RECV_WRITE__ === "true"', "true" if recv_on else "false")
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
.tab{border:1px solid var(--line);background:#fff;color:var(--text);border-radius:999px;padding:.45rem .85rem;font-size:.82rem;white-space:nowrap;cursor:pointer;font-family:inherit}
.tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.panel{display:none;padding:1rem;max-width:1120px;margin:0 auto}
.panel.on{display:block}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem;box-shadow:var(--shadow);margin-bottom:.85rem}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px}
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
.dir{font-size:.75rem;color:var(--muted)}
.qty-input{width:5rem;padding:.35rem .5rem;border:1px solid var(--line);border-radius:8px;font-family:inherit}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:center;justify-content:center;z-index:60;padding:1rem}
.modal-backdrop.on{display:flex}
.modal{background:#fff;border-radius:14px;max-width:640px;width:100%;max-height:90vh;overflow:auto;padding:1rem;box-shadow:var(--shadow)}
.modal h2{margin:0 0 .75rem;font-size:1rem}
@media(max-width:640px){.t-full{display:none}.t-short{display:inline}}
@media(min-width:641px){.t-short{display:none}}
</style>
</head>
<body>
<div id="busy">กำลังดำเนินการ…</div>
<div id="modalBackdrop" class="modal-backdrop"><div class="modal" id="modalBox"></div></div>
<header class="hdr">
  <h1>โอนสินค้า · __SITE__</h1>
  <div class="sub">__USER__ · ขอโอน → จัดออก → รับเข้า (HQ ↔ SYP)</div>
</header>
<nav class="tabs" id="tabs"></nav>
<main>
  <section class="panel on" id="panelMain"><div class="card"><div id="content" class="empty">กำลังโหลด…</div></div></section>
</main>
<script>
const SITE = "__SITE__";
const SHIP_WRITE = __SHIP_WRITE__ === "true";
const RECV_WRITE = __RECV_WRITE__ === "true";
const USER = __USER_JSON__;
const TABS = [
  {id:"suggest", label:"แนะนำโอน", short:"แนะนำ"},
  {id:"draft", label:"ขอโอน", short:"ขอโอน"},
  {id:"prepare", label:"รอจัด (ออก)", short:"รอจัด"},
  {id:"receive", label:"รอรับ (เข้า)", short:"รอรับ"},
  {id:"history", label:"ประวัติ", short:"ประวัติ"},
];
let activeTab = "suggest";
let draftLines = [];
let draftDirection = "to_syp";

function $(id){return document.getElementById(id)}
function fmtQty(n){return Number(n||0).toLocaleString("th-TH",{maximumFractionDigits:2})}
function uuid(){return crypto.randomUUID ? crypto.randomUUID() : String(Date.now())+"-"+Math.random().toString(16).slice(2)}
function dirLabel(fromB, toB){return (fromB||"?")+" → "+(toB||"?")}
function badge(status, fromB, toB){
  const m={draft:"b-requested",requested:"b-requested",partial_prepared:"b-await",awaiting_receive:"b-await",partial_received:"b-await",complete:"b-done",cancelled:"b-requested"};
  const fb = fromB||"HQ";
  const t={draft:"ร่าง",requested:"รอ "+fb+" จัด",partial_prepared:"จัดบางส่วน",awaiting_receive:"รอรับ",partial_received:"รับบางส่วน",complete:"เสร็จสิ้น",cancelled:"ยกเลิก"};
  return `<span class="badge ${m[status]||"b-requested"}">${t[status]||status||"-"}</span>`;
}
function setBusy(on){document.body.classList.toggle("busy",!!on)}
function showModal(html, onClose){
  const box = $("modalBox");
  box.innerHTML = html;
  $("modalBackdrop").classList.add("on");
  const close = ()=>{$("modalBackdrop").classList.remove("on"); box.innerHTML="";};
  $("modalBackdrop").onclick = e=>{if(e.target===$("modalBackdrop")) close();};
  box.querySelectorAll("[data-close]").forEach(b=>b.onclick=close);
  if(onClose) box._onClose = onClose;
  return {close, box};
}
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
  $("tabs").innerHTML = TABS.map(t=>`<button class="tab ${t.id===activeTab?"on":""}" data-tab="${t.id}"><span class="t-full">${t.label}</span><span class="t-short">${t.short}</span></button>`).join("");
  $("tabs").querySelectorAll(".tab").forEach(btn=>btn.onclick=()=>{activeTab=btn.dataset.tab; renderTabs(); loadPanel();});
}

async function openPrepareDialog(transferId){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  const lines = detail.lines||[];
  const pending = lines.filter(l=>{
    const req = Number(l.qty_requested||0);
    const prep = Number(l.qty_prepared||0);
    return req > prep;
  });
  if(!pending.length){alert("ไม่มีรายการที่ต้องจัด");return;}
  const rows = pending.map(l=>{
    const remain = Number(l.qty_requested||0)-Number(l.qty_prepared||0);
    return `<tr data-line="${l.line_id}"><td><code>${l.bcode}</code></td><td>${l.descr||""}</td><td>${fmtQty(l.qty_requested)}</td><td>${fmtQty(l.qty_prepared)}</td><td><input class="qty-input" type="number" min="0" max="${remain}" step="1" value="${remain}" data-bcode="${l.bcode}" data-line="${l.line_id}"/></td></tr>`;
  }).join("");
  const modal = showModal(`<h2>จัดสินค้า · ${detail.short_id||transferId}</h2>
    <div class="dir">${dirLabel(detail.from_branch, detail.to_branch)}</div>
    <div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>ขอ</th><th>จัดแล้ว</th><th>จัดครั้งนี้</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="row-actions"><button class="btn btn-ghost" data-close>ยกเลิก</button><button class="btn btn-primary" id="btnDoPrepare">ยืนยันจัดแล้ว</button></div>`);
  modal.box.querySelector("#btnDoPrepare").onclick = async()=>{
    const shipLines = [];
    modal.box.querySelectorAll(".qty-input").forEach(inp=>{
      const q = Number(inp.value||0);
      if(q>0) shipLines.push({line_id: inp.dataset.line, bcode: inp.dataset.bcode, qty_ship: q});
    });
    if(!shipLines.length){alert("ระบุจำนวนที่จัด");return;}
    if(!SHIP_WRITE && !confirm("โหมดทดสอบ: writer ปิดอยู่ จะบันทึกใน Supabase เท่านั้น")) return;
    try{
      await api("/transfer/api/prepare",{method:"POST",body:JSON.stringify({transfer_id:transferId,client_token:uuid(),lines:shipLines})});
      modal.close();
      loadPanel();
    }catch(e){alert(e.message);}
  };
}

async function openReceiveDialog(transferId){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  const shipments = detail.shipments||[];
  const openShip = shipments.filter(s=>!s.posted_at);
  if(!openShip.length){alert("ไม่มี shipment ที่รอรับ");return;}
  const ship = openShip[0];
  const shipLines = (ship.lines||[]).filter(sl=>{
    const shipped = Number(sl.qty_shipped||0);
    const recv = Number(sl.qty_received||0);
    return shipped > recv;
  });
  if(!shipLines.length){alert("รับครบแล้ว");return;}
  const rows = shipLines.map(sl=>{
    const remain = Number(sl.qty_shipped||0)-Number(sl.qty_received||0);
    return `<tr><td><code>${sl.bcode}</code></td><td>${fmtQty(sl.qty_shipped)}</td><td>${fmtQty(sl.qty_received||0)}</td><td><input class="qty-input" type="number" min="0" max="${remain}" step="1" value="${remain}" data-bcode="${sl.bcode}"/></td></tr>`;
  }).join("");
  const modal = showModal(`<h2>รับสินค้า · ${detail.short_id||transferId}</h2>
    <div class="dir">${dirLabel(detail.from_branch, detail.to_branch)} · ใบจัด ${ship.ship_billno||ship.tf_billno||"-"}</div>
    <div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>จัด</th><th>รับแล้ว</th><th>รับครั้งนี้</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="row-actions"><button class="btn btn-ghost" data-close>ยกเลิก</button><button class="btn btn-primary" id="btnDoReceive">ยืนยันรับแล้ว</button></div>`);
  modal.box.querySelector("#btnDoReceive").onclick = async()=>{
    const recvLines = [];
    modal.box.querySelectorAll(".qty-input").forEach(inp=>{
      const q = Number(inp.value||0);
      if(q>0) recvLines.push({bcode: inp.dataset.bcode, qty_receive: q});
    });
    if(!recvLines.length){alert("ระบุจำนวนที่รับ");return;}
    if(!RECV_WRITE && !confirm("โหมดทดสอบ: writer ปิดอยู่ จะบันทึกใน Supabase เท่านั้น")) return;
    try{
      await api("/transfer/api/receive",{method:"POST",body:JSON.stringify({transfer_id:transferId,shipment_id:ship.shipment_id,client_token:uuid(),lines:recvLines})});
      modal.close();
      loadPanel();
    }catch(e){alert(e.message);}
  };
}

async function renderDraftPanel(el){
  el.innerHTML = `<div class="card">
    <div style="margin-bottom:.75rem"><strong>ทิศทาง</strong>
      <div class="row-actions" style="margin-top:.5rem">
        <button class="btn ${draftDirection==="to_syp"?"btn-primary":"btn-ghost"}" data-dir="to_syp">ขอจาก HQ → SYP</button>
        <button class="btn ${draftDirection==="to_hq"?"btn-primary":"btn-ghost"}" data-dir="to_hq">ขอจาก SYP → HQ</button>
      </div>
    </div>
    <div class="row-actions">
      <input id="draftBcode" placeholder="รหัสสินค้า" style="flex:1;padding:.5rem;border:1px solid var(--line);border-radius:8px"/>
      <input id="draftQty" type="number" min="1" value="1" class="qty-input"/>
      <button class="btn btn-ghost" id="btnAddLine">เพิ่มบรรทัด</button>
    </div>
    <div id="draftTable" style="margin-top:.75rem"></div>
    <div class="row-actions"><button class="btn btn-primary" id="btnSubmitDraft">ส่งคำขอ</button></div>
  </div>`;
  el.querySelectorAll("[data-dir]").forEach(b=>b.onclick=()=>{draftDirection=b.dataset.dir; renderDraftPanel(el);});
  function renderLines(){
    const tbl = el.querySelector("#draftTable");
    if(!draftLines.length){tbl.innerHTML='<div class="empty">ยังไม่มีรายการ</div>';return;}
    tbl.innerHTML = `<div class="table-wrap"><table><thead><tr><th>รหัส</th><th>จำนวน</th><th></th></tr></thead><tbody>`+
      draftLines.map((l,i)=>`<tr><td><code>${l.bcode}</code></td><td>${fmtQty(l.qty)}</td><td><button class="btn btn-ghost" data-rm="${i}">ลบ</button></td></tr>`).join("")+
      `</tbody></table></div>`;
    tbl.querySelectorAll("[data-rm]").forEach(b=>b.onclick=()=>{draftLines.splice(Number(b.dataset.rm),1); renderLines();});
  }
  renderLines();
  el.querySelector("#btnAddLine").onclick = ()=>{
    const b = el.querySelector("#draftBcode").value.trim();
    const q = Number(el.querySelector("#draftQty").value||0);
    if(!b||q<=0){alert("ระบุรหัสและจำนวน");return;}
    draftLines.push({bcode:b, qty:q});
    el.querySelector("#draftBcode").value="";
    renderLines();
  };
  el.querySelector("#btnSubmitDraft").onclick = async()=>{
    if(!draftLines.length){alert("เพิ่มรายการก่อน");return;}
    try{
      const d = await api("/transfer/api/requests/draft",{method:"POST",body:JSON.stringify({direction:draftDirection,lines:draftLines})});
      await api("/transfer/api/submit",{method:"POST",body:JSON.stringify({transfer_id:d.transfer_id})});
      draftLines = [];
      alert("ส่งคำขอแล้ว: "+(d.short_id||d.transfer_id));
      activeTab = "prepare";
      renderTabs();
      loadPanel();
    }catch(e){alert(e.message);}
  };
}

async function loadPanel(){
  const el = $("content");
  try{
    if(activeTab==="suggest"){
      const rows = await api("/transfer/api/suggest");
      if(!rows.items||!rows.items.length){el.innerHTML='<div class="empty">ไม่พบสินค้าแนะนำโอน</div>';return;}
      el.innerHTML = `<div class="table-wrap"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>คงเหลือ</th><th>แนะนำ</th><th></th></tr></thead><tbody>`+
        rows.items.map(r=>`<tr><td><code>${r.bcode}</code></td><td>${r.descr||""}</td><td>${fmtQty(r.qtyoh2)}</td><td>${fmtQty(r.suggest_qty)}</td><td><button class="btn btn-ghost" data-add="${r.bcode}" data-qty="${r.suggest_qty}">เพิ่ม</button></td></tr>`).join("")+
        `</tbody></table></div>`;
      el.querySelectorAll("[data-add]").forEach(b=>b.onclick=async()=>{
        await api("/transfer/api/need-list",{method:"POST",body:JSON.stringify({bcode:b.dataset.add,qty:Number(b.dataset.qty),descr:""})});
        alert("เพิ่มในรายการต้องการแล้ว");
      });
      return;
    }
    if(activeTab==="draft"){ await renderDraftPanel(el); return; }

  const roleMap = {prepare:"prepare", receive:"receive", history:"history"};
  if(activeTab==="prepare" || activeTab==="receive"){
    const data = await api("/transfer/api/requests?role="+activeTab);
    const items = data.items||[];
    if(!items.length){el.innerHTML='<div class="empty">ไม่มีรายการ</div>';return;}
    const action = activeTab==="prepare" ? "prepare" : "receive";
    const label = activeTab==="prepare" ? "จัดแล้ว" : "รับแล้ว";
    el.innerHTML = `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>สถานะ</th><th>วันที่</th><th>รายการ</th><th></th></tr></thead><tbody>`+
      items.map(r=>`<tr>
        <td><code>${r.short_id}</code></td>
        <td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td>
        <td>${badge(r.status,r.from_branch,r.to_branch)}</td>
        <td>${(r.requested_at||r.created_at||"").slice(0,10)}</td>
        <td>${r.line_count||0} รายการ</td>
        <td><button class="btn btn-primary" data-action="${action}" data-id="${r.transfer_id}">${label}</button></td>
      </tr>`).join("")+
      `</tbody></table></div>`;
    el.querySelectorAll("[data-action='prepare']").forEach(b=>b.onclick=()=>openPrepareDialog(b.dataset.id));
    el.querySelectorAll("[data-action='receive']").forEach(b=>b.onclick=()=>openReceiveDialog(b.dataset.id));
    return;
  }

  if(activeTab==="history"){
    const data = await api("/transfer/api/requests?status=complete");
    const items = data.items||[];
    if(!items.length){el.innerHTML='<div class="empty">ไม่มีรายการ</div>';return;}
    el.innerHTML = `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>สถานะ</th><th>วันที่</th><th>รายการ</th></tr></thead><tbody>`+
      items.map(r=>`<tr><td><code>${r.short_id}</code></td><td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td><td>${badge(r.status,r.from_branch,r.to_branch)}</td><td>${(r.requested_at||r.created_at||"").slice(0,10)}</td><td>${r.line_count||0} รายการ</td></tr>`).join("")+
      `</tbody></table></div>`;
    return;
  }
  }catch(e){el.innerHTML='<div class="empty">'+String(e.message||e)+'</div>';}
}
renderTabs();
loadPanel();
</script>
</body>
</html>"""

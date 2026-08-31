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
    other = "HQ" if site_u == "SYP" else "SYP"
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace("__OTHER__", other)
        .replace('__SHIP_WRITE__ === "true"', "true" if ship_on else "false")
        .replace('__RECV_WRITE__ === "true"', "true" if recv_on else "false")
        .replace("__INITIALS__", html_lib.escape(initials(who)))
    )


_HTML = r"""<!doctype html>
<html lang="th" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light"/>
<meta name="theme-color" content="#f3f5f9" id="themeColor"/>
<title>โอนสินค้า · __SITE__</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--acc:#2f6bff;--ok:#15803d;--warn:#c2410c;--down:#dc2626;--card:#fff;--line:#e5e9f2;--text:#111827;--muted:#6b7280;--shadow:0 1px 2px rgba(16,24,40,.06),0 4px 12px rgba(16,24,40,.04)}
*{box-sizing:border-box}body{margin:0;font-family:Prompt,sans-serif;background:#f3f5f9;color:var(--text)}
button{font:inherit;color:var(--text);-webkit-appearance:none;appearance:none}
.hdr{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);padding:.75rem 1rem;box-shadow:var(--shadow);display:flex;align-items:center;gap:.65rem}
.hdr-main{flex:1;min-width:0}
.hdr h1{margin:0;font-size:1.05rem;color:var(--text)}.hdr .sub{font-size:.78rem;color:var(--muted)}
.back-btn{border:1px solid var(--line);background:#fff;color:var(--text);border-radius:10px;padding:.4rem .7rem;font:inherit;cursor:pointer;white-space:nowrap}
main{padding:1rem;max-width:720px;margin:0 auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem;box-shadow:var(--shadow);margin-bottom:.85rem}
.table-wrap{overflow:auto;border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:.88rem}
th,td{padding:.55rem .65rem;border-bottom:1px solid var(--line);text-align:left}
th{background:#f8fafc;position:sticky;top:0}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.72rem;font-weight:600}
.b-requested{background:#e8f0ff;color:#1d4ed8}.b-await{background:#ffedd5;color:#c2410c}.b-done{background:#dcfce7;color:#15803d}
.btn{border:0;border-radius:10px;padding:.55rem 1rem;font-family:inherit;font-weight:600;cursor:pointer;color:var(--text)}
.btn-primary{background:var(--acc);color:#fff}.btn-ghost{background:#fff;border:1px solid var(--line);color:var(--text)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-block{width:100%;text-align:left}
.row-actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.75rem}
.empty{color:var(--muted);text-align:center;padding:2rem 1rem}
#busy{position:fixed;inset:0;background:rgba(255,255,255,.75);display:none;align-items:center;justify-content:center;z-index:50;font-weight:600}
body.busy #busy{display:flex}
.dir{font-size:.75rem;color:var(--muted)}
.qty-input{width:5rem;padding:.35rem .5rem;border:1px solid var(--line);border-radius:8px;font-family:inherit;color:var(--text);background:#fff;color-scheme:light}
.text-input{flex:1;min-width:0;padding:.5rem;border:1px solid var(--line);border-radius:8px;font-family:inherit;color:var(--text);background:#fff;color-scheme:light}
.search-bar{display:flex;gap:.5rem;align-items:center;margin-bottom:.75rem}
.search-bar .text-input{flex:1}
.tool-section{border:1px solid var(--line);border-radius:12px;padding:.75rem;background:#f8fafc;margin-bottom:.75rem}
.tool-section .tool-title{font-size:.82rem;font-weight:600;margin:0 0 .5rem;color:var(--text)}
.tool-row{display:flex;gap:.5rem;align-items:flex-end;flex-wrap:wrap}
.field{flex:1;min-width:7rem}
.field label{display:block;font-size:.72rem;color:var(--muted);margin-bottom:.25rem}
.field .qty-input,.field .text-input{width:100%}
.unit-select{padding:.35rem .5rem;border:1px solid var(--line);border-radius:8px;font-family:inherit;font-size:.82rem;color:var(--text);background:#fff;color-scheme:light}
.meta{font-size:.72rem;color:var(--muted);line-height:1.35}
.toast{position:fixed;bottom:1rem;left:50%;transform:translateX(-50%);background:#111827;color:#fff;padding:.55rem 1rem;border-radius:10px;font-size:.85rem;z-index:70;display:none;max-width:90vw;text-align:center}
.toast.on{display:block}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:center;justify-content:center;z-index:60;padding:1rem}
.modal-backdrop.on{display:flex}
.modal{background:#fff;border-radius:14px;max-width:640px;width:100%;max-height:90vh;overflow:auto;padding:1rem;box-shadow:var(--shadow)}
.modal h2{margin:0 0 .75rem;font-size:1rem}
.action-grid{display:grid;gap:.75rem}
.action-card{border:1px solid var(--line);border-radius:14px;padding:1rem;background:#fff;color:var(--text);cursor:pointer;text-align:left;transition:border-color .15s,box-shadow .15s;width:100%}
.action-card:hover,.action-card:focus{border-color:var(--acc);box-shadow:var(--shadow);outline:none}
.action-card .title{font-size:1rem;font-weight:700;margin:0 0 .25rem;color:var(--text)}
.action-card .desc{font-size:.82rem;color:var(--muted);margin:0;line-height:1.45}
.action-card .count{display:inline-block;margin-top:.55rem;font-size:.75rem;font-weight:600;color:var(--acc);background:#e8f0ff;padding:.2rem .55rem;border-radius:999px}
.flow-hint{font-size:.82rem;color:var(--muted);background:#f8fafc;border:1px dashed var(--line);border-radius:12px;padding:.75rem .85rem;margin-bottom:.85rem;line-height:1.5}
.info-toggle{margin:.75rem 0;border:1px solid #fde68a;border-radius:12px;background:#fffbeb;overflow:hidden}
.info-toggle summary{cursor:pointer;padding:.6rem .85rem;font-size:.82rem;font-weight:600;color:#92400e;list-style:none;display:flex;align-items:center;gap:.35rem;user-select:none}
.info-toggle summary::-webkit-details-marker{display:none}
.info-toggle summary::before{content:"▸";font-size:.7rem;transition:transform .15s;flex-shrink:0}
.info-toggle[open] summary::before{transform:rotate(90deg)}
.info-toggle .info-body{padding:.65rem .85rem .75rem;border-top:1px solid #fde68a;font-size:.82rem;color:var(--text);line-height:1.55}
.info-toggle .info-body strong{color:#92400e}
.bill-explain{font-size:.82rem;color:var(--text);background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:.75rem .85rem;margin:.75rem 0;line-height:1.55}
.bill-explain strong{color:#92400e}
.bill-steps{margin:.45rem 0 0;padding-left:1.15rem}
.bill-steps li{margin:.35rem 0}
.bill-when{font-weight:600}
.bill-none{color:var(--warn);font-weight:500}
.steps{display:flex;gap:.35rem;margin-bottom:1rem;flex-wrap:wrap}
.step{flex:1;min-width:5.5rem;text-align:center;padding:.45rem .35rem;border-radius:10px;font-size:.72rem;background:#fff;border:1px solid var(--line);color:var(--muted)}
.step.on{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:600}
.step.done{background:#dcfce7;color:var(--ok);border-color:#bbf7d0}
.step-label{display:block;font-size:.68rem;opacity:.9;margin-top:.15rem}
.row-clickable{cursor:pointer}
.row-clickable:hover td{background:#f8fafc}
.status-tabs{display:flex;gap:.35rem;margin-bottom:.75rem;flex-wrap:wrap}
.status-tab{border:1px solid var(--line);background:#fff;color:var(--text);border-radius:999px;padding:.4rem .75rem;font-size:.8rem;cursor:pointer;font-family:inherit}
.status-tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.pipeline{display:flex;gap:.25rem;align-items:center;font-size:.68rem;color:var(--muted);margin-top:.35rem}
.pipe-dot{width:.45rem;height:.45rem;border-radius:50%;background:#d1d5db}
.pipe-dot.on{background:var(--acc)}.pipe-dot.done{background:var(--ok)}
</style>
</head>
<body>
<div id="busy">กำลังดำเนินการ…</div>
<div id="toast" class="toast"></div>
<div id="modalBackdrop" class="modal-backdrop"><div class="modal" id="modalBox"></div></div>
<header class="hdr">
  <button id="btnBack" class="back-btn" style="display:none">← กลับ</button>
  <div class="hdr-main">
    <h1 id="hdrTitle">โอนสินค้า · __SITE__</h1>
    <div class="sub" id="hdrSub">__USER__</div>
  </div>
</header>
<main><div id="content" class="empty">กำลังโหลด…</div></main>
<script>
const SITE = "__SITE__";
const OTHER = "__OTHER__";
const SHIP_WRITE = __SHIP_WRITE__ === "true";
const RECV_WRITE = __RECV_WRITE__ === "true";
const USER = __USER_JSON__;

let view = "home";
let requestStep = 1;
let orderDirection = SITE === "SYP" ? "to_syp" : "to_hq";
let statusFilter = "active";
let editingDraftId = null;
let receiveStep = 1;
let receiveShipment = null;
let suggestItems = [];
let suggestFilter = "";
let toastTimer = null;

const VIEWS = {
  home: {title: "โอนสินค้า · " + SITE, sub: "เลือกสิ่งที่ต้องการทำ"},
  request: {title: "ขอสินค้า", sub: "ขั้นตอนที่ " + requestStep + " จาก 3"},
  prepare: {title: "จัดส่งสินค้า", sub: "รายการที่รอจัดออกจาก " + SITE},
  receive: {title: "รับสินค้า", sub: "รายการที่รอรับเข้า " + SITE},
  status: {title: "ตรวจสอบสถานะ", sub: "ติดตามคำขอโอนทั้งหมด"},
};

function $(id){return document.getElementById(id)}
function fmtQty(n){
  const x = Number(n);
  if(n === null || n === undefined || n === "" || Number.isNaN(x)) return "—";
  if(Math.abs(x - Math.round(x)) < 1e-9) return String(Math.round(x));
  return x.toLocaleString("th-TH",{maximumFractionDigits:2});
}
function fmtQtyUi(qty, ui){
  const q = fmtQty(qty);
  const u = (ui || "").trim();
  if(q === "—") return q;
  return u ? (q + " " + u) : q;
}
function unitChoices(row){
  const mtp2 = Number(row.mtp2) || 1;
  const ui1 = (row.ui1 || "ชิ้น").trim() || "ชิ้น";
  const ui2 = (row.ui2 || "").trim();
  const out = [{id:"small", label:ui1, factor:1}];
  if(mtp2 > 1 && ui2) out.push({id:"large", label:ui2, factor:mtp2});
  return out;
}
function fmtStockDual(smallQty, row){
  const mtp2 = Number(row.mtp2) || 1;
  const ui1 = (row.ui1 || "").trim();
  const ui2 = (row.ui2 || "").trim();
  const main = fmtQtyUi(smallQty, ui1);
  if(mtp2 > 1 && ui2) return main + `<div class="meta">${fmtQty(smallQty / mtp2)} ${ui2}</div>`;
  return main;
}
function qtyToSmall(qty, unitId, row){
  const choices = unitChoices(row);
  const picked = choices.find(c=>c.id===unitId) || choices[0];
  return Number(qty||0) * picked.factor;
}
function defaultEntryQty(row){
  const choices = unitChoices(row);
  const small = Number(row.suggest_qty||0);
  if(choices.length > 1 && small >= (Number(row.mtp2)||1)) return {unit:"large", qty: small / (Number(row.mtp2)||1)};
  return {unit:"small", qty: small || 1};
}
function showToast(msg){
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("on");
  if(toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>el.classList.remove("on"), 2600);
}
function uuid(){return crypto.randomUUID ? crypto.randomUUID() : String(Date.now())+"-"+Math.random().toString(16).slice(2)}
function dirLabel(fromB, toB){return (fromB||"?")+" → "+(toB||"?")}
function shipBillPrefix(fromBranch){
  return (fromBranch||"").toUpperCase()==="SYP" ? "3TF" : "TF";
}
function receiveBillPrefix(fromBranch, toBranch){
  if((fromBranch||"").toUpperCase()==="SYP" && (toBranch||"").toUpperCase()==="HQ") return "3TF";
  return "TF";
}
function parts9Host(branch){
  return (branch||"").toUpperCase()==="SYP" ? "kss-pc (SYP)" : "KSS (HQ)";
}
function infoToggleHtml(title, bodyHtml){
  return `<details class="info-toggle"><summary>${title}</summary><div class="info-body">${bodyHtml}</div></details>`;
}
function billTimelineHtml(fromB, toB){
  const fb = (fromB||"HQ").toUpperCase();
  const tb = (toB||"SYP").toUpperCase();
  const shipP = shipBillPrefix(fb);
  const recvP = receiveBillPrefix(fb, tb);
  return infoToggleHtml("ใบ TF ถูกสร้างเมื่อไหร่?", `<ol class="bill-steps">
      <li><span class="bill-when">ส่งคำขอ</span> — บันทึกคำขอ <code>TRF-…</code> + แสตมป์ ICLOW (<strong>ยังไม่ออกใบ TF</strong> ใน PARTS9)</li>
      <li><span class="bill-when">${fb} จัดส่ง</span> — สร้างใบ <strong>${shipP} SIMAS</strong> บน ${parts9Host(fb)} (ตัดสต๊อกออก)</li>
      <li><span class="bill-when">${tb} รับเข้า</span> — สร้างใบ <strong>${recvP} PIMAS</strong> บน ${parts9Host(tb)} (เพิ่มสต๊อกเข้า)</li>
    </ol>`);
}
function submitBillNoteHtml(fromB, toB){
  const fb = (fromB||OTHER).toUpperCase();
  const tb = (toB||SITE).toUpperCase();
  const shipP = shipBillPrefix(fb);
  const recvP = receiveBillPrefix(fb, tb);
  return infoToggleHtml("ตอนกดยืนยันส่งคำขอ จะเกิดอะไรขึ้น?", `<ul class="bill-steps">
      <li>สร้างคำขอโอน <code>TRF-…</code> (อ้างอิงในระบบ — <strong>ไม่ใช่เลขบิล PARTS9</strong>)</li>
      <li>แสตมป์ ICLOW ว่าสั่งแล้ว (กันสั่งซ้ำในรายการรอสั่ง)</li>
      <li class="bill-none">ยังไม่ออกใบ TF — ใบ ${shipP} สร้างตอน ${fb} จัดส่ง · ใบ ${recvP} สร้างตอน ${tb} รับเข้า</li>
    </ul>`);
}
function prepareBillNoteHtml(fromB, toB){
  const fb = (fromB||SITE).toUpperCase();
  const tb = (toB||OTHER).toUpperCase();
  const shipP = shipBillPrefix(fb);
  const recvP = receiveBillPrefix(fb, tb);
  return infoToggleHtml("เมื่อยืนยันจัดส่ง ระบบจะ:", `<ul class="bill-steps">
      <li>สร้างใบ <strong>${shipP} SIMAS</strong> บน ${parts9Host(fb)} ทันที (ตัดสต๊อก ${fb})</li>
      <li>ยังไม่มีใบรับ — ${tb} จะออก <strong>${recvP} PIMAS</strong> ตอนกดรับเข้า</li>
    </ul>`);
}
function receiveBillNoteHtml(fromB, toB, shipBillno){
  const fb = (fromB||OTHER).toUpperCase();
  const tb = (toB||SITE).toUpperCase();
  const recvP = receiveBillPrefix(fb, tb);
  const shipP = shipBillPrefix(fb);
  const shipRef = shipBillno ? `<code>${shipBillno}</code>` : `ใบ ${shipP} ที่ ${fb} จัดไป`;
  return infoToggleHtml("เมื่อยืนยันรับเข้า ระบบจะ:", `<ul class="bill-steps">
      <li>สร้างใบ <strong>${recvP} PIMAS</strong> บน ${parts9Host(tb)} (เพิ่มสต๊อก ${tb})</li>
      <li>อ้างอิงใบจัด ${shipRef}</li>
      <li>อัปเดต ICLOW ว่ารับแล้ว</li>
    </ul>`);
}
function orderFlowText(){
  if(orderDirection === "to_syp") return OTHER + " จัดส่ง → " + SITE + " รับเข้า";
  return SITE === "HQ" ? (OTHER + " จัดส่ง → " + SITE + " รับเข้า") : (OTHER + " จัดส่ง → " + SITE + " รับเข้า");
}
function badge(status, fromB, toB){
  const m={draft:"b-requested",requested:"b-requested",partial_prepared:"b-await",awaiting_receive:"b-await",partial_received:"b-await",complete:"b-done",cancelled:"b-requested"};
  const fb = fromB||"HQ";
  const t={draft:"ร่าง",requested:"รอ "+fb+" จัด",partial_prepared:"จัดบางส่วน",awaiting_receive:"รอรับ",partial_received:"รับบางส่วน",complete:"เสร็จสิ้น",cancelled:"ยกเลิก"};
  return `<span class="badge ${m[status]||"b-requested"}">${t[status]||status||"-"}</span>`;
}
function pipeline(status){
  const steps = ["requested","prepared","received","done"];
  const idx = status==="complete" ? 3 : status==="awaiting_receive"||status==="partial_received" ? 2 : status==="partial_prepared" ? 1 : 0;
  const labels = ["ขอแล้ว","จัดแล้ว","รับแล้ว","เสร็จ"];
  return `<div class="pipeline">${labels.map((l,i)=>`<span class="pipe-dot ${i<idx?"done":i===idx?"on":""}"></span><span>${l}</span>`).join("")}</div>`;
}
function lineStatusLabel(status){
  const t={open:"รอจัด",partial_prepared:"จัดบางส่วน",prepared:"จัดแล้ว รอรับ",partial_received:"รับบางส่วน",complete:"เสร็จ",cancelled:"ยกเลิก"};
  return t[status]||status||"-";
}
function fmtDateTime(iso){
  return iso ? String(iso).slice(0,16).replace("T"," ") : "—";
}
function bindDetailRows(container){
  container.querySelectorAll("tr.row-clickable").forEach(tr=>{
    tr.onclick = e=>{
      if(e.target.closest("button")) return;
      openRequestDetail(tr.dataset.detail);
    };
  });
}
function setBusy(on){document.body.classList.toggle("busy",!!on)}
function showModal(html){
  const box = $("modalBox");
  box.innerHTML = html;
  $("modalBackdrop").classList.add("on");
  const close = ()=>{$("modalBackdrop").classList.remove("on"); box.innerHTML="";};
  $("modalBackdrop").onclick = e=>{if(e.target===$("modalBackdrop")) close();};
  box.querySelectorAll("[data-close]").forEach(b=>b.onclick=close);
  return {close, box};
}
async function api(path, opts){
  setBusy(true);
  try{
    const r = await fetch(path, Object.assign({credentials:"same-origin",headers:{"Content-Type":"application/json"}}, opts||{}));
    const j = await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(j.error||j.detail||("HTTP "+r.status));
    return j;
  } finally { setBusy(false); }
}
async function submitTransferLines(lines, direction){
  let transferId = editingDraftId;
  if(!transferId){
    const d = await api("/transfer/api/requests/draft",{method:"POST",body:JSON.stringify({direction})});
    transferId = d.transfer_id;
  }
  await api("/transfer/api/requests/"+transferId+"/lines",{
    method:"PUT",
    body:JSON.stringify({lines:lines.map(l=>({bcode:l.bcode,qty:l.qty,descr:l.descr||""}))}),
  });
  const submitted = await api("/transfer/api/requests/"+transferId+"/submit",{method:"POST",body:"{}"});
  editingDraftId = null;
  return submitted;
}
async function saveDraftLines(lines){
  let transferId = editingDraftId;
  if(!transferId){
    const d = await api("/transfer/api/requests/draft",{method:"POST",body:JSON.stringify({direction:orderDirection})});
    transferId = d.transfer_id;
    editingDraftId = transferId;
  }
  await api("/transfer/api/requests/"+transferId+"/lines",{
    method:"PUT",
    body:JSON.stringify({lines:lines.map(l=>({bcode:l.bcode,qty:l.qty,descr:l.descr||""}))}),
  });
  return transferId;
}
async function deleteDraft(transferId){
  if(!confirm("ลบร่างนี้?")) return;
  await api("/transfer/api/requests/"+transferId,{method:"DELETE"});
  if(editingDraftId === transferId) editingDraftId = null;
  showToast("ลบร่างแล้ว");
  render();
}
async function cancelRequest(transferId){
  if(!confirm("ยกเลิกคำขอนี้?")) return;
  await api("/transfer/api/requests/"+transferId+"/cancel",{method:"POST",body:"{}"});
  showToast("ยกเลิกคำขอแล้ว");
  render();
}
async function openRequestDetail(transferId){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  const lines = detail.items || detail.lines || [];
  const shipments = detail.shipments || [];
  const status = detail.status || (detail.header && detail.header.status) || "";
  const fromB = detail.from_branch;
  const toB = detail.to_branch;
  const lineRows = lines.map(ln=>`<tr>
    <td><code>${ln.bcode}</code></td>
    <td>${ln.descr||""}</td>
    <td>${fmtQty(ln.qty_requested)}</td>
    <td>${fmtQty(ln.qty_prepared)}</td>
    <td>${fmtQty(ln.qty_received)}</td>
    <td>${lineStatusLabel(ln.line_status)}</td>
  </tr>`).join("");
  let shipHtml = "";
  if(shipments.length){
    shipHtml = shipments.map((ship,i)=>{
      const shipBill = ship.ship_billno || ship.tf_billno || "—";
      const recvBill = ship.receive_billno || "";
      const slines = (ship.lines||[]).map(sl=>{
        const open = Math.max(Number(sl.qty_shipped||0)-Number(sl.qty_received||0),0);
        return `<tr><td><code>${sl.bcode||""}</code></td><td>${fmtQty(sl.qty_shipped)}</td><td>${fmtQty(sl.qty_received)}</td><td>${fmtQty(open)}</td></tr>`;
      }).join("");
      return `<div style="margin-top:.65rem">
        <p class="meta" style="margin:0"><strong>ใบจัด ${i+1}</strong> · <code>${shipBill}</code>${recvBill ? ` · ใบรับ <code>${recvBill}</code>` : ""}</p>
        ${slines ? `<div class="table-wrap" style="margin-top:.35rem"><table><thead><tr><th>รหัส</th><th>จัด</th><th>รับแล้ว</th><th>ค้างรับ</th></tr></thead><tbody>${slines}</tbody></table></div>` : ""}
      </div>`;
    }).join("");
    shipHtml = `<div class="tool-section" style="margin-top:.75rem"><p class="tool-title">ใบ TF / การจัดส่ง</p>${shipHtml}</div>`;
  }
  const canCancel = status==="requested";
  const isDraft = status==="draft";
  const modal = showModal(`<h2>รายละเอียด · <code>${detail.short_id||transferId}</code></h2>
    <p class="dir">${dirLabel(fromB, toB)}</p>
    <p style="margin:.35rem 0">${badge(status, fromB, toB)} ${pipeline(status)}</p>
    <p class="meta">สร้าง ${fmtDateTime(detail.created_at)} · ส่งคำขอ ${fmtDateTime(detail.requested_at)}</p>
    <div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>ขอ</th><th>จัด</th><th>รับ</th><th>สถานะ</th></tr></thead><tbody>
      ${lineRows || '<tr><td colspan="6" class="empty">ไม่มีรายการ</td></tr>'}
    </tbody></table></div>
    ${shipHtml}
    <div class="row-actions">
      <button class="btn btn-ghost" data-close>ปิด</button>
      ${canCancel ? `<button class="btn btn-ghost" id="btnDetailCancel">ยกเลิกคำขอ</button>` : ""}
      ${isDraft ? `<button class="btn btn-primary" id="btnDetailEdit">แก้ไขร่าง</button>` : ""}
    </div>`);
  const cancelBtn = modal.box.querySelector("#btnDetailCancel");
  if(cancelBtn) cancelBtn.onclick = async()=>{ modal.close(); await cancelRequest(transferId); };
  const editBtn = modal.box.querySelector("#btnDetailEdit");
  if(editBtn) editBtn.onclick = ()=>{ modal.close(); editDraft(transferId); };
}
async function editDraft(transferId){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  editingDraftId = transferId;
  orderDirection = (detail.to_branch||"SYP").toUpperCase() === SITE ? "to_syp" : "to_hq";
  const lines = detail.items || detail.lines || [];
  for(const n of await (await api("/transfer/api/need-list")).items || []){
    await api("/transfer/api/need-list/"+n.need_id,{method:"DELETE"});
  }
  for(const ln of lines){
    await api("/transfer/api/need-list",{method:"POST",body:JSON.stringify({
      bcode:ln.bcode, qty:ln.qty_requested, descr:ln.descr||"", suggest_qty:ln.qty_requested,
    })});
  }
  view = "request";
  requestStep = 2;
  render();
}
function goHome(){ view="home"; requestStep=1; receiveStep=1; receiveShipment=null; editingDraftId=null; render(); }
function goView(v){ view=v; if(v==="request" && !editingDraftId) requestStep=1; if(v==="receive"){ receiveStep=1; receiveShipment=null; } render(); }
function setReceiveStep(n){ receiveStep=n; render(); }
function setRequestStep(n){ requestStep=n; render(); }

function updateHeader(){
  const titles = {
    home: ["โอนสินค้า · " + SITE, USER + " · เลือกสิ่งที่ต้องการทำ"],
    request: ["ขอสินค้าจาก " + OTHER, "ขั้นตอนที่ " + requestStep + " จาก 3 · " + orderFlowText()],
    prepare: ["จัดส่งไป " + OTHER, "รายการที่ " + SITE + " ต้องจัดออก"],
    receive: ["รับสินค้าจาก " + OTHER, receiveStep===1 ? "เลือกคำขอที่จัดส่งมาแล้ว" : receiveStep===2 ? "ขั้นตอนที่ 2 จาก 3 · ระบุจำนวนรับ" : "ขั้นตอนที่ 3 จาก 3 · ยืนยันรับเข้า"],
    status: ["ตรวจสอบสถานะ", "ติดตามคำขอโอนทั้งหมด"],
  };
  const t = titles[view] || titles.home;
  $("hdrTitle").textContent = t[0];
  $("hdrSub").textContent = t[1];
  $("btnBack").style.display = view === "home" ? "none" : "";
}

function stepBar(current){
  const labels = ["1. เลือกทิศทาง","2. เลือกสินค้า","3. ยืนยันส่ง"];
  return `<div class="steps">${labels.map((l,i)=>{
    const n = i+1;
    const cls = n===current ? "on" : n<current ? "done" : "";
    return `<div class="step ${cls}">${l}<span class="step-label">${n===1?"ขอจากสาขาไหน":n===2?"เพิ่มรายการ": "ตรวจสอบ"}</span></div>`;
  }).join("")}</div>`;
}
function receiveStepBar(current){
  const labels = ["1. เลือกคำขอ","2. ระบุจำนวน","3. ยืนยันรับ"];
  return `<div class="steps">${labels.map((l,i)=>{
    const n = i+1;
    const cls = n===current ? "on" : n<current ? "done" : "";
    return `<div class="step ${cls}">${l}<span class="step-label">${n===1?"เปิดคำขอ":n===2?"กรอกจำนวน":"ออกใบ TF"}</span></div>`;
  }).join("")}</div>`;
}
function groupReceiveQueue(items){
  const map = new Map();
  for(const row of items){
    const key = row.shipment_id;
    if(!map.has(key)){
      map.set(key, {
        transfer_id: row.transfer_id,
        shipment_id: row.shipment_id,
        short_id: row.short_id,
        from_branch: row.from_branch,
        to_branch: row.to_branch,
        ship_billno: row.ship_billno,
        lines: [],
      });
    }
    map.get(key).lines.push(row);
  }
  return [...map.values()];
}

async function fetchCounts(){
  try{
    const [prep, recv] = await Promise.all([
      api("/transfer/api/requests?role=prepare"),
      api("/transfer/api/receive-lines"),
    ]);
    return {prepare:(prep.items||[]).length, receive:(recv.items||[]).length};
  }catch(e){ return {prepare:0, receive:0}; }
}

async function renderHome(el){
  const counts = await fetchCounts();
  el.innerHTML = `
    <div class="flow-hint"><strong>ขั้นตอนโอนสินค้า</strong><br>
    1) สาขาที่<strong>ต้องการสินค้า</strong> กดขอโอน → 2) สาขาที่<strong>มีสินค้า</strong> กดจัดส่ง → 3) สาขาที่ขอ กดรับเข้า</div>
    ${billTimelineHtml(OTHER, SITE)}
    <div class="action-grid">
      <button class="action-card" data-go="request">
        <p class="title">📥 ขอสินค้าจาก ${OTHER}</p>
        <p class="desc">ฉันอยู่ที่ ${SITE} และต้องการให้ ${OTHER} ส่งสินค้ามา</p>
      </button>
      <button class="action-card" data-go="prepare">
        <p class="title">📤 จัดส่งไป ${OTHER}</p>
        <p class="desc">มีคำขอรอจัด — ${SITE} ต้องจัดสินค้าออก${counts.prepare ? `<span class="count">${counts.prepare} รายการรอจัด</span>` : ""}</p>
      </button>
      <button class="action-card" data-go="receive">
        <p class="title">📦 รับสินค้าจาก ${OTHER}</p>
        <p class="desc">สินค้าถูกจัดส่งมาแล้ว — เปิดคำขอ กรอกจำนวน แล้วยืนยันรับ${counts.receive ? `<span class="count">${counts.receive} รายการรอรับ</span>` : ""}</p>
      </button>
      <button class="action-card" data-go="status">
        <p class="title">📋 ตรวจสอบสถานะ</p>
        <p class="desc">ดูคำขอที่ส่งแล้ว กำลังจัด รอรับ หรือเสร็จสิ้น</p>
      </button>
    </div>`;
  el.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>goView(b.dataset.go));
}

async function renderRequest(el){
  if(requestStep === 1){
    if(SITE === "SYP") orderDirection = "to_syp";
    else orderDirection = "to_hq";
    el.innerHTML = `${stepBar(1)}
      <div class="card">
        <p style="margin:0 0 .5rem"><strong>คุณอยู่ที่ ${SITE}</strong></p>
        <p style="margin:0 0 .75rem">ต้องการขอสินค้าจาก <strong>${OTHER}</strong> ให้ส่งมาที่ ${SITE}</p>
        <div class="flow-hint" style="margin-bottom:0">
          <strong>ขั้นตอนถัดไป:</strong><br>
          1. เลือกรายการสินค้า → 2. ส่งคำขอ → 3. รอ ${OTHER} จัดส่ง → 4. กลับมากดรับสินค้าที่นี่
        </div>
        <div class="row-actions" style="margin-top:1rem">
          <button class="btn btn-ghost" onclick="goHome()">ยกเลิก</button>
          <button class="btn btn-primary" id="btnReqNext1">ถัดไป → เลือกสินค้า</button>
        </div>
      </div>`;
    el.querySelector("#btnReqNext1").onclick = ()=>setRequestStep(2);
    return;
  }

  if(requestStep === 2){
    const [rows, cart] = await Promise.all([api("/transfer/api/suggest"), api("/transfer/api/need-list")]);
    suggestItems = rows.items || [];
    const cartItems = cart.items || [];
    const q = (suggestFilter || "").trim().toLowerCase();
    const filtered = q ? suggestItems.filter(r=>{
      const b = (r.bcode||"").toLowerCase();
      const d = (r.descr||"").toLowerCase();
      return b.includes(q) || d.includes(q);
    }) : suggestItems;

    let html = stepBar(2) + `<div class="card">
      <p style="margin:0 0 .75rem"><strong>ทิศทาง:</strong> ${OTHER} → ${SITE}</p>

      <div class="search-bar">
        <input id="suggestSearch" class="text-input" placeholder="ค้นหาในรายการ (รหัส / รายละเอียด)" value="${suggestFilter.replace(/"/g,"&quot;")}"/>
      </div>

      <div class="tool-section">
        <p class="tool-title">เพิ่มรหัสเอง (ไม่อยู่ในรายการแนะนำ)</p>
        <div class="tool-row">
          <div class="field" style="flex:2">
            <label for="manualBcode">รหัสสินค้า (BCODE)</label>
            <input id="manualBcode" class="text-input" placeholder="เช่น 15010490"/>
          </div>
          <div class="field" style="max-width:6rem">
            <label for="manualQty">จำนวน</label>
            <input id="manualQty" type="number" min="1" value="1" class="qty-input"/>
          </div>
          <button class="btn btn-primary" id="btnManualAdd" style="margin-bottom:1px">เพิ่ม</button>
        </div>
      </div>

      <p class="meta" style="margin:0 0 .5rem">รายการแนะนำจาก ICLOW รอสั่ง — เลือกจำนวนแล้วกดเพิ่ม</p>`;

    if(!suggestItems.length){
      html += `<div class="empty">ไม่พบรายการแนะนำ — ใช้เพิ่มรหัสเองด้านบน</div>`;
    } else if(!filtered.length){
      html += `<div class="empty">ไม่พบ "${suggestFilter}" ในรายการ — ลองค้นหาใหม่ หรือเพิ่มรหัสเอง</div>`;
    } else {
      html += `<div class="table-wrap"><table><thead><tr>
        <th>รหัส</th><th>รายละเอียด</th><th>คงเหลือ HQ</th><th>คงเหลือ SYP</th><th>แนะนำ</th><th>หน่วย</th><th>จำนวน</th><th></th>
      </tr></thead><tbody>`;
      html += filtered.map((r)=>{
        const idx = suggestItems.indexOf(r);
        const entry = defaultEntryQty(r);
        const unitOpts = unitChoices(r).map(c=>`<option value="${c.id}" ${c.id===entry.unit?"selected":""}>${c.label}</option>`).join("");
        return `<tr><td><code>${r.bcode}</code></td><td>${r.descr||""}</td>
          <td>${fmtStockDual(r.hq_qtyoh2,r)}</td><td>${fmtStockDual(r.syp_qtyoh2,r)}</td>
          <td>${fmtStockDual(r.suggest_qty,r)}</td>
          <td><select class="unit-select" data-unit="${idx}">${unitOpts}</select></td>
          <td><input class="qty-input" type="number" min="0.01" step="any" value="${entry.qty}" data-qty="${idx}"/></td>
          <td><button class="btn btn-ghost" data-add="${idx}">เพิ่ม</button></td></tr>`;
      }).join("");
      html += `</tbody></table></div>`;
      if(q) html += `<p class="meta" style="margin:.5rem 0 0">แสดง ${filtered.length} จาก ${suggestItems.length} รายการ</p>`;
    }
    html += `</div>`;

    html += `<div class="card"><strong>รายการในคำขอ (${cartItems.length})</strong>`;
    if(!cartItems.length) html += `<div class="empty">ยังไม่มีรายการ</div>`;
    else {
      html += `<div class="table-wrap" style="margin-top:.5rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>จำนวน</th><th></th></tr></thead><tbody>`;
      html += cartItems.map(n=>`<tr><td><code>${n.bcode}</code></td><td>${n.descr||""}</td><td>${fmtQty(n.qty)}</td>
        <td><button class="btn btn-ghost" data-del="${n.need_id}">ลบ</button></td></tr>`).join("");
      html += `</tbody></table></div>`;
    }
    html += `<div class="row-actions">
      <button class="btn btn-ghost" onclick="setRequestStep(1)">← ย้อนกลับ</button>
      <button class="btn btn-primary" id="btnReqNext2" ${cartItems.length?"":"disabled"}>ถัดไป → ตรวจสอบ</button>
    </div></div>`;
    el.innerHTML = html;

    const searchEl = el.querySelector("#suggestSearch");
    if(searchEl){
      searchEl.oninput = ()=>{ suggestFilter = searchEl.value; renderRequest(el); };
      searchEl.onkeydown = e=>{ if(e.key==="Enter"){ e.preventDefault(); suggestFilter = searchEl.value; renderRequest(el); } };
    }

    el.querySelectorAll("[data-add]").forEach(btn=>btn.onclick=async()=>{
      const idx = Number(btn.dataset.add);
      const row = suggestItems[idx];
      if(!row) return;
      const unitId = el.querySelector(`[data-unit="${idx}"]`).value;
      const qty = Number(el.querySelector(`[data-qty="${idx}"]`).value||0);
      const qtySmall = qtyToSmall(qty, unitId, row);
      if(qtySmall <= 0){alert("ระบุจำนวน");return;}
      await api("/transfer/api/need-list",{method:"POST",body:JSON.stringify({
        bcode:row.bcode, qty:qtySmall, suggest_qty:row.suggest_qty, descr:row.descr||"", hq_qtyoh2:row.hq_qtyoh2,
      })});
      showToast("เพิ่มแล้ว");
      setRequestStep(2);
    });
    el.querySelector("#btnManualAdd").onclick = async()=>{
      const b = el.querySelector("#manualBcode").value.trim();
      const q = Number(el.querySelector("#manualQty").value||0);
      if(!b||q<=0){alert("ระบุรหัสและจำนวน");return;}
      await api("/transfer/api/need-list",{method:"POST",body:JSON.stringify({bcode:b, qty:q, descr:""})});
      showToast("เพิ่มแล้ว");
      setRequestStep(2);
    };
    el.querySelectorAll("[data-del]").forEach(btn=>btn.onclick=async()=>{
      await api("/transfer/api/need-list/"+btn.dataset.del,{method:"DELETE"});
      setRequestStep(2);
    });
    el.querySelector("#btnReqNext2").onclick = ()=>setRequestStep(3);
    return;
  }

  if(requestStep === 3){
    const cart = await api("/transfer/api/need-list");
    const cartItems = cart.items || [];
    el.innerHTML = `${stepBar(3)}
      <div class="card">
        <p><strong>ทิศทาง:</strong> ${OTHER} จัดส่ง → ${SITE} รับเข้า</p>
        <p class="meta">ตรวจสอบรายการก่อนส่งคำขอ — ${OTHER} จะเห็นในรายการรอจัด</p>
        ${submitBillNoteHtml(OTHER, SITE)}
        <div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>จำนวน (หน่วยเล็ก)</th></tr></thead><tbody>
          ${cartItems.map(n=>`<tr><td><code>${n.bcode}</code></td><td>${n.descr||""}</td><td>${fmtQty(n.qty)}</td></tr>`).join("")}
        </tbody></table></div>
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setRequestStep(2)">← แก้ไขรายการ</button>
          ${editingDraftId ? `<button class="btn btn-ghost" id="btnSaveDraft">บันทึกร่าง</button>` : ""}
          <button class="btn btn-primary" id="btnConfirmSubmit">ยืนยันส่งคำขอ</button>
        </div>
      </div>`;
    el.querySelector("#btnConfirmSubmit").onclick = async()=>{
      if(!cartItems.length) return;
      try{
        const submitted = await submitTransferLines(
          cartItems.map(n=>({bcode:n.bcode, qty:n.qty, descr:n.descr||""})),
          orderDirection,
        );
        for(const n of cartItems) await api("/transfer/api/need-list/"+n.need_id,{method:"DELETE"});
        showToast("ส่งคำขอแล้ว: "+(submitted.short_id||submitted.transfer_id));
        goView("status");
        statusFilter = "active";
      }catch(e){alert(e.message);}
    };
    const saveBtn = el.querySelector("#btnSaveDraft");
    if(saveBtn){
      saveBtn.onclick = async()=>{
        if(!cartItems.length) return;
        try{
          const id = await saveDraftLines(cartItems.map(n=>({bcode:n.bcode, qty:n.qty, descr:n.descr||""})));
          showToast("บันทึกร่างแล้ว: "+id.slice(0,8));
          goView("status");
          statusFilter = "active";
        }catch(e){alert(e.message);}
      };
    }
  }
}

async function openPrepareDialog(transferId){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  const lines = (detail.items || detail.lines || []).filter(l=>Number(l.qty_requested||0)>Number(l.qty_prepared||0));
  if(!lines.length){alert("ไม่มีรายการที่ต้องจัด");return;}
  const rows = lines.map(l=>{
    const remain = Number(l.qty_requested||0)-Number(l.qty_prepared||0);
    return `<tr><td><code>${l.bcode}</code></td><td>${l.descr||""}</td><td>${fmtQty(l.qty_requested)}</td><td>${fmtQty(l.qty_prepared)}</td>
      <td><input class="qty-input" type="number" min="0" max="${remain}" step="1" value="${remain}" data-bcode="${l.bcode}" data-line="${l.line_id}"/></td></tr>`;
  }).join("");
  const modal = showModal(`<h2>จัดสินค้า · ${detail.short_id||transferId}</h2>
    <div class="dir">${dirLabel(detail.from_branch, detail.to_branch)}</div>
    ${prepareBillNoteHtml(detail.from_branch, detail.to_branch)}
    <p class="meta">ระบุจำนวนที่จัดในครั้งนี้ แล้วกดยืนยัน</p>
    <div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>ขอ</th><th>จัดแล้ว</th><th>จัดครั้งนี้</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="row-actions"><button class="btn btn-ghost" data-close>ยกเลิก</button><button class="btn btn-primary" id="btnDoPrepare">ยืนยันจัดแล้ว</button></div>`);
  modal.box.querySelector("#btnDoPrepare").onclick = async()=>{
    const shipLines = [];
    modal.box.querySelectorAll(".qty-input").forEach(inp=>{
      const q = Number(inp.value||0);
      if(q>0) shipLines.push({line_id:inp.dataset.line, bcode:inp.dataset.bcode, qty_ship:q});
    });
    if(!shipLines.length){alert("ระบุจำนวนที่จัด");return;}
    if(!SHIP_WRITE && !confirm("โหมดทดสอบ: writer ปิดอยู่")) return;
    try{
      const result = await api("/transfer/api/requests/"+transferId+"/prepare",{method:"POST",body:JSON.stringify({client_token:uuid(),lines:shipLines})});
      const bill = result.ship_billno || result.tf_billno || "";
      modal.close();
      showToast(bill ? ("จัดสินค้าแล้ว — ออกใบ "+bill) : "จัดสินค้าแล้ว");
      render();
    }catch(e){alert(e.message);}
  };
}

async function submitReceive(shipment, qtyByLineId){
  const recvLines = shipment.lines.map(ln=>{
    const q = Number(qtyByLineId[ln.shipment_line_id]||0);
    return {
      shipment_line_id: ln.shipment_line_id,
      line_id: ln.line_id,
      bcode: ln.bcode,
      qty_receive: q,
      iclow_id: ln.iclow_id||undefined,
    };
  }).filter(l=>l.qty_receive>0);
  if(!recvLines.length) throw new Error("ระบุจำนวนที่รับ");
  if(!RECV_WRITE && !confirm("โหมดทดสอบ: writer ปิดอยู่")) throw new Error("ยกเลิก");
  return api("/transfer/api/shipments/"+shipment.shipment_id+"/receive",{
    method:"POST",
    body:JSON.stringify({client_token:uuid(), lines:recvLines}),
  });
}

async function renderReceive(el){
  const data = await api("/transfer/api/receive-lines");
  const queue = groupReceiveQueue(data.items||[]);
  if(!queue.length){
    el.innerHTML = `<div class="card"><div class="empty">ไม่มีรายการรอรับ<br><span class="meta">จะแสดงเมื่อ ${OTHER} จัดส่งและออกใบ TF แล้วเท่านั้น</span></div>
      <div class="row-actions"><button class="btn btn-ghost" onclick="goHome()">กลับหน้าหลัก</button></div></div>`;
    return;
  }

  if(receiveStep === 1){
    el.innerHTML = `${receiveStepBar(1)}
      <div class="flow-hint">เลือกคำขอที่ ${OTHER} จัดส่งแล้ว (มีใบ TF SIMAS) → กรอกจำนวนรับ → ยืนยันเพื่อออกใบ TF PIMAS</div>
      ${billTimelineHtml(OTHER, SITE)}
      <div class="card"><div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>ใบจัด</th><th>รายการค้างรับ</th><th>วันที่</th><th></th></tr></thead><tbody>
        ${queue.map((g,i)=>`<tr>
          <td><code>${g.short_id}</code></td>
          <td class="dir">${dirLabel(g.from_branch,g.to_branch)}</td>
          <td><code>${g.ship_billno||"-"}</code></td>
          <td>${g.lines.length} รายการ</td>
          <td>—</td>
          <td><button class="btn btn-primary" data-recv-group="${i}">เปิดรับสินค้า</button></td>
        </tr>`).join("")}
      </tbody></table></div>
      <div class="row-actions"><button class="btn btn-ghost" onclick="goHome()">กลับหน้าหลัก</button></div></div>`;
    window._receiveGroups = queue;
    el.querySelectorAll("[data-recv-group]").forEach(b=>b.onclick=()=>{
      receiveShipment = window._receiveGroups[Number(b.dataset.recvGroup)];
      setReceiveStep(2);
    });
    return;
  }

  if(!receiveShipment){
    receiveStep = 1;
    return renderReceive(el);
  }

  const ship = receiveShipment;
  const openLines = (ship.lines||[]).filter(l=>Number(l.qty_open||0)>0);
  if(!openLines.length){
    receiveShipment = null;
    receiveStep = 1;
    return renderReceive(el);
  }

  if(receiveStep === 2){
    const rows = openLines.map(ln=>{
      const remain = Number(ln.qty_open||0);
      return `<tr><td><code>${ln.bcode}</code></td><td>${ln.descr||""}</td><td>${fmtQty(ln.qty_shipped)}</td><td>${fmtQty(ln.qty_received)}</td>
        <td><input class="qty-input recv-qty" type="number" min="0" max="${remain}" step="1" value="${remain}"
          data-shipment-line="${ln.shipment_line_id}"/></td></tr>`;
    }).join("");
    el.innerHTML = `${receiveStepBar(2)}
      <div class="card">
        <p><strong>${ship.short_id}</strong> · ${dirLabel(ship.from_branch, ship.to_branch)}</p>
        <p class="meta">ใบจัด <code>${ship.ship_billno||"-"}</code> — ระบุจำนวนที่รับแต่ละรายการ</p>
        ${receiveBillNoteHtml(ship.from_branch, ship.to_branch, ship.ship_billno)}
        <div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>จัด</th><th>รับแล้ว</th><th>รับครั้งนี้</th></tr></thead><tbody>${rows}</tbody></table></div>
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setReceiveStep(1)">← เลือกคำขออื่น</button>
          <button class="btn btn-primary" id="btnRecvNext2">ถัดไป → ตรวจสอบ</button>
        </div>
      </div>`;
    el.querySelector("#btnRecvNext2").onclick = ()=>{
      const qtyMap = {};
      let any = false;
      el.querySelectorAll(".recv-qty").forEach(inp=>{
        const q = Number(inp.value||0);
        if(q>0){ qtyMap[inp.dataset.shipmentLine]=q; any=true; }
      });
      if(!any){alert("ระบุจำนวนที่รับ");return;}
      ship._qtyDraft = qtyMap;
      setReceiveStep(3);
    };
    return;
  }

  if(receiveStep === 3){
    const qtyMap = ship._qtyDraft||{};
    const confirmRows = openLines.filter(ln=>Number(qtyMap[ln.shipment_line_id]||0)>0).map(ln=>`
      <tr><td><code>${ln.bcode}</code></td><td>${ln.descr||""}</td><td>${fmtQty(ln.qty_shipped)}</td><td>${fmtQty(ln.qty_received)}</td><td><strong>${fmtQty(qtyMap[ln.shipment_line_id])}</strong></td></tr>
    `).join("");
    el.innerHTML = `${receiveStepBar(3)}
      <div class="card">
        <p><strong>${ship.short_id}</strong> · ${dirLabel(ship.from_branch, ship.to_branch)}</p>
        <p class="meta">ใบจัด <code>${ship.ship_billno||"-"}</code></p>
        ${receiveBillNoteHtml(ship.from_branch, ship.to_branch, ship.ship_billno)}
        <div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th>จัด</th><th>รับแล้ว</th><th>รับครั้งนี้</th></tr></thead><tbody>${confirmRows}</tbody></table></div>
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setReceiveStep(2)">← แก้ไขจำนวน</button>
          <button class="btn btn-primary" id="btnConfirmReceive">ยืนยันรับเข้า (ออกใบ TF)</button>
        </div>
      </div>`;
    el.querySelector("#btnConfirmReceive").onclick = async()=>{
      try{
        const result = await submitReceive(ship, qtyMap);
        const bill = result.receive_billno || "";
        showToast(bill ? ("รับสินค้าแล้ว — ออกใบ "+bill) : "รับสินค้าแล้ว");
        receiveShipment = null;
        receiveStep = 1;
        render();
      }catch(e){ if(e.message!=="ยกเลิก") alert(e.message); }
    };
  }
}

async function renderPrepare(el){
  const data = await api("/transfer/api/requests?role=prepare");
  const items = data.items||[];
  if(!items.length){
    el.innerHTML = `<div class="card"><div class="empty">ไม่มีรายการรอจัด<br><span class="meta">เมื่อสาขาอื่นส่งคำขอมา จะแสดงที่นี่</span></div>
      <div class="row-actions"><button class="btn btn-ghost" onclick="goHome()">กลับหน้าหลัก</button></div></div>`;
    return;
  }
  el.innerHTML = `<div class="flow-hint">เลือกคำขอ → ระบุจำนวนที่จัด → ระบบออกใบ TF SIMAS ให้อัตโนมัติ</div>
    ${billTimelineHtml(SITE, OTHER)}
    <div class="card"><div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>สถานะ</th><th>วันที่</th><th>รายการ</th><th></th></tr></thead><tbody>
      ${items.map(r=>`<tr>
        <td><code>${r.short_id}</code></td><td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td>
        <td>${badge(r.status,r.from_branch,r.to_branch)}</td>
        <td>${(r.requested_at||r.created_at||"").slice(0,10)}</td><td>${r.line_count||0}</td>
        <td><button class="btn btn-primary" data-prep="${r.transfer_id}">จัดสินค้า</button></td>
      </tr>`).join("")}
    </tbody></table></div></div>`;
  el.querySelectorAll("[data-prep]").forEach(b=>b.onclick=()=>openPrepareDialog(b.dataset.prep));
}

async function renderStatus(el){
  const isDone = statusFilter === "done";
  const data = await api("/transfer/api/requests" + (isDone ? "?status=complete" : ""));
  let items = data.items||[];
  if(!isDone) items = items.filter(r=>r.status!=="complete"&&r.status!=="cancelled");
  const drafts = isDone ? [] : items.filter(r=>r.status==="draft");
  const active = isDone ? items : items.filter(r=>r.status!=="draft");
  el.innerHTML = `
    <div class="status-tabs">
      <button class="status-tab ${statusFilter==="active"?"on":""}" data-sf="active">กำลังดำเนินการ</button>
      <button class="status-tab ${statusFilter==="done"?"on":""}" data-sf="done">เสร็จสิ้น</button>
    </div>`;
  if(drafts.length){
    el.innerHTML += `<div class="card"><strong>ร่าง (${drafts.length})</strong>
      <p class="meta">ยังไม่ส่งคำขอ — แก้ไขหรือลบได้</p>
      <div class="table-wrap" style="margin-top:.5rem"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>รายการ</th><th>วันที่</th><th></th></tr></thead><tbody>
        ${drafts.map(r=>`<tr class="row-clickable" data-detail="${r.transfer_id}">
          <td><code>${r.short_id}</code></td>
          <td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td>
          <td>${r.line_count||0}</td>
          <td>${(r.created_at||"").slice(0,10)}</td>
          <td class="row-actions" style="margin:0">
            <button class="btn btn-ghost" data-detail-btn="${r.transfer_id}">ดู</button>
            <button class="btn btn-ghost" data-edit="${r.transfer_id}">แก้ไข</button>
            <button class="btn btn-ghost" data-del-draft="${r.transfer_id}">ลบ</button>
          </td>
        </tr>`).join("")}
      </tbody></table></div></div>`;
  }
  if(!active.length && !drafts.length){
    el.innerHTML += `<div class="card"><div class="empty">ไม่มีรายการ</div></div>`;
  } else if(active.length){
    el.innerHTML += `<div class="card"><div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>สถานะ</th><th>ความคืบหน้า</th><th>วันที่</th><th></th></tr></thead><tbody>
      ${active.map(r=>{
        const canCancel = r.status==="requested";
        return `<tr class="row-clickable" data-detail="${r.transfer_id}">
        <td><code>${r.short_id}</code></td><td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td>
        <td>${badge(r.status,r.from_branch,r.to_branch)}</td>
        <td>${pipeline(r.status)}</td>
        <td>${(r.requested_at||r.created_at||"").slice(0,10)}</td>
        <td class="row-actions" style="margin:0">
          <button class="btn btn-ghost" data-detail-btn="${r.transfer_id}">ดู</button>
          ${canCancel ? `<button class="btn btn-ghost" data-cancel="${r.transfer_id}">ยกเลิก</button>` : ""}
        </td>
      </tr>`;
      }).join("")}
    </tbody></table></div></div>`;
  }
  el.querySelectorAll("[data-sf]").forEach(b=>b.onclick=()=>{statusFilter=b.dataset.sf; renderStatus(el);});
  el.querySelectorAll("[data-detail-btn]").forEach(b=>b.onclick=e=>{e.stopPropagation(); openRequestDetail(b.dataset.detailBtn);});
  bindDetailRows(el);
  el.querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>editDraft(b.dataset.edit));
  el.querySelectorAll("[data-del-draft]").forEach(b=>b.onclick=()=>deleteDraft(b.dataset.delDraft));
  el.querySelectorAll("[data-cancel]").forEach(b=>b.onclick=()=>cancelRequest(b.dataset.cancel));
}

async function render(){
  updateHeader();
  const el = $("content");
  try{
    if(view==="home") await renderHome(el);
    else if(view==="request") await renderRequest(el);
    else if(view==="prepare") await renderPrepare(el);
    else if(view==="receive") await renderReceive(el);
    else if(view==="status") await renderStatus(el);
  }catch(e){el.innerHTML='<div class="card empty">'+String(e.message||e)+'</div>';}
}

$("btnBack").onclick = goHome;
render();
</script>
</body>
</html>"""

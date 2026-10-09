from __future__ import annotations

import html as html_lib
import json

APP = "kcw-hq-po"
SESSION_COOKIE = "kcw_hq_po"


def page(*, user_name: str = "", stamp_enabled: bool = False) -> str:
    who = (user_name or "operator").strip()
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__STAMP__", "true" if stamp_enabled else "false")
    )


_HTML = r"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light"/>
<title>สั่งซื้อ HQ</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --blue:#1d4ed8;--blue-deep:#1e3a8a;--blue-soft:#dbeafe;--blue-wash:#eff6ff;
  --line:#dbe3ef;--muted:#64748b;--text:#0f172a;--bg:#f4f7fb;--card:#fff;
  --warn:#9a3412;--warn-bg:#fff7ed;--ok:#166534;--ok-bg:#dcfce7;--wait:#9a3412;--wait-bg:#ffedd5;
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{font-family:Prompt,"Noto Sans Thai",system-ui,sans-serif;background:var(--bg);color:var(--text);-webkit-tap-highlight-color:transparent}
button,input{font-family:inherit;touch-action:manipulation}
header{position:sticky;top:0;z-index:8;background:linear-gradient(180deg,#1e40af 0%,#1d4ed8 100%);color:#fff;padding:max(14px,env(safe-area-inset-top)) 14px 12px}
header h1{margin:0;font-size:18px;font-weight:650;letter-spacing:-.01em}
header p{margin:2px 0 10px;font-size:13px;opacity:.9}
.tabs{display:flex;gap:8px}
.tabs button{flex:1;min-height:40px;border:1px solid rgba(255,255,255,.45);background:transparent;color:#fff;border-radius:999px;padding:8px 12px;font-size:14px;font-weight:600}
.tabs button.on{background:#fff;color:var(--blue);border-color:#fff}
main{padding:12px 12px calc(20px + env(safe-area-inset-bottom));max-width:860px;margin:0 auto}
body.has-dock main{padding-bottom:calc(92px + env(safe-area-inset-bottom))}
.note{background:var(--warn-bg);color:var(--warn);border-radius:12px;padding:10px 12px;font-size:13px;line-height:1.45;margin-bottom:12px}
.toolbar{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}
.toggle{display:flex;gap:6px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:4px}
.toggle button{flex:1;min-height:38px;border:0;background:transparent;border-radius:9px;padding:7px 8px;font-size:13px;color:var(--muted);font-weight:600}
.toggle button.on{background:var(--blue);color:#fff}
.bar{display:flex;gap:8px}
input[type=search]{width:100%;min-height:44px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:16px;background:#fff;color:var(--text)}
input[type=search]:focus{outline:2px solid #93c5fd;border-color:var(--blue)}
.count{font-size:12px;color:var(--muted);padding:0 2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;margin-bottom:10px;overflow:hidden;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.card h2{margin:0;padding:12px;font-size:15px;background:var(--blue-wash);display:flex;justify-content:space-between;gap:8px;align-items:flex-start;line-height:1.35}
.card h2 .title{min-width:0;overflow-wrap:anywhere}
.card h2 .count{flex:none;margin-top:2px}
.line{display:grid;grid-template-columns:32px minmax(0,1fr) auto;gap:8px;padding:12px;border-top:1px solid var(--line);align-items:start}
.line .code{font-weight:600;line-height:1.4;overflow-wrap:anywhere}
.sku{display:inline-block;background:var(--blue-soft);color:var(--blue-deep);border-radius:6px;padding:0 6px;font-size:12px;font-weight:700;margin-right:4px;vertical-align:1px}
.line .meta{color:var(--muted);font-size:12px;margin-top:3px;line-height:1.4;overflow-wrap:anywhere}
.ai{color:var(--blue);font-size:12px;margin-top:6px;padding:6px 8px;background:var(--blue-wash);border-radius:8px;line-height:1.4}
.qty{text-align:right;font-weight:700;font-size:16px;color:var(--blue-deep);white-space:nowrap}
input[type=checkbox]{width:22px;height:22px;margin:2px 0 0;accent-color:var(--blue)}
.actions{padding:10px 12px;border-top:1px solid var(--line);display:flex}
.actions button{width:100%;min-height:44px;background:var(--blue);color:#fff;border:0;border-radius:12px;padding:10px 12px;font-weight:650;font-size:14px}
.actions button.ghost{background:#fff;color:var(--warn);border:1px solid #fdba74}
.actions button:disabled{opacity:.6}
.empty,.spin-wrap{color:var(--muted);padding:28px 16px;text-align:center}
.spin-wrap{display:flex;flex-direction:column;align-items:center;gap:10px}
.spin{width:22px;height:22px;border:2.5px solid var(--blue-soft);border-top-color:var(--blue);border-radius:50%;animation:spin .7s linear infinite;display:inline-block}
.spin.sm{width:16px;height:16px;border-width:2px}
@keyframes spin{to{transform:rotate(360deg)}}
.insight{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin-bottom:10px;color:var(--blue-deep);font-size:13px}
.insight[hidden]{display:none}
.badge{flex:none;font-size:12px;font-weight:650;border-radius:999px;padding:3px 8px;background:var(--blue-soft);color:var(--blue-deep)}
.badge.wait{background:var(--wait-bg);color:var(--wait)}
.badge.done{background:var(--ok-bg);color:var(--ok)}
#dock{position:fixed;left:0;right:0;bottom:0;z-index:9;background:#fff;border-top:1px solid var(--line);box-shadow:0 -8px 24px rgba(15,23,42,.08);padding:10px 12px calc(10px + env(safe-area-inset-bottom))}
#dock[hidden]{display:none}
#dock button{width:100%;min-height:46px;border:0;border-radius:12px;background:var(--blue);color:#fff;font-weight:700;font-size:15px}
#busy{position:fixed;inset:0;z-index:30;background:rgba(15,23,42,.38);display:flex;align-items:center;justify-content:center;padding:24px}
#busy[hidden]{display:none}
.busy-card{background:#fff;border-radius:16px;padding:22px 26px;display:flex;flex-direction:column;align-items:center;gap:12px;min-width:180px;box-shadow:0 12px 40px rgba(15,23,42,.18);color:var(--blue-deep);font-weight:600}
@media (min-width:720px){
  header{padding-left:24px;padding-right:24px}
  .tabs{max-width:420px}
  main{padding-left:20px;padding-right:20px}
  .toolbar{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .bar{grid-column:1 / -1}
  .line{padding:12px 14px}
}
</style>
</head>
<body>
<header>
  <h1>สั่งซื้อ HQ</h1>
  <p id="who"></p>
  <div class="tabs">
    <button type="button" id="tabOrder" class="on">รอสั่ง</button>
    <button type="button" id="tabDone">สั่งแล้ว</button>
  </div>
</header>
<main>
  <div id="banner"></div>
  <section id="orderView">
    <div class="toolbar">
      <div class="toggle">
        <button type="button" id="viewVendor" class="on">ตามเจ้าหนี้</button>
        <button type="button" id="viewProduct">ตามสินค้า</button>
      </div>
      <div class="toggle">
        <button type="button" id="srcAll" class="on">ทั้งหมด</button>
        <button type="button" id="srcIclow">ICLOW</button>
        <button type="button" id="srcAi">AI</button>
      </div>
      <div class="bar"><input id="q" type="search" placeholder="ค้นรหัส สินค้า หรือเจ้าหนี้" enterkeyhint="search"/></div>
    </div>
    <div id="insightNote" class="insight" hidden></div>
    <div id="list"><div class="spin-wrap"><span class="spin" aria-hidden="true"></span><span>กำลังโหลดรายการรอสั่ง…</span></div></div>
  </section>
  <section id="doneView" hidden>
    <div id="orders"></div>
  </section>
</main>
<div id="dock" hidden><button type="button" id="dockConfirm">ยืนยันที่เลือก</button></div>
<div id="busy" hidden>
  <div class="busy-card"><span class="spin" aria-hidden="true"></span><div id="busyText">กำลังดำเนินการ…</div></div>
</div>
<script>
const USER = __USER_JSON__;
const STAMP = __STAMP__;
let savedView = "vendor";
try { savedView = localStorage.getItem("hqpo-view") || "vendor"; } catch (e) {}
const state = {items:[], vendors:[], view: savedView, source:"all", q:"", orders:[], busy:false};
document.getElementById("who").textContent = USER;
if(!STAMP){
  document.getElementById("banner").innerHTML = '<div class="note">ยังไม่เปิดบันทึกลง ICLOW (HQ_PO_ICLOW_STAMP_ENABLED) — ดูรายการและคำแนะนำ AI ได้ แต่ยืนยันสั่งซื้อยังไม่ได้</div>';
}

function esc(s){return String(s??"").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function spinner(text){
  return `<div class="spin-wrap" role="status"><span class="spin" aria-hidden="true"></span><span>${esc(text)}</span></div>`;
}
function setBusy(on, text){
  state.busy = !!on;
  const el = document.getElementById("busy");
  document.getElementById("busyText").textContent = text || "กำลังดำเนินการ…";
  el.hidden = !on;
}
function setInsight(text){
  const el = document.getElementById("insightNote");
  if(!text){ el.hidden = true; el.innerHTML = ""; return; }
  el.hidden = false;
  el.innerHTML = `<span class="spin sm" aria-hidden="true"></span><span>${esc(text)}</span>`;
}
function qtyText(n){
  const v = Number(n);
  if(!Number.isFinite(v)) return "—";
  return Math.abs(v-Math.round(v))<1e-9 ? String(Math.round(v)) : String(Math.round(v*100)/100);
}
function vendorTitle(row){
  const name = row.vendor_name || "";
  const code = row.vendor || "";
  if(!code) return "ไม่ระบุเจ้าหนี้";
  return name ? `${name} · ${code}` : code;
}
function match(row){
  if(state.source==="iclow" && row.source==="insight") return false;
  if(state.source==="ai" && !(row.propose_meta || row.source==="insight")) return false;
  const q = state.q.trim().toLowerCase();
  if(!q) return true;
  return [row.bcode, row.descr, row.mcode, row.vendor, row.vendor_name].join(" ").toLowerCase().includes(q);
}
function aiHtml(row){
  const m = row.propose_meta;
  if(!m || !m.ai_qty) return "";
  const note = row.source==="insight" ? " · ไม่แตะ ICLOW" : "";
  return `<div class="ai">AI ${esc(qtyText(m.ai_qty))}${row.ui?(" "+esc(row.ui)):""}${note}<div>${esc(m.reason||"")}</div></div>`;
}
function lineHtml(row){
  const check = row.confirmable && STAMP
    ? `<input type="checkbox" data-id="${row.iclow_id}" data-vendor="${esc(row.vendor||"")}" aria-label="เลือก ${esc(row.bcode||"")}"/>`
    : `<input type="checkbox" disabled/>`;
  const stock = (row.company_qtyoh2==null) ? "" : `คงเหลือรวม ${esc(qtyText(row.company_qtyoh2))} · HQ ${esc(qtyText(row.hq_qtyoh2))} / SYP ${esc(qtyText(row.syp_qtyoh2))}`;
  const mcode = row.mcode ? `<div class="meta">${esc(row.mcode)}</div>` : "";
  return `<div class="line">
    ${check}
    <div>
      <div class="code"><span class="sku">${esc(row.bcode||"—")}</span>${esc(row.descr||"")}</div>
      ${mcode}
      ${stock ? `<div class="meta">${stock}</div>` : ""}
      ${aiHtml(row)}
    </div>
    <div class="qty">${esc(qtyText(row.qty))}<div class="meta">${esc(row.ui||"")}</div></div>
  </div>`;
}
function syncDock(){
  const n = document.querySelectorAll("#list input[type=checkbox][data-id]:checked").length;
  const dock = document.getElementById("dock");
  const show = !!(STAMP && n && !state.busy);
  dock.hidden = !show;
  document.body.classList.toggle("has-dock", show);
  if(show) document.getElementById("dockConfirm").textContent = `ยืนยันที่เลือก ${n} รายการ`;
}
function renderList(){
  const host = document.getElementById("list");
  const items = state.items.filter(match);
  if(!items.length){ host.innerHTML = '<div class="empty">ไม่มีรายการ</div>'; syncDock(); return; }
  if(state.view==="product"){
    host.innerHTML = `<div class="card"><h2><span class="title">สินค้า</span><span class="count">${items.length} รายการ</span></h2>${items.map(lineHtml).join("")}</div>`;
    syncDock();
    return;
  }
  const groups = new Map();
  for(const row of items){
    const key = row.vendor || "";
    if(!groups.has(key)) groups.set(key, {vendor:key, vendor_name:row.vendor_name, lines:[]});
    const g = groups.get(key);
    if(!g.vendor_name && row.vendor_name) g.vendor_name = row.vendor_name;
    g.lines.push(row);
  }
  const ordered = [...groups.values()].sort((a,b) => (a.vendor?0:1)-(b.vendor?0:1) || vendorTitle(a).localeCompare(vendorTitle(b),'th'));
  host.innerHTML = ordered.map(g => {
    const n = g.lines.filter(r => r.confirmable).length;
    const btn = STAMP && n ? `<div class="actions"><button type="button" data-confirm="${esc(g.vendor)}">ยืนยันที่เลือกของเจ้าหนี้นี้</button></div>` : "";
    return `<div class="card"><h2><span class="title">${esc(vendorTitle(g))}</span><span class="count">${g.lines.length} รายการ</span></h2>${g.lines.map(lineHtml).join("")}${btn}</div>`;
  }).join("");
  syncDock();
}
function setView(view){
  state.view = view;
  try { localStorage.setItem("hqpo-view", view); } catch (e) {}
  document.getElementById("viewVendor").classList.toggle("on", view==="vendor");
  document.getElementById("viewProduct").classList.toggle("on", view==="product");
  renderList();
}
function setSource(source){
  state.source = source;
  for(const [id, val] of [["srcAll","all"],["srcIclow","iclow"],["srcAi","ai"]]){
    document.getElementById(id).classList.toggle("on", source===val);
  }
  renderList();
}
async function loadInsight(){
  setInsight("กำลังโหลดคำแนะนำ AI…");
  try {
    const res = await fetch("/hq-po/api/insight");
    if(!res.ok){ setInsight(""); return; }
    const data = await res.json();
    const extra = data.items || [];
    const have = new Set(state.items.filter(row => row.source==="insight").map(row => row.bcode));
    const add = extra.filter(row => row.bcode && !have.has(row.bcode));
    if(add.length){
      state.items = state.items.concat(add);
      renderList();
    }
  } catch (err) {
  } finally {
    setInsight("");
  }
}
async function loadSuggest(){
  const host = document.getElementById("list");
  host.innerHTML = spinner("กำลังโหลดรายการรอสั่ง…");
  syncDock();
  try {
    const res = await fetch("/hq-po/api/suggest");
    if(!res.ok){ host.innerHTML = '<div class="empty">โหลดรายการไม่ได้</div>'; return; }
    const data = await res.json();
    state.items = data.items || [];
    state.vendors = data.vendors || [];
    renderList();
    if(data.insight_pending) loadInsight();
  } catch (err) {
    host.innerHTML = '<div class="empty">โหลดรายการไม่ได้</div>';
  }
}
function checkedFor(vendor){
  const boxes = [...document.querySelectorAll(`input[type=checkbox][data-vendor="${CSS.escape(vendor)}"]:checked`)];
  return boxes.map(box => {
    const id = Number(box.dataset.id);
    return state.items.find(row => row.iclow_id===id);
  }).filter(Boolean);
}
function checkedRows(){
  return [...document.querySelectorAll("#list input[type=checkbox][data-id]:checked")]
    .map(box => state.items.find(row => row.iclow_id===Number(box.dataset.id)))
    .filter(Boolean);
}
async function postVendor(vendor, picked){
  const sample = picked[0];
  const res = await fetch("/hq-po/api/orders", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      vendor: vendor,
      vendor_name: sample.vendor_name || "",
      lines: picked.map(row => ({iclow_id: row.iclow_id, propose_meta: row.propose_meta || null})),
    }),
  });
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.message || "สั่งซื้อไม่สำเร็จ");
  return data.docno || "";
}
async function confirmRows(rows){
  if(state.busy) return;
  const byVendor = new Map();
  for(const row of rows){
    if(!row || !row.confirmable) continue;
    const key = row.vendor || "";
    if(!byVendor.has(key)) byVendor.set(key, []);
    byVendor.get(key).push(row);
  }
  if(!byVendor.size){ alert("เลือกรายการ ICLOW ก่อน"); return; }
  const docs = [];
  let failed = null;
  setBusy(true, "กำลังบันทึกใบสั่งซื้อ…");
  try{
    for(const [vendor, picked] of byVendor) docs.push(await postVendor(vendor, picked));
  }catch(err){
    failed = err;
  }finally{
    setBusy(false);
  }
  if(failed){
    alert(failed.message || "สั่งซื้อไม่สำเร็จ");
    await loadSuggest();
    return;
  }
  alert("สั่งแล้ว " + docs.filter(Boolean).join(", "));
  await loadSuggest();
}
async function confirmVendor(vendor){
  await confirmRows(checkedFor(vendor));
}
async function loadOrders(){
  const host = document.getElementById("orders");
  host.innerHTML = spinner("กำลังโหลดใบที่สั่งแล้ว…");
  try {
    const res = await fetch("/hq-po/api/orders");
    if(!res.ok){ host.innerHTML = '<div class="empty">โหลดใบที่สั่งแล้วไม่ได้</div>'; return; }
    const data = await res.json();
    const orders = data.orders || [];
    if(!orders.length){ host.innerHTML = '<div class="empty">ยังไม่มีใบสั่งซื้อ</div>'; return; }
    host.innerHTML = orders.map(order => {
      const badge = order.receive_label==="รับแล้ว" ? "done" : "wait";
      const lines = (order.lines||[]).map(line => {
        const rec = line.receive || {};
        const pi = rec.pimas_billno ? ` · PI ${esc(rec.pimas_billno)}` : (rec.rcvdno ? ` · ${esc(rec.rcvdno)}` : "");
        return `<div class="line"><div></div><div><div class="code"><span class="sku">${esc(line.bcode||"—")}</span>${esc(line.descr||"")}</div><div class="meta">${esc(rec.label||"")}${pi}</div></div><div class="qty">${esc(qtyText(line.qty))}</div></div>`;
      }).join("");
      const cancel = STAMP && order.receive_label!=="รับแล้ว"
        ? `<div class="actions"><button type="button" class="ghost" data-cancel="${esc(order.order_id)}">ยกเลิกใบนี้</button></div>` : "";
      const title = order.vendor_name || order.vendor_acctno || "ไม่ระบุเจ้าหนี้";
      return `<div class="card"><h2><span class="title">${esc(order.docno)} · ${esc(title)}</span><span class="badge ${badge}">${esc(order.receive_label||"")}</span></h2>${lines}${cancel}</div>`;
    }).join("");
  } catch (err) {
    host.innerHTML = '<div class="empty">โหลดใบที่สั่งแล้วไม่ได้</div>';
  }
}
async function cancelOrder(id){
  if(state.busy) return;
  if(!confirm("ยกเลิกใบนี้และคืน ICLOW เป็นรอสั่งซื้อ?")) return;
  setBusy(true, "กำลังยกเลิก…");
  let failed = null;
  try {
    const res = await fetch(`/hq-po/api/orders/${id}/cancel`, {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"});
    const data = await res.json().catch(()=>({}));
    if(!res.ok) failed = new Error(data.message || "ยกเลิกไม่สำเร็จ");
  } catch (err) {
    failed = err;
  } finally {
    setBusy(false);
  }
  if(failed){ alert(failed.message || "ยกเลิกไม่สำเร็จ"); return; }
  await loadOrders();
  await loadSuggest();
}
document.getElementById("viewVendor").onclick = () => setView("vendor");
document.getElementById("viewProduct").onclick = () => setView("product");
document.getElementById("srcAll").onclick = () => setSource("all");
document.getElementById("srcIclow").onclick = () => setSource("iclow");
document.getElementById("srcAi").onclick = () => setSource("ai");
document.getElementById("q").oninput = (e) => { state.q = e.target.value; renderList(); };
document.getElementById("tabOrder").onclick = () => {
  document.getElementById("tabOrder").classList.add("on");
  document.getElementById("tabDone").classList.remove("on");
  document.getElementById("orderView").hidden = false;
  document.getElementById("doneView").hidden = true;
};
document.getElementById("tabDone").onclick = () => {
  document.getElementById("tabDone").classList.add("on");
  document.getElementById("tabOrder").classList.remove("on");
  document.getElementById("orderView").hidden = true;
  document.getElementById("doneView").hidden = false;
  loadOrders();
};
document.getElementById("list").onclick = (e) => {
  const btn = e.target.closest("[data-confirm]");
  if(btn){ confirmVendor(btn.getAttribute("data-confirm") || ""); return; }
};
document.getElementById("list").onchange = () => syncDock();
document.getElementById("dockConfirm").onclick = () => confirmRows(checkedRows());
document.getElementById("orders").onclick = (e) => {
  const btn = e.target.closest("[data-cancel]");
  if(btn) cancelOrder(btn.getAttribute("data-cancel"));
};
document.getElementById("viewVendor").classList.toggle("on", state.view!=="product");
document.getElementById("viewProduct").classList.toggle("on", state.view==="product");
loadSuggest();
</script>
</body>
</html>
"""

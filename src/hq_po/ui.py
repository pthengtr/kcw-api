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
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<meta name="color-scheme" content="light"/>
<title>สั่งซื้อ HQ</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{--acc:#0f766e;--acc-soft:#ccfbf1;--line:#e5e7eb;--muted:#6b7280;--text:#111827;--bg:#f4f7f6;--card:#fff;--warn:#9a3412;--ai:#1d4ed8}
*{box-sizing:border-box}
body{margin:0;font-family:Prompt,sans-serif;background:var(--bg);color:var(--text)}
header{background:var(--acc);color:#fff;padding:14px 16px 12px}
header h1{margin:0;font-size:18px;font-weight:600}
header p{margin:4px 0 0;font-size:13px;opacity:.9}
main{padding:12px;max-width:980px;margin:0 auto}
.tabs,.toggle{display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap}
button,select{font-family:inherit}
.tabs button,.toggle button{border:1px solid var(--line);background:#fff;border-radius:999px;padding:6px 12px;font-size:13px}
.tabs button.on,.toggle button.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.bar{display:flex;gap:8px;margin-bottom:10px}
input[type=search]{flex:1;border:1px solid var(--line);border-radius:10px;padding:8px 10px;font:inherit}
.note{background:#fff7ed;color:var(--warn);border-radius:10px;padding:10px 12px;font-size:13px;margin-bottom:10px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;margin-bottom:10px;overflow:hidden}
.card h2{margin:0;padding:10px 12px;font-size:15px;background:#f0fdfa;display:flex;justify-content:space-between;gap:8px;align-items:center}
.card h2 span{color:var(--muted);font-weight:500;font-size:12px}
.line{display:grid;grid-template-columns:28px 1fr auto;gap:8px;padding:10px 12px;border-top:1px solid var(--line);align-items:start}
.line .code{font-weight:600}
.line .meta{color:var(--muted);font-size:12px;margin-top:2px}
.ai{color:var(--ai);font-size:12px;margin-top:4px}
.qty{text-align:right;font-weight:600}
.actions{padding:10px 12px;border-top:1px solid var(--line);display:flex;justify-content:flex-end}
.actions button,.ghost{background:var(--acc);color:#fff;border:0;border-radius:10px;padding:8px 12px;font-weight:600}
.ghost{background:#fff;color:var(--warn);border:1px solid #fdba74}
.empty{color:var(--muted);padding:24px;text-align:center}
.badge{font-size:12px;border-radius:999px;padding:2px 8px;background:var(--acc-soft);color:#115e59}
.badge.wait{background:#ffedd5;color:#9a3412}
.badge.done{background:#dcfce7;color:#166534}
.err{color:#b91c1c;font-size:13px;margin:8px 0}
</style>
</head>
<body>
<header>
  <h1>สั่งซื้อ HQ</h1>
  <p id="who"></p>
</header>
<main>
  <div class="tabs">
    <button type="button" id="tabOrder" class="on">รอสั่ง</button>
    <button type="button" id="tabDone">สั่งแล้ว</button>
  </div>
  <div id="banner"></div>
  <section id="orderView">
    <div class="toggle">
      <button type="button" id="viewVendor" class="on">ตามเจ้าหนี้</button>
      <button type="button" id="viewProduct">ตามสินค้า</button>
    </div>
    <div class="toggle">
      <button type="button" id="srcAll" class="on">ทั้งหมด</button>
      <button type="button" id="srcIclow">ICLOW</button>
      <button type="button" id="srcAi">AI</button>
    </div>
    <div class="bar"><input id="q" type="search" placeholder="ค้นรหัส สินค้า หรือเจ้าหนี้"/></div>
    <div id="list"></div>
  </section>
  <section id="doneView" hidden>
    <div id="orders"></div>
  </section>
</main>
<script>
const USER = __USER_JSON__;
const STAMP = __STAMP__;
const state = {items:[], vendors:[], view: localStorage.getItem("hqpo-view") || "vendor", source:"all", q:"", orders:[]};
document.getElementById("who").textContent = USER;
if(!STAMP){
  document.getElementById("banner").innerHTML = '<div class="note">ยังไม่เปิดบันทึกลง ICLOW (HQ_PO_ICLOW_STAMP_ENABLED) — ดูรายการและคำแนะนำ AI ได้ แต่ยืนยันสั่งซื้อยังไม่ได้</div>';
}

function esc(s){return String(s??"").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
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
    ? `<input type="checkbox" data-id="${row.iclow_id}" data-vendor="${esc(row.vendor||"")}"/>`
    : `<input type="checkbox" disabled/>`;
  const stock = (row.company_qtyoh2==null) ? "" : `คงเหลือรวม ${esc(qtyText(row.company_qtyoh2))} (HQ ${esc(qtyText(row.hq_qtyoh2))} / SYP ${esc(qtyText(row.syp_qtyoh2))})`;
  return `<div class="line">
    ${check}
    <div>
      <div class="code">${esc(row.bcode)} ${esc(row.descr||"")}</div>
      <div class="meta">${esc(row.mcode||"")} ${stock}</div>
      ${aiHtml(row)}
    </div>
    <div class="qty">${esc(qtyText(row.qty))}<div class="meta">${esc(row.ui||"")}</div></div>
  </div>`;
}
function renderList(){
  const host = document.getElementById("list");
  const items = state.items.filter(match);
  if(!items.length){ host.innerHTML = '<div class="empty">ไม่มีรายการ</div>'; return; }
  if(state.view==="product"){
    const btn = STAMP ? `<div class="actions"><button type="button" id="confirmProduct">ยืนยันที่เลือก (แยกใบตามเจ้าหนี้)</button></div>` : "";
    host.innerHTML = `<div class="card"><h2>สินค้า <span>${items.length}</span></h2>${items.map(lineHtml).join("")}${btn}</div>`;
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
    const btn = STAMP && n ? `<div class="actions"><button type="button" data-confirm="${esc(g.vendor)}">ยืนยันสั่ง ${esc(vendorTitle(g))}</button></div>` : "";
    return `<div class="card"><h2>${esc(vendorTitle(g))} <span>${g.lines.length} รายการ</span></h2>${g.lines.map(lineHtml).join("")}${btn}</div>`;
  }).join("");
}
function setView(view){
  state.view = view;
  localStorage.setItem("hqpo-view", view);
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
async function loadSuggest(){
  const res = await fetch("/hq-po/api/suggest");
  if(!res.ok){ document.getElementById("list").innerHTML = '<div class="empty">โหลดรายการไม่ได้</div>'; return; }
  const data = await res.json();
  state.items = data.items || [];
  state.vendors = data.vendors || [];
  renderList();
}
function checkedFor(vendor){
  const boxes = [...document.querySelectorAll(`input[type=checkbox][data-vendor="${CSS.escape(vendor)}"]:checked`)];
  return boxes.map(box => {
    const id = Number(box.dataset.id);
    return state.items.find(row => row.iclow_id===id);
  }).filter(Boolean);
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
  const byVendor = new Map();
  for(const row of rows){
    if(!row || !row.confirmable) continue;
    const key = row.vendor || "";
    if(!byVendor.has(key)) byVendor.set(key, []);
    byVendor.get(key).push(row);
  }
  if(!byVendor.size){ alert("เลือกรายการ ICLOW ก่อน"); return; }
  const docs = [];
  try{
    for(const [vendor, picked] of byVendor) docs.push(await postVendor(vendor, picked));
  }catch(err){
    alert(err.message || "สั่งซื้อไม่สำเร็จ");
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
      return `<div class="line"><div></div><div><div class="code">${esc(line.bcode)} ${esc(line.descr||"")}</div><div class="meta">${esc(rec.label||"")}${pi}</div></div><div class="qty">${esc(qtyText(line.qty))}</div></div>`;
    }).join("");
    const cancel = STAMP && order.receive_label!=="รับแล้ว"
      ? `<div class="actions"><button type="button" class="ghost" data-cancel="${esc(order.order_id)}">ยกเลิกใบนี้</button></div>` : "";
    const title = order.vendor_name || order.vendor_acctno || "ไม่ระบุเจ้าหนี้";
    return `<div class="card"><h2>${esc(order.docno)} · ${esc(title)} <span class="badge ${badge}">${esc(order.receive_label||"")}</span></h2>${lines}${cancel}</div>`;
  }).join("");
}
async function cancelOrder(id){
  if(!confirm("ยกเลิกใบนี้และคืน ICLOW เป็นรอสั่งซื้อ?")) return;
  const res = await fetch(`/hq-po/api/orders/${id}/cancel`, {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"});
  const data = await res.json().catch(()=>({}));
  if(!res.ok){ alert(data.message || "ยกเลิกไม่สำเร็จ"); return; }
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
  if(e.target.closest("#confirmProduct")){
    const picked = [...document.querySelectorAll('#list input[type=checkbox][data-id]:checked')]
      .map(box => state.items.find(row => row.iclow_id===Number(box.dataset.id)))
      .filter(Boolean);
    confirmRows(picked);
  }
};
document.getElementById("orders").onclick = (e) => {
  const btn = e.target.closest("[data-cancel]");
  if(btn) cancelOrder(btn.getAttribute("data-cancel"));
};
setView(state.view==="product" ? "product" : "vendor");
loadSuggest();
</script>
</body>
</html>
"""

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
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'"/>
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
.search-status{display:flex;align-items:center;gap:8px;margin:0;color:var(--blue-deep);font-size:13px;font-weight:650}
.search-status[hidden]{display:none}
input[type=search]{width:100%;min-height:44px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:16px;background:#fff;color:var(--text)}
input[type=search]:focus{outline:2px solid #93c5fd;border-color:var(--blue)}
.count{font-size:12px;color:var(--muted);padding:0 2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;margin-bottom:10px;overflow:hidden;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.card h2{margin:0;padding:12px;font-size:15px;background:var(--blue-wash);display:flex;justify-content:space-between;gap:8px;align-items:flex-start;line-height:1.35}
.card h2 .title{min-width:0;overflow-wrap:anywhere}
.card h2 .count{flex:none;margin-top:2px}
.line{display:grid;grid-template-columns:32px minmax(0,1fr) auto;gap:8px;padding:12px;border-top:1px solid var(--line);align-items:start}
.line.plain{grid-template-columns:minmax(0,1fr) auto}
.line .code{font-weight:600;line-height:1.4;overflow-wrap:anywhere}
.sku{display:inline-block;background:var(--blue-soft);color:var(--blue-deep);border-radius:6px;padding:0 6px;font-size:12px;font-weight:700;margin-right:4px;vertical-align:1px}
.line .meta{color:var(--muted);font-size:12px;margin-top:3px;line-height:1.4;overflow-wrap:anywhere}
.ai{color:var(--blue);font-size:12px;margin-top:6px;padding:6px 8px;background:var(--blue-wash);border-radius:8px;line-height:1.4}
.qty{text-align:right;font-weight:700;font-size:16px;color:var(--blue-deep);white-space:nowrap}
.line button.ghost{display:block;margin-top:8px;min-height:36px;background:#fff;color:var(--warn);border:1px solid #fdba74;border-radius:10px;padding:6px 10px;font-size:13px;font-weight:650}
.recs{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.rec{border:1px solid var(--line);background:#fff;color:var(--blue-deep);border-radius:999px;padding:4px 8px;font-size:12px;font-weight:650}
.rec.off{border:0;background:transparent;color:var(--muted);padding:4px 0}
.qty-edit{display:flex;align-items:center;justify-content:flex-end;gap:6px}
.qty-in{width:84px;min-height:40px;border:1px solid var(--line);border-radius:10px;padding:6px 8px;font-size:16px;font-weight:700;text-align:right;color:var(--blue-deep);background:#fff}
.qty-in:focus{outline:2px solid #93c5fd;border-color:var(--blue)}
.vendor-pick{display:flex;flex-direction:column;gap:4px;margin-top:8px;font-size:12px;color:var(--muted);font-weight:650}
.vendor-pick select{width:100%;max-width:100%;min-height:40px;border:1px solid var(--line);border-radius:10px;padding:6px 8px;font:650 14px Prompt,"Noto Sans Thai",sans-serif;color:var(--text);background:#fff}
.unit-pick{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.unit-pick button,.peer-btn{min-height:36px;border:1px solid var(--line);background:#fff;border-radius:999px;padding:4px 10px;font-size:13px;font-weight:650;color:var(--blue-deep)}
.unit-pick button.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.peer-btn{border-radius:10px;margin-top:8px}
.line-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.line-actions .peer-btn{margin-top:0}
.vendor-card{display:flex;width:100%;justify-content:space-between;align-items:center;gap:8px;text-align:left;background:#fff;border:1px solid var(--line);border-radius:14px;margin-bottom:10px;padding:14px 12px;font:650 15px Prompt,"Noto Sans Thai",sans-serif;color:var(--text);box-shadow:0 1px 2px rgba(15,23,42,.04)}
.vendor-card .title{min-width:0;overflow-wrap:anywhere}
.back{display:block;width:100%;min-height:42px;margin-bottom:10px;border:1px solid var(--line);background:#fff;border-radius:12px;font-weight:650;color:var(--blue-deep)}
.peers{margin-top:8px}
.peer-sec{margin-top:6px}
.peer{display:block;width:100%;text-align:left;border:1px solid var(--line);background:#fff;border-radius:10px;padding:8px 10px;margin-top:4px;font:600 13px Prompt,"Noto Sans Thai",sans-serif;color:var(--text)}
.peer .meta{display:block;font-weight:500}
#sheet{position:fixed;inset:0;z-index:20;background:#eef2f7;overflow:auto;padding:12px 12px calc(118px + env(safe-area-inset-bottom))}
#sheet[hidden]{display:none}
.sheet-top{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.sheet-top button{flex:1 1 40%;min-height:42px;border-radius:12px;border:1px solid var(--line);background:#fff;font-weight:650;font-size:14px}
.sheet-top button.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.sheet-preview{overflow:auto;-webkit-overflow-scrolling:touch}
#printSheet{display:none}
.doc{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 14px;margin:0 auto 12px;max-width:640px}
.doc h2{margin:0;font-size:20px}
.doc .who{margin:4px 0 12px;color:var(--muted);font-size:13px}
.doc table{width:100%;border-collapse:collapse}
.doc th{text-align:left;font-size:12px;color:var(--muted);font-weight:650;border-bottom:1px solid var(--line);padding:6px 4px}
.doc td{border-bottom:1px solid var(--line);padding:8px 4px;vertical-align:top;font-size:14px}
.doc td.num{text-align:right;font-weight:700;white-space:nowrap}
.sheet-foot{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--line);padding:10px 12px calc(10px + env(safe-area-inset-bottom))}
.sheet-foot p{margin:0 0 8px;font-size:12px;color:var(--muted);text-align:center}
.sheet-foot button{width:100%;min-height:46px;border:0;border-radius:12px;background:var(--blue);color:#fff;font-weight:700;font-size:15px}
input[type=checkbox]{width:22px;height:22px;margin:2px 0 0;accent-color:var(--blue)}
.actions{padding:10px 12px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:8px}
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
@media print{
  body[data-print="po"] > *:not(#printSheet){display:none !important}
  body[data-print="po"] #printSheet{display:block !important;background:#fff;color:#111}
}
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
        <button type="button" id="viewProduct" class="on">ตามสินค้า</button>
        <button type="button" id="viewVendor">ตามเจ้าหนี้</button>
      </div>
      <div class="toggle">
        <button type="button" id="srcAll" class="on">ทั้งหมด</button>
        <button type="button" id="srcIclow">ICLOW</button>
        <button type="button" id="srcAi">AI</button>
      </div>
      <div class="bar"><input id="q" type="search" placeholder="ค้นรหัส ชื่อสินค้า ชื่อรุ่น เบอร์แท้ เบอร์โรงงาน ยี่ห้อ หรือเจ้าหนี้" enterkeyhint="search" autocomplete="off"/></div>
      <p id="qStatus" class="search-status" role="status"><span class="spin sm" aria-hidden="true"></span><span id="qStatusText">กำลังโหลดรายการรอสั่ง…</span></p>
    </div>
    <div id="insightNote" class="insight" hidden></div>
    <div id="list"><div class="spin-wrap"><span class="spin" aria-hidden="true"></span><span>กำลังโหลดรายการรอสั่ง…</span></div></div>
  </section>
  <section id="doneView" hidden>
    <div id="orders"></div>
  </section>
</main>
<div id="dock" hidden><button type="button" id="dockConfirm">ดูใบส่งเจ้าหนี้</button></div>
<div id="sheet" hidden>
  <div class="sheet-top">
    <button type="button" id="sheetClose">ปิด</button>
    <button type="button" id="varSimple" class="on">แบบย่อ</button>
    <button type="button" id="varFull">แบบเต็ม</button>
    <button type="button" id="sheetPrint">พิมพ์</button>
    <button type="button" id="sheetCopy">คัดลอกส่งฝ่ายขาย</button>
  </div>
  <div id="sheetBody"></div>
  <div class="sheet-foot">
    <p id="sheetFootNote">ส่งให้ฝ่ายขายก่อน แล้วค่อยบันทึกว่าสั่งแล้ว</p>
    <button type="button" id="sheetCommit">บันทึกว่าสั่งแล้ว</button>
  </div>
</div>
<div id="printSheet" aria-hidden="true"></div>
<div id="busy" hidden>
  <div class="busy-card"><span class="spin" aria-hidden="true"></span><div id="busyText">กำลังดำเนินการ…</div></div>
</div>
<script>
const USER = __USER_JSON__;
const STAMP = __STAMP__;
const state = {items:[], view:"product", vendorKey:null, source:"all", q:"", orders:[], busy:false, loading:true, sheet:[], forms:null, variant:"simple", sheetSaved:false};
let searchTimer = 0;
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
function showSearchStatus(text){
  const el = document.getElementById("qStatus");
  document.getElementById("qStatusText").textContent = text;
  el.hidden = false;
}
function hideSearchStatus(){
  document.getElementById("qStatus").hidden = true;
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
function haystack(row){
  row._hay = [row.bcode, row.descr, row.model, row.pcode, row.mcode, row.brand, row.vendor, row.vendor_name].join(" ").toLowerCase();
  return row._hay;
}
function match(row){
  if(state.source==="iclow" && row.source==="insight") return false;
  if(state.source==="ai" && !(row.propose_meta || row.source==="insight")) return false;
  const q = state.q.trim().toLowerCase();
  if(!q) return true;
  return (row._hay || haystack(row)).includes(q);
}
function rowKey(row){
  if(row.iclow_id) return "iclow:" + row.iclow_id;
  return "ai:" + (row.bcode || "");
}
function findRow(key){
  return state.items.find(row => rowKey(row)===key);
}
function orderQty(row){
  const raw = row.order_qty != null && row.order_qty !== "" ? row.order_qty : row.qty;
  const v = Number(raw);
  return Number.isFinite(v) && v > 0 ? v : 0;
}
function aiQty(row){
  const m = row.propose_meta;
  if(m && m.ai_qty) return Number(m.ai_qty);
  if(row.source==="insight") return Number(row.qty) || 0;
  return 0;
}
function recHtml(row){
  const key = rowKey(row);
  const p9 = Number(row.parts9_qty);
  const ai = aiQty(row);
  const p9el = p9 > 0
    ? `<button type="button" class="rec" data-fill="${esc(key)}" data-fillq="${esc(String(p9))}">PARTS9 ${esc(qtyText(p9))}</button>`
    : `<span class="rec off">PARTS9 —</span>`;
  const aiel = ai > 0
    ? `<button type="button" class="rec" data-fill="${esc(key)}" data-fillq="${esc(String(ai))}">AI ${esc(qtyText(ai))}</button>`
    : `<span class="rec off">AI —</span>`;
  const reason = row.propose_meta && row.propose_meta.reason
    ? `<div class="ai">${esc(row.propose_meta.reason)}</div>` : "";
  return `<div class="recs">${p9el}${aiel}</div>${reason}`;
}
function moneyText(n){
  const v = Number(n);
  if(!Number.isFinite(v) || v <= 0) return "";
  const rounded = Math.round(v * 100) / 100;
  if(Math.abs(rounded - Math.round(rounded)) < 1e-9) return Math.round(rounded).toLocaleString("en-US") + ".-";
  return rounded.toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
}
function productMeta(row){
  const id = [];
  const model = String(row.model || "").trim();
  const pcode = String(row.pcode || "").trim();
  const mcode = String(row.mcode || "").trim();
  const brand = String(row.brand || "").trim();
  if(model) id.push("ชื่อรุ่น " + esc(model));
  if(pcode) id.push("เบอร์แท้ " + esc(pcode));
  if(mcode) id.push("เบอร์โรงงาน " + esc(mcode));
  if(brand) id.push("ยี่ห้อ " + esc(brand));
  const money = [];
  const price = moneyText(row.price);
  const cost = moneyText(row.cost);
  if(price) money.push("ราคา " + price);
  if(cost) money.push("ค่า " + cost);
  return (id.length ? `<div class="meta">${id.join(" · ")}</div>` : "")
    + (money.length ? `<div class="meta">${money.join(" · ")}</div>` : "");
}
function supplierLabel(s){
  const name = String(s.name || "").trim();
  const acct = String(s.acctno || "").trim();
  const bits = [];
  if(name) bits.push(name);
  if(acct && acct !== name) bits.push(acct);
  if(!bits.length) bits.push(acct || "—");
  if(Number(s.bills) > 0) bits.push(String(s.bills) + " บิล");
  if(s.last_date) bits.push(String(s.last_date));
  return bits.join(" · ");
}
function selectedUnit(row){
  return String(row.order_ui || row.ui || row.ui1 || "").trim();
}
function unitHtml(row){
  const ui1 = String(row.ui1 || "").trim();
  const ui2 = String(row.ui2 || "").trim();
  const mtp = Number(row.mtp2);
  const current = selectedUnit(row);
  if(!ui1 || !ui2 || !(mtp > 1) || ui1 === ui2) return "";
  const smallOn = current === ui1 || !current ? " on" : "";
  const largeOn = current === ui2 ? " on" : "";
  return `<div class="unit-pick" role="group" aria-label="หน่วย ${esc(row.bcode || "")}">
    <button type="button" class="unit${smallOn}" data-unit="${esc(rowKey(row))}" data-u="${esc(ui1)}">${esc(ui1)}</button>
    <button type="button" class="unit${largeOn}" data-unit="${esc(rowKey(row))}" data-u="${esc(ui2)}">${esc(ui2)} ×${esc(qtyText(mtp))}</button>
  </div>`;
}
function supplierSelect(row){
  const options = row.suppliers || [];
  if(!options.length) return `<div class="meta">ไม่พบเจ้าหนี้ที่สั่งได้</div>`;
  const opts = options.map(s => {
    const selected = String(row.vendor || "") === String(s.acctno || "") ? " selected" : "";
    return `<option value="${esc(s.acctno || "")}"${selected}>${esc(supplierLabel(s))}</option>`;
  }).join("");
  return `<label class="vendor-pick">เจ้าหนี้<select data-pick="${esc(rowKey(row))}" aria-label="เจ้าหนี้ ${esc(row.bcode || "")}">${opts}</select></label>`;
}
function productTools(row){
  if(!row.bcode) return "";
  const key = esc(rowKey(row));
  return `<div class="line-actions"><button type="button" class="peer-btn" data-vendors="${key}">เปลี่ยนเจ้าหนี้</button><button type="button" class="peer-btn" data-peers="${key}">สินค้าแทน</button></div><div class="peers" data-vendorbox="${key}" hidden></div><div class="peers" data-peerbox="${key}" hidden></div>`;
}
function qtyCell(row){
  if(!(row.confirmable && STAMP)){
    return `<div class="qty">${esc(qtyText(row.qty))}<div class="meta">${esc(row.ui||"")}</div></div>`;
  }
  return `<div class="qty-edit"><input class="qty-in" data-qty="${esc(rowKey(row))}" inputmode="decimal" enterkeyhint="done" value="${esc(qtyText(orderQty(row)))}" aria-label="จำนวน ${esc(row.bcode||"")}"/><span class="meta">${esc(selectedUnit(row))}</span></div>`;
}
function lineHtml(row, mode){
  const pick = mode === "pick";
  const check = !pick ? "" : (row.confirmable && STAMP
    ? `<input type="checkbox" data-key="${esc(rowKey(row))}" data-vendor="${esc(row.vendor||"")}" aria-label="เลือก ${esc(row.bcode||"")}"${row.picked ? " checked" : ""}/>`
    : `<input type="checkbox" disabled/>`);
  const incoming = Number(row.incoming_qty);
  const incomingText = incoming > 0 ? ` · ค้างรับ ${esc(qtyText(incoming))}` : "";
  const packs = Number(row.mtp2);
  const ui2 = String(row.ui2 || "").trim();
  const packText = row.company_qtyoh2 != null && packs > 1 && ui2
    ? ` · ${esc(qtyText(Number(row.company_qtyoh2) / packs))} ${esc(ui2)}` : "";
  const stock = (row.company_qtyoh2==null) ? "" : `คงเหลือรวม ${esc(qtyText(row.company_qtyoh2))} · HQ ${esc(qtyText(row.hq_qtyoh2))} / SYP ${esc(qtyText(row.syp_qtyoh2))}${packText}${incomingText}`;
  const vendorLine = pick ? "" : `<div class="meta" data-vendor-label>${esc(vendorTitle(row))}</div>`;
  const tools = pick ? "" : productTools(row);
  return `<div class="line${pick ? "" : " plain"}" id="line-${esc(rowKey(row))}">
    ${check}
    <div>
      <div class="code"><span class="sku">${esc(row.bcode||"—")}</span>${esc(row.descr||"")}</div>
      ${productMeta(row)}
      ${vendorLine}
      ${unitHtml(row)}
      ${stock ? `<div class="meta">${stock}</div>` : ""}
      ${recHtml(row)}
      ${tools}
    </div>
    ${qtyCell(row)}
  </div>`;
}
function syncDock(){
  const open = state.view === "vendor" && state.vendorKey != null;
  const n = open ? document.querySelectorAll("#list input[type=checkbox][data-key]:checked").length : 0;
  const dock = document.getElementById("dock");
  const show = !!(STAMP && n && !state.busy);
  dock.hidden = !show;
  document.body.classList.toggle("has-dock", show);
  if(show) document.getElementById("dockConfirm").textContent = `ดูใบส่งเจ้าหนี้ ${n} รายการ`;
}
function scheduleRender(label, delay){
  clearTimeout(searchTimer);
  if(state.loading){
    showSearchStatus("กำลังโหลดรายการรอสั่ง…");
    document.getElementById("list").innerHTML = spinner("กำลังโหลดรายการรอสั่ง…");
    syncDock();
    return;
  }
  if(label){
    showSearchStatus(label);
    document.getElementById("list").innerHTML = spinner(label);
    syncDock();
  }
  searchTimer = setTimeout(() => {
    requestAnimationFrame(() => {
      renderList();
      hideSearchStatus();
    });
  }, delay || 0);
}
function vendorGroups(items){
  const groups = new Map();
  for(const row of items){
    const key = row.vendor || "";
    if(!groups.has(key)) groups.set(key, {vendor:key, vendor_name:row.vendor_name || "", lines:[]});
    const g = groups.get(key);
    if(!g.vendor_name && row.vendor_name) g.vendor_name = row.vendor_name;
    g.lines.push(row);
  }
  return [...groups.values()].sort((a,b) => (a.vendor?0:1)-(b.vendor?0:1) || vendorTitle(a).localeCompare(vendorTitle(b),"th"));
}
function renderList(){
  const y = window.scrollY;
  const host = document.getElementById("list");
  if(state.loading){
    showSearchStatus("กำลังโหลดรายการรอสั่ง…");
    host.innerHTML = spinner("กำลังโหลดรายการรอสั่ง…");
    syncDock();
    return;
  }
  const items = state.items.filter(match);
  const typing = document.activeElement && document.activeElement.id === "q";
  if(state.view==="product"){
    host.innerHTML = items.length
      ? `<div class="card"><h2><span class="title">สินค้า</span><span class="count">${items.length} รายการ</span></h2>${items.map(row => lineHtml(row, "product")).join("")}</div>`
      : '<div class="empty">ไม่มีรายการ</div>';
    syncDock();
    if(!typing) window.scrollTo(0, y);
    return;
  }
  if(state.vendorKey == null){
    const groups = vendorGroups(items);
    host.innerHTML = groups.length
      ? groups.map(g => `<button type="button" class="vendor-card" data-open-vendor="${esc(g.vendor)}"><span class="title">${esc(vendorTitle(g))}</span><span class="badge">${g.lines.length}</span></button>`).join("")
      : '<div class="empty">ไม่มีรายการ</div>';
    syncDock();
    if(!typing) window.scrollTo(0, y);
    return;
  }
  const lines = items.filter(row => (row.vendor || "") === state.vendorKey);
  const named = state.items.find(row => (row.vendor || "") === state.vendorKey);
  const title = named ? vendorTitle(named) : (state.vendorKey || "ไม่ระบุเจ้าหนี้");
  const body = lines.length ? lines.map(row => lineHtml(row, "pick")).join("") : '<div class="empty">ไม่มีรายการ</div>';
  host.innerHTML = `<button type="button" class="back" data-vendor-back>เจ้าหนี้ทั้งหมด</button><div class="card"><h2><span class="title">${esc(title)}</span><span class="count">${lines.length} รายการ</span></h2>${body}</div>`;
  syncDock();
  if(!typing) window.scrollTo(0, y);
}
function setView(view){
  state.view = view;
  state.vendorKey = null;
  document.getElementById("viewVendor").classList.toggle("on", view==="vendor");
  document.getElementById("viewProduct").classList.toggle("on", view==="product");
  scheduleRender("กำลังจัดรายการ…", 0);
}
function setSource(source){
  state.source = source;
  for(const [id, val] of [["srcAll","all"],["srcIclow","iclow"],["srcAi","ai"]]){
    document.getElementById(id).classList.toggle("on", source===val);
  }
  scheduleRender("กำลังจัดรายการ…", 0);
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
    for(const row of add) haystack(row);
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
  state.loading = true;
  clearTimeout(searchTimer);
  showSearchStatus("กำลังโหลดรายการรอสั่ง…");
  host.innerHTML = spinner("กำลังโหลดรายการรอสั่ง…");
  syncDock();
  try {
    const res = await fetch("/hq-po/api/suggest");
    if(!res.ok){
      state.loading = false;
      hideSearchStatus();
      host.innerHTML = '<div class="empty">โหลดรายการไม่ได้</div>';
      return;
    }
    const data = await res.json();
    state.items = data.items || [];
    for(const row of state.items) haystack(row);
    state.loading = false;
    hideSearchStatus();
    renderList();
    if(data.insight_pending) loadInsight();
  } catch (err) {
    state.loading = false;
    hideSearchStatus();
    host.innerHTML = '<div class="empty">โหลดรายการไม่ได้</div>';
  }
}
function checkedRows(){
  return [...document.querySelectorAll("#list input[type=checkbox][data-key]:checked")]
    .map(box => findRow(box.dataset.key || ""))
    .filter(Boolean);
}
function linePayload(row){
  const meta = Object.assign({}, row.propose_meta || {});
  if(row.parts9_qty) meta.parts9_qty = row.parts9_qty;
  const body = {qty: orderQty(row), vendor: row.vendor || "", ui: selectedUnit(row), propose_meta: Object.keys(meta).length ? meta : null};
  if(row.iclow_id) body.iclow_id = row.iclow_id;
  else body.bcode = row.bcode;
  return body;
}
async function postVendor(vendor, picked){
  const sample = picked[0];
  const res = await fetch("/hq-po/api/orders", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      vendor: vendor,
      vendor_name: sample.vendor_name || "",
      lines: picked.map(linePayload),
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
  if(!byVendor.size){ alert("เลือกรายการและใส่จำนวน"); return; }
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
  closeSheet();
  alert("สั่งแล้ว " + docs.filter(Boolean).join(", "));
  await loadSuggest();
}
function groupsOf(rows){
  const groups = new Map();
  for(const row of rows){
    if(!row || !row.confirmable || orderQty(row) <= 0) continue;
    const key = row.vendor || "";
    if(!groups.has(key)) groups.set(key, {vendor:key, vendor_name:row.vendor_name, docno:row.docno||"", docdate:row.docdate||"", lines:[]});
    groups.get(key).lines.push(row);
  }
  return [...groups.values()];
}
function sheetPayload(){
  return {
    groups: groupsOf(state.sheet).map(g => ({
      vendor: g.vendor,
      vendor_name: g.vendor_name || "",
      docno: g.docno || "",
      docdate: g.docdate || "",
      lines: g.lines.map(row => ({
        bcode: row.bcode || "",
        descr: row.descr || "",
        qty: orderQty(row),
        ui: selectedUnit(row),
        model: row.model || "",
        brand: row.brand || "",
        pcode: row.pcode || "",
        mcode: row.mcode || "",
      })),
    })),
  };
}
function showVariant(variant){
  state.variant = variant === "full" ? "full" : "simple";
  document.getElementById("varSimple").classList.toggle("on", state.variant==="simple");
  document.getElementById("varFull").classList.toggle("on", state.variant==="full");
  const html = (state.forms && state.forms[state.variant + "_html"]) || "";
  document.getElementById("sheetBody").innerHTML = html
    ? `<div class="sheet-preview">${html}</div>`
    : '<div class="empty">ไม่มีแบบฟอร์ม</div>';
}
function setSheetMode(saved){
  state.sheetSaved = !!saved;
  document.getElementById("sheetCommit").hidden = !!saved;
  document.getElementById("sheetFootNote").textContent = saved
    ? "ใบที่บันทึกแล้ว — พิมพ์หรือคัดลอกส่งฝ่ายขายได้"
    : "ส่งให้ฝ่ายขายก่อน แล้วค่อยบันทึกว่าสั่งแล้ว";
}
async function loadSheetForms(){
  document.getElementById("sheetBody").innerHTML = spinner("กำลังจัดใบสั่งซื้อ…");
  state.forms = null;
  try {
    const res = await fetch("/hq-po/api/sheet", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify(sheetPayload()),
    });
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.message || "จัดใบสั่งซื้อไม่สำเร็จ");
    state.forms = data;
    showVariant(state.variant);
  } catch (err) {
    document.getElementById("sheetBody").innerHTML = `<div class="empty">${esc(err.message || "จัดใบสั่งซื้อไม่สำเร็จ")}</div>`;
  }
}
function currentSheetText(){
  return (state.forms && state.forms[state.variant + "_text"]) || "";
}
function openSheet(rows, opts){
  const picked = (rows||[]).filter(row => row && row.confirmable && orderQty(row) > 0);
  if(!picked.length){ alert("เลือกรายการและใส่จำนวน"); return; }
  state.sheet = picked;
  setSheetMode(!!(opts && opts.saved));
  document.getElementById("sheet").hidden = false;
  window.scrollTo(0,0);
  loadSheetForms();
}
function closeSheet(){
  state.sheet = [];
  const el = document.getElementById("sheet");
  if(el) el.hidden = true;
}
async function loadOrders(){
  const host = document.getElementById("orders");
  host.innerHTML = spinner("กำลังโหลดใบที่สั่งแล้ว…");
  try {
    const res = await fetch("/hq-po/api/orders");
    if(!res.ok){ host.innerHTML = '<div class="empty">โหลดใบที่สั่งแล้วไม่ได้</div>'; return; }
    const data = await res.json();
    const orders = data.orders || [];
    if(!orders.length){ host.innerHTML = '<div class="empty">ยังไม่มีใบสั่งซื้อ</div>'; state.orders = []; return; }
    state.orders = orders;
    host.innerHTML = orders.map(order => {
      const badge = order.receive_label==="รับแล้ว" ? "done" : "wait";
      const lines = (order.lines||[]).map(line => {
        const rec = line.receive || {};
        const pi = rec.pimas_billno ? ` · PI ${esc(rec.pimas_billno)}` : (rec.rcvdno ? ` · ${esc(rec.rcvdno)}` : "");
        const canReturn = STAMP && line.line_id && !rec.received && !rec.unknown;
        const lineCancel = canReturn
          ? `<button type="button" class="ghost" data-cancel-line="${esc(order.order_id)}" data-line="${esc(line.line_id)}" data-bcode="${esc(line.bcode||"")}">ยกเลิกบรรทัด</button>`
          : "";
        return `<div class="line"><div></div><div><div class="code"><span class="sku">${esc(line.bcode||"—")}</span>${esc(line.descr||"")}</div>${productMeta(line)}<div class="meta">${esc(rec.label||"")}${pi}</div>${lineCancel}</div><div class="qty">${esc(qtyText(line.qty))}</div></div>`;
      }).join("");
      const anyReceived = (order.lines||[]).some(line => (line.receive||{}).received);
      const cancel = STAMP && !anyReceived && order.receive_label!=="รับแล้ว"
        ? `<button type="button" class="ghost" data-cancel="${esc(order.order_id)}">ยกเลิกใบนี้</button>` : "";
      const reprint = `<button type="button" data-sheet="${esc(order.order_id)}">พิมพ์ / คัดลอก</button>`;
      const actions = `<div class="actions">${reprint}${cancel}</div>`;
      const title = order.vendor_name || order.vendor_acctno || "ไม่ระบุเจ้าหนี้";
      return `<div class="card"><h2><span class="title">${esc(order.docno)} · ${esc(title)}</span><span class="badge ${badge}">${esc(order.receive_label||"")}</span></h2>${lines}${actions}</div>`;
    }).join("");
  } catch (err) {
    host.innerHTML = '<div class="empty">โหลดใบที่สั่งแล้วไม่ได้</div>';
  }
}
async function cancelLine(orderId, lineId, bcode){
  if(state.busy) return;
  const name = bcode ? ` ${bcode}` : "";
  if(!confirm(`ยกเลิก${name} และคืนไปรายการรอสั่ง?`)) return;
  setBusy(true, "กำลังยกเลิกบรรทัด…");
  let failed = null;
  try {
    const res = await fetch(`/hq-po/api/orders/${orderId}/lines/${lineId}/cancel`, {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"});
    const data = await res.json().catch(()=>({}));
    if(!res.ok) failed = new Error(data.message || "ยกเลิกบรรทัดไม่สำเร็จ");
  } catch (err) {
    failed = err;
  } finally {
    setBusy(false);
  }
  if(failed){ alert(failed.message || "ยกเลิกบรรทัดไม่สำเร็จ"); return; }
  await loadOrders();
  await loadSuggest();
}
async function cancelOrder(id){
  if(state.busy) return;
  if(!confirm("ยกเลิกใบนี้บน ICLOW?")) return;
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
document.getElementById("q").oninput = (e) => {
  state.q = e.target.value;
  scheduleRender(state.loading ? "" : "กำลังค้นหา…", state.loading ? 0 : 180);
};
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
function peerLineHtml(owner, line){
  const bits = [];
  const cost = moneyText(line.cost);
  if(line.brand) bits.push(line.brand);
  if(cost) bits.push("ค่า " + cost);
  if(line.company_qtyoh2 != null) bits.push("คงเหลือ " + qtyText(line.company_qtyoh2));
  if(line.vendor_name || line.vendor) bits.push(line.vendor_name || line.vendor);
  return `<button type="button" class="peer" data-use="${esc(rowKey(owner))}" data-peer="${esc(line.bcode)}"><span class="sku">${esc(line.bcode)}</span>${esc(line.descr||"")}<span class="meta">${esc(bits.join(" · "))}</span></button>`;
}
function peerPanelHtml(row){
  const groups = ((row.peers && row.peers.groups) || []).filter(g => (g.lines||[]).length);
  if(!groups.length) return `<div class="meta">ไม่พบสินค้าแทน</div>`;
  return groups.map(g => `<div class="peer-sec"><div class="meta">${esc(g.label||"")}</div>${(g.lines||[]).map(line => peerLineHtml(row, line)).join("")}</div>`).join("");
}
async function loadPeers(row){
  if(!row || !row.bcode) return;
  const box = document.querySelector(`[data-peerbox="${CSS.escape(rowKey(row))}"]`);
  if(!box) return;
  if(row.peers && box.dataset.open === "1"){
    box.hidden = true;
    box.dataset.open = "";
    return;
  }
  box.hidden = false;
  box.dataset.open = "1";
  if(row.peers){ box.innerHTML = peerPanelHtml(row); return; }
  box.innerHTML = spinner("กำลังหาสินค้าแทน…");
  try {
    const res = await fetch("/hq-po/api/peers/" + encodeURIComponent(row.bcode));
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.message || "หาสินค้าแทนไม่ได้");
    row.peers = data;
    box.innerHTML = peerPanelHtml(row);
  } catch (err) {
    box.innerHTML = `<div class="meta">${esc(err.message || "หาสินค้าแทนไม่ได้")}</div>`;
  }
}
function findPeer(row, bcode){
  const groups = (row.peers && row.peers.groups) || [];
  for(const group of groups){
    const hit = (group.lines||[]).find(line => String(line.bcode||"") === bcode);
    if(hit) return hit;
  }
  return null;
}
function scrollToRow(row){
  const el = document.getElementById("line-" + rowKey(row));
  if(el) el.scrollIntoView({block:"center"});
}
function usePeer(row, bcode){
  if(!row || !bcode) return;
  const hit = findPeer(row, bcode);
  if(!hit) return;
  const existing = state.items.find(item => String(item.bcode||"") === bcode);
  if(!existing && !hit.vendor){
    alert("สินค้านี้ยังไม่มีเจ้าหนี้ที่สั่งได้");
    return;
  }
  if(existing){
    renderList();
    scrollToRow(existing);
    return;
  }
  const added = {
    iclow_id: null,
    source: "peer",
    confirmable: !!hit.vendor,
    vendor: hit.vendor || "",
    vendor_name: hit.vendor_name || "",
    bcode: hit.bcode,
    descr: hit.descr || "",
    model: hit.model || "",
    brand: hit.brand || "",
    pcode: hit.pcode || "",
    mcode: hit.mcode || "",
    ui: hit.ui1 || hit.ui || "",
    ui1: hit.ui1 || hit.ui || "",
    ui2: hit.ui2 || "",
    mtp2: hit.mtp2 || 1,
    price: hit.price,
    cost: hit.cost,
    qty: orderQty(row) || 1,
    order_qty: orderQty(row) || 1,
    hq_qtyoh2: hit.hq_qtyoh2,
    syp_qtyoh2: hit.syp_qtyoh2,
    company_qtyoh2: hit.company_qtyoh2,
    propose_meta: {iclow_origin: "peer"},
  };
  const idx = state.items.indexOf(row);
  state.items.splice(idx < 0 ? state.items.length : idx + 1, 0, added);
  haystack(added);
  renderList();
  scrollToRow(added);
}
async function loadSuppliers(row){
  if(!row || !row.bcode) return;
  const box = document.querySelector(`[data-vendorbox="${CSS.escape(rowKey(row))}"]`);
  if(!box) return;
  if(row.suppliers && box.dataset.open === "1"){
    box.hidden = true;
    box.dataset.open = "";
    return;
  }
  box.hidden = false;
  box.dataset.open = "1";
  if(row.suppliers){ box.innerHTML = supplierSelect(row); return; }
  box.innerHTML = spinner("กำลังหาเจ้าหนี้…");
  try {
    const params = new URLSearchParams();
    if(row.vendor) params.set("current", row.vendor);
    if(row.vendor_name) params.set("current_name", row.vendor_name);
    const qs = params.toString();
    const res = await fetch("/hq-po/api/suppliers/" + encodeURIComponent(row.bcode) + (qs ? "?" + qs : ""));
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.message || "หาเจ้าหนี้ไม่ได้");
    row.suppliers = data.suppliers || [];
    box.innerHTML = supplierSelect(row);
  } catch (err) {
    box.innerHTML = `<div class="meta">${esc(err.message || "หาเจ้าหนี้ไม่ได้")}</div>`;
  }
}
document.getElementById("list").onclick = (e) => {
  const unit = e.target.closest("[data-unit]");
  if(unit){
    const row = findRow(unit.dataset.unit || "");
    const u = unit.dataset.u || "";
    if(row && u){
      row.order_ui = u;
      const line = unit.closest(".line");
      if(line){
        line.querySelectorAll("[data-unit]").forEach(btn => btn.classList.toggle("on", btn.dataset.u === u));
        const meta = line.querySelector(".qty-edit .meta");
        if(meta) meta.textContent = u;
      }
    }
    return;
  }
  const back = e.target.closest("[data-vendor-back]");
  if(back){ state.vendorKey = null; renderList(); return; }
  const open = e.target.closest("[data-open-vendor]");
  if(open){ state.vendorKey = open.getAttribute("data-open-vendor") || ""; renderList(); return; }
  const vendors = e.target.closest("[data-vendors]");
  if(vendors){ loadSuppliers(findRow(vendors.dataset.vendors || "")); return; }
  const peers = e.target.closest("[data-peers]");
  if(peers){ loadPeers(findRow(peers.dataset.peers || "")); return; }
  const use = e.target.closest("[data-use]");
  if(use){ usePeer(findRow(use.dataset.use || ""), use.dataset.peer || ""); return; }
  const fill = e.target.closest("[data-fill]");
  if(fill){
    const row = findRow(fill.dataset.fill || "");
    const q = Number(fill.dataset.fillq);
    if(row && q > 0){
      row.order_qty = q;
      const input = document.querySelector(`input[data-qty="${CSS.escape(fill.dataset.fill || "")}"]`);
      if(input) input.value = qtyText(q);
    }
    return;
  }
};
document.getElementById("list").oninput = (e) => {
  const input = e.target.closest("input[data-qty]");
  if(!input) return;
  const row = findRow(input.dataset.qty || "");
  if(row) row.order_qty = input.value;
};
document.getElementById("list").onchange = (e) => {
  const box = e.target.closest("input[type=checkbox][data-key]");
  if(box){
    const picked = findRow(box.dataset.key || "");
    if(picked) picked.picked = box.checked;
    syncDock();
    return;
  }
  const pick = e.target.closest("select[data-pick]");
  if(!pick){ syncDock(); return; }
  const row = findRow(pick.dataset.pick || "");
  const hit = row && (row.suppliers || []).find(s => s.acctno === pick.value);
  if(hit && row){
    row.vendor = hit.acctno;
    row.vendor_name = hit.name || "";
    row._hay = "";
    haystack(row);
    const line = document.getElementById("line-" + rowKey(row));
    const shown = line && line.querySelector("[data-vendor-label]");
    if(shown) shown.textContent = vendorTitle(row);
  }
};
document.getElementById("dockConfirm").onclick = () => openSheet(checkedRows());
document.getElementById("sheetClose").onclick = () => closeSheet();
document.getElementById("varSimple").onclick = () => { if(state.forms) showVariant("simple"); };
document.getElementById("varFull").onclick = () => { if(state.forms) showVariant("full"); };
document.getElementById("sheetPrint").onclick = () => {
  const html = (state.forms && state.forms[state.variant + "_html"]) || "";
  if(!html){ alert("กำลังจัดใบสั่งซื้อ"); return; }
  document.getElementById("printSheet").innerHTML = html;
  document.body.setAttribute("data-print", "po");
  window.print();
};
window.addEventListener("afterprint", () => document.body.removeAttribute("data-print"));
document.getElementById("sheetCopy").onclick = async () => {
  const text = currentSheetText();
  if(!text){ alert("กำลังจัดใบสั่งซื้อ"); return; }
  try {
    await navigator.clipboard.writeText(text);
    alert("คัดลอกแล้ว วางส่งฝ่ายขายได้");
  } catch (err) {
    alert(text);
  }
};
document.getElementById("sheetCommit").onclick = () => confirmRows(state.sheet || []);
function openSavedSheet(id){
  const order = (state.orders || []).find(row => row.order_id === id);
  if(!order) return;
  const rows = (order.lines || []).filter(line => !line.canceled_at).map(line => ({
    confirmable: true,
    vendor: order.vendor_acctno || "",
    vendor_name: order.vendor_name || "",
    docno: order.docno || "",
    docdate: order.ordered_at || "",
    bcode: line.bcode || "",
    descr: line.descr || "",
    qty: line.qty,
    order_qty: line.qty,
    ui: line.ui || "",
  }));
  openSheet(rows, {saved:true});
}
document.getElementById("orders").onclick = (e) => {
  const sheet = e.target.closest("[data-sheet]");
  if(sheet){ openSavedSheet(sheet.getAttribute("data-sheet")); return; }
  const lineBtn = e.target.closest("[data-cancel-line]");
  if(lineBtn){
    cancelLine(lineBtn.getAttribute("data-cancel-line"), lineBtn.getAttribute("data-line"), lineBtn.getAttribute("data-bcode") || "");
    return;
  }
  const btn = e.target.closest("[data-cancel]");
  if(btn) cancelOrder(btn.getAttribute("data-cancel"));
};
document.getElementById("viewVendor").classList.toggle("on", state.view==="vendor");
document.getElementById("viewProduct").classList.toggle("on", state.view==="product");
loadSuggest();
</script>
</body>
</html>
"""

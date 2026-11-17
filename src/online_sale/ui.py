from __future__ import annotations

import html as html_lib
import json

APP = "kcw-online-sale"
SESSION_COOKIE = "kcw_online_sale"

_HTML = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>ขายออนไลน์</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --red:#9b1c2c;--line:#dbe3ef;--muted:#64748b;--text:#0f172a;--bg:#f4f7fb;--card:#fff;
  --bad:#b42318;--ok:#166534;
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{font-family:Prompt,"Noto Sans Thai",system-ui,sans-serif;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;z-index:8;background:linear-gradient(180deg,#9b1c2c,#7a1624);color:#fff;padding:max(14px,env(safe-area-inset-top)) 14px 12px}
header .top{display:flex;justify-content:space-between;gap:12px;align-items:flex-start}
header h1{margin:0;font-size:18px;font-weight:650;color:#fff}
header p{margin:2px 0 10px;font-size:13px;opacity:.92;color:#fff}
header .badge{font-size:12px;opacity:.95;color:#fff;white-space:nowrap}
.tabs{display:flex;gap:8px;flex-wrap:wrap}
.tabs button{flex:1;min-width:5.5rem;min-height:40px;border:1px solid rgba(255,255,255,.45);background:transparent;color:#fff;border-radius:999px;padding:8px 10px;font:inherit;font-size:13px;font-weight:600;cursor:pointer}
.tabs button.on{background:#fff;color:var(--red);border-color:#fff}
main{padding:12px 12px calc(24px + env(safe-area-inset-bottom));max-width:1100px;margin:0 auto;display:grid;gap:12px}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:end}
.field{display:grid;gap:4px;font-size:13px}
.field span{color:#475467;font-size:12px}
input,select,button,textarea{font:inherit;color:var(--text)}
input,select,textarea{border:1px solid #d0d5dd;border-radius:10px;padding:9px 11px;background:#fff;min-width:0}
button,.btn{border:0;border-radius:10px;padding:9px 12px;background:var(--red);color:#fff;font-weight:600;cursor:pointer}
button.ghost{background:#fff;color:#334155;border:1px solid #d0d5dd}
button:disabled{opacity:.55;cursor:default}
table{width:100%;border-collapse:collapse;font-size:13px;color:var(--text)}
th,td{border-bottom:1px solid #eaecf0;padding:7px 4px;text-align:left;vertical-align:top;color:var(--text)}
.num{text-align:right;white-space:nowrap}
.meta{color:var(--muted);font-size:12px}
.err{color:var(--bad)}
.ok{color:var(--ok)}
.warn{color:#b54708}
.total{font-size:18px;font-weight:700;color:var(--text)}
.hidden{display:none!important}
a{color:var(--red);font-weight:600}
.status-cancel{color:var(--bad);font-weight:700}
.status-draft{color:#1d4ed8;font-weight:700}
.status-printed{color:#b54708;font-weight:700}
.stock-over td{background:#fff1f0}
.edit-banner{background:#fff7ed;border:1px solid #fdba74;color:#9a3412;padding:8px 10px;border-radius:10px;margin-bottom:10px;font-size:13px}
table input.cell{width:5.5rem;padding:6px 8px;border-radius:8px}
table input.cell.price{width:7rem}
.qty-with-unit{display:inline-flex;align-items:center;gap:6px}
.unit-select{min-width:5.5rem;max-width:7.5rem;padding:6px 8px;border-radius:8px;font-weight:600}
table select.unit-select{width:6.5rem;padding:5px 6px}
.pick-bar{display:flex;gap:10px;flex-wrap:wrap;align-items:center;justify-content:space-between;margin:12px 0 8px}
.pick-bar .count{color:var(--muted);font-size:13px}
iframe.toframe{width:100%;min-height:75vh;border:1px solid var(--line);border-radius:14px;background:#fff}
@media(max-width:800px){input,select{width:100%}}
</style>
</head>
<body>
<header>
  <div class="top">
    <div>
      <h1>ขายออนไลน์</h1>
      <p>TAD / CNTAD / ใบเต็ม TO — <span id="who"></span></p>
    </div>
    <div class="badge" id="writeBadge"></div>
  </div>
  <nav class="tabs noprint">
    <button type="button" data-tab="sale" class="on">ขาย</button>
    <button type="button" data-tab="search">ค้นหา</button>
    <button type="button" data-tab="return">คืนสินค้า</button>
    <button type="button" data-tab="to">ใบเต็ม TO</button>
  </nav>
</header>
<main>
<section id="tab-sale" class="panel">
  <div id="editBanner" class="edit-banner hidden"></div>
  <div class="row">
    <label class="field"><span>แพลตฟอร์ม</span>
      <select id="platform"></select>
    </label>
    <label class="field"><span>ร้านค้า</span>
      <select id="shop"><option value="">— เลือกร้าน —</option></select>
    </label>
    <label class="field" style="flex:1;min-width:220px"><span>เลขคำสั่งซื้อ (วางจากแพลตฟอร์ม)</span>
      <input id="po" type="text" inputmode="text" autocomplete="off" spellcheck="false" placeholder="วางเลขคำสั่งซื้อ">
    </label>
    <button type="button" class="ghost" id="checkPo">ตรวจซ้ำ</button>
  </div>
  <p class="meta" id="poStatus"></p>
  <div class="row" style="margin-top:10px">
    <label class="field" style="flex:1;min-width:180px"><span>รหัสสินค้า / บาร์โค้ด</span>
      <input id="bcode" autocomplete="off" placeholder="สแกนหรือพิมพ์แล้ว Enter">
    </label>
    <label class="field"><span>จำนวน</span>
      <span class="qty-with-unit">
        <input id="qty" type="number" min="0.01" step="1" value="1" style="width:6rem">
        <select id="qtyUnit" class="unit-select" disabled><option value="">หน่วย</option></select>
      </span>
    </label>
    <label class="field"><span>ราคา/หน่วย (รวม VAT)</span><input id="price" type="number" min="0.01" step="0.01" style="width:8rem"></label>
    <button type="button" id="addLine">เพิ่ม</button>
  </div>
  <p class="meta" id="prodHint"></p>
  <p class="meta warn hidden" id="stockWarn"></p>
  <table id="linesTable" style="margin-top:12px">
    <thead><tr><th>รหัส</th><th>ชื่อ</th><th>ที่เก็บ</th><th class="num">สต็อก</th><th class="num">จำนวน</th><th>หน่วย</th><th class="num">ราคา</th><th class="num">รวม</th><th></th></tr></thead>
    <tbody></tbody>
  </table>
  <div class="row" style="justify-content:space-between;margin-top:12px">
    <div class="total">ยอดขายรวม <span id="grand">0.00</span></div>
    <div class="row">
      <button type="button" class="ghost hidden" id="cancelEdit">ยกเลิกแก้ไข</button>
      <button type="button" class="ghost" id="saveDraft" disabled>บันทึกฉบับร่าง</button>
      <button type="button" id="saveSale" disabled>บันทึกขาย</button>
    </div>
  </div>
  <p id="saleMsg" class="meta"></p>
</section>

<section id="tab-search" class="panel hidden">
  <div class="row">
    <label class="field" style="flex:1;min-width:180px"><span>ค้นหา TAD / ฉบับร่าง / TO / CNTAD / เลขคำสั่งซื้อ</span>
      <input id="q" autocomplete="off">
    </label>
    <label class="field"><span>ประเภท</span>
      <select id="qKind">
        <option value="">ทั้งหมด</option>
        <option value="draft">ฉบับร่าง</option>
        <option value="tad">TAD / CNTAD</option>
      </select>
    </label>
    <label class="field"><span>แพลตฟอร์ม</span><select id="qPlatform"><option value="">ทั้งหมด</option></select></label>
    <label class="field"><span>ร้าน</span><select id="qShop"><option value="">ทั้งหมด</option></select></label>
    <label class="field"><span>จากวันที่</span><input id="df" type="date"></label>
    <label class="field"><span>ถึงวันที่</span><input id="dt" type="date"></label>
    <button type="button" id="doSearch">ค้นหา</button>
  </div>
  <div id="searchResults" style="margin-top:12px"></div>
</section>

<section id="tab-return" class="panel hidden">
  <div class="row">
    <label class="field" style="flex:1;min-width:200px"><span>เลขบิล TAD อ้างอิง</span>
      <input id="retTad" placeholder="TAD6911-001" autocomplete="off">
    </label>
    <button type="button" id="loadReturn">โหลดบิล</button>
  </div>
  <div id="returnBox" style="margin-top:12px"></div>
</section>

<section id="tab-to" class="panel hidden" style="padding:0;border:0;background:transparent">
  <iframe class="toframe" id="toFrame" title="ใบเต็ม TO" src="/to-bill/"></iframe>
</section>
</main>
<script>
const USER = __USER_JSON__;
const WRITE = __WRITE__;
const state = {
  platforms:[], shops:[], lines:[], product:null, write:WRITE,
  editBillno:null, editDraftId:null, searchBills:[],
  poLenByPlatform: { tiktok:18, lazada:16, shopee:14 },
};

const $ = (id) => document.getElementById(id);
const money = (n) => Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});
function stockUnits(ln){ return Number(ln.qty||0) * (Number(ln.mtp||1) || 1); }
function unitChoices(p){
  const ui1 = ((p && p.ui1) || (p && p.ui) || 'หน่วย').trim() || 'หน่วย';
  const ui2 = ((p && p.ui2) || '').trim();
  const mtp2 = Number((p && p.mtp2) || 1) || 1;
  const out = [{ui:ui1, mtp:1}];
  if (mtp2 > 1 && ui2 && ui2 !== ui1) out.push({ui:ui2, mtp:mtp2});
  return out;
}
function fillUnitSelect(sel, product, chosenUi=''){
  if (!product) {
    sel.innerHTML = '<option value="">หน่วย</option>';
    sel.disabled = true;
    return;
  }
  const choices = unitChoices(product);
  const want = (chosenUi || product.ui || product.ui1 || choices[0].ui || '').trim();
  sel.innerHTML = '';
  sel.disabled = false;
  for (const c of choices) {
    const o = document.createElement('option');
    o.value = c.ui;
    o.dataset.mtp = String(c.mtp);
    o.textContent = c.mtp > 1 ? `${c.ui} (×${c.mtp})` : c.ui;
    if (c.ui === want) o.selected = true;
    sel.appendChild(o);
  }
  if (!sel.value && choices.length) sel.selectedIndex = 0;
}
function selectedUnit(sel){
  const opt = sel && sel.selectedOptions && sel.selectedOptions[0];
  return {
    ui: (sel && sel.value) || 'หน่วย',
    mtp: Number((opt && opt.dataset.mtp) || 1) || 1,
  };
}
function lineUnitSelectHtml(ln, idx){
  const choices = unitChoices(ln);
  const opts = choices.map(c => {
    const sel = c.ui === (ln.ui||'') ? ' selected' : '';
    const label = c.mtp > 1 ? `${c.ui} (×${c.mtp})` : c.ui;
    return `<option value="${c.ui}" data-mtp="${c.mtp}"${sel}>${label}</option>`;
  }).join('');
  return `<select class="unit-select" data-unit="${idx}">${opts || `<option value="${ln.ui||'หน่วย'}" data-mtp="${ln.mtp||1}">${ln.ui||'หน่วย'}</option>`}</select>`;
}

async function api(path, opts={}) {
  const res = await fetch('/online-sale'+path, {
    headers: {'Content-Type':'application/json', ...(opts.headers||{})},
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const err = new Error(data.message || data.detail || data.error || ('HTTP '+res.status));
    err.code = data.error || '';
    err.status = res.status;
    throw err;
  }
  return data;
}

function showTab(name) {
  document.querySelectorAll('.tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab===name));
  ['sale','search','return','to'].forEach(t => $(`tab-${t}`).classList.toggle('hidden', t!==name));
  const url = new URL(location.href);
  url.searchParams.set('tab', name);
  history.replaceState(null, '', url);
}

document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => showTab(b.dataset.tab));

function fillPlatformSelect(sel, withAll=false) {
  sel.innerHTML = withAll ? '<option value="">ทั้งหมด</option>' : '';
  for (const p of state.platforms) {
    const o = document.createElement('option');
    o.value = p.id; o.textContent = p.label;
    sel.appendChild(o);
  }
}

async function loadShops(platform, sel, selected='') {
  sel.innerHTML = '<option value="">— เลือกร้าน —</option>';
  if (!platform) return;
  const data = await api('/api/shops?platform='+encodeURIComponent(platform));
  state.shops = data.shops || [];
  for (const s of state.shops) {
    const o = document.createElement('option');
    o.value = s.acctno;
    o.textContent = `${s.shop_name} (${s.acctno})`;
    if (selected && s.acctno === selected) o.selected = true;
    sel.appendChild(o);
  }
}

function oversoldLines() {
  return state.lines.filter(ln => stockUnits(ln) > Number(ln.qtyoh2||0));
}

function updateStockWarn() {
  const bad = oversoldLines();
  const el = $('stockWarn');
  if (!bad.length) { el.classList.add('hidden'); el.textContent=''; return; }
  el.classList.remove('hidden');
  el.textContent = 'แจ้งเตือน: จำนวนขายเกินสต็อก — ' + bad.map(l => {
    const need = stockUnits(l);
    return `${l.bcode} (${l.qty} ${l.ui||''} = ${need}/${l.qtyoh2})`;
  }).join(', ');
}

function expectedPoLen(platform){
  const key = String(platform || '').trim().toLowerCase();
  const n = state.poLenByPlatform[key];
  return (typeof n === 'number' && n > 0) ? n : null;
}
function poValue(){
  // Keep as plain text — never Number() — so digits are not truncated/changed.
  return String($('po').value || '').trim();
}
function poLengthOk(){
  const po = poValue();
  if (!po) return false;
  const expected = expectedPoLen($('platform').value);
  if (expected == null) return true;
  return po.length === expected;
}
function syncPoStatus(){
  const po = poValue();
  const expected = expectedPoLen($('platform').value);
  const el = $('poStatus');
  if (!po) {
    if (expected != null) {
      el.textContent = `เลขคำสั่งซื้อต้องมี ${expected} ตัวอักษร`;
      el.className = 'meta';
    } else {
      el.textContent = '';
      el.className = 'meta';
    }
    return false;
  }
  if (expected != null && po.length !== expected) {
    el.textContent = `เลขคำสั่งซื้อต้องมี ${expected} ตัวอักษร (ตอนนี้ ${po.length} ตัว) — ตรวจว่าคัดลอกครบหรือไม่`;
    el.className = 'meta err';
    return false;
  }
  if (!el.classList.contains('ok') && !el.classList.contains('err')) {
    el.textContent = expected != null
      ? `เลขคำสั่งซื้อครบ ${expected} ตัวอักษร`
      : `เลขคำสั่งซื้อ ${po.length} ตัวอักษร`;
    el.className = 'meta ok';
  } else if (el.classList.contains('err') && (expected == null || po.length === expected)) {
    el.textContent = expected != null
      ? `เลขคำสั่งซื้อครบ ${expected} ตัวอักษร`
      : `เลขคำสั่งซื้อ ${po.length} ตัวอักษร`;
    el.className = 'meta ok';
  }
  return true;
}
function syncPoMaxLength(){
  const expected = expectedPoLen($('platform').value);
  const inp = $('po');
  if (expected != null) inp.setAttribute('maxlength', String(expected));
  else inp.removeAttribute('maxlength');
}
function saleFormReady(){
  return !!(WRITE && state.lines.length && $('shop').value && poLengthOk());
}
function syncEditBanner() {
  const banner = $('editBanner');
  const cancel = $('cancelEdit');
  if (state.editBillno) {
    banner.classList.remove('hidden');
    banner.textContent = `กำลังแก้ไขบิล ${state.editBillno} — แก้เลขคำสั่งซื้อ แพลตฟอร์ม ร้านค้า รายการ แล้วกดบันทึก`;
    cancel.classList.remove('hidden');
    $('saveSale').textContent = 'บันทึกการแก้ไข';
    $('saveDraft').classList.add('hidden');
  } else if (state.editDraftId) {
    banner.classList.remove('hidden');
    banner.textContent = `กำลังแก้ไขฉบับร่าง — แก้สินค้า/จำนวน/ราคา แล้วกดบันทึกฉบับร่าง หรือยืนยันขายเพื่อออก TAD`;
    cancel.classList.remove('hidden');
    $('saveSale').textContent = 'ยืนยันขาย (ออก TAD)';
    $('saveDraft').classList.remove('hidden');
  } else {
    banner.classList.add('hidden');
    banner.textContent = '';
    cancel.classList.add('hidden');
    $('saveSale').textContent = 'บันทึกขาย';
    $('saveDraft').classList.remove('hidden');
  }
}

function clearSaleForm() {
  state.editBillno = null;
  state.editDraftId = null;
  state.lines = [];
  state.product = null;
  $('po').value = '';
  $('bcode').value = '';
  $('qty').value = '1';
  $('price').value = '';
  fillUnitSelect($('qtyUnit'), null);
  $('qtyUnit').disabled = true;
  $('prodHint').textContent = '';
  $('poStatus').textContent = '';
  $('saleMsg').textContent = '';
  syncEditBanner();
  syncPoMaxLength();
  syncPoStatus();
  renderLines();
}

function renderLines() {
  const tb = $('linesTable').querySelector('tbody');
  tb.innerHTML = '';
  let grand = 0;
  state.lines.forEach((ln, idx) => {
    grand += Number(ln.qty) * Number(ln.price);
    const over = stockUnits(ln) > Number(ln.qtyoh2||0);
    const tr = document.createElement('tr');
    if (over) tr.className = 'stock-over';
    tr.innerHTML = `<td>${ln.bcode}</td><td>${ln.descr||''}</td><td>${ln.location||''}</td>
      <td class="num">${ln.qtyoh2}</td>
      <td class="num"><input class="cell" data-f="qty" data-i="${idx}" type="number" min="0.01" step="1" value="${ln.qty}"></td>
      <td>${lineUnitSelectHtml(ln, idx)}</td>
      <td class="num"><input class="cell price" data-f="price" data-i="${idx}" type="number" min="0.01" step="0.01" value="${ln.price}"></td>
      <td class="num">${money(ln.qty*ln.price)}</td>
      <td><button type="button" class="ghost" data-del="${idx}">ลบ</button></td>`;
    tb.appendChild(tr);
  });
  function refreshTotals() {
    let g = 0;
    state.lines.forEach((ln, i) => {
      g += Number(ln.qty) * Number(ln.price);
      const row = tb.children[i];
      if (!row) return;
      row.classList.toggle('stock-over', stockUnits(ln) > Number(ln.qtyoh2||0));
      const sumCell = row.querySelector('td:nth-child(8)');
      if (sumCell) sumCell.textContent = money(ln.qty * ln.price);
    });
    $('grand').textContent = money(g);
    updateStockWarn();
    const ready = saleFormReady();
    $('saveSale').disabled = !ready;
    $('saveDraft').disabled = !ready || !!state.editBillno;
  }
  tb.querySelectorAll('input[data-f]').forEach(inp => {
    inp.oninput = () => {
      const i = Number(inp.dataset.i);
      const f = inp.dataset.f;
      const v = Number(inp.value||0);
      if (!state.lines[i]) return;
      state.lines[i][f] = v;
      if (f === 'qty' && stockUnits(state.lines[i]) > Number(state.lines[i].qtyoh2||0)) {
        const need = stockUnits(state.lines[i]);
        $('saleMsg').textContent = `${state.lines[i].bcode} จำนวน ${v} ${state.lines[i].ui||''} (=${need}) เกินสต็อกคงเหลือ ${state.lines[i].qtyoh2}`;
        $('saleMsg').className = 'meta warn';
      }
      refreshTotals();
    };
  });
  tb.querySelectorAll('select[data-unit]').forEach(sel => {
    sel.onchange = () => {
      const i = Number(sel.dataset.unit);
      const ln = state.lines[i];
      if (!ln) return;
      const next = selectedUnit(sel);
      const oldMtp = Number(ln.mtp||1) || 1;
      const newMtp = next.mtp;
      if (oldMtp !== newMtp && oldMtp > 0 && newMtp > 0) {
        const factor = oldMtp / newMtp;
        ln.qty = Number((Number(ln.qty||0) * factor).toFixed(4));
        ln.price = Number((Number(ln.price||0) / factor).toFixed(2));
      }
      ln.ui = next.ui;
      ln.mtp = newMtp;
      renderLines();
    };
  });
  tb.querySelectorAll('button[data-del]').forEach(b => b.onclick = () => {
    state.lines.splice(Number(b.dataset.del),1); renderLines();
  });
  $('grand').textContent = money(grand);
  updateStockWarn();
  syncEditBanner();
  const ready = saleFormReady();
  $('saveSale').disabled = !ready;
  $('saveDraft').disabled = !ready || !!state.editBillno;
}

async function lookupProduct() {
  const code = $('bcode').value.trim();
  if (!code) return;
  try {
    const data = await api('/api/product?code='+encodeURIComponent(code));
    state.product = data.product;
    fillUnitSelect($('qtyUnit'), data.product);
    const units = unitChoices(data.product).map(c => c.mtp > 1 ? `${c.ui}×${c.mtp}` : c.ui).join('/');
    $('prodHint').textContent = `${data.product.descr} · หน่วย ${units || data.product.ui || 'หน่วย'} · สต็อก ${data.product.qtyoh2} · ที่เก็บ ${data.product.location||'-'}`;
    $('prodHint').className = 'meta ok';
    $('bcode').value = data.product.bcode;
  } catch (e) {
    state.product = null;
    fillUnitSelect($('qtyUnit'), null);
    $('qtyUnit').disabled = true;
    $('prodHint').textContent = e.message;
    $('prodHint').className = 'meta err';
  }
}

function addLine() {
  if (!state.product) { lookupProduct().then(() => { if (state.product) addLine(); }); return; }
  const qty = Number($('qty').value||0);
  const price = Number($('price').value||0);
  const unit = selectedUnit($('qtyUnit'));
  if (qty<=0 || price<=0) { $('saleMsg').textContent='ใส่จำนวนและราคา'; $('saleMsg').className='meta err'; return; }
  const need = qty * (unit.mtp || 1);
  if (need > Number(state.product.qtyoh2||0)) {
    const ok = confirm(`${state.product.bcode} จำนวน ${qty} ${unit.ui} (=${need}) เกินสต็อกคงเหลือ ${state.product.qtyoh2}\\nต้องการเพิ่มรายการต่อหรือไม่?`);
    if (!ok) return;
  }
  const existing = state.lines.find(l =>
    l.bcode===state.product.bcode && Number(l.price)===price && (l.ui||'')===unit.ui
  );
  if (existing) existing.qty = Number(existing.qty) + qty;
  else state.lines.push({
    bcode: state.product.bcode,
    descr: state.product.descr,
    location: state.product.location,
    qtyoh2: state.product.qtyoh2,
    ui: unit.ui,
    ui1: state.product.ui1 || state.product.ui,
    ui2: state.product.ui2 || '',
    mtp2: state.product.mtp2 || 1,
    mtp: unit.mtp,
    qty, price,
  });
  $('bcode').value=''; $('qty').value='1'; $('price').value='';
  fillUnitSelect($('qtyUnit'), null);
  $('qtyUnit').disabled = true;
  state.product=null; $('prodHint').textContent='';
  renderLines(); $('bcode').focus();
}

async function hydrateLines(sourceLines, { creditStock=false } = {}) {
  const lines = [];
  for (const ln of sourceLines || []) {
    let qtyoh2 = 0, location = ln.location1 || ln.location || '', descr = ln.detail || ln.descr || '';
    let ui1 = ln.ui || 'หน่วย', ui2 = '', mtp2 = 1;
    try {
      const prod = await api('/api/product?code='+encodeURIComponent(ln.bcode));
      qtyoh2 = prod.product.qtyoh2;
      location = prod.product.location || location;
      descr = prod.product.descr || descr;
      ui1 = prod.product.ui1 || prod.product.ui || ui1;
      ui2 = prod.product.ui2 || '';
      mtp2 = Number(prod.product.mtp2 || 1) || 1;
    } catch (_) {}
    const mtp = Number(ln.mtp || 0) > 0
      ? Number(ln.mtp)
      : ((ln.ui || '') === ui2 && mtp2 > 1 ? mtp2 : 1);
    if (creditStock) {
      // When editing TAD, available stock includes qty already on this bill (base units).
      qtyoh2 = Number(qtyoh2) + Math.abs(Number(ln.qty)||0) * (mtp || 1);
    }
    lines.push({
      bcode: ln.bcode,
      descr,
      location,
      qtyoh2,
      ui: ln.ui || ui1 || 'หน่วย',
      ui1,
      ui2,
      mtp2,
      mtp,
      qty: Math.abs(Number(ln.qty)||0),
      price: Number(ln.price)||0,
    });
  }
  return lines;
}

async function loadBillForEdit(billno) {
  const data = await api('/api/bills/'+encodeURIComponent(billno));
  const bill = data.bill;
  if (bill.kind !== 'tad') throw new Error('แก้ไขได้เฉพาะบิล TAD');
  if (bill.canceled) throw new Error('บิลนี้ถูกยกเลิกแล้ว');
  state.editBillno = bill.billno;
  state.editDraftId = null;
  if (bill.platform) $('platform').value = bill.platform;
  await loadShops($('platform').value, $('shop'), bill.acctno);
  syncPoMaxLength();
  $('po').value = bill.online_po || '';
  syncPoStatus();
  state.lines = await hydrateLines(bill.lines || [], { creditStock:true });
  syncEditBanner();
  renderLines();
  showTab('sale');
  $('saleMsg').textContent = `โหลดบิล ${bill.billno} แล้ว — แก้ไขได้เลย`;
  $('saleMsg').className = 'meta ok';
}

async function loadDraftForEdit(draftId) {
  const data = await api('/api/drafts/'+encodeURIComponent(draftId));
  const draft = data.draft;
  if (draft.canceled || draft.status === 'canceled') throw new Error('ฉบับร่างนี้ถูกยกเลิกแล้ว');
  if (draft.status === 'sold') throw new Error('ฉบับร่างนี้ยืนยันขายไปแล้ว');
  state.editDraftId = draft.draft_id;
  state.editBillno = null;
  if (draft.platform) $('platform').value = draft.platform;
  await loadShops($('platform').value, $('shop'), draft.acctno);
  syncPoMaxLength();
  $('po').value = draft.online_po || '';
  syncPoStatus();
  state.lines = await hydrateLines(draft.lines || []);
  syncEditBanner();
  renderLines();
  showTab('sale');
  const stamped = draft.pick_printed || draft.status === 'printed' ? ' (พิมพ์ใบจัดแล้ว)' : '';
  $('saleMsg').textContent = `โหลดฉบับร่างคำสั่งซื้อ ${draft.online_po||''}${stamped} — แก้แล้วกดยืนยันขายเพื่อออก TAD`;
  $('saleMsg').className = 'meta ok';
}

function salePayload(allow, confirmUnmapped=false){
  return {
    acctno: $('shop').value,
    online_po: poValue(),
    platform: $('platform').value,
    draft_id: state.editDraftId || '',
    allow_oversell: !!allow,
    confirm_unmapped: !!confirmUnmapped,
    lines: state.lines.map(l => ({
      bcode:l.bcode, qty:l.qty, price:l.price, detail:l.descr, descr:l.descr,
      ui:l.ui, mtp:l.mtp, ui1:l.ui1, ui2:l.ui2, mtp2:l.mtp2,
      location:l.location, location1:l.location, qtyoh2:l.qtyoh2,
    })),
  };
}

async function confirmUnmappedOrThrow(err){
  if (err && err.code === 'staff_unmapped') {
    const ok = confirm(err.message + '\\n\\nยืนยันออกเอกสารด้วยชื่อ LINE ชั่วคราวหรือไม่?');
    if (ok) return true;
  }
  throw err;
}

async function init() {
  $('who').textContent = USER || 'operator';
  $('writeBadge').textContent = WRITE ? 'บันทึกได้' : 'โหมดอ่านอย่างเดียว (ยังไม่เปิด WRITE)';
  const meta = await api('/api/meta');
  state.platforms = meta.platforms || [];
  state.write = !!meta.write_enabled;
  if (meta.po_len_by_platform && typeof meta.po_len_by_platform === 'object') {
    state.poLenByPlatform = Object.assign({}, state.poLenByPlatform, meta.po_len_by_platform);
  }
  fillPlatformSelect($('platform'));
  fillPlatformSelect($('qPlatform'), true);
  await loadShops($('platform').value, $('shop'));
  syncPoMaxLength();
  syncPoStatus();
  $('platform').onchange = async () => {
    await loadShops($('platform').value, $('shop'));
    syncPoMaxLength();
    syncPoStatus();
    renderLines();
  };
  $('qPlatform').onchange = async () => {
    $('qShop').innerHTML = '<option value="">ทั้งหมด</option>';
    if (!$('qPlatform').value) return;
    const data = await api('/api/shops?platform='+encodeURIComponent($('qPlatform').value));
    for (const s of data.shops||[]) {
      const o=document.createElement('option'); o.value=s.acctno; o.textContent=`${s.shop_name} (${s.acctno})`;
      $('qShop').appendChild(o);
    }
  };
  $('shop').onchange = renderLines;
  $('po').oninput = () => { syncPoStatus(); renderLines(); };
  $('po').onpaste = () => { setTimeout(() => { syncPoStatus(); renderLines(); }, 0); };
  $('bcode').addEventListener('keydown', e => { if (e.key==='Enter'){ e.preventDefault(); lookupProduct(); }});
  $('bcode').addEventListener('blur', lookupProduct);
  $('addLine').onclick = addLine;
  $('cancelEdit').onclick = () => clearSaleForm();
  $('checkPo').onclick = async () => {
    try {
      if (!poLengthOk()) {
        syncPoStatus();
        return;
      }
      const data = await api('/api/check-po', {method:'POST', body: JSON.stringify({
        acctno:$('shop').value,
        online_po: poValue(),
        platform: $('platform').value,
        exclude_billno: state.editBillno || '',
        exclude_draft_id: state.editDraftId || '',
      })});
      if (data.ok) { $('poStatus').textContent='เลขคำสั่งซื้อใช้ได้'; $('poStatus').className='meta ok'; }
      else { $('poStatus').textContent='ซ้ำกับ '+data.duplicates.map(d=>d.billno).join(', '); $('poStatus').className='meta err'; }
    } catch(e) { $('poStatus').textContent=e.message; $('poStatus').className='meta err'; }
  };
  $('saveDraft').onclick = async () => {
    if (state.editBillno) return;
    if (!poLengthOk()) {
      syncPoStatus();
      $('saleMsg').textContent = $('poStatus').textContent || 'เลขคำสั่งซื้อไม่ถูกต้อง';
      $('saleMsg').className = 'meta err';
      return;
    }
    $('saleMsg').textContent='กำลังบันทึกฉบับร่าง...'; $('saleMsg').className='meta';
    try {
      const data = await api('/api/drafts', {method:'POST', body: JSON.stringify(salePayload(false))});
      const draft = data.draft;
      state.editDraftId = draft.draft_id;
      state.editBillno = null;
      syncEditBanner();
      $('saleMsg').innerHTML = `บันทึกฉบับร่างแล้ว · คำสั่งซื้อ <b>${draft.online_po||''}</b> — ไปหน้าค้นหาเพื่อพิมพ์ใบจัดสินค้ารวม`;
      $('saleMsg').className='meta ok';
    } catch(e) { $('saleMsg').textContent=e.message; $('saleMsg').className='meta err'; }
  };
  $('saveSale').onclick = async () => {
    if (!poLengthOk()) {
      syncPoStatus();
      $('saleMsg').textContent = $('poStatus').textContent || 'เลขคำสั่งซื้อไม่ถูกต้อง';
      $('saleMsg').className = 'meta err';
      return;
    }
    const bad = oversoldLines();
    let allow = false;
    if (bad.length) {
      allow = confirm('จำนวนขายเกินสต็อกคงเหลือ:\\n' + bad.map(l => `${l.bcode}: ขาย ${l.qty} ${l.ui||''} (=${stockUnits(l)}) / คงเหลือ ${l.qtyoh2}`).join('\\n') + '\\n\\nบันทึกต่อหรือไม่?');
      if (!allow) return;
    }
    $('saleMsg').textContent='กำลังบันทึก...'; $('saleMsg').className='meta';
    let confirmUnmapped = false;
    try {
      const editing = !!state.editBillno;
      let data;
      while (true) {
        const payload = salePayload(allow, confirmUnmapped);
        try {
          data = editing
            ? await api('/api/sales/'+encodeURIComponent(state.editBillno), {method:'PATCH', body: JSON.stringify(payload)})
            : await api('/api/sales', {method:'POST', body: JSON.stringify(payload)});
          break;
        } catch (e) {
          if (editing) throw e;
          await confirmUnmappedOrThrow(e);
          confirmUnmapped = true;
        }
      }
      const verb = editing ? 'แก้ไขแล้ว' : (state.editDraftId ? 'ยืนยันขายแล้ว' : 'บันทึกแล้ว');
      const billno = data.result.billno;
      clearSaleForm();
      $('saleMsg').innerHTML = `${verb} <b>${billno}</b>
        · <a href="/online-sale/print/tad/${encodeURIComponent(billno)}" target="_blank">พิมพ์ใบ TAD</a>
        · <a href="/to-bill/?tad=${encodeURIComponent(billno)}" target="_blank">ออกใบเต็ม TO</a>`;
      $('saleMsg').className='meta ok';
    } catch(e) { $('saleMsg').textContent=e.message; $('saleMsg').className='meta err'; }
  };
  function canPickDraft(b){ return b && b.kind==='draft' && !b.canceled && b.status !== 'sold' && b.status !== 'canceled'; }
  function selectedPickDraftIds(){
    return [...document.querySelectorAll('#searchResults input.pick-draft:checked')].map(el => el.value);
  }
  function syncPickBar(){
    const btn = $('printPick');
    const count = $('pickCount');
    if (!btn || !count) return;
    const nos = selectedPickDraftIds();
    count.textContent = nos.length ? `เลือกแล้ว ${nos.length} ฉบับร่าง` : 'เลือกฉบับร่างเพื่อพิมพ์ใบจัด';
    btn.disabled = nos.length === 0;
  }
  function renderSearchResults(bills, toDocs){
    const box = $('searchResults');
    state.searchBills = bills || [];
    if (!bills.length && !toDocs.length) { box.innerHTML='<p class="meta">ไม่พบรายการ</p>'; return; }
    const pickable = bills.filter(canPickDraft);
    box.innerHTML = `
      <div class="pick-bar">
        <button type="button" id="printPick" disabled>พิมพ์ใบจัดสินค้ารวม</button>
        <span class="count" id="pickCount">เลือกฉบับร่างเพื่อพิมพ์ใบจัด</span>
      </div>
      <table><thead><tr>
        <th style="width:2.2rem"><input type="checkbox" id="pickAll" title="เลือกฉบับร่างทั้งหมด" ${pickable.length?'':'disabled'}></th>
        <th>เลขบิล / ฉบับร่าง</th><th>สถานะ</th><th>วันที่</th><th>ร้าน / ลูกค้า</th><th>คำสั่งซื้อ</th><th class="num">ยอด</th><th></th>
      </tr></thead><tbody></tbody></table>`;
    const tb = box.querySelector('tbody');
    for (const b of bills) {
      const tr = document.createElement('tr');
      let status = '';
      if (b.kind === 'draft') {
        if (b.canceled || b.status === 'canceled') status = '<span class="status-cancel">ยกเลิก</span>';
        else if (b.pick_printed || b.status === 'printed') status = '<span class="status-printed">พิมพ์ใบจัดแล้ว</span>';
        else status = '<span class="status-draft">ฉบับร่าง</span>';
      } else if (b.canceled) {
        status = '<span class="status-cancel">ยกเลิก</span>';
      } else {
        status = b.kind==='cntad' ? 'CNTAD' : 'TAD';
      }
      let actions = '';
      if (b.kind === 'draft') {
        if (canPickDraft(b)) {
          actions = `<a href="#" data-edit-draft="${b.draft_id}">แก้ไข / ยืนยันขาย</a>`;
          if (WRITE) actions += ` · <a href="#" data-cancel-draft="${b.draft_id}">ยกเลิก</a>`;
        } else {
          actions = '<span class="meta">—</span>';
        }
      } else if (b.kind==='cntad') {
        actions = `<a href="/online-sale/print/cntad/${encodeURIComponent(b.billno)}" target="_blank">พิมพ์</a>`;
      } else {
        actions = `<a href="/online-sale/print/tad/${encodeURIComponent(b.billno)}" target="_blank">พิมพ์ TAD</a>`;
      }
      if (b.kind==='tad' && !b.canceled) {
        actions += ` · <a href="#" data-edit="${b.billno}">แก้ไข</a>`;
        actions += ` · <a href="#" data-ret="${b.billno}">คืน</a>`;
        actions += ` · <a href="/to-bill/?tad=${encodeURIComponent(b.billno)}" target="_blank">ใบเต็ม</a>`;
      }
      if (b.to_docno) {
        actions += ` · <a href="/to-bill/?tad=${encodeURIComponent(b.billno)}" target="_blank">${b.to_docno}</a>`;
      }
      const pickCell = canPickDraft(b)
        ? `<input type="checkbox" class="pick-draft" value="${b.draft_id}">`
        : '';
      const label = b.kind === 'draft' ? (b.billno || 'ฉบับร่าง') : b.billno;
      tr.innerHTML = `<td>${pickCell}</td><td>${label}</td><td>${status}</td><td>${b.bill_date||''}</td><td>${b.shop_name||b.acctname||b.acctno||''}</td>
        <td>${b.online_po||''}</td><td class="num">${money(b.aftertax)}</td>
        <td>${actions}</td>`;
      tb.appendChild(tr);
    }
    for (const inv of toDocs) {
      const tr = document.createElement('tr');
      const docno = inv.docno || '';
      const tad = inv.tad_billno || '';
      const st = inv.status === 'void'
        ? '<span class="status-cancel">ยกเลิก</span>'
        : (inv.status === 'issued' ? 'ออกแล้ว' : (inv.status || 'TO'));
      const openHref = tad
        ? `/to-bill/?tad=${encodeURIComponent(tad)}`
        : '/to-bill/';
      tr.innerHTML = `<td></td><td>${docno}</td><td>${st}</td><td>${(inv.bill_date||inv.issued_at||'').toString().slice(0,10)}</td>
        <td>${inv.customer_name||inv.acctname_kss||''}</td>
        <td>${inv.online_po||''}</td><td class="num">${money(inv.aftertax)}</td>
        <td><a href="${openHref}" target="_blank">เปิดใบเต็ม</a>
          ${tad ? ` · <span class="meta">${tad}</span>` : ''}</td>`;
      tb.appendChild(tr);
    }
    const pickAll = $('pickAll');
    if (pickAll) {
      pickAll.onchange = () => {
        box.querySelectorAll('input.pick-draft').forEach(el => { el.checked = pickAll.checked; });
        syncPickBar();
      };
    }
    box.querySelectorAll('input.pick-draft').forEach(el => {
      el.onchange = () => {
        if (pickAll) {
          const all = [...box.querySelectorAll('input.pick-draft')];
          pickAll.checked = all.length > 0 && all.every(x => x.checked);
          pickAll.indeterminate = all.some(x => x.checked) && !pickAll.checked;
        }
        syncPickBar();
      };
    });
    $('printPick').onclick = () => {
      const nos = selectedPickDraftIds();
      if (!nos.length) return;
      window.open('/online-sale/print/pick?drafts='+encodeURIComponent(nos.join(',')), '_blank');
      // Refresh after print so status flips to พิมพ์ใบจัดแล้ว.
      setTimeout(() => { $('doSearch').click(); }, 800);
    };
    syncPickBar();
    box.querySelectorAll('a[data-ret]').forEach(a => a.onclick = (e) => {
      e.preventDefault(); $('retTad').value=a.dataset.ret; showTab('return'); $('loadReturn').click();
    });
    box.querySelectorAll('a[data-edit]').forEach(a => a.onclick = async (e) => {
      e.preventDefault();
      try { await loadBillForEdit(a.dataset.edit); }
      catch (err) { alert(err.message); }
    });
    box.querySelectorAll('a[data-edit-draft]').forEach(a => a.onclick = async (e) => {
      e.preventDefault();
      try { await loadDraftForEdit(a.dataset.editDraft); }
      catch (err) { alert(err.message); }
    });
    box.querySelectorAll('a[data-cancel-draft]').forEach(a => a.onclick = async (e) => {
      e.preventDefault();
      if (!confirm('ยืนยันยกเลิกฉบับร่างนี้?')) return;
      try {
        await api('/api/drafts/'+encodeURIComponent(a.dataset.cancelDraft), {method:'DELETE'});
        $('doSearch').click();
      } catch (err) { alert(err.message); }
    });
  }
  $('doSearch').onclick = async () => {
    const params = new URLSearchParams({
      q: $('q').value.trim(),
      platform: $('qPlatform').value,
      acctno: $('qShop').value,
      date_from: $('df').value,
      date_to: $('dt').value,
      kind: $('qKind').value,
    });
    const data = await api('/api/search?'+params);
    renderSearchResults(data.bills || [], data.to_invoices || []);
  };
  $('loadReturn').onclick = async () => {
    const box = $('returnBox');
    try {
      const data = await api('/api/returns/preview?tad='+encodeURIComponent($('retTad').value.trim()));
      const reasons = (data.reasons||[]).map(r => `<option value="${r.id}">${r.label}</option>`).join('');
      box.innerHTML = `<p class="meta">${data.bill.billno} · ${data.bill.acctname} · คำสั่งซื้อ ${data.bill.online_po||'-'}</p>
        <table><thead><tr><th>รหัส</th><th>รายการ</th><th class="num">ขาย</th><th class="num">คืนแล้ว</th><th class="num">คงเหลือ</th><th class="num">คืนครั้งนี้</th></tr></thead>
        <tbody id="retLines"></tbody></table>
        <div class="row" style="margin-top:10px">
          <label class="field"><span>เหตุผล</span><select id="reason">${reasons}</select></label>
          <label class="field" style="flex:1"><span>ระบุเหตุผล (ถ้าเลือก อื่นๆ)</span><input id="reasonNote"></label>
          <button type="button" id="saveReturn" ${WRITE?'':'disabled'}>บันทึกใบลดหนี้</button>
        </div>
        <p id="retMsg" class="meta"></p>`;
      const tb = $('retLines');
      for (const ln of data.lines) {
        const tr = document.createElement('tr');
        tr.innerHTML = `<td>${ln.bcode}</td><td>${ln.detail}</td><td class="num">${ln.sold_qty}</td>
          <td class="num">${ln.returned_qty}</td><td class="num">${ln.remain_qty}</td>
          <td class="num"><input data-bcode="${ln.bcode}" data-price="${ln.price}" data-detail="${ln.detail.replace(/"/g,'&quot;')}" data-ui="${ln.ui||''}" data-max="${ln.remain_qty}" type="number" min="0" max="${ln.remain_qty}" step="1" value="0" style="width:5rem"></td>`;
        tb.appendChild(tr);
      }
      $('saveReturn').onclick = async () => {
        const lines = [];
        tb.querySelectorAll('input[data-bcode]').forEach(inp => {
          const qty = Number(inp.value||0);
          if (qty>0) lines.push({bcode:inp.dataset.bcode, qty, price:Number(inp.dataset.price), detail:inp.dataset.detail, ui:inp.dataset.ui});
        });
        let confirmUnmapped = false;
        try {
          let saved;
          while (true) {
            try {
              saved = await api('/api/returns', {method:'POST', body: JSON.stringify({
                tad_billno: data.bill.billno,
                reason_id: $('reason').value,
                reason_note: $('reasonNote').value,
                confirm_unmapped: confirmUnmapped,
                lines,
              })});
              break;
            } catch (e) {
              await confirmUnmappedOrThrow(e);
              confirmUnmapped = true;
            }
          }
          $('retMsg').innerHTML = `บันทึกแล้ว <b>${saved.result.billno}</b> · <a href="/online-sale/print/cntad/${encodeURIComponent(saved.result.billno)}?reason=${encodeURIComponent(saved.bill.reason||'')}" target="_blank">พิมพ์ใบลดหนี้</a>`;
          $('retMsg').className='meta ok';
        } catch(e) { $('retMsg').textContent=e.message; $('retMsg').className='meta err'; }
      };
    } catch(e) { box.innerHTML = `<p class="err">${e.message}</p>`; }
  };

  const tab = new URL(location.href).searchParams.get('tab') || 'sale';
  showTab(['sale','search','return','to'].includes(tab) ? tab : 'sale');
  const tad = new URL(location.href).searchParams.get('tad');
  if (tad) {
    $('toFrame').src = '/to-bill/?tad='+encodeURIComponent(tad);
    if (tab==='to' || new URL(location.href).searchParams.get('open')==='to') showTab('to');
  }
}
init().catch(e => { $('saleMsg').textContent = e.message; $('saleMsg').className='meta err'; });
</script>
</body>
</html>
"""


def page(*, user_name: str = "", write_enabled: bool = False) -> str:
    who = (user_name or "operator").strip()
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__WRITE__", "true" if write_enabled else "false")
    )

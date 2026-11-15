from __future__ import annotations

import html as html_lib
import json

APP = "kcw-online-sale"
SESSION_COOKIE = "kcw_online_sale"

_HTML = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ขายออนไลน์</title>
<style>
:root { color-scheme: light; --red:#9b1c2c; --bd:#e4e7ec; --muted:#667085; }
*{box-sizing:border-box}
body{margin:0;font-family:Prompt,"Noto Sans Thai",sans-serif;background:#f6f7f9;color:#111}
header{display:flex;justify-content:space-between;gap:12px;align-items:center;padding:12px 16px;background:#fff;border-bottom:3px solid var(--red)}
h1{margin:0;font-size:20px}
header p{margin:2px 0 0;color:var(--muted);font-size:13px}
.tabs{display:flex;gap:6px;flex-wrap:wrap;padding:10px 16px 0;max-width:1100px;margin:0 auto}
.tabs button{border:1px solid var(--bd);background:#fff;border-radius:999px;padding:7px 14px;cursor:pointer;font:inherit}
.tabs button.on{background:var(--red);color:#fff;border-color:var(--red)}
main{max-width:1100px;margin:0 auto;padding:12px 16px 40px;display:grid;gap:12px}
.panel{background:#fff;border:1px solid var(--bd);border-radius:12px;padding:14px}
.row{display:flex;gap:8px;flex-wrap:wrap;align-items:end}
.field{display:grid;gap:4px;font-size:14px}
.field span{color:#475467;font-size:12px}
input,select,button,textarea{font:inherit}
input,select,textarea{border:1px solid #d0d5dd;border-radius:8px;padding:8px 10px;background:#fff;min-width:0}
button,.btn{border:0;border-radius:8px;padding:8px 12px;background:var(--red);color:#fff;cursor:pointer}
button.ghost{background:#fff;color:#344054;border:1px solid #d0d5dd}
button:disabled{opacity:.55;cursor:default}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border-bottom:1px solid #eaecf0;padding:6px 4px;text-align:left;vertical-align:top}
.num{text-align:right;white-space:nowrap}
.meta{color:var(--muted);font-size:13px}
.err{color:#b42318}
.ok{color:#027a48}
.banner{background:#fef0c7;border-radius:8px;padding:8px 10px;margin-bottom:10px}
.total{font-size:18px;font-weight:800}
.hidden{display:none!important}
iframe.toframe{width:100%;min-height:75vh;border:1px solid var(--bd);border-radius:12px;background:#fff}
@media(max-width:800px){input,select{width:100%}}
</style>
</head>
<body>
<header>
  <div>
    <h1>ขายออนไลน์</h1>
    <p>TAD / CNTAD / ใบเต็ม TO — <span id="who"></span></p>
  </div>
  <div class="meta" id="writeBadge"></div>
</header>
<nav class="tabs noprint">
  <button type="button" data-tab="sale" class="on">ขาย</button>
  <button type="button" data-tab="search">ค้นหา</button>
  <button type="button" data-tab="return">คืนสินค้า</button>
  <button type="button" data-tab="to">ใบเต็ม TO</button>
</nav>
<main>
<section id="tab-sale" class="panel">
  <div class="row">
    <label class="field"><span>แพลตฟอร์ม</span>
      <select id="platform"></select>
    </label>
    <label class="field"><span>ร้านค้า</span>
      <select id="shop"><option value="">— เลือกร้าน —</option></select>
    </label>
    <label class="field" style="flex:1;min-width:220px"><span>เลขคำสั่งซื้อ (วางจากแพลตฟอร์ม)</span>
      <input id="po" maxlength="15" autocomplete="off" placeholder="วางเลขคำสั่งซื้อ">
    </label>
    <button type="button" class="ghost" id="checkPo">ตรวจซ้ำ</button>
  </div>
  <p class="meta" id="poStatus"></p>
  <div class="row" style="margin-top:10px">
    <label class="field" style="flex:1;min-width:180px"><span>รหัสสินค้า / บาร์โค้ด</span>
      <input id="bcode" autocomplete="off" placeholder="สแกนหรือพิมพ์แล้ว Enter">
    </label>
    <label class="field"><span>จำนวน</span><input id="qty" type="number" min="0.01" step="1" value="1" style="width:6rem"></label>
    <label class="field"><span>ราคา/หน่วย (รวม VAT)</span><input id="price" type="number" min="0.01" step="0.01" style="width:8rem"></label>
    <button type="button" id="addLine">เพิ่ม</button>
  </div>
  <p class="meta" id="prodHint"></p>
  <table id="linesTable" style="margin-top:12px">
    <thead><tr><th>รหัส</th><th>ชื่อ</th><th>ที่เก็บ</th><th class="num">สต็อก</th><th class="num">จำนวน</th><th class="num">ราคา</th><th class="num">รวม</th><th></th></tr></thead>
    <tbody></tbody>
  </table>
  <div class="row" style="justify-content:space-between;margin-top:12px">
    <div class="total">ยอดขายรวม <span id="grand">0.00</span></div>
    <button type="button" id="saveSale" disabled>บันทึกขาย</button>
  </div>
  <p id="saleMsg" class="meta"></p>
</section>

<section id="tab-search" class="panel hidden">
  <div class="row">
    <label class="field" style="flex:1;min-width:180px"><span>ค้นหา TAD / TO / CNTAD / เลขคำสั่งซื้อ</span>
      <input id="q" autocomplete="off">
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
const state = { platforms:[], shops:[], lines:[], product:null, write:WRITE };

const $ = (id) => document.getElementById(id);
const money = (n) => Number(n||0).toLocaleString('en-US',{minimumFractionDigits:2,maximumFractionDigits:2});

async function api(path, opts={}) {
  const res = await fetch('/online-sale'+path, {
    headers: {'Content-Type':'application/json', ...(opts.headers||{})},
    ...opts,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || data.detail || data.error || ('HTTP '+res.status));
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

async function loadShops(platform, sel) {
  sel.innerHTML = '<option value="">— เลือกร้าน —</option>';
  if (!platform) return;
  const data = await api('/api/shops?platform='+encodeURIComponent(platform));
  state.shops = data.shops || [];
  for (const s of state.shops) {
    const o = document.createElement('option');
    o.value = s.acctno;
    o.textContent = `${s.shop_name} (${s.acctno})`;
    sel.appendChild(o);
  }
}

function renderLines() {
  const tb = $('linesTable').querySelector('tbody');
  tb.innerHTML = '';
  let grand = 0;
  state.lines.forEach((ln, idx) => {
    grand += ln.qty * ln.price;
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${ln.bcode}</td><td>${ln.descr}</td><td>${ln.location||''}</td>
      <td class="num">${ln.qtyoh2}</td><td class="num">${ln.qty}</td><td class="num">${money(ln.price)}</td>
      <td class="num">${money(ln.qty*ln.price)}</td>
      <td><button type="button" class="ghost" data-i="${idx}">ลบ</button></td>`;
    tb.appendChild(tr);
  });
  tb.querySelectorAll('button[data-i]').forEach(b => b.onclick = () => {
    state.lines.splice(Number(b.dataset.i),1); renderLines();
  });
  $('grand').textContent = money(grand);
  $('saveSale').disabled = !(WRITE && state.lines.length && $('shop').value && $('po').value.trim());
}

async function lookupProduct() {
  const code = $('bcode').value.trim();
  if (!code) return;
  try {
    const data = await api('/api/product?code='+encodeURIComponent(code));
    state.product = data.product;
    $('prodHint').textContent = `${data.product.descr} · สต็อก ${data.product.qtyoh2} · ที่เก็บ ${data.product.location||'-'}`;
    $('prodHint').className = 'meta ok';
    $('bcode').value = data.product.bcode;
  } catch (e) {
    state.product = null;
    $('prodHint').textContent = e.message;
    $('prodHint').className = 'meta err';
  }
}

function addLine() {
  if (!state.product) { lookupProduct().then(() => { if (state.product) addLine(); }); return; }
  const qty = Number($('qty').value||0);
  const price = Number($('price').value||0);
  if (qty<=0 || price<=0) { $('saleMsg').textContent='ใส่จำนวนและราคา'; $('saleMsg').className='meta err'; return; }
  const existing = state.lines.find(l => l.bcode===state.product.bcode && l.price===price);
  if (existing) existing.qty += qty;
  else state.lines.push({
    bcode: state.product.bcode,
    descr: state.product.descr,
    location: state.product.location,
    qtyoh2: state.product.qtyoh2,
    ui: state.product.ui,
    qty, price,
  });
  $('bcode').value=''; $('qty').value='1'; $('price').value='';
  state.product=null; $('prodHint').textContent='';
  renderLines(); $('bcode').focus();
}

async function init() {
  $('who').textContent = USER || 'operator';
  $('writeBadge').textContent = WRITE ? 'บันทึกได้' : 'โหมดอ่านอย่างเดียว (ยังไม่เปิด WRITE)';
  const meta = await api('/api/meta');
  state.platforms = meta.platforms || [];
  state.write = !!meta.write_enabled;
  fillPlatformSelect($('platform'));
  fillPlatformSelect($('qPlatform'), true);
  await loadShops($('platform').value, $('shop'));
  $('platform').onchange = async () => {
    await loadShops($('platform').value, $('shop'));
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
  $('po').oninput = renderLines;
  $('bcode').addEventListener('keydown', e => { if (e.key==='Enter'){ e.preventDefault(); lookupProduct(); }});
  $('bcode').addEventListener('blur', lookupProduct);
  $('addLine').onclick = addLine;
  $('checkPo').onclick = async () => {
    try {
      const data = await api('/api/check-po', {method:'POST', body: JSON.stringify({acctno:$('shop').value, online_po:$('po').value})});
      if (data.ok) { $('poStatus').textContent='เลขคำสั่งซื้อใช้ได้'; $('poStatus').className='meta ok'; }
      else { $('poStatus').textContent='ซ้ำกับ '+data.duplicates.map(d=>d.billno).join(', '); $('poStatus').className='meta err'; }
    } catch(e) { $('poStatus').textContent=e.message; $('poStatus').className='meta err'; }
  };
  $('saveSale').onclick = async () => {
    $('saleMsg').textContent='กำลังบันทึก...'; $('saleMsg').className='meta';
    try {
      const data = await api('/api/sales', {method:'POST', body: JSON.stringify({
        acctno: $('shop').value,
        online_po: $('po').value.trim(),
        lines: state.lines.map(l => ({bcode:l.bcode, qty:l.qty, price:l.price, detail:l.descr, ui:l.ui})),
      })});
      $('saleMsg').innerHTML = `บันทึกแล้ว <b>${data.result.billno}</b> · <a href="/online-sale/print/tad/${encodeURIComponent(data.result.billno)}" target="_blank">พิมพ์ใบ TAD</a>
        · <a href="/to-bill/?tad=${encodeURIComponent(data.result.billno)}" target="_blank">ออกใบเต็ม TO</a>`;
      $('saleMsg').className='meta ok';
      state.lines=[]; $('po').value=''; renderLines();
    } catch(e) { $('saleMsg').textContent=e.message; $('saleMsg').className='meta err'; }
  };
  $('doSearch').onclick = async () => {
    const params = new URLSearchParams({
      q: $('q').value.trim(),
      platform: $('qPlatform').value,
      acctno: $('qShop').value,
      date_from: $('df').value,
      date_to: $('dt').value,
    });
    const data = await api('/api/search?'+params);
    const box = $('searchResults');
    if (!(data.bills||[]).length) { box.innerHTML='<p class="meta">ไม่พบรายการ</p>'; return; }
    box.innerHTML = `<table><thead><tr><th>เลขบิล</th><th>วันที่</th><th>ร้าน</th><th>คำสั่งซื้อ</th><th class="num">ยอด</th><th></th></tr></thead><tbody></tbody></table>`;
    const tb = box.querySelector('tbody');
    for (const b of data.bills) {
      const tr = document.createElement('tr');
      const printHref = b.kind==='cntad'
        ? `/online-sale/print/cntad/${encodeURIComponent(b.billno)}`
        : `/online-sale/print/tad/${encodeURIComponent(b.billno)}`;
      const extra = b.kind==='tad'
        ? ` · <a href="#" data-ret="${b.billno}">คืน</a> · <a href="/to-bill/?tad=${encodeURIComponent(b.billno)}" target="_blank">ใบเต็ม</a>`
        : '';
      tr.innerHTML = `<td>${b.billno}</td><td>${b.bill_date||''}</td><td>${b.acctname||b.acctno}</td>
        <td>${b.online_po||''}</td><td class="num">${money(b.aftertax)}</td>
        <td><a href="${printHref}" target="_blank">พิมพ์</a>${extra}</td>`;
      tb.appendChild(tr);
    }
    box.querySelectorAll('a[data-ret]').forEach(a => a.onclick = (e) => {
      e.preventDefault(); $('retTad').value=a.dataset.ret; showTab('return'); $('loadReturn').click();
    });
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
        try {
          const saved = await api('/api/returns', {method:'POST', body: JSON.stringify({
            tad_billno: data.bill.billno,
            reason_id: $('reason').value,
            reason_note: $('reasonNote').value,
            lines,
          })});
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

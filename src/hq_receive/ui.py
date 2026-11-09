from __future__ import annotations

import html as html_lib
import json

APP = "kcw-hq-receive"
SESSION_COOKIE = "kcw_hq_receive"


def page(*, user_name: str = "", write_enabled: bool = False) -> str:
    who = (user_name or "operator").strip()
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__WRITE__", "true" if write_enabled else "false")
    )


_HTML = r"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>รับสินค้าเข้า HQ</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --green:#166534;--line:#dbe3ef;--muted:#64748b;--text:#0f172a;--bg:#f4f7fb;--card:#fff;
  --warn:#9a3412;--warn-bg:#fff7ed;--bad:#b42318;--bad-bg:#fef3f2;--wash:#f0fdf4;
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{font-family:Prompt,"Noto Sans Thai",system-ui,sans-serif;background:var(--bg);color:var(--text)}
header{position:sticky;top:0;z-index:8;background:linear-gradient(180deg,#166534,#15803d);color:#fff;padding:max(14px,env(safe-area-inset-top)) 14px 12px}
header h1{margin:0;font-size:18px;font-weight:650}
header p{margin:2px 0 10px;font-size:13px;opacity:.92}
.tabs{display:flex;gap:8px;flex-wrap:wrap}
.tabs button{flex:1;min-width:5.5rem;min-height:40px;border:1px solid rgba(255,255,255,.45);background:transparent;color:#fff;border-radius:999px;padding:8px 10px;font-size:13px;font-weight:600}
.tabs button.on{background:#fff;color:var(--green);border-color:#fff}
main{padding:12px 12px calc(24px + env(safe-area-inset-bottom));max-width:960px;margin:0 auto}
.note{background:var(--warn-bg);color:var(--warn);border-radius:12px;padding:10px 12px;font-size:13px;line-height:1.45;margin-bottom:12px}
.note.bad{background:var(--bad-bg);color:var(--bad)}
.panel{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:12px;margin-bottom:12px}
.bar{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;align-items:center}
input,select,button,textarea{font:inherit}
input,select,textarea{border:1px solid #d0d5dd;border-radius:10px;padding:9px 11px;background:#fff;min-width:0}
button{border:0;border-radius:10px;padding:9px 12px;background:var(--green);color:#fff;font-weight:600;cursor:pointer}
button.ghost{background:#fff;color:#334155;border:1px solid #d0d5dd}
button:disabled{opacity:.55;cursor:default}
.list .row{display:flex;gap:10px;align-items:flex-start;border:1px solid var(--line);border-radius:12px;padding:10px;margin-top:8px;background:#fff}
.list .row.on{border-color:#86efac;background:var(--wash)}
.meta{color:var(--muted);font-size:12px;margin-top:3px}
.grid{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.field{display:grid;gap:4px;font-size:13px}
.field span{color:#475467;font-size:12px}
table{width:100%;border-collapse:collapse;font-size:13px}
th,td{border-bottom:1px solid #eaecf0;padding:7px 4px;text-align:left;vertical-align:top}
th.num,td.num{text-align:right;white-space:nowrap}
.chip{display:inline-block;border-radius:999px;padding:2px 8px;font-size:12px;background:#f2f4f7}
.chip.ok{background:#dcfce7;color:#166534}
.chip.hold,.chip.mismatch{background:#ffedd5;color:#9a3412}
.totals{display:grid;gap:4px;font-size:14px;margin-top:8px}
.totals div{display:flex;justify-content:space-between}
.totals .net{font-weight:700;font-size:16px;margin-top:4px}
.err{color:var(--bad);font-size:13px;margin-top:8px}
.preview{max-width:12rem;border:1px solid var(--line);border-radius:8px;background:#fff}
dialog{border:1px solid var(--line);border-radius:14px;padding:16px;max-width:28rem;width:calc(100% - 24px)}
dialog::backdrop{background:rgba(15,23,42,.35)}
dialog h3{margin:0 0 10px;font-size:16px}
.num input[type=text]{width:5.5rem;text-align:right;font:inherit;border:1px solid #d0d5dd;border-radius:8px;padding:6px 8px}
.thumb{width:44px;height:44px;object-fit:cover;border-radius:8px;background:#e2e8f0;display:block;flex:none}
.thumb-btn{padding:0;border:0;background:transparent;border-radius:8px;flex:none;cursor:zoom-in;line-height:0}
.po-lines{margin:8px 0 0 28px;display:grid;gap:6px}
.po-line{display:flex;gap:8px;align-items:flex-start;padding:6px 8px;border:1px solid #eef2f7;border-radius:10px;background:#f8fafc;font-size:12px}
.po-line .grow{flex:1;min-width:0}
.po-line .bits{color:var(--muted);margin-top:2px;line-height:1.35}
.linkish{background:transparent;border:0;color:#166534;padding:0;font:inherit;font-weight:600;cursor:pointer;text-decoration:underline}
#photoOverlay{position:fixed;inset:0;z-index:40;background:rgba(15,23,42,.55);display:flex;align-items:center;justify-content:center;padding:16px}
#photoOverlay[hidden]{display:none}
#photoOverlay img{max-width:min(92vw,28rem);max-height:80vh;border-radius:12px;background:#fff}
@media (max-width:720px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
<header>
  <h1>รับสินค้าเข้า HQ</h1>
  <p>ผู้ใช้: __USER__ · เลือก PO → ตรวจจำนวน/ต้นทุน · ยืนยันก่อนตัดสต็อก</p>
  <div class="tabs">
    <button type="button" class="on" data-tab="receive">รับเข้า</button>
    <button type="button" data-tab="creditnotes">ใบลดหนี้</button>
    <button type="button" data-tab="stickers">บาร์โค้ด</button>
    <button type="button" data-tab="issues">ผิดปกติ</button>
    <button type="button" data-tab="history">ประวัติ</button>
  </div>
</header>
<main>
  <div id="banner" class="note" hidden></div>

  <section id="tab-receive">
    <div class="panel">
      <div class="bar">
        <input id="vendorQ" placeholder="ค้นหาเจ้าหนี้ / รหัส" style="flex:1"/>
        <button type="button" class="ghost" id="btnVendors">ค้นหา</button>
      </div>
      <div id="vendorList" class="list"></div>
    </div>

    <div class="panel" id="openPanel" hidden>
      <div class="bar">
        <strong id="vendorTitle" style="flex:1"></strong>
        <button type="button" class="ghost" id="btnReloadPos">รีเฟรช PO</button>
      </div>
      <p class="meta">เลือก PO ที่ตรงกับบิล (เลือกได้หลายใบ) — ดูรายการสินค้าในแต่ละใบด้านล่าง แล้วดึงรายการค้างรับมาตรวจ</p>
      <div id="openPos" class="list"></div>
      <div class="bar" style="margin-top:10px">
        <button type="button" id="btnUsePos" disabled>ดึงรายการจาก PO ที่เลือก</button>
        <button type="button" class="ghost" id="btnNewProduct">สร้างสินค้าใหม่</button>
      </div>
      <details style="margin-top:12px">
        <summary class="meta" style="cursor:pointer">ตัวเลือก: อ่านหัวบิลจากรูป (ไม่ match สินค้า)</summary>
        <div class="bar" style="margin-top:8px">
          <input type="file" id="invoiceFile" accept="image/jpeg,image/png,image/webp"/>
          <button type="button" class="ghost" id="btnExtract">AI อ่านหัวบิล</button>
        </div>
        <div id="aiMeta" class="meta"></div>
      </details>
    </div>

    <dialog id="newProductDlg">
      <h3>สร้างรหัสสินค้าใหม่</h3>
      <div class="grid">
        <label class="field"><span>รหัสสินค้า *</span><input id="npBcode" autocomplete="off"/></label>
        <label class="field"><span>หน่วย</span><input id="npUi" value="ชิ้น"/></label>
        <label class="field" style="grid-column:1/-1"><span>ชื่อสินค้า *</span><input id="npDescr"/></label>
        <label class="field"><span>ยี่ห้อ</span><input id="npBrand"/></label>
        <label class="field"><span>รุ่น</span><input id="npModel"/></label>
        <label class="field"><span>เบอร์แท้</span><input id="npPcode"/></label>
        <label class="field"><span>เบอร์โรงงาน</span><input id="npMcode"/></label>
        <label class="field"><span>ที่เก็บ</span><input id="npLoc1" placeholder="LOCATION1" autocomplete="off"/></label>
        <label class="field"><span>รหัสคุม</span><input id="npCode1" maxlength="1" placeholder="เช่น I / C / O" autocomplete="off"/></label>
        <label class="field"><span>ราคา</span><input id="npPrice" inputmode="decimal" value="0"/></label>
        <label class="field"><span>ค่า</span><input id="npCost" inputmode="decimal" value="0"/></label>
        <label class="field"><span>จุดสั่ง (L)</span><input id="npQtymin" inputmode="decimal" value="0"/></label>
      </div>
      <div id="npErr" class="err" hidden></div>
      <div class="bar" style="margin-top:12px">
        <button type="button" id="btnCreateProduct">สร้างแล้วใส่รายการ</button>
        <button type="button" class="ghost" id="btnCancelProduct">ยกเลิก</button>
      </div>
    </dialog>

    <dialog id="editProductDlg">
      <h3>แก้ไขข้อมูลสินค้า</h3>
      <p class="meta" id="epBcodeLabel" style="margin:0 0 8px"></p>
      <div class="grid">
        <label class="field" style="grid-column:1/-1"><span>ชื่อสินค้า *</span><input id="epDescr"/></label>
        <label class="field"><span>ยี่ห้อ</span><input id="epBrand"/></label>
        <label class="field"><span>รุ่น</span><input id="epModel"/></label>
        <label class="field"><span>เบอร์แท้</span><input id="epPcode"/></label>
        <label class="field"><span>เบอร์โรงงาน</span><input id="epMcode"/></label>
        <label class="field"><span>ที่เก็บ</span><input id="epLoc1"/></label>
        <label class="field"><span>รหัสคุม</span><input id="epCode1" maxlength="1"/></label>
        <label class="field"><span>ราคา</span><input id="epPrice" inputmode="decimal"/></label>
        <label class="field"><span>ค่า</span><input id="epCost" inputmode="decimal"/></label>
      </div>
      <div id="epErr" class="err" hidden></div>
      <div class="bar" style="margin-top:12px">
        <button type="button" id="btnSaveProduct">บันทึก</button>
        <button type="button" class="ghost" id="btnCancelEditProduct">ยกเลิก</button>
      </div>
    </dialog>

    <div id="photoOverlay" hidden><img id="photoImg" alt="รูปสินค้า"/></div>

    <div class="panel" id="draftPanel" hidden>
      <div class="grid">
        <label class="field"><span>เลขบิลเจ้าหนี้</span><input id="vendorBillno"/></label>
        <label class="field"><span>วันที่บิล</span><input id="vendorBillDate" type="date"/></label>
        <label class="field"><span>วันที่รับ</span><input id="receiveDate" type="date"/></label>
        <label class="field"><span>ชำระ</span>
          <select id="payMethod">
            <option value="credit">ลงบัญชี</option>
            <option value="cash">ชำระสด</option>
          </select>
        </label>
        <label class="field"><span>ผู้รับสินค้า</span><input id="receiver"/></label>
        <label class="field"><span>ส่วนลดท้ายบิล</span><input id="billDiscount" type="number" step="0.01" value="0"/></label>
      </div>
      <div class="note" id="varianceHint" hidden style="margin-top:10px">
        จำนวนตามบิล ≠ รับจริง — เลือกว่าจะทำใบลดหนี้ / รอของตามมา / เปลี่ยนสินค้า
      </div>
      <div style="overflow:auto;margin-top:10px">
        <table>
          <thead>
            <tr>
              <th>รหัส</th><th>ชื่อ</th>
              <th class="num">ตามบิล</th><th class="num">รับจริง</th><th>หน่วย</th>
              <th class="num">ต้นทุน</th><th class="num">ส่วนลด</th><th class="num">รวม</th>
              <th>ส่วนต่าง</th><th>สถานะ</th><th></th>
            </tr>
          </thead>
          <tbody id="draftLines"></tbody>
        </table>
      </div>
      <div class="totals">
        <div><span>ยอดสินค้า</span><span id="sumSub">0</span></div>
        <div><span>ส่วนลด</span><span id="sumDisc">0</span></div>
        <div><span>VAT 7%</span><span><label><input type="checkbox" id="vatOn"/> คิด VAT</label> · <span id="sumVat">0</span></span></div>
        <div class="net"><span>ยอดสุทธิ</span><span id="sumNet">0</span></div>
      </div>
      <div class="bar" style="margin-top:12px">
        <button type="button" class="ghost" id="btnSaveDraft">บันทึกร่าง</button>
        <button type="button" id="btnConfirm">ยืนยันรับเข้า</button>
        <button type="button" class="ghost" id="btnDraftNewProduct">+ สินค้าใหม่</button>
        <button type="button" class="ghost" id="btnToStickers" disabled>ไปพิมพ์บาร์โค้ด</button>
      </div>
      <div id="draftErr" class="err" hidden></div>
      <div id="draftResult" class="meta" style="margin-top:8px"></div>
    </div>
  </section>

  <section id="tab-creditnotes" hidden>
    <div class="panel">
      <div class="bar">
        <strong style="flex:1">ใบลดหนี้รอเอกสารจากเจ้าหนี้ (7KCCN)</strong>
        <select id="cnStatusFilter">
          <option value="awaiting_vendor_doc">รอเอกสาร</option>
          <option value="completed">ครบแล้ว</option>
          <option value="">ทั้งหมด</option>
        </select>
        <button type="button" class="ghost" id="btnCreditNotes">รีเฟรช</button>
      </div>
      <p class="meta">ลิงก์กับบิลซื้อ BN… · กรอกเลขที่และวันที่จริงเมื่อได้เอกสาร VAT จากเจ้าหนี้</p>
      <div id="creditNoteList" class="list"></div>
    </div>
  </section>

  <section id="tab-stickers" hidden>
    <div class="panel">
      <p class="meta">พิมพ์จากรายการที่รับแล้ว / ตรวจแล้วเท่านั้น · ดาวน์โหลด TSPL .prn สำหรับ TSC TE310 / 244 Pro</p>
      <div id="stickerLines" class="list"></div>
      <div class="bar">
        <select id="printerModel"><option value="te310">TSC TE310</option><option value="ttp244pro">TSC 244 Pro</option></select>
        <input id="printerHost" placeholder="IP เครื่องพิมพ์ (ว่าง = ดาวน์โหลด)" style="flex:1"/>
        <button type="button" class="ghost" id="btnPreview">พรีวิว</button>
        <button type="button" id="btnPrintDl">ดาวน์โหลด .prn</button>
        <button type="button" class="ghost" id="btnPrintLan">พิมพ์ LAN</button>
      </div>
      <img id="stickerPreview" class="preview" hidden alt="preview"/>
      <div id="stickerJobs" class="list" style="margin-top:10px"></div>
    </div>
  </section>

  <section id="tab-issues" hidden>
    <div class="panel">
      <div class="bar"><button type="button" class="ghost" id="btnIssues">รีเฟรช</button></div>
      <div id="issueList" class="list"></div>
    </div>
  </section>

  <section id="tab-history" hidden>
    <div class="panel">
      <div class="bar"><button type="button" class="ghost" id="btnHistory">รีเฟรช</button></div>
      <div id="historyList" class="list"></div>
    </div>
  </section>
</main>
<script>
const USER = __USER_JSON__;
const WRITE_ENABLED = __WRITE__;
const state = {
  vendor: null,
  openPos: [],
  openLines: [],
  selectedPos: new Set(),
  draftLines: [],
  receiptId: null,
  extractionId: null,
  pimasBillno: null,
  stickerSource: [],
  editIdx: null,
};

function esc(s){
  return String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}
function thumbHtml(row){
  if(!row || !row.photo) return '';
  const label = String(row.bcode || '').trim();
  return `<button type="button" class="thumb-btn" data-photo="${esc(row.photo)}" aria-label="ดูรูป${label ? ' ' + esc(label) : ''}"><img class="thumb" alt="" loading="lazy" src="${esc(row.photo)}" onerror="this.closest('button').remove()"/></button>`;
}
function openPhoto(src){
  const url = String(src || '').trim();
  if(!url) return;
  el('photoImg').src = url;
  el('photoOverlay').hidden = false;
}
function closePhoto(){
  el('photoOverlay').hidden = true;
  el('photoImg').removeAttribute('src');
}
function productBits(row){
  const bits = [];
  if(row.model) bits.push('รุ่น ' + row.model);
  if(row.brand) bits.push('ยี่ห้อ ' + row.brand);
  if(row.pcode) bits.push('เบอร์แท้ ' + row.pcode);
  if(row.mcode) bits.push('เบอร์โรงงาน ' + row.mcode);
  return bits.join(' · ');
}

function money(n){ return Number(n||0).toLocaleString('th-TH',{minimumFractionDigits:2,maximumFractionDigits:2}); }
function el(id){ return document.getElementById(id); }
function showBanner(text, bad=false){
  const b = el('banner');
  b.hidden = !text;
  b.textContent = text || '';
  b.className = 'note' + (bad ? ' bad' : '');
}
async function api(path, opts={}){
  const res = await fetch('/hq-receive/api' + path, {
    headers: opts.body instanceof FormData ? undefined : {'Content-Type':'application/json', ...(opts.headers||{})},
    credentials:'same-origin',
    ...opts,
  });
  const ct = res.headers.get('content-type') || '';
  if(ct.includes('application/octet-stream')){
    if(!res.ok) throw new Error('print failed');
    return res;
  }
  const data = await res.json().catch(()=>({}));
  if(!res.ok){
    const msg = data.detail || data.message || data.error || res.statusText;
    throw new Error(typeof msg === 'string' ? msg : JSON.stringify(msg));
  }
  return data;
}

function setTab(name){
  document.querySelectorAll('.tabs button').forEach(btn=> btn.classList.toggle('on', btn.dataset.tab === name));
  ['receive','creditnotes','stickers','issues','history'].forEach(t=> el('tab-'+t).hidden = t !== name);
  if(name==='history') loadHistory();
  if(name==='issues') loadIssues();
  if(name==='creditnotes') loadCreditNotes();
  if(name==='stickers'){ renderStickerLines(); loadStickerJobs(); }
}
document.querySelectorAll('.tabs button').forEach(btn=> btn.addEventListener('click', ()=> setTab(btn.dataset.tab)));

async function loadVendors(){
  const q = el('vendorQ').value.trim();
  const data = await api('/vendors?q=' + encodeURIComponent(q));
  const box = el('vendorList');
  box.innerHTML = '';
  (data.vendors||[]).forEach(v=>{
    const row = document.createElement('div');
    row.className = 'row' + (state.vendor && state.vendor.acctno===v.acctno ? ' on' : '');
    row.innerHTML = `<div style="flex:1"><div><strong>${v.name||v.acctno}</strong> <span class="chip">${v.acctno}</span></div>
      <div class="meta">ค้างรับ ${v.line_count||0} รายการ · ${(v.qty_total||0).toLocaleString('th-TH')} ชิ้น</div></div>`;
    row.onclick = ()=> selectVendor(v);
    box.appendChild(row);
  });
  if(!(data.vendors||[]).length) box.innerHTML = '<div class="meta">ไม่พบเจ้าหนี้</div>';
}

async function selectVendor(v){
  state.vendor = v;
  state.selectedPos = new Set();
  state.openPos = [];
  state.openLines = [];
  state.draftLines = [];
  state.receiptId = null;
  state.extractionId = null;
  state.pimasBillno = null;
  el('vendorTitle').textContent = (v.name||v.acctno) + ' (' + v.acctno + ')';
  el('openPanel').hidden = false;
  el('draftPanel').hidden = true;
  el('aiMeta').textContent = '';
  el('receiver').value = USER;
  await loadOpenPos();
  await loadVendors();
}

function renderPoLines(po){
  const lines = po.lines || [];
  if(!lines.length) return '<div class="meta" style="margin:6px 0 0 28px">ไม่มีรายการใน PO นี้</div>';
  return `<div class="po-lines">${lines.map(ln => {
    const bits = productBits(ln);
    const qty = Number(ln.qty||0);
    return `<div class="po-line">${thumbHtml(ln)}
      <div class="grow">
        <div><strong>${esc(ln.bcode||'')}</strong> ${esc(ln.descr||'')}</div>
        ${bits ? `<div class="bits">${esc(bits)}</div>` : ''}
        <div class="bits">ค้าง ${qty.toLocaleString('th-TH')}${ln.ui ? ' ' + esc(ln.ui) : ''}</div>
      </div>
    </div>`;
  }).join('')}</div>`;
}

async function loadOpenPos(){
  if(!state.vendor) return;
  const data = await api('/open-pos?acctno=' + encodeURIComponent(state.vendor.acctno));
  state.openPos = data.pos || [];
  const box = el('openPos');
  box.innerHTML = '';
  state.openPos.forEach(po=>{
    const id = String(po.po_docno || '');
    const row = document.createElement('div');
    row.className = 'row' + (state.selectedPos.has(id) ? ' on' : '');
    row.innerHTML = `<label style="display:flex;gap:10px;align-items:flex-start;flex:1;cursor:pointer">
        <input type="checkbox" ${state.selectedPos.has(id)?'checked':''}/>
        <div style="flex:1"><div><strong>${esc(id)}</strong></div>
        <div class="meta">ค้างรับ ${po.line_count||0} รายการ · ${(po.qty_total||0).toLocaleString('th-TH')} ชิ้น${po.docdate ? ' · ' + esc(po.docdate) : ''}</div></div>
      </label>
      ${renderPoLines(po)}`;
    const cb = row.querySelector('input[type=checkbox]');
    cb.onchange = ()=>{
      if(cb.checked) state.selectedPos.add(id); else state.selectedPos.delete(id);
      row.classList.toggle('on', cb.checked);
      el('btnUsePos').disabled = state.selectedPos.size === 0;
    };
    row.querySelectorAll('button[data-photo]').forEach(btn=>{
      btn.onclick = (e)=>{ e.preventDefault(); e.stopPropagation(); openPhoto(btn.dataset.photo); };
    });
    box.appendChild(row);
  });
  el('btnUsePos').disabled = state.selectedPos.size === 0;
  if(!state.openPos.length) box.innerHTML = '<div class="meta">ไม่มี PO ค้างรับของเจ้าหนี้นี้</div>';
}

function lineFromOpen(ln){
  const q = Number(ln.qty||0);
  const cost = Number(ln.cost || ln.costlast || 0);
  return {
    iclow_id: ln.iclow_id, bcode: ln.bcode, descr: ln.descr || '',
    brand: ln.brand || '', model: ln.model || '',
    pcode: ln.pcode || '', mcode: ln.mcode || '',
    photo: ln.photo || '', location1: ln.location1 || '', code1: ln.code1 || '',
    price1: ln.price1 != null ? Number(ln.price1) : null,
    qty: q, bill_qty: q, received_qty: q, open_qty: q, variance_action: null,
    ui: ln.ui || '', cost: cost, discount: 0, amount: 0,
    po_docno: ln.hq_po_docno || ln.docno || '', status: 'ok', flags: []
  };
}

async function useSelectedPos(){
  if(!state.vendor || !state.selectedPos.size) return;
  const po = [...state.selectedPos].map(encodeURIComponent).join(',');
  try{
    const data = await api('/open-lines?acctno=' + encodeURIComponent(state.vendor.acctno) + '&po=' + po);
    state.openLines = data.lines || [];
    state.draftLines = state.openLines.map(lineFromOpen);
    if(!state.draftLines.length){
      showBanner('PO ที่เลือกไม่มีรายการค้างรับ', true);
      return;
    }
    openDraft();
    showBanner('ดึง ' + state.draftLines.length + ' รายการจาก ' + state.selectedPos.size + ' PO — ตรวจจำนวน/ต้นทุนแล้วยืนยัน');
  }catch(e){ showBanner(e.message||String(e), true); }
}

function openNewProductDlg(){
  if(!state.vendor){ showBanner('เลือกเจ้าหนี้ก่อน', true); return; }
  el('npErr').hidden = true;
  el('npBcode').value = '';
  el('npDescr').value = '';
  el('npUi').value = 'ชิ้น';
  el('npBrand').value = '';
  el('npModel').value = '';
  el('npPcode').value = '';
  el('npMcode').value = '';
  el('npLoc1').value = '';
  el('npCode1').value = '';
  el('npPrice').value = '0';
  el('npCost').value = '0';
  el('npQtymin').value = '0';
  el('newProductDlg').showModal();
}

async function createNewProduct(){
  el('npErr').hidden = true;
  const body = {
    bcode: el('npBcode').value.trim(),
    descr: el('npDescr').value.trim(),
    ui: el('npUi').value.trim() || 'ชิ้น',
    vendor: state.vendor ? state.vendor.acctno : '',
    brand: el('npBrand').value.trim(),
    model: el('npModel').value.trim(),
    pcode: el('npPcode').value.trim(),
    mcode: el('npMcode').value.trim(),
    location1: el('npLoc1').value.trim(),
    code1: el('npCode1').value.trim().toUpperCase(),
    price1: Number(String(el('npPrice').value||'0').replace(/,/g,'')) || 0,
    cost: Number(String(el('npCost').value||'0').replace(/,/g,'')) || 0,
    qtymin: Number(String(el('npQtymin').value||'0').replace(/,/g,'')) || 0,
  };
  try{
    const data = await api('/products', {method:'POST', body: JSON.stringify(body)});
    const p = data.product || {};
    const cost = Number(p.cost || body.cost || 0);
    state.draftLines.push({
      iclow_id: null, bcode: p.bcode, descr: p.descr || body.descr,
      brand: p.brand || body.brand, model: p.model || body.model,
      pcode: p.pcode || body.pcode, mcode: p.mcode || body.mcode,
      location1: p.location1 || body.location1, code1: p.code1 || body.code1,
      photo: '', price1: Number(p.price1 || body.price1 || 0) || null,
      qty: 1, bill_qty: 1, received_qty: 1, open_qty: null, variance_action: null,
      ui: p.ui || body.ui, cost: cost, discount: 0, amount: cost,
      po_docno: '', status: 'ok', flags: ['new_product']
    });
    el('newProductDlg').close();
    openDraft();
    showBanner('สร้างรหัส ' + p.bcode + ' แล้ว — ใส่ในรายการรับเข้า');
  }catch(e){
    el('npErr').hidden = false;
    el('npErr').textContent = e.message || String(e);
  }
}

function openEditProduct(idx){
  const ln = state.draftLines[idx];
  if(!ln || !ln.bcode){ showBanner('ไม่มีรหัสสินค้า', true); return; }
  state.editIdx = idx;
  el('epErr').hidden = true;
  el('epBcodeLabel').textContent = 'รหัส ' + ln.bcode;
  el('epDescr').value = ln.descr || '';
  el('epBrand').value = ln.brand || '';
  el('epModel').value = ln.model || '';
  el('epPcode').value = ln.pcode || '';
  el('epMcode').value = ln.mcode || '';
  el('epLoc1').value = ln.location1 || '';
  el('epCode1').value = ln.code1 || '';
  el('epPrice').value = ln.price1 != null && ln.price1 !== '' ? String(ln.price1) : '';
  el('epCost').value = ln.cost != null && ln.cost !== '' ? String(ln.cost) : '';
  el('editProductDlg').showModal();
}

async function saveEditProduct(){
  el('epErr').hidden = true;
  const idx = state.editIdx;
  const ln = state.draftLines[idx];
  if(ln == null){ el('editProductDlg').close(); return; }
  const body = {
    descr: el('epDescr').value.trim(),
    brand: el('epBrand').value.trim(),
    model: el('epModel').value.trim(),
    pcode: el('epPcode').value.trim(),
    mcode: el('epMcode').value.trim(),
    location1: el('epLoc1').value.trim(),
    code1: el('epCode1').value.trim().toUpperCase(),
    price1: Number(String(el('epPrice').value||'0').replace(/,/g,'')) || 0,
    cost: Number(String(el('epCost').value||'0').replace(/,/g,'')) || 0,
  };
  try{
    const data = await api('/products/' + encodeURIComponent(ln.bcode), {
      method:'PUT', body: JSON.stringify(body)
    });
    const p = data.product || {};
    ln.descr = p.descr || body.descr;
    ln.brand = p.brand != null ? p.brand : body.brand;
    ln.model = p.model != null ? p.model : body.model;
    ln.pcode = p.pcode != null ? p.pcode : body.pcode;
    ln.mcode = p.mcode != null ? p.mcode : body.mcode;
    ln.location1 = p.location1 != null ? p.location1 : body.location1;
    ln.code1 = p.code1 != null ? p.code1 : body.code1;
    if(p.price1 != null) ln.price1 = Number(p.price1);
    else ln.price1 = body.price1;
    if(p.cost != null) ln.cost = Number(p.cost);
    else ln.cost = body.cost;
    el('editProductDlg').close();
    state.editIdx = null;
    renderDraft();
    showBanner('อัปเดต ' + ln.bcode + ' ในระบบแล้ว');
  }catch(e){
    el('epErr').hidden = false;
    el('epErr').textContent = e.message || String(e);
  }
}

function openDraft(){
  el('draftPanel').hidden = false;
  el('draftResult').textContent = '';
  el('draftErr').hidden = true;
  if(!el('receiveDate').value) el('receiveDate').value = new Date().toISOString().slice(0,10);
  renderDraft();
}

function qtyDiff(ln){
  const bill = Number(ln.bill_qty != null ? ln.bill_qty : ln.qty || 0);
  const recv = Number(ln.received_qty != null ? ln.received_qty : bill);
  return Math.round((bill - recv) * 10000) / 10000;
}
function hasVariance(ln){
  return Math.abs(qtyDiff(ln)) > 0.0001;
}
function varianceSelect(ln, idx){
  if(!hasVariance(ln) || ln.status === 'hold') return '<span class="meta">—</span>';
  const v = ln.variance_action || '';
  return `<select data-var="${idx}" style="min-width:8.5rem;font-size:12px">
    <option value="">เลือก…</option>
    <option value="credit_note" ${v==='credit_note'?'selected':''}>ทำใบลดหนี้</option>
    <option value="wait_rest" ${v==='wait_rest'?'selected':''}>รอของตามมา</option>
    <option value="change_product" ${v==='change_product'?'selected':''}>เปลี่ยนสินค้า</option>
  </select>`;
}

function numVal(raw){
  const n = Number(String(raw||'').replace(/,/g,'').trim());
  return Number.isFinite(n) ? n : 0;
}

function refreshVarianceCell(idx){
  const ln = state.draftLines[idx];
  if(!ln) return;
  const cell = document.querySelector(`[data-vardiff="${idx}"]`);
  if(!cell) return;
  const diff = qtyDiff(ln);
  cell.innerHTML = `${hasVariance(ln)?('<span class="chip mismatch">'+(diff>0?'ขาด ':'เกิน ')+Math.abs(diff)+'</span>'):'—'}<div style="margin-top:4px">${varianceSelect(ln, idx)}</div>`;
  const sel = cell.querySelector('select[data-var]');
  if(sel){
    sel.addEventListener('change', ()=>{
      const v = sel.value || null;
      ln.variance_action = v;
      if(v === 'change_product'){
        ln.status = 'hold';
        ln.hold_reason = 'เปลี่ยนสินค้า';
      } else if(ln.status === 'hold' && ln.hold_reason === 'เปลี่ยนสินค้า'){
        ln.status = 'ok';
        ln.hold_reason = null;
      }
      renderDraft();
    });
  }
}

function renderDraft(){
  const body = el('draftLines');
  body.innerHTML = '';
  state.draftLines.forEach((ln, idx)=>{
    if(ln.bill_qty == null) ln.bill_qty = Number(ln.qty||0);
    if(ln.received_qty == null) ln.received_qty = Number(ln.bill_qty||0);
    const tr = document.createElement('tr');
    const st = ln.status || 'ok';
    const costText = (ln.cost == null || ln.cost === '') ? '' : String(ln.cost);
    const bits = productBits(ln);
    tr.innerHTML = `<td>
        <div style="display:flex;gap:8px;align-items:flex-start">
          ${thumbHtml(ln)}
          <div><strong>${esc(ln.bcode||'')}</strong>
            <div class="meta">${esc(ln.po_docno||'')}${ln.flags&&ln.flags.includes('new_product')?' · สินค้าใหม่':''}${ln.open_qty!=null?' · ค้าง '+ln.open_qty:''}</div>
          </div>
        </div>
      </td>
      <td>${esc(ln.descr||'')}${bits?`<div class="meta">${esc(bits)}</div>`:''}
        <div style="margin-top:4px"><button type="button" class="linkish" data-edit="${idx}">แก้ไข</button></div>
      </td>
      <td class="num"><input data-k="bill_qty" data-i="${idx}" type="text" inputmode="decimal" value="${ln.bill_qty}"/></td>
      <td class="num"><input data-k="received_qty" data-i="${idx}" type="text" inputmode="decimal" value="${ln.received_qty}"/></td>
      <td>${esc(ln.ui||'')}</td>
      <td class="num"><input data-k="cost" data-i="${idx}" type="text" inputmode="decimal" value="${costText}"/></td>
      <td class="num"><input data-k="discount" data-i="${idx}" type="text" inputmode="decimal" value="${ln.discount||0}"/></td>
      <td class="num" data-amt="${idx}">0.00</td>
      <td data-vardiff="${idx}"></td>
      <td><span class="chip ${st}">${st}</span></td>
      <td>
        <button type="button" class="ghost" data-hold="${idx}">${st==='hold'?'ปลดพัก':'พัก'}</button>
        <button type="button" class="ghost" data-skip="${idx}" title="ไม่รับรอบนี้ คงค้างรับ">ไม่รับ</button>
      </td>`;
    body.appendChild(tr);
    refreshVarianceCell(idx);
  });
  body.querySelectorAll('input[data-k]').forEach(inp=>{
    inp.addEventListener('input', ()=>{
      const i = Number(inp.dataset.i); const k = inp.dataset.k;
      const ln = state.draftLines[i];
      ln[k] = numVal(inp.value);
      ln.qty = Number(ln.bill_qty||0);
      if(!hasVariance(ln)) ln.variance_action = null;
      if(ln.status==='mismatch') ln.status='ok';
      refreshVarianceCell(i);
      recompute();
    });
  });
  body.querySelectorAll('button[data-hold]').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const i = Number(btn.dataset.hold);
      state.draftLines[i].status = state.draftLines[i].status === 'hold' ? 'ok' : 'hold';
      renderDraft();
    });
  });
  body.querySelectorAll('button[data-skip]').forEach(btn=>{
    btn.addEventListener('click', ()=>{
      const i = Number(btn.dataset.skip);
      state.draftLines.splice(i, 1);
      renderDraft();
    });
  });
  body.querySelectorAll('button[data-edit]').forEach(btn=>{
    btn.addEventListener('click', ()=> openEditProduct(Number(btn.dataset.edit)));
  });
  body.querySelectorAll('button[data-photo]').forEach(btn=>{
    btn.addEventListener('click', (e)=>{ e.preventDefault(); openPhoto(btn.dataset.photo); });
  });
  recompute();
}

function recompute(){
  let sub = 0;
  let needVariance = false;
  state.draftLines.forEach((ln, idx)=>{
    const bill = Number(ln.bill_qty != null ? ln.bill_qty : ln.qty || 0);
    ln.qty = bill;
    const amt = Math.max(0, bill*Number(ln.cost||0) - Number(ln.discount||0));
    ln.amount = amt;
    const cell = document.querySelector(`[data-amt="${idx}"]`);
    if(cell){ cell.textContent = money(amt); cell.parentElement.style.opacity = ln.status==='hold' ? .45 : 1; }
    if(ln.status !== 'hold') sub += amt;
    if(ln.status !== 'hold' && hasVariance(ln) && !ln.variance_action) needVariance = true;
  });
  const disc = Number(el('billDiscount').value||0);
  const before = Math.max(0, sub - disc);
  const vat = el('vatOn').checked ? Math.round(before * 0.07 * 100)/100 : 0;
  const net = before + vat;
  el('sumSub').textContent = money(sub);
  el('sumDisc').textContent = money(disc);
  el('sumVat').textContent = money(vat);
  el('sumNet').textContent = money(net);
  const hint = el('varianceHint');
  if(hint){ hint.hidden = !needVariance && !state.draftLines.some(ln => ln.status!=='hold' && hasVariance(ln)); }
  return {subtotal:sub, discount:disc, tax:vat, net};
}

function draftPayload(){
  const t = recompute();
  return {
    vendor_acctno: state.vendor.acctno,
    vendor_name: state.vendor.name || state.vendor.acctno,
    vendor_billno: el('vendorBillno').value.trim(),
    vendor_bill_date: el('vendorBillDate').value || null,
    receive_date: el('receiveDate').value || null,
    pay_method: el('payMethod').value,
    receiver: el('receiver').value.trim() || USER,
    discount: t.discount,
    tax: t.tax,
    vat_rate: el('vatOn').checked ? 7 : 0,
    net: t.net,
    extraction_id: state.extractionId,
    lines: state.draftLines,
  };
}

async function saveDraft(){
  el('draftErr').hidden = true;
  try{
    const body = draftPayload();
    let data;
    if(state.receiptId) data = await api('/receipts/' + state.receiptId, {method:'PUT', body: JSON.stringify(body)});
    else { data = await api('/receipts', {method:'POST', body: JSON.stringify(body)}); state.receiptId = data.receipt_id; }
    el('draftResult').textContent = 'บันทึกร่างแล้ว · ' + (data.short_id || data.receipt_id);
  }catch(e){ el('draftErr').hidden=false; el('draftErr').textContent=e.message||String(e); }
}

async function confirmDraft(){
  el('draftErr').hidden = true;
  const unresolved = state.draftLines.filter(ln =>
    ln.status !== 'hold' && hasVariance(ln) && !ln.variance_action
  );
  if(unresolved.length){
    el('draftErr').hidden=false;
    el('draftErr').textContent='มีรายการที่จำนวนบิล≠รับจริง — เลือกทำใบลดหนี้ / รอของตามมา / เปลี่ยนสินค้าก่อนยืนยัน';
    return;
  }
  try{
    await saveDraft();
    const data = await api('/receipts/' + state.receiptId + '/confirm', {method:'POST', body:'{}'});
    const w = data.write || {};
    const cn = data.credit_note || w.credit_note || {};
    let msg = w.dry_run
      ? 'Dry-run ผ่าน (ยังไม่เขียน PARTS9) — เปิด HQ_RECEIVE_PIMAS_WRITE_ENABLED เมื่อพร้อม'
      : ('รับเข้าแล้ว · บิล ' + (w.pimas_billno || w.kcw_billno));
    if(w.cn_billno || cn.cn_billno) msg += ' · ใบลดหนี้ ' + (w.cn_billno || cn.cn_billno);
    if((data.warnings||[]).length) msg += ' · ' + data.warnings.join(' · ');
    el('draftResult').textContent = msg;
    showBanner(msg, !!w.dry_run);
    state.pimasBillno = w.pimas_billno || null;
    const stickers = data.sticker_lines || state.draftLines
      .filter(ln => ln.status !== 'hold')
      .map(ln => ({
        bcode: ln.bcode,
        qty: Math.max(1, Math.round(Number(ln.received_qty != null ? ln.received_qty : ln.qty)||1)),
        descr: ln.descr||'', selected:true
      }));
    state.stickerSource = (stickers||[]).filter(ln => Number(ln.qty)>0)
      .map(ln => ({...ln, selected: true, qty: Math.max(1, Math.round(Number(ln.qty)||1))}));
    el('btnToStickers').disabled = state.stickerSource.length === 0;
    if(cn && (cn.status === 'awaiting_vendor_doc' || (w.credit_note||{}).is_vat)){
      /* keep receive panel; operator can open credit-notes tab */
    }
  }catch(e){ el('draftErr').hidden=false; el('draftErr').textContent=e.message||String(e); }
}

async function loadCreditNotes(){
  const st = el('cnStatusFilter').value;
  const q = st ? ('?status=' + encodeURIComponent(st)) : '';
  const data = await api('/credit-notes' + q);
  const box = el('creditNoteList');
  box.innerHTML = '';
  (data.credit_notes||[]).forEach(cn=>{
    const row = document.createElement('div');
    row.className = 'row';
    const awaiting = cn.status === 'awaiting_vendor_doc';
    row.innerHTML = `<div style="flex:1">
        <div><strong>${cn.cn_billno||'-'}</strong>
          <span class="chip ${awaiting?'mismatch':'ok'}">${awaiting?'รอเอกสาร':'ครบแล้ว'}</span>
          ${cn.is_vat?'<span class="chip">VAT</span>':''}
        </div>
        <div class="meta">บิลซื้อ ${cn.source_pimas_billno||'-'} · ${cn.vendor_name||cn.vendor_acctno||''}
          · สุทธิ ${money(cn.aftertax)} · รายการ ${(cn.lines||[]).length}</div>
        ${cn.vendor_cn_no?('<div class="meta">เลขเจ้าหนี้ '+cn.vendor_cn_no+(cn.vendor_cn_date?' · '+cn.vendor_cn_date:'')+'</div>'):''}
        ${awaiting?`<div class="bar" style="margin-top:8px">
          <input data-cnno placeholder="เลขที่ใบลดหนี้เจ้าหนี้" style="flex:1"/>
          <input data-cndate type="date"/>
          <button type="button" data-save>บันทึก</button>
        </div>`:''}
      </div>`;
    const saveBtn = row.querySelector('button[data-save]');
    if(saveBtn){
      saveBtn.onclick = async ()=>{
        const no = row.querySelector('[data-cnno]').value.trim();
        const dt = row.querySelector('[data-cndate]').value || null;
        try{
          await api('/credit-notes/' + cn.credit_note_id + '/vendor-doc', {
            method:'POST', body: JSON.stringify({vendor_cn_no: no, vendor_cn_date: dt})
          });
          showBanner('บันทึกเลขใบลดหนี้เจ้าหนี้แล้ว · ' + no);
          loadCreditNotes();
        }catch(e){ showBanner(e.message||String(e), true); }
      };
    }
    box.appendChild(row);
  });
  if(!(data.credit_notes||[]).length) box.innerHTML = '<div class="meta">ไม่มีใบลดหนี้ตามตัวกรองนี้</div>';
}

async function runExtract(){
  if(!state.vendor) return;
  const f = el('invoiceFile').files[0];
  if(!f){ showBanner('เลือกไฟล์รูปบิลก่อน', true); return; }
  const fd = new FormData();
  fd.append('file', f);
  fd.append('vendor_acctno', state.vendor.acctno);
  try{
    const data = await api('/invoices/extract', {method:'POST', body: fd});
    state.extractionId = data.extraction_id;
    const s = data.structured || {};
    if(s.vendor_billno) el('vendorBillno').value = s.vendor_billno;
    if(s.bill_date) el('vendorBillDate').value = s.bill_date;
    if(Number(s.discount||0)) el('billDiscount').value = s.discount;
    if(Number(s.vat||0) > 0) el('vatOn').checked = true;
    el('aiMeta').textContent = 'อ่านหัวบิลแล้ว · เลขบิล ' + (s.vendor_billno||'-') +
      ' · conf ' + ((data.confidence||0)*100).toFixed(0) + '%' +
      ((s.warnings||[]).length ? ' · ' + s.warnings.join('; ') : '');
    showBanner('เติมหัวบิลจาก AI แล้ว — รายการสินค้าให้เลือกจาก PO');
    if(state.draftLines.length) openDraft();
  }catch(e){ showBanner(e.message||String(e), true); }
}

function renderStickerLines(){
  const box = el('stickerLines');
  box.innerHTML = '';
  if(!state.stickerSource.length){
    box.innerHTML = '<div class="meta">ยังไม่มีรายการ — ยืนยันรับเข้าก่อน หรือเลือกจากประวัติ</div>';
    return;
  }
  state.stickerSource.forEach((ln, idx)=>{
    const row = document.createElement('label');
    row.className = 'row' + (ln.selected ? ' on' : '');
    row.innerHTML = `<input type="checkbox" ${ln.selected?'checked':''}/>
      <div class="grow" style="flex:1"><strong>${ln.bcode}</strong> ${ln.descr||''}</div>
      <input type="number" min="1" value="${ln.qty}" style="width:4.5rem" data-q="${idx}"/>`;
    const cb = row.querySelector('input[type=checkbox]');
    cb.onchange = ()=>{ ln.selected = cb.checked; row.classList.toggle('on', cb.checked); };
    row.querySelector('input[type=number]').oninput = (e)=>{ ln.qty = Math.max(1, Number(e.target.value||1)); };
    box.appendChild(row);
  });
}

function selectedStickers(){
  return state.stickerSource.filter(ln => ln.selected).map(ln => ({bcode: ln.bcode, qty: ln.qty, descr: ln.descr||''}));
}

async function previewStickers(){
  const lines = selectedStickers();
  if(!lines.length){ showBanner('เลือกสินค้าอย่างน้อย 1 รายการ', true); return; }
  const data = await api('/stickers/preview', {method:'POST', body: JSON.stringify({
    lines, printer_model: el('printerModel').value
  })});
  if(data.preview_png_b64){
    el('stickerPreview').src = 'data:image/png;base64,' + data.preview_png_b64;
    el('stickerPreview').hidden = false;
  }
}

async function printStickers(action){
  const lines = selectedStickers();
  if(!lines.length){ showBanner('เลือกสินค้าอย่างน้อย 1 รายการ', true); return; }
  const body = {
    lines, action, printer_model: el('printerModel').value,
    printer_host: el('printerHost').value.trim(),
    receipt_id: state.receiptId, pimas_billno: state.pimasBillno
  };
  if(action === 'download'){
    const res = await api('/stickers/print', {method:'POST', body: JSON.stringify(body)});
    const blob = await res.blob();
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'kcw-hq-receive-stickers.prn';
    a.click();
    showBanner('ดาวน์โหลด .prn แล้ว');
  }else{
    await api('/stickers/print', {method:'POST', body: JSON.stringify(body)});
    showBanner('ส่งพิมพ์แล้ว');
  }
  loadStickerJobs();
}

async function loadStickerJobs(){
  const data = await api('/stickers/jobs' + (state.receiptId ? ('?receipt_id='+encodeURIComponent(state.receiptId)) : ''));
  const box = el('stickerJobs');
  box.innerHTML = '';
  (data.jobs||[]).forEach(j=>{
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `<div style="flex:1"><div><strong>${j.job_id?.slice?.(0,8)||j.job_id}</strong> <span class="chip">${j.action}</span></div>
      <div class="meta">${j.copies||0} แผ่น · ${j.printer_model||''} · ${j.pimas_billno||j.receipt_id||''}</div></div>`;
    box.appendChild(row);
  });
}

async function loadHistory(){
  const data = await api('/history');
  const box = el('historyList');
  box.innerHTML = '';
  (data.receipts||[]).forEach(r=>{
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `<div style="flex:1"><div><strong>${r.short_id||r.receipt_id}</strong> <span class="chip ${r.status==='confirmed'?'ok':'hold'}">${r.status}</span></div>
      <div class="meta">${r.vendor_name||r.vendor_acctno||''} · บิลเจ้าหนี้ ${r.vendor_billno||'-'} · PIMAS ${r.pimas_billno||'-'} · สุทธิ ${money(r.net)}</div></div>
      <button type="button" class="ghost">บาร์โค้ด</button>`;
    row.querySelector('button').onclick = async (e)=>{
      e.stopPropagation();
      try{
        const full = await api('/receipts/' + r.receipt_id);
        state.receiptId = r.receipt_id;
        state.pimasBillno = r.pimas_billno;
        state.stickerSource = (full.lines||[]).filter(ln => ln.status !== 'hold')
          .map(ln => {
            const q = Number(ln.received_qty != null ? ln.received_qty : ln.qty || 0);
            return {bcode: ln.bcode, qty: Math.max(1, Math.round(q||1)), descr: ln.descr||'', selected:true};
          })
          .filter(ln => Number(ln.qty)>0);
        setTab('stickers');
      }catch(err){ showBanner(err.message||String(err), true); }
    };
    box.appendChild(row);
  });
  if(!(data.receipts||[]).length) box.innerHTML = '<div class="meta">ยังไม่มีประวัติ</div>';
}

async function loadIssues(){
  const data = await api('/discrepancies?status=open');
  const box = el('issueList');
  box.innerHTML = '';
  (data.discrepancies||[]).forEach(d=>{
    const row = document.createElement('div');
    row.className = 'row';
    row.innerHTML = `<div style="flex:1"><div><span class="chip mismatch">${d.kind}</span> <strong>${d.bcode||'-'}</strong></div>
      <div class="meta">${JSON.stringify(d.detail||{})}</div></div>`;
    box.appendChild(row);
  });
  if(!(data.discrepancies||[]).length) box.innerHTML = '<div class="meta">ไม่มีรายการผิดปกติค้างอยู่</div>';
}

el('btnVendors').onclick = ()=> loadVendors().catch(e=> showBanner(e.message, true));
el('vendorQ').addEventListener('keydown', e=>{ if(e.key==='Enter'){ e.preventDefault(); el('btnVendors').click(); }});
el('btnReloadPos').onclick = ()=> loadOpenPos().catch(e=> showBanner(e.message, true));
el('btnUsePos').onclick = ()=> useSelectedPos();
el('btnNewProduct').onclick = ()=> openNewProductDlg();
el('btnDraftNewProduct').onclick = ()=> openNewProductDlg();
el('btnCreateProduct').onclick = ()=> createNewProduct();
el('btnCancelProduct').onclick = ()=> el('newProductDlg').close();
el('btnSaveProduct').onclick = ()=> saveEditProduct();
el('btnCancelEditProduct').onclick = ()=> { state.editIdx = null; el('editProductDlg').close(); };
el('photoOverlay').onclick = ()=> closePhoto();
el('btnExtract').onclick = ()=> runExtract();
el('btnSaveDraft').onclick = ()=> saveDraft();
el('btnConfirm').onclick = ()=> confirmDraft();
el('btnToStickers').onclick = ()=> setTab('stickers');
el('btnHistory').onclick = ()=> loadHistory().catch(e=> showBanner(e.message, true));
el('btnIssues').onclick = ()=> loadIssues().catch(e=> showBanner(e.message, true));
el('btnCreditNotes').onclick = ()=> loadCreditNotes().catch(e=> showBanner(e.message, true));
el('cnStatusFilter').onchange = ()=> loadCreditNotes().catch(e=> showBanner(e.message, true));
el('btnPreview').onclick = ()=> previewStickers().catch(e=> showBanner(e.message, true));
el('btnPrintDl').onclick = ()=> printStickers('download').catch(e=> showBanner(e.message, true));
el('btnPrintLan').onclick = ()=> printStickers('print').catch(e=> showBanner(e.message, true));
el('billDiscount').addEventListener('input', recompute);
el('vatOn').addEventListener('change', recompute);

(async function init(){
  try{
    const meta = await api('/meta');
    if(!meta.write_enabled) showBanner('โหมดปลอดภัย: ยังไม่เขียน PIMAS จนกว่าจะเปิด HQ_RECEIVE_PIMAS_WRITE_ENABLED');
    if(meta.sticker_printer_model) el('printerModel').value = meta.sticker_printer_model;
    const cfg = await api('/stickers/config');
    if(cfg.default_host) el('printerHost').value = cfg.default_host;
    await loadVendors();
  }catch(e){ showBanner(e.message || String(e), true); }
})();
</script>
</body>
</html>
"""

from __future__ import annotations

APP = "pay-notes"
SESSION_COOKIE = "kcw_pay_notes"


def page(*, user_name: str = "", site: str = "HQ", write_enabled: bool = False) -> str:
    who = (user_name or "operator").strip()
    site_u = (site or "HQ").upper()
    write_flag = "true" if write_enabled else "false"
    return _HTML.replace("__USER__", who).replace("__SITE__", site_u).replace("__WRITE__", write_flag)


_HTML = r"""<!doctype html>
<html lang="th" data-theme="dark">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="dark light"/>
<meta name="theme-color" content="#0c1014" id="themeColor"/>
<title>ชำระเจ้าหนี้</title>
<script>
(function () {
  try {
    var t = localStorage.getItem("kcw.pay_notes.theme");
    if (t !== "light" && t !== "dark") {
      t = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
</script>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
:root { --acc:#3d9cf0; --ok:#3ecf8e; --warn:#e6b450; --down:#e25c5c; --on-acc:#071018; }
html[data-theme="dark"] {
  color-scheme: dark;
  --bg:#0c1014; --card:#161d26; --line:#2a3542; --text:#e8eef4; --muted:#8b9aab; --chip:#243040; --inset:#0a0e12;
}
html[data-theme="light"] {
  color-scheme: light;
  --bg:#f4f6f8; --card:#ffffff; --line:#d5dde6; --text:#1b2430; --muted:#5b6b7c; --chip:#e8eef4; --inset:#eef2f6;
}
* { box-sizing:border-box; }
body { margin:0; font-family:Prompt,sans-serif; background:var(--bg); color:var(--text); }
header { padding:.75rem 1rem; border-bottom:1px solid var(--line); position:sticky; top:0; background:var(--bg); z-index:2; }
.brand { display:flex; align-items:flex-start; justify-content:space-between; gap:.6rem; }
h1 { margin:0; font-size:1.05rem; }
.meta { font-size:.78rem; color:var(--muted); margin-top:.2rem; }
.tabs { display:flex; gap:.35rem; margin-top:.55rem; flex-wrap:wrap; }
.tabs button { flex:1; min-width:5.5rem; border:1px solid var(--line); background:var(--chip); color:var(--text); border-radius:.55rem; padding:.45rem; font:inherit; cursor:pointer; }
.tabs button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:600; }
main { max-width:960px; margin:0 auto; padding:1rem; }
.panel { display:none; }
.panel.on { display:block; }
.card { background:var(--card); border:1px solid var(--line); border-radius:.65rem; padding:.85rem; margin-bottom:.75rem; }
label { display:block; font-size:.78rem; color:var(--muted); margin:.35rem 0 .15rem; }
input, select, button, textarea { font:inherit; padding:.5rem .65rem; border-radius:.5rem; border:1px solid var(--line); background:var(--inset); color:var(--text); width:100%; }
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:600; cursor:pointer; width:auto; }
button.theme { width:auto; min-width:2.6rem; flex:0 0 auto; background:var(--chip); cursor:pointer; }
button.linkish { width:auto; background:none; border:none; color:var(--acc); text-decoration:underline; cursor:pointer; padding:0; }
.row { display:flex; gap:.5rem; flex-wrap:wrap; align-items:center; }
.row > * { flex:1; min-width:8rem; }
.bill { display:flex; gap:.5rem; align-items:flex-start; padding:.35rem 0; border-bottom:1px solid var(--line); }
.bill:last-child { border-bottom:none; }
.bill input { width:auto; flex:0 0 auto; }
.note-row { padding:.55rem 0; border-bottom:1px solid var(--line); }
.note-row:last-child { border-bottom:none; }
.badge { font-size:.72rem; padding:.1rem .4rem; border-radius:.35rem; background:var(--chip); color:var(--muted); }
.err { color:var(--down); font-size:.85rem; margin:.35rem 0; }
.ok { color:var(--ok); font-size:.85rem; }
.thumbs { display:flex; gap:.35rem; flex-wrap:wrap; margin-top:.35rem; }
.thumbs img { width:72px; height:72px; object-fit:cover; border-radius:.35rem; border:1px solid var(--line); }
.hidden { display:none !important; }
.dlg {
  border:1px solid var(--line); border-radius:.7rem; background:var(--card); color:var(--text);
  padding:1rem; max-width:36rem; width:calc(100% - 2rem);
  max-height:min(92dvh, 40rem); overflow-y:auto; overscroll-behavior:contain;
}
.dlg::backdrop { background:rgba(0,0,0,.55); }
.pay-box {
  margin:.5rem 0 .75rem; padding:.65rem .75rem; border-radius:.55rem;
  border:1px solid var(--line); background:var(--inset);
}
.pay-box .pay-line { display:flex; justify-content:space-between; gap:.5rem; margin:.2rem 0; font-size:.9rem; }
.pay-box .pay-line strong { font-variant-numeric:tabular-nums; }
.pay-box .pay-net { margin-top:.35rem; padding-top:.4rem; border-top:1px solid var(--line); font-weight:700; }
.seg { display:flex; gap:.35rem; margin:.25rem 0 .35rem; }
.seg button {
  flex:1; width:auto; cursor:pointer; background:var(--chip); color:var(--text);
}
.seg button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:600; }
.disc-box {
  margin:.55rem 0; padding:.65rem .75rem; border-radius:.55rem;
  border:1px solid var(--line); background:var(--inset);
}
.disc-box .pay-line { display:flex; justify-content:space-between; gap:.5rem; margin:.2rem 0; font-size:.9rem; }
.disc-box .pay-net { margin-top:.35rem; padding-top:.4rem; border-top:1px solid var(--line); font-weight:700; }
input[type="date"] {
  min-height: 2.75rem;
  font-size: 1.05rem;
  letter-spacing: .02em;
  cursor: pointer;
}
.date-hint { font-size:.72rem; color:var(--muted); margin:.1rem 0 .35rem; }
.date-ce { font-variant-numeric: tabular-nums; }
.bill-status {
  margin:.45rem 0 .15rem; padding:.55rem .7rem; border-radius:.5rem;
  border:1px solid var(--line); background:var(--chip); font-size:.9rem; font-weight:600;
}
.bill-status.empty { color:var(--muted); font-weight:500; }
.filters {
  display:grid; gap:.5rem .65rem; margin:.35rem 0 .65rem;
  grid-template-columns: repeat(auto-fit, minmax(9.5rem, 1fr));
}
.filters label { margin-top:0; }
.filters input, .filters select { width:100%; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <div>
      <h1>ชำระเจ้าหนี้ · __SITE__</h1>
      <div class="meta">__USER__ · HQ only · ใบวางบิล → รอชำระ → ใบสำคัญจ่าย</div>
    </div>
    <button type="button" class="theme" id="themeBtn" aria-label="สลับธีม">มืด</button>
  </div>
  <div class="tabs">
    <button type="button" id="tabCreate" class="on">ใบวางบิล</button>
    <button type="button" id="tabPending">รอชำระ</button>
    <button type="button" id="tabProof">ใบสำคัญจ่าย</button>
  </div>
</header>
<main>
  <section id="panelCreate" class="panel on">
    <div class="card">
      <label>ค้นหาเจ้าหนี้ (APMAS)</label>
      <div class="row">
        <input id="vendorQ" placeholder="รหัส / ชื่อ / เลขภาษี"/>
        <button type="button" class="primary" id="btnVendorSearch">ค้นหา</button>
      </div>
      <div id="vendorResults"></div>
      <div id="vendorPick" class="hidden">
        <p><span class="badge" id="pickedVendor"></span></p>
        <label>เลขที่ใบวางบิล (NOTENO) — สูงสุด 15 ตัวอักษร</label>
        <input id="noteno" maxlength="15"/>
        <label>วันครบกำหนดชำระ</label>
        <p class="date-hint">แตะเพื่อเปิดปฏิทิน · ใช้ปี ค.ศ. เช่น 2026 (ไม่พิมพ์ พ.ศ. 2569) · แก้ทีหลังได้ที่แท็บรอชำระ</p>
        <input id="dueDate" class="date-ce" type="date" lang="en" inputmode="none"/>
        <label>บัญชีธนาคาร (required)</label>
        <select id="bankSelect"></select>
        <details style="margin-top:.5rem"><summary>เพิ่มบัญชีใหม่</summary>
          <label>ธนาคาร</label><input id="newBankName"/>
          <label>ชื่อบัญชี</label><input id="newAcctName"/>
          <label>เลขบัญชี</label><input id="newAcctNo"/>
          <button type="button" id="btnAddBank" style="margin-top:.35rem">บันทึกบัญชี</button>
        </details>
        <label style="margin-top:.65rem">เลือกบิล (ยังไม่ผูกโน้ต · unpaid)</label>
        <div class="row" style="margin:.25rem 0 .35rem">
          <button type="button" id="btnRefreshBills">รีเฟรชรายการบิล</button>
        </div>
        <div id="billList"></div>
        <div class="bill-status empty" id="billSelectStatus">ยังไม่ได้เลือกบิล</div>
        <div class="disc-box">
          <label style="margin-top:0">ส่วนลด (บันทึกกับใบวางบิล)</label>
          <div class="seg" role="group" aria-label="ประเภทส่วนลด">
            <button type="button" class="on" id="discModeAmount" data-mode="amount">จำนวนเงิน (บาท)</button>
            <button type="button" id="discModePercent" data-mode="percent">% จากยอดบิล</button>
          </div>
          <label id="discInputLabel" for="discInput">ส่วนลด (บาท)</label>
          <input id="discInput" type="number" inputmode="decimal" step="0.01" min="0" value="0"/>
          <div class="pay-line"><span>ยอดบิลที่เลือก</span><strong id="discBillAmt">0.00</strong></div>
          <div class="pay-line"><span>ส่วนลด</span><strong id="discResolved">0.00</strong></div>
          <div class="pay-line pay-net"><span>ยอดสุทธิที่จะจ่าย</span><strong id="discNetAmt">0.00</strong></div>
        </div>
        <label>รูปใบวางบิล (≥1 ก่อนส่ง)</label>
        <input id="billImages" type="file" accept="image/*" multiple/>
        <div class="thumbs" id="billThumbs"></div>
        <div class="row" style="margin-top:.65rem">
          <button type="button" class="primary" id="btnCreateNote">บันทึกใบวางบิล</button>
        </div>
        <div id="createMsg"></div>
      </div>
    </div>
  </section>

  <section id="panelPending" class="panel">
    <div class="card">
      <div class="row" style="margin-bottom:.35rem">
        <button type="button" class="primary" id="btnRefreshPending">รีเฟรช</button>
        <button type="button" id="btnClearPendingFilters">ล้างตัวกรอง</button>
      </div>
      <div class="filters" id="pendingFilters">
        <div>
          <label for="pfQ">ค้นหา AP / ชื่อ / เลขใบวางบิล</label>
          <input id="pfQ" placeholder="เช่น BRC หรือ 08-003" autocomplete="off"/>
        </div>
        <div>
          <label for="pfAcct">รหัส AP</label>
          <select id="pfAcct"><option value="">ทั้งหมด</option></select>
        </div>
        <div>
          <label for="pfMonth">เดือนครบกำหนด</label>
          <select id="pfMonth"><option value="">ทั้งหมด</option></select>
        </div>
        <div>
          <label for="pfFrom">ครบกำหนดตั้งแต่</label>
          <input id="pfFrom" class="date-ce" type="date" lang="en" inputmode="none"/>
        </div>
        <div>
          <label for="pfTo">ถึงวันที่</label>
          <input id="pfTo" class="date-ce" type="date" lang="en" inputmode="none"/>
        </div>
        <div>
          <label for="pfSort">เรียงโดย</label>
          <select id="pfSort">
            <option value="due_asc">วันครบกำหนด ↑</option>
            <option value="due_desc">วันครบกำหนด ↓</option>
            <option value="acct_asc">รหัส AP ↑</option>
            <option value="acct_desc">รหัส AP ↓</option>
            <option value="note_asc">เลขใบวางบิล ↑</option>
            <option value="note_desc">เลขใบวางบิล ↓</option>
            <option value="amt_desc">ยอดบิลมาก→น้อย</option>
            <option value="amt_asc">ยอดบิลน้อย→มาก</option>
            <option value="notedate_desc">วันที่โน้ตใหม่→เก่า</option>
            <option value="notedate_asc">วันที่โน้ตเก่า→ใหม่</option>
          </select>
        </div>
      </div>
      <div class="bill-status empty" id="pendingStatus">ยังไม่มีรายการ</div>
      <div id="pendingList"></div>
    </div>
  </section>

  <section id="panelProof" class="panel">
    <div class="card">
      <div class="row"><button type="button" class="primary" id="btnRefreshProof">รีเฟรช</button></div>
      <div id="proofList"></div>
    </div>
  </section>
</main>

<dialog id="dlgPay" class="dlg">
  <h2 style="margin:0 0 .5rem;font-size:1rem">บันทึกใบสำคัญจ่าย</h2>
  <div id="payDetail" class="meta"></div>
  <div class="pay-box">
    <div class="pay-line"><span>ยอดบิล</span><strong id="payBillAmt">0.00</strong></div>
    <div class="pay-line"><span>ส่วนลด (จากใบวางบิล)</span><strong id="payDiscountAmt">0.00</strong></div>
    <div class="pay-line pay-net"><span>ยอดสุทธิ</span><strong id="payNetAmt">0.00</strong></div>
    <p class="meta" id="payBankLine" style="margin:.45rem 0 0"></p>
  </div>
  <label>วิธีชำระ</label>
  <div class="seg" role="group" aria-label="วิธีชำระ">
    <button type="button" class="on" id="settleTransfer" data-settle="transfer">โอน</button>
    <button type="button" id="settleCheque" data-settle="cheque">เช็ค</button>
    <button type="button" id="settleCash" data-settle="cash">เงินสด</button>
  </div>
  <p class="meta" id="settleHint" style="margin:.15rem 0 .35rem">โอน → ใส่คำว่า โอน ใน CHKNO · เช็ค → เลขที่เช็ค · เงินสด → เว้น CHKNO ว่างได้</p>
  <label id="payChknoLabel" for="payChkno">CHKNO</label>
  <input id="payChkno" value="โอน" maxlength="15"/>
  <label for="payChkamt">CHKAMT (ยอดโอน / เช็ค / เงินสด)</label>
  <input id="payChkamt" type="number" inputmode="decimal" step="0.01" min="0"/>
  <label for="payChkdate">วันที่โอน / เช็ค</label>
  <p class="date-hint">แตะเพื่อเปิดปฏิทิน · ปี ค.ศ.</p>
  <input id="payChkdate" class="date-ce" type="date" lang="en" inputmode="none"/>
  <label for="payBankGl">บัญชีธนาคาร GL (BPDET.ACCTNO)</label>
  <input id="payBankGl" value="2101.7"/>
  <div class="row" style="margin-top:.75rem">
    <button type="button" class="primary" id="btnConfirmPay">บันทึก voucher + BPDET</button>
    <button type="button" id="btnClosePay">ปิด</button>
  </div>
  <div id="payMsg"></div>
</dialog>

<script>
const WRITE_ENABLED = __WRITE__;
let picked = null;
let uploadedPaths = [];
let payTarget = null;
let discMode = 'amount';
let settleMethod = 'transfer';
let pendingRows = [];

function $(id) { return document.getElementById(id); }
function themeLabel(t) { return t === "light" ? "สว่าง" : "มืด"; }
function applyTheme(t) {
  const next = t === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", next);
  const btn = $("themeBtn");
  if (btn) btn.textContent = themeLabel(next);
  const meta = $("themeColor");
  if (meta) meta.setAttribute("content", next === "light" ? "#f4f6f8" : "#0c1014");
  try { localStorage.setItem("kcw.pay_notes.theme", next); } catch (e) {}
}
$("themeBtn").onclick = () => {
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
};
applyTheme(document.documentElement.getAttribute("data-theme") || "dark");

function fmtMoney(n) { return Number(n||0).toLocaleString('th-TH', {minimumFractionDigits:2, maximumFractionDigits:2}); }
function todayISO() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${y}-${m}-${day}`;
}
/** Calendar-only: open native picker, block typing so ปี ค.ศ./พ.ศ. ไม่ปนกัน */
function wireDatePicker(el) {
  if (!el || el.dataset.dateWired === '1') return;
  el.dataset.dateWired = '1';
  el.setAttribute('lang', 'en');
  el.setAttribute('inputmode', 'none');
  el.classList.add('date-ce');
  const open = () => { try { if (typeof el.showPicker === 'function') el.showPicker(); } catch (_) {} };
  el.addEventListener('pointerdown', open);
  el.addEventListener('focus', open);
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Tab' || e.key === 'Escape' || e.key === 'Enter') return;
    e.preventDefault();
    open();
  });
}
function wireDatePickers(root) {
  (root || document).querySelectorAll('input[type="date"]').forEach(wireDatePicker);
}

function showTab(name) {
  ['Pending','Create','Proof'].forEach(t => {
    const key = t.toLowerCase();
    $('tab' + t).classList.toggle('on', name === key);
    $('panel' + t).classList.toggle('on', name === key);
  });
  if (name === 'pending') loadPending();
  if (name === 'proof') loadProof();
  if (name === 'create' && picked) loadBills();
}
$('tabPending').onclick = () => showTab('pending');
$('tabCreate').onclick = () => showTab('create');
$('tabProof').onclick = () => showTab('proof');

async function api(path, opts) {
  const r = await fetch('/pay-notes/api' + path, opts || {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || j.error || r.statusText);
  return j;
}

async function loadPending() {
  $('pendingList').innerHTML = 'กำลังโหลด…';
  $('pendingStatus').className = 'bill-status empty';
  $('pendingStatus').textContent = 'กำลังโหลด…';
  try {
    pendingRows = await api('/pending');
    rebuildPendingFilterOptions();
    renderPendingList();
  } catch (e) {
    pendingRows = [];
    $('pendingList').innerHTML = `<p class="err">${e.message}</p>`;
    $('pendingStatus').className = 'bill-status empty';
    $('pendingStatus').textContent = 'โหลดไม่สำเร็จ';
  }
}
$('btnRefreshPending').onclick = loadPending;

function remDue(r) {
  const d = ((r.reminder || {}).due_date || '');
  return String(d).slice(0, 10);
}
function rebuildPendingFilterOptions() {
  const accts = [...new Map(
    pendingRows.map(r => [String(r.acctno || '').trim(), String(r.acctname || '').trim()])
  ).entries()].filter(([a]) => a).sort((a, b) => a[0].localeCompare(b[0], 'th'));
  const curAcct = $('pfAcct').value;
  $('pfAcct').innerHTML = '<option value="">ทั้งหมด</option>' + accts.map(([a, n]) =>
    `<option value="${a}">${a}${n ? ' — ' + n : ''}</option>`
  ).join('');
  if ([...$('pfAcct').options].some(o => o.value === curAcct)) $('pfAcct').value = curAcct;

  const months = [...new Set(pendingRows.map(remDue).filter(d => d.length >= 7).map(d => d.slice(0, 7)))].sort();
  const curMonth = $('pfMonth').value;
  const monthLabel = (ym) => {
    const [y, m] = ym.split('-');
    const names = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];
    return `${names[Number(m)] || m} ${y}`;
  };
  $('pfMonth').innerHTML = '<option value="">ทั้งหมด</option>' + months.map(ym =>
    `<option value="${ym}">${monthLabel(ym)}</option>`
  ).join('');
  if ([...$('pfMonth').options].some(o => o.value === curMonth)) $('pfMonth').value = curMonth;
}
function filteredPendingRows() {
  const q = ($('pfQ').value || '').trim().toLowerCase();
  const acct = ($('pfAcct').value || '').trim();
  const month = ($('pfMonth').value || '').trim();
  const from = ($('pfFrom').value || '').trim();
  const to = ($('pfTo').value || '').trim();
  let rows = pendingRows.filter(r => {
    const due = remDue(r);
    if (acct && String(r.acctno || '').trim() !== acct) return false;
    if (month && !due.startsWith(month)) return false;
    if (from && (!due || due < from)) return false;
    if (to && (!due || due > to)) return false;
    if (q) {
      const hay = [
        r.acctno, r.acctname, r.noteno, due,
        ((r.reminder || {}).vendor_bank || {}).bank_name,
        ((r.reminder || {}).vendor_bank || {}).bank_account_number,
      ].map(x => String(x || '').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  const sort = $('pfSort').value || 'due_asc';
  const cmpStr = (a, b) => String(a || '').localeCompare(String(b || ''), 'th', {numeric: true});
  const cmpNum = (a, b) => Number(a || 0) - Number(b || 0);
  rows = [...rows].sort((a, b) => {
    switch (sort) {
      case 'due_desc': return cmpStr(remDue(b), remDue(a));
      case 'acct_asc': return cmpStr(a.acctno, b.acctno) || cmpStr(a.noteno, b.noteno);
      case 'acct_desc': return cmpStr(b.acctno, a.acctno) || cmpStr(a.noteno, b.noteno);
      case 'note_asc': return cmpStr(a.noteno, b.noteno);
      case 'note_desc': return cmpStr(b.noteno, a.noteno);
      case 'amt_asc': return cmpNum(a.BILLAMT, b.BILLAMT);
      case 'amt_desc': return cmpNum(b.BILLAMT, a.BILLAMT);
      case 'notedate_asc': return cmpStr(a.NOTEDATE, b.NOTEDATE);
      case 'notedate_desc': return cmpStr(b.NOTEDATE, a.NOTEDATE);
      case 'due_asc':
      default: return cmpStr(remDue(a), remDue(b)) || cmpStr(a.acctno, b.acctno);
    }
  });
  return rows;
}
function clearPendingFilters() {
  $('pfQ').value = '';
  $('pfAcct').value = '';
  $('pfMonth').value = '';
  $('pfFrom').value = '';
  $('pfTo').value = '';
  $('pfSort').value = 'due_asc';
  renderPendingList();
}
$('btnClearPendingFilters').onclick = clearPendingFilters;
['pfQ','pfAcct','pfMonth','pfFrom','pfTo','pfSort'].forEach(id => {
  const el = $(id);
  el.addEventListener(el.tagName === 'INPUT' && el.type !== 'date' ? 'input' : 'change', renderPendingList);
});

function renderPendingList() {
  const rows = filteredPendingRows();
  const total = pendingRows.length;
  const shown = rows.length;
  const sumBill = rows.reduce((s, r) => s + Number(r.BILLAMT || 0), 0);
  const sumNet = rows.reduce((s, r) => {
    const disc = Number((r.reminder || {}).discount_amount || 0);
    return s + Math.max(0, Number(r.BILLAMT || 0) - disc);
  }, 0);
  if (!total) {
    $('pendingStatus').className = 'bill-status empty';
    $('pendingStatus').textContent = 'ไม่มีรายการรอชำระ (จากบริการนี้)';
    $('pendingList').innerHTML = '';
    return;
  }
  $('pendingStatus').className = 'bill-status';
  $('pendingStatus').textContent = shown === total
    ? `แสดง ${shown} รายการ · บิล ${fmtMoney(sumBill)} · จ่าย ${fmtMoney(sumNet)}`
    : `แสดง ${shown} จาก ${total} · บิล ${fmtMoney(sumBill)} · จ่าย ${fmtMoney(sumNet)}`;
  if (!shown) {
    $('pendingList').innerHTML = '<p class="meta">ไม่พบรายการตามตัวกรอง</p>';
    return;
  }
  $('pendingList').innerHTML = rows.map(r => {
      const rem = r.reminder || {};
      const due = remDue(r);
      const bank = rem.vendor_bank || {};
      const bill = Number(r.BILLAMT || 0);
      const disc = Number(rem.discount_amount || 0);
      const net = Math.max(0, bill - disc);
      const discHint = rem.discount_mode === 'percent'
        ? `ส่วนลด ${Number(rem.discount_input||0)}% = ${fmtMoney(disc)}`
        : (disc > 0 ? `ส่วนลด ${fmtMoney(disc)}` : 'ไม่มีส่วนลด');
      const key = `${r.acctno}|${r.noteno}`;
      return `<div class="note-row">
        <strong>${r.acctname || r.acctno}</strong> · ${r.noteno}<br/>
        <span class="meta">บิล ${fmtMoney(bill)} · ${discHint} · จ่าย ${fmtMoney(net)} · ${r.BILLCNT} บิล</span><br/>
        <span class="meta">${bank.bank_name || ''} ${bank.bank_account_number || ''}</span>
        <div class="row" style="margin-top:.35rem; align-items:flex-end">
          <div style="flex:1;min-width:10rem">
            <label style="margin-top:0">วันครบกำหนดชำระ</label>
            <div class="row" style="margin:0; align-items:center; gap:.35rem">
              <span class="meta" data-due-view="${key}" style="font-size:1.05rem;color:var(--text);font-variant-numeric:tabular-nums">${due || '—'}</span>
              <button type="button" class="linkish" data-due-edit="${key}" title="แก้ไขวันครบกำหนด" aria-label="แก้ไขวันครบกำหนด">แก้ไข</button>
              <input type="date" class="date-ce hidden" lang="en" inputmode="none" value="${due}"
                data-due-input="${key}" data-due-orig="${due}"/>
              <button type="button" class="primary hidden" data-due-save="${key}">บันทึก</button>
              <button type="button" class="linkish hidden" data-due-cancel="${key}">ยกเลิก</button>
            </div>
            <span class="meta" data-due-status="${key}"></span>
          </div>
          <button type="button" class="primary"
            data-pay-acct="${r.acctno}"
            data-pay-note="${r.noteno}"
            data-pay-amt="${bill}"
            data-pay-disc="${disc}"
            data-pay-bank="${(bank.bank_name||'') + ' ' + (bank.bank_account_name||'') + ' # ' + (bank.bank_account_number||'')}">บันทึกใบสำคัญ</button>
        </div>
      </div>`;
  }).join('');
  wireDatePickers($('pendingList'));

  function dueEls(key) {
    return {
      view: $('pendingList').querySelector(`[data-due-view="${key}"]`),
      edit: $('pendingList').querySelector(`[data-due-edit="${key}"]`),
      inp: $('pendingList').querySelector(`[data-due-input="${key}"]`),
      save: $('pendingList').querySelector(`[data-due-save="${key}"]`),
      cancel: $('pendingList').querySelector(`[data-due-cancel="${key}"]`),
      status: $('pendingList').querySelector(`[data-due-status="${key}"]`),
    };
  }
  function setDueEditMode(key, on) {
    const el = dueEls(key);
    if (!el.inp) return;
    el.view.classList.toggle('hidden', on);
    el.edit.classList.toggle('hidden', on);
    el.inp.classList.toggle('hidden', !on);
    el.save.classList.toggle('hidden', !on);
    el.cancel.classList.toggle('hidden', !on);
    if (on) {
      el.inp.value = el.inp.dataset.dueOrig || '';
      try { el.inp.focus(); if (typeof el.inp.showPicker === 'function') el.inp.showPicker(); } catch (_) {}
    }
  }
  $('pendingList').querySelectorAll('[data-due-edit]').forEach(btn => {
    btn.onclick = () => setDueEditMode(btn.dataset.dueEdit, true);
  });
  $('pendingList').querySelectorAll('[data-due-cancel]').forEach(btn => {
    btn.onclick = () => {
      const key = btn.dataset.dueCancel;
      const el = dueEls(key);
      el.inp.value = el.inp.dataset.dueOrig || '';
      if (el.status) el.status.textContent = '';
      setDueEditMode(key, false);
    };
  });
  $('pendingList').querySelectorAll('[data-due-save]').forEach(btn => {
    btn.onclick = async () => {
      const key = btn.dataset.dueSave;
      const [acct, note] = key.split('|');
      const el = dueEls(key);
      const next = (el.inp.value || '').trim();
      if (!next) { alert('เลือกวันครบกำหนด'); return; }
      if (next === el.inp.dataset.dueOrig) {
        setDueEditMode(key, false);
        return;
      }
      btn.disabled = true;
      if (el.status) el.status.textContent = 'กำลังบันทึก…';
      try {
        await api(`/reminder/${encodeURIComponent(acct)}/${encodeURIComponent(note)}`, {
          method: 'PATCH', headers: {'Content-Type':'application/json'},
          body: JSON.stringify({due_date: next})
        });
        const row = pendingRows.find(x => String(x.acctno) === acct && String(x.noteno) === note);
        if (row && row.reminder) row.reminder.due_date = next;
        el.inp.dataset.dueOrig = next;
        el.view.textContent = next;
        if (el.status) el.status.textContent = '';
        setDueEditMode(key, false);
        rebuildPendingFilterOptions();
        renderPendingList();
      } catch (e) {
        alert(e.message);
        if (el.status) el.status.textContent = '';
      } finally {
        btn.disabled = false;
      }
    };
  });
  $('pendingList').querySelectorAll('[data-pay-acct]').forEach(btn => {
    btn.onclick = () => openPay(
      btn.dataset.payAcct,
      btn.dataset.payNote,
      btn.dataset.payAmt,
      btn.dataset.payDisc,
      btn.dataset.payBank || ''
    );
  });
}

function setSettleMethod(method) {
  settleMethod = method === 'cheque' ? 'cheque' : (method === 'cash' ? 'cash' : 'transfer');
  ['transfer','cheque','cash'].forEach(m => {
    const el = $('settle' + m.charAt(0).toUpperCase() + m.slice(1));
    if (el) el.classList.toggle('on', settleMethod === m);
  });
  const hints = {
    transfer: 'โอน → ใส่คำว่า โอน ใน CHKNO (ตาม BPDET จริง)',
    cheque: 'เช็ค → กรอกเลขที่เช็คใน CHKNO',
    cash: 'เงินสด → เว้น CHKNO ว่างได้ (ตามระบบเดิมมักไม่ใส่เลข)'
  };
  $('settleHint').textContent = hints[settleMethod];
  if (settleMethod === 'transfer') {
    $('payChknoLabel').textContent = 'CHKNO (โอน)';
    if (!$('payChkno').value.trim() || $('payChkno').dataset.auto === '1') {
      $('payChkno').value = 'โอน';
      $('payChkno').dataset.auto = '1';
    }
    $('payBankGl').disabled = false;
    if (!$('payBankGl').value.trim()) $('payBankGl').value = '2101.7';
  } else if (settleMethod === 'cheque') {
    $('payChknoLabel').textContent = 'CHKNO (เลขที่เช็ค)';
    if ($('payChkno').value.trim() === 'โอน' || $('payChkno').dataset.auto === '1') {
      $('payChkno').value = '';
      $('payChkno').dataset.auto = '1';
    }
    $('payBankGl').disabled = false;
    if (!$('payBankGl').value.trim()) $('payBankGl').value = '2101.7';
  } else {
    $('payChknoLabel').textContent = 'CHKNO (เว้นว่างได้)';
    if ($('payChkno').value.trim() === 'โอน' || $('payChkno').dataset.auto === '1') {
      $('payChkno').value = '';
      $('payChkno').dataset.auto = '1';
    }
    $('payBankGl').disabled = false;
  }
}
$('settleTransfer').onclick = () => setSettleMethod('transfer');
$('settleCheque').onclick = () => setSettleMethod('cheque');
$('settleCash').onclick = () => setSettleMethod('cash');
$('payChkno').addEventListener('input', () => { $('payChkno').dataset.auto = '0'; });

function openPay(acct, note, billamt, discount, bankname) {
  const bill = Number(billamt || 0);
  const disc = Number(discount || 0);
  const net = Math.max(0, bill - disc);
  payTarget = {acctno: acct, noteno: note, billamt: bill, discount: disc, netamt: net};
  $('payDetail').textContent = `${acct} · ${note}`;
  $('payBillAmt').textContent = fmtMoney(bill);
  $('payDiscountAmt').textContent = fmtMoney(disc);
  $('payNetAmt').textContent = fmtMoney(net);
  $('payBankLine').textContent = (bankname || '').trim() || '— ไม่พบบัญชีธนาคาร —';
  $('payChkamt').value = String(net);
  $('payChkdate').value = todayISO();
  $('payBankGl').value = '2101.7';
  $('payMsg').innerHTML = '';
  $('payChkno').dataset.auto = '1';
  setSettleMethod('transfer');
  wireDatePickers($('dlgPay'));
  $('dlgPay').showModal();
  try { $('payChkamt').focus(); } catch (_) {}
}
$('btnClosePay').onclick = () => $('dlgPay').close();
$('btnConfirmPay').onclick = async () => {
  if (!WRITE_ENABLED) { $('payMsg').innerHTML = '<p class="err">KSS write ปิดอยู่</p>'; return; }
  if (!payTarget) return;
  const chkno = $('payChkno').value.trim();
  const chkamt = Number($('payChkamt').value || 0);
  if (settleMethod === 'cheque' && !chkno) {
    $('payMsg').innerHTML = '<p class="err">กรอกเลขที่เช็ค (CHKNO)</p>'; return;
  }
  if (chkamt <= 0 && payTarget.netamt > 0) {
    $('payMsg').innerHTML = '<p class="err">กรอก CHKAMT</p>'; return;
  }
  try {
    const res = await api('/vouchers', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: payTarget.acctno,
        noteno: payTarget.noteno,
        settle_method: settleMethod,
        chkno,
        chkamt,
        chkdate: $('payChkdate').value,
        bank_gl: $('payBankGl').value.trim()
      })
    });
    $('payMsg').innerHTML = `<p class="ok">voucher ${res.voucno} · ส่งบัญชีอัปโหลดหลักฐานได้</p>`;
    setTimeout(() => { $('dlgPay').close(); loadPending(); showTab('proof'); }, 800);
  } catch (e) { $('payMsg').innerHTML = `<p class="err">${e.message}</p>`; }
};

async function loadProof() {
  $('proofList').innerHTML = 'กำลังโหลด…';
  try {
    const rows = await api('/awaiting-proof');
    if (!rows.length) { $('proofList').innerHTML = '<p class="meta">ไม่มีใบสำคัญจ่ายที่รออัปโหลดหลักฐาน</p>'; return; }
    $('proofList').innerHTML = rows.map(r => `
      <div class="note-row">
        <strong>${r.acctname || r.acctno}</strong> · ${r.noteno}<br/>
        <span class="meta">VOUCNO ${r.voucno} · ${fmtMoney(r.NETAMT || r.BILLAMT)} · ${r.VOUCDATE || ''}</span>
        <div class="row" style="margin-top:.35rem">
          <input type="file" accept="image/*" data-upload-proof="${r.voucno}"/>
        </div>
      </div>`).join('');
    $('proofList').querySelectorAll('[data-upload-proof]').forEach(inp => {
      inp.onchange = async (ev) => {
        const voucno = inp.dataset.uploadProof;
        for (const file of ev.target.files) {
          const fd = new FormData();
          fd.append('voucno', voucno);
          fd.append('file', file);
          const r = await fetch('/pay-notes/api/images/payment', {method:'POST', body: fd});
          const j = await r.json().catch(() => ({}));
          if (!r.ok) { alert(j.detail || j.error); return; }
        }
        loadProof();
      };
    });
  } catch (e) { $('proofList').innerHTML = `<p class="err">${e.message}</p>`; }
}
$('btnRefreshProof').onclick = loadProof;

async function searchVendors() {
  const q = $('vendorQ').value.trim();
  if (!q) return;
  $('vendorResults').innerHTML = '…';
  try {
    const rows = await api('/vendors?q=' + encodeURIComponent(q));
    $('vendorResults').innerHTML = rows.map(v =>
      `<button type="button" style="display:block;width:100%;text-align:left;margin:.25rem 0" data-acct="${v.acctno}" data-name="${v.acctname}">${v.acctno} — ${v.acctname}</button>`
    ).join('') || '<p class="meta">ไม่พบ</p>';
    $('vendorResults').querySelectorAll('button[data-acct]').forEach(b => {
      b.onclick = () => pickVendor(b.dataset.acct, b.dataset.name);
    });
  } catch (e) { $('vendorResults').innerHTML = `<p class="err">${e.message}</p>`; }
}
$('btnVendorSearch').onclick = searchVendors;

async function pickVendor(acctno, acctname) {
  picked = {acctno, acctname};
  $('pickedVendor').textContent = acctno + ' — ' + acctname;
  $('vendorPick').classList.remove('hidden');
  if (!$('dueDate').value) $('dueDate').value = todayISO();
  uploadedPaths = [];
  $('billThumbs').innerHTML = '';
  await loadBanks();
  await loadBills();
}

async function loadBanks() {
  const rows = await api('/banks?acctno=' + encodeURIComponent(picked.acctno));
  $('bankSelect').innerHTML = rows.map(b =>
    `<option value="${b.bank_id}">${b.bank_name} · ${b.bank_account_number}${b.is_default?' ★':''}</option>`
  ).join('') || '<option value="">— เพิ่มบัญชี —</option>';
}

async function loadBills() {
  if (!picked) {
    $('billList').innerHTML = '';
    updateBillSelectStatus();
    return;
  }
  $('billList').innerHTML = '<p class="meta">กำลังโหลดบิล…</p>';
  try {
    const rows = await api('/bills?acctno=' + encodeURIComponent(picked.acctno));
    $('billList').innerHTML = rows.map(b =>
      `<label class="bill"><input type="checkbox" value="${b.BILLNO}" data-amt="${Number(b.AFTERTAX)||0}"/> <span>${b.BILLNO} · ${b.BILLDATE} · ${fmtMoney(b.AFTERTAX)}</span></label>`
    ).join('') || '<p class="meta">ไม่มีบิลว่าง (บิลที่ผูกโน้ตแล้วจะไม่แสดง)</p>';
    $('billList').querySelectorAll('input[type=checkbox]').forEach(cb => {
      cb.addEventListener('change', updateBillSelectStatus);
    });
  } catch (e) {
    $('billList').innerHTML = `<p class="err">${e.message}</p>`;
  }
  updateBillSelectStatus();
}
function selectedBillTotal() {
  const checked = [...$('billList').querySelectorAll('input[type=checkbox]:checked')];
  return {
    n: checked.length,
    total: checked.reduce((s, cb) => s + (Number(cb.dataset.amt) || 0), 0),
  };
}
function resolveDiscAmount(bill) {
  const raw = Math.max(0, Number($('discInput').value || 0));
  if (discMode === 'percent') return Math.round(bill * Math.min(raw, 100) / 100 * 100) / 100;
  return Math.round(raw * 100) / 100;
}
function syncDiscPreview() {
  const { total } = selectedBillTotal();
  const disc = resolveDiscAmount(total);
  const net = Math.max(0, total - disc);
  $('discBillAmt').textContent = fmtMoney(total);
  $('discResolved').textContent = fmtMoney(disc);
  $('discNetAmt').textContent = fmtMoney(net);
  const over = disc - total > 1e-9;
  $('discResolved').style.color = over ? 'var(--down)' : '';
}
function setDiscMode(mode) {
  discMode = mode === 'percent' ? 'percent' : 'amount';
  $('discModeAmount').classList.toggle('on', discMode === 'amount');
  $('discModePercent').classList.toggle('on', discMode === 'percent');
  $('discInputLabel').textContent = discMode === 'percent' ? 'ส่วนลด (%)' : 'ส่วนลด (บาท)';
  $('discInput').step = discMode === 'percent' ? '0.01' : '0.01';
  $('discInput').max = discMode === 'percent' ? '100' : '';
  syncDiscPreview();
}
$('discModeAmount').onclick = () => setDiscMode('amount');
$('discModePercent').onclick = () => setDiscMode('percent');
$('discInput').addEventListener('input', syncDiscPreview);

function updateBillSelectStatus() {
  const el = $('billSelectStatus');
  if (!el) return;
  const { n, total } = selectedBillTotal();
  if (!n) {
    el.className = 'bill-status empty';
    el.textContent = 'ยังไม่ได้เลือกบิล';
  } else {
    el.className = 'bill-status';
    el.textContent = `เลือกแล้ว ${n} บิล · รวม ${fmtMoney(total)}`;
  }
  syncDiscPreview();
}
$('btnRefreshBills').onclick = () => loadBills();

$('btnAddBank').onclick = async () => {
  try {
    await api('/banks', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: picked.acctno,
        bank_name: $('newBankName').value.trim(),
        bank_account_name: $('newAcctName').value.trim(),
        bank_account_number: $('newAcctNo').value.trim(),
      })
    });
    await loadBanks();
  } catch (e) { alert(e.message); }
};

$('billImages').onchange = async (ev) => {
  const noteno = $('noteno').value.trim();
  if (!picked || !noteno) { alert('เลือกเจ้าหนี้และกรอก NOTENO ก่อน'); ev.target.value=''; return; }
  for (const file of ev.target.files) {
    const fd = new FormData();
    fd.append('acctno', picked.acctno);
    fd.append('noteno', noteno);
    fd.append('file', file);
    const r = await fetch('/pay-notes/api/images/bill', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { alert(j.detail || j.error); continue; }
    uploadedPaths.push(j.path);
    if (j.url) $('billThumbs').innerHTML += `<img src="${j.url}" alt=""/>`;
  }
  ev.target.value = '';
};

$('btnCreateNote').onclick = async () => {
  const noteno = $('noteno').value.trim();
  const due = $('dueDate').value;
  const bank_id = $('bankSelect').value;
  const billnos = [...$('billList').querySelectorAll('input:checked')].map(x => x.value);
  $('createMsg').innerHTML = '';
  if (!WRITE_ENABLED) { $('createMsg').innerHTML = '<p class="err">KSS write ปิดอยู่ (PAY_NOTES_WRITE_ENABLED)</p>'; return; }
  if (!noteno || !due || !bank_id) { $('createMsg').innerHTML = '<p class="err">กรอกเลขใบวางบิล, เลือกวันครบกำหนดจากปฏิทิน, และบัญชีธนาคาร</p>'; return; }
  if (!billnos.length) { $('createMsg').innerHTML = '<p class="err">เลือกบิลอย่างน้อย 1</p>'; return; }
  if (!uploadedPaths.length) { $('createMsg').innerHTML = '<p class="err">อัปโหลดรูปใบวางบิลอย่างน้อย 1</p>'; return; }
  const { total } = selectedBillTotal();
  const discAmt = resolveDiscAmount(total);
  if (discAmt - total > 1e-9) {
    $('createMsg').innerHTML = '<p class="err">ส่วนลดมากกว่ายอดบิล</p>';
    return;
  }
  try {
    const res = await api('/notes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: picked.acctno, acctname: picked.acctname, noteno, due_date: due,
        bank_id, billnos,
        discount_mode: discMode,
        discount_input: Number($('discInput').value || 0)
      })
    });
    const rem = res.reminder || {};
    const discShow = Number(rem.discount_amount != null ? rem.discount_amount : discAmt);
    const netShow = Math.max(0, Number(res.billamt || total) - discShow);
    $('createMsg').innerHTML = `<p class="ok">บันทึกใบวางบิลแล้ว · ${res.noteno} · บิล ${fmtMoney(res.billamt)} · ส่วนลด ${fmtMoney(discShow)} · จ่าย ${fmtMoney(netShow)}</p>`;
    uploadedPaths = [];
    $('billThumbs').innerHTML = '';
    $('discInput').value = '0';
    setDiscMode('amount');
    await loadBills();
    showTab('pending');
  } catch (e) {
    $('createMsg').innerHTML = `<p class="err">${e.message}</p>`;
    // KSS may have stamped bills even when reminder failed — refresh so noted bills disappear.
    await loadBills();
  }
};

showTab('create');
setDiscMode('amount');
wireDatePickers(document);
</script>
</body>
</html>
"""

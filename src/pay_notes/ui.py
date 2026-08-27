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
.dlg { border:1px solid var(--line); border-radius:.7rem; background:var(--card); color:var(--text); padding:1rem; max-width:36rem; width:calc(100% - 2rem); }
.dlg::backdrop { background:rgba(0,0,0,.55); }
input[type="date"] {
  min-height: 2.75rem;
  font-size: 1.05rem;
  letter-spacing: .02em;
  cursor: pointer;
}
.date-hint { font-size:.72rem; color:var(--muted); margin:.1rem 0 .35rem; }
.date-ce { font-variant-numeric: tabular-nums; }
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
        <label>วันครบกำหนด</label>
        <p class="date-hint">แตะเพื่อเปิดปฏิทิน · ใช้ปี ค.ศ. เช่น 2026 (ไม่พิมพ์ พ.ศ. 2569)</p>
        <input id="dueDate" class="date-ce" type="date" lang="en" inputmode="none"/>
        <label>บัญชีธนาคาร (required)</label>
        <select id="bankSelect"></select>
        <details style="margin-top:.5rem"><summary>เพิ่มบัญชีใหม่</summary>
          <label>ธนาคาร</label><input id="newBankName"/>
          <label>ชื่อบัญชี</label><input id="newAcctName"/>
          <label>เลขบัญชี</label><input id="newAcctNo"/>
          <button type="button" id="btnAddBank" style="margin-top:.35rem">บันทึกบัญชี</button>
        </details>
        <label style="margin-top:.65rem">เลือกบิล (unpaid · unnoted · unvoucher)</label>
        <div id="billList"></div>
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
      <div class="row"><button type="button" class="primary" id="btnRefreshPending">รีเฟรช</button></div>
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
  <label>ส่วนลด (voucher)</label>
  <input id="payDiscount" type="number" step="0.01" value="0"/>
  <label>CHKNO (เช่น โอน / เลขเช็ค)</label>
  <input id="payChkno" value="โอน"/>
  <label>CHKAMT</label>
  <input id="payChkamt" type="number" step="0.01"/>
  <label>BANKNAME</label>
  <input id="payBankname"/>
  <label>บัญชีธนาคาร GL (BPDET.ACCTNO)</label>
  <input id="payBankGl" value="2101.7"/>
  <label>วันที่โอน / เช็ค</label>
  <p class="date-hint">แตะเพื่อเปิดปฏิทิน · ปี ค.ศ.</p>
  <input id="payChkdate" class="date-ce" type="date" lang="en" inputmode="none"/>
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
  try {
    const rows = await api('/pending');
    if (!rows.length) { $('pendingList').innerHTML = '<p class="meta">ไม่มีรายการรอชำระ (จากบริการนี้)</p>'; return; }
    $('pendingList').innerHTML = rows.map(r => {
      const rem = r.reminder || {};
      const due = (rem.due_date || '').slice(0, 10);
      const bank = rem.vendor_bank || {};
      return `<div class="note-row">
        <strong>${r.acctname || r.acctno}</strong> · ${r.noteno}<br/>
        <span class="meta">${fmtMoney(r.BILLAMT)} · ${r.BILLCNT} บิล · due ${due}</span><br/>
        <span class="meta">${bank.bank_name || ''} ${bank.bank_account_number || ''}</span>
        <div class="row" style="margin-top:.35rem">
          <input type="date" class="date-ce" lang="en" inputmode="none" value="${due}" data-due-input="${r.acctno}|${r.noteno}"/>
          <button type="button" class="primary" data-save-due="${r.acctno}|${r.noteno}">บันทึก due</button>
          <button type="button" class="primary" data-pay="${r.acctno}|${r.noteno}|${r.BILLAMT||0}|${(bank.bank_name||'') + ' ' + (bank.bank_account_name||'') + ' # ' + (bank.bank_account_number||'')}">บันทึกใบสำคัญ</button>
        </div>
      </div>`;
    }).join('');
    wireDatePickers($('pendingList'));
    $('pendingList').querySelectorAll('[data-save-due]').forEach(btn => {
      btn.onclick = async () => {
        const [acct, note] = btn.dataset.saveDue.split('|');
        const inp = $('pendingList').querySelector(`[data-due-input="${acct}|${note}"]`);
        try {
          await api(`/reminder/${encodeURIComponent(acct)}/${encodeURIComponent(note)}`, {
            method: 'PATCH', headers: {'Content-Type':'application/json'},
            body: JSON.stringify({due_date: inp.value})
          });
          loadPending();
        } catch (e) { alert(e.message); }
      };
    });
    $('pendingList').querySelectorAll('[data-pay]').forEach(btn => {
      btn.onclick = () => openPay(...btn.dataset.pay.split('|'));
    });
  } catch (e) {
    $('pendingList').innerHTML = `<p class="err">${e.message}</p>`;
  }
}
$('btnRefreshPending').onclick = loadPending;

function openPay(acct, note, billamt, bankname) {
  payTarget = {acctno: acct, noteno: note, billamt: Number(billamt||0)};
  $('payDetail').textContent = `${acct} · ${note} · ${fmtMoney(billamt)}`;
  $('payDiscount').value = '0';
  $('payChkno').value = 'โอน';
  $('payChkamt').value = String(billamt || 0);
  $('payBankname').value = (bankname || '').trim();
  $('payBankGl').value = '2101.7';
  $('payChkdate').value = todayISO();
  $('payMsg').innerHTML = '';
  $('dlgPay').showModal();
}
$('btnClosePay').onclick = () => $('dlgPay').close();
$('btnConfirmPay').onclick = async () => {
  if (!WRITE_ENABLED) { $('payMsg').innerHTML = '<p class="err">KSS write ปิดอยู่</p>'; return; }
  if (!payTarget) return;
  const disc = Number($('payDiscount').value || 0);
  const amt = Number($('payChkamt').value || 0);
  try {
    const res = await api('/vouchers', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: payTarget.acctno,
        noteno: payTarget.noteno,
        discount: disc,
        bpdet: [{
          chkno: $('payChkno').value.trim(),
          chkamt: amt,
          bankname: $('payBankname').value.trim(),
          acctno: $('payBankGl').value.trim() || '2101.7',
          paytype: 2,
          chkdate: $('payChkdate').value
        }]
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
  const rows = await api('/bills?acctno=' + encodeURIComponent(picked.acctno));
  $('billList').innerHTML = rows.map(b =>
    `<label class="bill"><input type="checkbox" value="${b.BILLNO}"/> <span>${b.BILLNO} · ${b.BILLDATE} · ${fmtMoney(b.AFTERTAX)}</span></label>`
  ).join('') || '<p class="meta">ไม่มีบิลว่าง</p>';
}

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
  try {
    const res = await api('/notes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: picked.acctno, acctname: picked.acctname, noteno, due_date: due,
        bank_id, billnos
      })
    });
    $('createMsg').innerHTML = `<p class="ok">บันทึกใบวางบิลแล้ว · ${res.noteno} · ${fmtMoney(res.billamt)}</p>`;
    showTab('pending');
  } catch (e) { $('createMsg').innerHTML = `<p class="err">${e.message}</p>`; }
};

showTab('create');
wireDatePickers(document);
</script>
</body>
</html>
"""

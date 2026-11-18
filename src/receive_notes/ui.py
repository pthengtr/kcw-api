from __future__ import annotations

import html as html_lib
import json
import re

from src.receive_notes.company_banks import (
    DEFAULT_RECEIVE_BANK_KEY,
    list_company_receive_accounts,
)

APP = "receive-notes"
SESSION_COOKIE = "kcw_receive_notes"


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
    write_enabled: bool = False,
) -> str:
    who = (user_name or "operator").strip()
    site_u = (site or "HQ").upper()
    company = list_company_receive_accounts()
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace("__WRITE__", "true" if write_enabled else "false")
        .replace("__INITIALS__", html_lib.escape(initials(who)))
        .replace("__COMPANY_RECV_JSON__", json.dumps(company, ensure_ascii=False))
        .replace("__DEFAULT_RECV_BANK__", json.dumps(DEFAULT_RECEIVE_BANK_KEY))
    )


_HTML = r"""<!doctype html>
<html lang="th" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light dark"/>
<title>รับชำระลูกหนี้</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root {
  --acc:#0f766e; --acc-soft:#ccfbf1; --on-acc:#fff;
  --ok:#15803d; --warn:#c2410c; --down:#dc2626;
  --bg:#f3f5f9; --card:#fff; --text:#0f172a; --muted:#64748b; --line:#e2e8f0;
  --shadow:0 1px 2px rgba(16,24,40,.06), 0 4px 12px rgba(16,24,40,.04);
}
[data-theme=dark] {
  --bg:#0b1220; --card:#111827; --text:#e5e7eb; --muted:#94a3b8; --line:#1f2937;
  --acc-soft:#134e4a; --shadow:none;
}
* { box-sizing:border-box; }
body { margin:0; font-family:Prompt,system-ui,sans-serif; background:var(--bg); color:var(--text); }
header { display:flex; align-items:center; justify-content:space-between; gap:1rem; padding:1rem 1.15rem; }
h1 { margin:0; font-size:1.25rem; }
.sub { color:var(--muted); font-size:.85rem; }
.tabs { display:flex; gap:.4rem; padding:0 1.15rem 1rem; flex-wrap:wrap; }
.tab { border:1px solid var(--line); background:var(--card); color:var(--text); border-radius:999px; padding:.45rem .9rem; cursor:pointer; font:inherit; }
.tab.active { background:var(--acc); color:var(--on-acc); border-color:var(--acc); }
.panel { display:none; padding:0 1.15rem 2.5rem; }
.panel.active { display:block; }
.card { background:var(--card); border:1px solid var(--line); border-radius:14px; padding:1rem; box-shadow:var(--shadow); margin-bottom:1rem; }
.row { display:flex; gap:.75rem; flex-wrap:wrap; align-items:end; }
label { display:flex; flex-direction:column; gap:.35rem; font-size:.85rem; color:var(--muted); min-width:140px; flex:1; }
input, select, textarea, button { font:inherit; }
input, select, textarea { border:1px solid var(--line); border-radius:10px; padding:.55rem .7rem; background:var(--card); color:var(--text); }
button.btn { border:0; border-radius:10px; padding:.55rem .9rem; background:var(--acc); color:#fff; cursor:pointer; }
button.btn.secondary { background:var(--acc-soft); color:var(--acc); }
button.btn.ghost { background:transparent; color:var(--muted); border:1px solid var(--line); }
button:disabled { opacity:.5; cursor:not-allowed; }
table { width:100%; border-collapse:collapse; font-size:.9rem; }
th, td { padding:.55rem .4rem; border-bottom:1px solid var(--line); text-align:left; vertical-align:top; }
th { color:var(--muted); font-weight:500; }
.num { text-align:right; font-variant-numeric:tabular-nums; }
.pill { display:inline-block; padding:.15rem .5rem; border-radius:999px; font-size:.75rem; background:var(--acc-soft); color:var(--acc); }
.pill.warn { background:#ffedd5; color:#c2410c; }
.pill.ok { background:#dcfce7; color:#15803d; }
.msg { margin:.5rem 0; padding:.65rem .8rem; border-radius:10px; background:var(--acc-soft); }
.msg.err { background:#fee2e2; color:#991b1b; }
.hidden { display:none !important; }
.avatar { width:36px; height:36px; border-radius:50%; background:var(--acc); color:#fff; display:grid; place-items:center; font-weight:600; }
.menu { position:relative; }
.menu-pop { display:none; position:absolute; right:0; top:110%; background:var(--card); border:1px solid var(--line); border-radius:12px; min-width:220px; padding:.4rem; z-index:20; box-shadow:var(--shadow); }
.menu.open .menu-pop { display:block; }
.menu-pop button { width:100%; text-align:left; background:transparent; border:0; padding:.55rem .7rem; border-radius:8px; cursor:pointer; color:var(--text); }
.channels { display:grid; gap:.6rem; }
.channel { display:grid; grid-template-columns:120px 1fr 1fr auto; gap:.5rem; align-items:center; }
@media (max-width:800px) {
  .channel { grid-template-columns:1fr 1fr; }
}
</style>
</head>
<body>
<header>
  <div>
    <h1 id="pageTitle">รับชำระลูกหนี้ · __SITE__</h1>
    <div class="sub">ผู้ใช้: __USER__ · เขียน KSS: <span id="writeFlag">—</span></div>
  </div>
  <div class="row" style="align-items:center">
    <div class="menu" id="moreMenu">
      <button class="btn ghost" type="button" id="moreBtn">เพิ่มเติม ▾</button>
      <div class="menu-pop">
        <button type="button" id="enableManualCash">เปิดรับเงินสดด้วยมือ (ข้อยกเว้น)</button>
      </div>
    </div>
    <div class="avatar">__INITIALS__</div>
  </div>
</header>

<nav class="tabs" id="tabs">
  <button class="tab active" data-tab="receive">รับชำระ</button>
  <button class="tab" data-tab="notes">ใบวางบิล</button>
  <button class="tab" data-tab="review">รอตรวจสอบ</button>
  <button class="tab" data-tab="vouchers">ใบสำคัญรับเงิน</button>
  <button class="tab" data-tab="debtor">ข้อมูลลูกหนี้</button>
</nav>

<section class="panel active" id="tab-receive">
  <div class="card">
    <div class="row">
      <label>ค้นหาลูกหนี้<input id="debtorQ" placeholder="รหัส / ชื่อ" autocomplete="off"/></label>
      <label>ลูกหนี้
        <select id="debtorSelect"><option value="">— เลือก —</option></select>
      </label>
    </div>
    <div id="recvMsg" class="msg hidden"></div>
    <div style="overflow:auto;margin-top:.8rem">
      <table>
        <thead><tr><th></th><th>บิล</th><th>วันที่</th><th>ครบกำหนด</th><th>VAT</th><th class="num">ยอด</th><th class="num">รับครั้งนี้</th></tr></thead>
        <tbody id="billBody"></tbody>
      </table>
    </div>
    <div class="row" style="margin-top:1rem">
      <label>ส่วนลด<input id="discount" type="number" step="0.01" value="0"/></label>
      <label>หมายเหตุ<input id="remark"/></label>
      <label>ยืนยันได้รับเงินแล้ว
        <select id="moneyConfirmed"><option value="1">ใช่ — ตัดหนี้ได้</option><option value="0">ยังไม่ยืนยัน</option></select>
      </label>
    </div>
    <h3 style="margin:1rem 0 .5rem;font-size:1rem">ช่องทางรับเงิน</h3>
    <div class="channels" id="channels"></div>
    <div class="row" style="margin-top:.8rem">
      <button class="btn secondary" type="button" id="addTransfer">+ โอน</button>
      <button class="btn secondary" type="button" id="addCheque">+ เช็ค</button>
      <button class="btn secondary" type="button" id="addCashTiger">+ เงินสด Tiger</button>
      <button class="btn secondary hidden" type="button" id="addCashManual">+ เงินสดมือ</button>
      <div style="flex:1"></div>
      <button class="btn" type="button" id="submitReceive" disabled>รับชำระ</button>
    </div>
    <p class="sub hidden" id="cashManualHint"></p>
  </div>
</section>

<section class="panel" id="tab-notes">
  <div class="card">
    <div class="row">
      <button class="btn" type="button" id="refreshNotes">รีเฟรช</button>
      <button class="btn secondary" type="button" id="openCreateNote">สร้างใบวางบิลจากบิลที่เลือกในแท็บรับชำระ</button>
    </div>
    <div id="notesMsg" class="msg hidden"></div>
    <table style="margin-top:.8rem">
      <thead><tr><th>เลขโน้ต</th><th>ลูกหนี้</th><th>วันที่</th><th>VAT</th><th class="num">ยอด</th><th></th></tr></thead>
      <tbody id="notesBody"></tbody>
    </table>
  </div>
</section>

<section class="panel" id="tab-review">
  <div class="card">
    <button class="btn secondary" type="button" id="refreshReview">รีเฟรช</button>
    <div id="reviewMsg" class="msg hidden"></div>
    <table style="margin-top:.8rem">
      <thead><tr><th>สถานะ</th><th>ลูกหนี้</th><th class="num">ยอด</th><th>Tiger / Sync</th><th></th></tr></thead>
      <tbody id="reviewBody"></tbody>
    </table>
  </div>
</section>

<section class="panel" id="tab-vouchers">
  <div class="card">
    <div class="row">
      <label>วันที่รับ<input id="reportDay" type="date"/></label>
      <button class="btn secondary" type="button" id="refreshVouchers">โหลด</button>
    </div>
    <div id="dailyTotals" class="msg hidden"></div>
    <h3 style="font-size:1rem">ใบสำคัญรับเงิน (overlay)</h3>
    <table>
      <thead><tr><th>เลข</th><th>ลูกหนี้</th><th>สถานะ</th><th class="num">ยอด</th><th></th></tr></thead>
      <tbody id="voucherBody"></tbody>
    </table>
    <h3 style="font-size:1rem;margin-top:1.2rem">กระทบยอด Tiger วันนี้</h3>
    <table>
      <thead><tr><th>Attempt</th><th>สถานะ</th><th class="num">ยอด</th><th>PaymentNo</th></tr></thead>
      <tbody id="tigerBody"></tbody>
    </table>
  </div>
</section>

<section class="panel" id="tab-debtor">
  <div class="card">
    <div class="row">
      <label>ลูกหนี้ (ใช้รายการจากแท็บรับชำระ)
        <select id="debtorSummarySelect"><option value="">— เลือก —</option></select>
      </label>
      <button class="btn secondary" type="button" id="loadDebtorSummary">ดูข้อมูล</button>
    </div>
    <div id="debtorSummary" class="msg hidden"></div>
    <table style="margin-top:.8rem">
      <thead><tr><th>บิลค้าง</th><th>วันที่</th><th class="num">ยอด</th></tr></thead>
      <tbody id="debtorBills"></tbody>
    </table>
  </div>
</section>

<script>
const USER = __USER_JSON__;
const SITE = "__SITE__";
const WRITE = __WRITE__;
const COMPANY = __COMPANY_RECV_JSON__;
const DEFAULT_BANK = __DEFAULT_RECV_BANK__;

let debtors = [];
let bills = [];
let selectedAcct = null;
let channels = [];
let manualCashEnabled = false;
let pollTimers = {};

const $ = (id) => document.getElementById(id);
function fmt(n){ return Number(n||0).toLocaleString('th-TH',{minimumFractionDigits:2, maximumFractionDigits:2}); }
function show(el, text, err){ el.classList.remove('hidden'); el.className = 'msg' + (err?' err':''); el.textContent = text; }
function hide(el){ el.classList.add('hidden'); }

async function api(path, opts){
  const r = await fetch('/receive-notes/api' + path, opts || {});
  const j = await r.json().catch(() => ({ok:false,error:'bad json'}));
  if (!r.ok || j.ok === false) throw Object.assign(new Error(j.error || r.statusText), {code:j.code, payload:j});
  return j;
}

function setTab(name){
  document.querySelectorAll('.tab').forEach(t => t.classList.toggle('active', t.dataset.tab===name));
  document.querySelectorAll('.panel').forEach(p => p.classList.toggle('active', p.id === 'tab-'+name));
  if (name==='notes') refreshNotes();
  if (name==='review') refreshReview();
  if (name==='vouchers') refreshVouchers();
}

document.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => setTab(t.dataset.tab)));
$('writeFlag').textContent = WRITE ? 'เปิด' : 'ปิด (read-only)';
$('pageTitle').textContent = `รับชำระลูกหนี้ · ${SITE}`;
$('reportDay').value = new Date().toISOString().slice(0,10);

$('moreBtn').onclick = () => $('moreMenu').classList.toggle('open');
document.addEventListener('click', (e) => {
  if (!$('moreMenu').contains(e.target)) $('moreMenu').classList.remove('open');
});
$('enableManualCash').onclick = () => {
  manualCashEnabled = true;
  $('addCashManual').classList.remove('hidden');
  $('cashManualHint').classList.remove('hidden');
  $('cashManualHint').textContent = 'เงินสดมือเป็นข้อยกเว้น — ต้องระบุเหตุผลเมื่อรับชำระ';
  $('moreMenu').classList.remove('open');
};

let searchTimer = null;
$('debtorQ').addEventListener('input', () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(searchDebtors, 250);
});

async function searchDebtors(){
  const q = $('debtorQ').value.trim();
  if (!q) return;
  const j = await api('/debtors?q=' + encodeURIComponent(q));
  debtors = j.debtors || [];
  fillDebtorSelects();
}
function fillDebtorSelects(){
  for (const sel of [$('debtorSelect'), $('debtorSummarySelect')]) {
    const cur = sel.value;
    sel.innerHTML = '<option value="">— เลือก —</option>' + debtors.map(d =>
      `<option value="${d.acctno}">${d.acctno} · ${d.acctname||''}</option>`
    ).join('');
    if (cur) sel.value = cur;
  }
}
$('debtorSelect').onchange = async () => {
  const acct = $('debtorSelect').value;
  selectedAcct = debtors.find(d => d.acctno === acct) || {acctno:acct, acctname:''};
  if (!acct) { bills=[]; renderBills(); return; }
  const j = await api('/bills?acctno=' + encodeURIComponent(acct));
  bills = j.bills || [];
  renderBills();
  $('submitReceive').disabled = !WRITE;
};

function renderBills(){
  $('billBody').innerHTML = bills.map(b => {
    const mode = b.JOURMODE === '2' ? 'Non-VAT' : 'VAT';
    return `<tr>
      <td><input type="checkbox" class="bill-ck" value="${b.BILLNO}" data-amt="${b.AFTERTAX}" checked/></td>
      <td>${b.BILLNO}${b.NOTENO ? `<div class="sub">โน้ต ${b.NOTENO}</div>`:''}</td>
      <td>${(b.BILLDATE||'').slice(0,10)}</td>
      <td>${(b.DUEDATE||'—').toString().slice(0,10)}</td>
      <td>${mode}</td>
      <td class="num">${fmt(b.AFTERTAX)}</td>
      <td class="num"><input type="number" step="0.01" class="alloc" data-bill="${b.BILLNO}" value="${b.AFTERTAX}" style="width:110px;text-align:right"/></td>
    </tr>`;
  }).join('') || '<tr><td colspan="7">ไม่มีบิลค้างชำระ</td></tr>';
}

function selectedAllocations(){
  const out = [];
  document.querySelectorAll('.bill-ck:checked').forEach(ck => {
    const billno = ck.value;
    const inp = document.querySelector(`.alloc[data-bill="${billno}"]`);
    out.push({billno, allocate_amt: Number(inp?.value || ck.dataset.amt || 0)});
  });
  return out;
}

function addChannel(method){
  channels.push({
    settle_method: method,
    amount: 0,
    chkno: method==='transfer' ? 'โอน' : '',
    chkdate: new Date().toISOString().slice(0,10),
    receive_bank_key: DEFAULT_BANK,
    bankname: '',
    _manual: method==='cash_manual'
  });
  // normalize cash_manual -> cash with flag
  if (method === 'cash_manual') {
    channels[channels.length-1].settle_method = 'cash';
    channels[channels.length-1]._manual = true;
  }
  if (method === 'cash' || method === 'cash_tiger') {
    channels[channels.length-1].settle_method = 'cash';
    channels[channels.length-1]._manual = false;
  }
  renderChannels();
}
function renderChannels(){
  const bankOpts = COMPANY.map(b => `<option value="${b.key}">${b.label}</option>`).join('');
  $('channels').innerHTML = channels.map((c,i) => {
    const isCash = c.settle_method === 'cash';
    const isTransfer = c.settle_method === 'transfer';
    const isCheque = c.settle_method === 'cheque';
    return `<div class="channel" data-i="${i}">
      <strong>${isCash ? (c._manual?'เงินสดมือ':'เงินสด Tiger') : isTransfer?'โอน':'เช็ค'}</strong>
      <input type="number" step="0.01" data-f="amount" value="${c.amount||''}" placeholder="จำนวน"/>
      ${isTransfer ? `<select data-f="receive_bank_key">${bankOpts}</select>` : ''}
      ${isCheque ? `<input data-f="chkno" placeholder="เลขเช็ค" value="${c.chkno||''}"/>` : ''}
      ${isCash && c._manual ? `<input data-f="reason" placeholder="เหตุผลข้อยกเว้น" value="${c.reason||''}"/>` : '<span></span>'}
      <button class="btn ghost" type="button" data-del="${i}">ลบ</button>
    </div>`;
  }).join('') || '<div class="sub">เพิ่มช่องทางรับเงินอย่างน้อย 1 รายการ</div>';
  $('channels').querySelectorAll('select[data-f=receive_bank_key]').forEach((sel, idx) => {
    const ch = channels.filter(c=>c.settle_method==='transfer')[idx];
    if (ch) sel.value = ch.receive_bank_key || DEFAULT_BANK;
  });
  $('channels').querySelectorAll('[data-f]').forEach(el => {
    el.addEventListener('change', syncChannelsFromDom);
    el.addEventListener('input', syncChannelsFromDom);
  });
  $('channels').querySelectorAll('[data-del]').forEach(btn => {
    btn.onclick = () => { channels.splice(Number(btn.dataset.del),1); renderChannels(); };
  });
}
function syncChannelsFromDom(){
  document.querySelectorAll('.channel').forEach((row) => {
    const i = Number(row.dataset.i);
    const c = channels[i];
    if (!c) return;
    row.querySelectorAll('[data-f]').forEach(el => {
      const f = el.dataset.f;
      if (f === 'amount') c.amount = Number(el.value||0);
      else if (f === 'reason') c.reason = el.value;
      else c[f] = el.value;
    });
  });
}
$('addTransfer').onclick = () => addChannel('transfer');
$('addCheque').onclick = () => addChannel('cheque');
$('addCashTiger').onclick = () => addChannel('cash');
$('addCashManual').onclick = () => addChannel('cash_manual');

function startTigerPoll(receiptId){
  if (pollTimers[receiptId]) return;
  pollTimers[receiptId] = setInterval(async () => {
    try {
      const j = await api('/receipts/' + receiptId + '/tiger');
      const st = j.attempt?.status;
      if (st === 'success') {
        clearInterval(pollTimers[receiptId]); delete pollTimers[receiptId];
        await api('/receipts/' + receiptId + '/complete-tiger', {method:'POST'});
        show($('recvMsg'), 'Tiger สำเร็จ — ตัดหนี้และออกใบสำคัญแล้ว');
        refreshReview();
      } else if (['failed','cancelled','canceled'].includes(st)) {
        clearInterval(pollTimers[receiptId]); delete pollTimers[receiptId];
        show($('recvMsg'), 'Tiger ไม่สำเร็จ — ไปแท็บรอตรวจสอบ', true);
        refreshReview();
      }
    } catch (_) {}
  }, 2000);
}

async function refreshNotes(){
  hide($('notesMsg'));
  try {
    const j = await api('/pending-notes');
    $('notesBody').innerHTML = (j.notes||[]).map(n => `<tr>
      <td>${n.noteno}</td>
      <td>${n.acctno}<div class="sub">${n.acctname||''}</div></td>
      <td>${(n.NOTEDATE||n.notedate||'').toString().slice(0,10)}</td>
      <td>${n.JOURMODE||n.jourmode}</td>
      <td class="num">${fmt(n.BILLAMT||n.billamt)}</td>
      <td><button class="btn secondary" data-recv-note="${n.acctno}|${n.noteno}|${n.acctname||''}">รับชำระ</button></td>
    </tr>`).join('') || '<tr><td colspan="6">ไม่มีใบวางบิลค้าง</td></tr>';
    $('notesBody').querySelectorAll('[data-recv-note]').forEach(btn => {
      btn.onclick = async () => {
        const [acctno, noteno, acctname] = btn.dataset.recvNote.split('|');
        setTab('receive');
        if (!debtors.find(d=>d.acctno===acctno)) {
          debtors.unshift({acctno, acctname});
          fillDebtorSelects();
        }
        $('debtorSelect').value = acctno;
        selectedAcct = {acctno, acctname};
        const detail = await api(`/notes/detail?acctno=${encodeURIComponent(acctno)}&noteno=${encodeURIComponent(noteno)}`);
        bills = (detail.bills||[]).filter(b => b.PAID !== 'Y' && !(b.VOUCNO2||'').trim());
        renderBills();
        $('remark').value = `จากใบวางบิล ${noteno}`;
        window.__pendingNote = noteno;
        show($('recvMsg'), `โหลดบิลจากใบวางบิล ${noteno} แล้ว — กดรับชำระได้`);
      };
    });
  } catch (e) { show($('notesMsg'), e.message, true); }
}
$('refreshNotes').onclick = refreshNotes;
$('openCreateNote').onclick = async () => {
  if (!WRITE) return show($('notesMsg'), 'เขียน KSS ปิดอยู่', true);
  if (!selectedAcct?.acctno) return show($('notesMsg'), 'เลือกลูกหนี้และบิลในแท็บรับชำระก่อน', true);
  const billnos = selectedAllocations().map(a=>a.billno);
  if (!billnos.length) return show($('notesMsg'), 'เลือกบิลก่อน', true);
  try {
    const j = await api('/notes', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({
      acctno: selectedAcct.acctno, acctname: selectedAcct.acctname||'', billnos
    })});
    show($('notesMsg'), `สร้างใบวางบิล ${j.noteno} แล้ว`);
    refreshNotes();
  } catch (e) { show($('notesMsg'), e.message, true); }
};

async function refreshReview(){
  hide($('reviewMsg'));
  try {
    const j = await api('/review');
    $('reviewBody').innerHTML = (j.items||[]).map(r => `<tr>
      <td><span class="pill warn">${r.workflow_status}</span></td>
      <td>${r.acctno}<div class="sub">${r.acctname||''}</div></td>
      <td class="num">${fmt(r.netamt)}</td>
      <td class="sub">${r.tiger_attempt_id||'—'} / ${r.kss_sync_status}${r.kss_sync_error? ' · '+r.kss_sync_error:''}</td>
      <td>
        ${r.workflow_status==='awaiting_tiger' ? `<button class="btn secondary" data-act="tiger" data-id="${r.id}">เช็ค Tiger</button>`:''}
        ${r.kss_sync_status==='failed' || !r.voucno ? `<button class="btn secondary" data-act="resync" data-id="${r.id}">ส่ง KSS ใหม่</button>`:''}
        ${r.proof_status==='awaiting' ? `<label class="btn secondary">แนบหลักฐาน<input type="file" data-proof="${r.id}" hidden/></label>`:''}
        ${r.workflow_status==='review' && !r.money_confirmed ? `<button class="btn" data-act="confirm" data-id="${r.id}">ยืนยันรับเงิน</button>`:''}
      </td>
    </tr>`).join('') || '<tr><td colspan="5">ไม่มีรายการรอตรวจสอบ</td></tr>';
    wireReviewActions();
  } catch (e) { show($('reviewMsg'), e.message, true); }
}
function wireReviewActions(){
  $('reviewBody').querySelectorAll('[data-act]').forEach(btn => {
    btn.onclick = async () => {
      const id = btn.dataset.id;
      try {
        if (btn.dataset.act === 'tiger') {
          await api('/receipts/' + id + '/complete-tiger', {method:'POST'});
          show($('reviewMsg'), 'Tiger complete แล้ว');
        } else if (btn.dataset.act === 'resync') {
          await api('/receipts/' + id + '/resync', {method:'POST'});
          show($('reviewMsg'), 'Resync แล้ว');
        } else if (btn.dataset.act === 'confirm') {
          await api('/receipts/' + id + '/confirm-money', {method:'POST'});
          show($('reviewMsg'), 'ยืนยันและตัดหนี้แล้ว');
        }
        refreshReview();
      } catch (e) { show($('reviewMsg'), e.message, true); }
    };
  });
  $('reviewBody').querySelectorAll('input[data-proof]').forEach(inp => {
    inp.onchange = async () => {
      const fd = new FormData();
      fd.append('receipt_id', inp.dataset.proof);
      fd.append('file', inp.files[0]);
      const r = await fetch('/receive-notes/api/images/payment', {method:'POST', body: fd});
      const j = await r.json();
      if (!j.ok) show($('reviewMsg'), j.error||'upload failed', true);
      else { show($('reviewMsg'), 'แนบหลักฐานแล้ว'); refreshReview(); }
    };
  });
}
$('refreshReview').onclick = refreshReview;

async function refreshVouchers(){
  const day = $('reportDay').value;
  try {
    const [rep, rec] = await Promise.all([
      api('/reports/daily?received_at=' + encodeURIComponent(day)),
      api('/receipts?received_at=' + encodeURIComponent(day)),
    ]);
    const t = rep.totals || {};
    show($('dailyTotals'), `รายวัน ${day}: รวม ${fmt(t.netamt)} · Tiger ${fmt(t.cash_tiger)} · เงินสดมือ ${fmt(t.cash_manual)} · โอน ${fmt(t.transfer)} · เช็ค ${fmt(t.cheque)} (${t.count} รายการ)`);
    $('voucherBody').innerHTML = (rec.receipts||[]).map(r => `<tr>
      <td>${r.voucno || '—'}</td>
      <td>${r.acctno}<div class="sub">${r.acctname||''}</div></td>
      <td><span class="pill ${r.workflow_status==='done'?'ok':'warn'}">${r.workflow_status}</span>
        <div class="sub">sync ${r.kss_sync_status}</div></td>
      <td class="num">${fmt(r.netamt)}</td>
      <td>
        ${r.kss_sync_status!=='synced' ? `<button class="btn secondary" data-resync="${r.id}">ส่งใหม่</button>`:''}
        <label class="btn ghost">หลักฐาน<input type="file" data-proof="${r.id}" data-vouc="${r.voucno||''}" hidden/></label>
      </td>
    </tr>`).join('') || '<tr><td colspan="5">ไม่มีรายการ</td></tr>';
    $('tigerBody').innerHTML = (rep.tiger_attempts||[]).map(a => `<tr>
      <td>${a.id}</td><td>${a.status}</td><td class="num">${fmt(a.amount)}</td><td>${a.tiger_payment_no||'—'}</td>
    </tr>`).join('') || '<tr><td colspan="4">ไม่มี attempt</td></tr>';
    $('voucherBody').querySelectorAll('[data-resync]').forEach(btn => {
      btn.onclick = async () => {
        try { await api('/receipts/' + btn.dataset.resync + '/resync', {method:'POST'}); refreshVouchers(); }
        catch(e){ alert(e.message); }
      };
    });
    $('voucherBody').querySelectorAll('input[data-proof]').forEach(inp => {
      inp.onchange = async () => {
        const fd = new FormData();
        fd.append('receipt_id', inp.dataset.proof);
        if (inp.dataset.vouc) fd.append('voucno', inp.dataset.vouc);
        fd.append('file', inp.files[0]);
        await fetch('/receive-notes/api/images/payment', {method:'POST', body: fd});
        refreshVouchers();
      };
    });
  } catch (e) { show($('dailyTotals'), e.message, true); }
}
$('refreshVouchers').onclick = refreshVouchers;

$('loadDebtorSummary').onclick = async () => {
  const acct = $('debtorSummarySelect').value || $('debtorSelect').value;
  if (!acct) return;
  const j = await api('/debtor-summary?acctno=' + encodeURIComponent(acct));
  show($('debtorSummary'), `ค้าง ${j.open_bill_count} บิล · ${fmt(j.open_bill_amount)} บาท · ใบวางบิลค้าง ${ (j.pending_notes||[]).length } · รับล่าสุด ${ (j.recent_receipts||[]).length }`);
  $('debtorBills').innerHTML = (j.open_bills||[]).map(b => `<tr>
    <td>${b.BILLNO}</td><td>${(b.BILLDATE||'').slice(0,10)}</td><td class="num">${fmt(b.AFTERTAX)}</td>
  </tr>`).join('') || '<tr><td colspan="3">ไม่มีบิลค้าง</td></tr>';
};

$('submitReceive').onclick = async () => {
  hide($('recvMsg'));
  if (!WRITE) return show($('recvMsg'), 'เขียน KSS ปิดอยู่ (RECEIVE_NOTES_WRITE_ENABLED)', true);
  if (!selectedAcct?.acctno) return show($('recvMsg'), 'เลือกลูกหนี้ก่อน', true);
  syncChannelsFromDom();
  const allocations = selectedAllocations();
  if (!allocations.length) return show($('recvMsg'), 'เลือกบิลอย่างน้อย 1 ใบ', true);
  if (!channels.length) return show($('recvMsg'), 'เพิ่มช่องทางรับเงิน', true);
  const billTotal = allocations.reduce((s,a)=>s+Number(a.allocate_amt||0),0);
  const disc = Number($('discount').value||0);
  const net = Math.round((billTotal - disc)*100)/100;
  if (channels.length===1 && !channels[0].amount) channels[0].amount = net;
  const chSum = channels.reduce((s,c)=>s+Number(c.amount||0),0);
  if (Math.abs(chSum - net) > 0.05) return show($('recvMsg'), `ยอดช่องทาง ${fmt(chSum)} ไม่ตรงสุทธิ ${fmt(net)}`, true);
  const hasManual = channels.some(c => c.settle_method==='cash' && c._manual);
  const hasTiger = channels.some(c => c.settle_method==='cash' && !c._manual);
  if (hasManual && hasTiger) return show($('recvMsg'), 'อย่าผสมเงินสด Tiger กับเงินสดมือ', true);
  if (hasManual && !(channels.find(c=>c._manual)?.reason||'').trim()) return show($('recvMsg'), 'ระบุเหตุผลเงินสดมือ', true);
  const body = {
    acctno: selectedAcct.acctno,
    acctname: selectedAcct.acctname || '',
    allocations,
    channels: channels.map(c => ({
      settle_method: c.settle_method,
      amount: Number(c.amount||0),
      chkno: c.chkno || null,
      chkdate: c.chkdate || new Date().toISOString().slice(0,10),
      receive_bank_key: c.receive_bank_key || null,
      bankname: c.bankname || null,
    })),
    discount: disc,
    noteno: window.__pendingNote || null,
    remark: $('remark').value || null,
    money_confirmed: $('moneyConfirmed').value === '1',
    cash_mode: hasManual ? 'manual' : (hasTiger ? 'tiger' : null),
    cash_manual_reason: hasManual ? (channels.find(c=>c._manual)?.reason || '') : null,
  };
  try {
    const j = await api('/receive', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
    window.__pendingNote = null;
    const parts = (j.receipts||[]).map(r => {
      const rc = r.receipt || {};
      if (r.tiger_attempt) startTigerPoll(rc.id);
      if (r.tiger_error) return `${rc.workflow_status}: ${r.tiger_error.message}`;
      return rc.voucno ? `ใบสำคัญ ${rc.voucno}` : rc.workflow_status;
    });
    show($('recvMsg'), 'บันทึกแล้ว: ' + parts.join(' · '));
    $('debtorSelect').dispatchEvent(new Event('change'));
  } catch (e) {
    show($('recvMsg'), e.message, true);
  }
};
</script>
</body>
</html>
"""

from __future__ import annotations

import html as html_lib
import json
import re

APP = "pay-notes"
SESSION_COOKIE = "kcw_pay_notes"


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


def page(*, user_name: str = "", site: str = "HQ", write_enabled: bool = False) -> str:
    who = (user_name or "operator").strip()
    site_u = (site or "HQ").upper()
    write_flag = "true" if write_enabled else "false"
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace("__WRITE__", write_flag)
        .replace("__INITIALS__", html_lib.escape(initials(who)))
    )


_HTML = r"""<!doctype html>
<html lang="th" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light dark"/>
<meta name="theme-color" content="#f3f5f9" id="themeColor"/>
<title>ชำระเจ้าหนี้</title>
<script>
(function () {
  try {
    var t = localStorage.getItem("kcw.pay_notes.theme");
    if (t !== "light" && t !== "dark") t = "light";
    document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
</script>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root {
  --acc:#2f6bff; --acc-soft:#e8f0ff; --on-acc:#fff;
  --ok:#15803d; --ok-bg:#dcfce7;
  --warn:#c2410c; --warn-bg:#ffedd5;
  --down:#dc2626; --down-bg:#fee2e2;
  --soon:#15803d; --soon-bg:#dcfce7;
  --proof:#a16207; --proof-bg:#fef3c7;
  --shadow:0 1px 2px rgba(16,24,40,.06), 0 4px 12px rgba(16,24,40,.04);
}
html[data-theme="dark"] {
  color-scheme: dark;
  --bg:#0c1014; --card:#161d26; --line:#2a3542; --text:#e8eef4; --muted:#8b9aab;
  --chip:#243040; --inset:#0a0e12; --acc-soft:#1a2744;
  --ok-bg:#163024; --warn-bg:#3a2718; --down-bg:#3a1c1c; --soon-bg:#163024; --proof-bg:#3a3018;
  --shadow:none; --head:#0c1014;
}
html[data-theme="light"] {
  color-scheme: light;
  --bg:#f3f5f9; --card:#ffffff; --line:#e6eaf0; --text:#1b2430; --muted:#6b7c8f;
  --chip:#f3f5f8; --inset:#f7f9fc; --head:#ffffff;
}
* { box-sizing:border-box; }
body { margin:0; font-family:Prompt,sans-serif; background:var(--bg); color:var(--text); }
button, input, select, textarea { font:inherit; }
button { cursor:pointer; }
a { color:var(--acc); }
.hidden { display:none !important; }
header {
  position:sticky; top:0; z-index:5; background:var(--head);
  border-bottom:1px solid var(--line); padding:.85rem 1.25rem 0;
}
.topbar { display:flex; align-items:center; justify-content:space-between; gap:.75rem; }
h1 { margin:0; font-size:1.2rem; font-weight:700; letter-spacing:-.01em; }
.crumb { font-size:.78rem; color:var(--muted); margin-top:.15rem; }
.avatar {
  width:2.15rem; height:2.15rem; border-radius:50%; border:0;
  background:#dbeafe; color:#1d4ed8; font-weight:700; font-size:.78rem;
  flex:0 0 auto;
}
html[data-theme="dark"] .avatar { background:#1e3a5f; color:#93c5fd; }
.tabs { display:flex; gap:1.35rem; margin-top:.7rem; }
.tabs button {
  appearance:none; background:none; border:0; border-bottom:2px solid transparent;
  color:var(--muted); padding:.45rem 0 .7rem; font-weight:500; font-size:.95rem;
}
.tabs button.on { color:var(--acc); font-weight:600; border-bottom-color:var(--acc); }
main { max-width:1120px; margin:0 auto; padding:1.1rem 1.15rem 2.5rem; }
.panel { display:none; }
.panel.on { display:block; }
.card {
  background:var(--card); border:1px solid var(--line); border-radius:.85rem;
  box-shadow:var(--shadow); padding:1rem;
}
.card + .card, .kpis + .card, .card + .kpis { margin-top:.85rem; }
.toolbar { display:flex; gap:.55rem; flex-wrap:wrap; align-items:center; }
.grow { flex:1 1 16rem; min-width:12rem; }
.field {
  position:relative; display:flex; align-items:center; gap:.35rem;
  background:var(--card); border:1px solid var(--line); border-radius:.65rem;
  padding:.15rem .7rem; min-height:2.55rem; color:var(--muted);
}
.field input, .field select {
  border:0; background:transparent; color:var(--text); width:100%;
  padding:.4rem .15rem; outline:none; min-width:0;
}
.field .ico { flex:0 0 auto; display:flex; opacity:.7; }
.btn {
  display:inline-flex; align-items:center; justify-content:center; gap:.4rem;
  border:1px solid var(--line); background:var(--card); color:var(--text);
  border-radius:.65rem; padding:.5rem .9rem; min-height:2.55rem; font-weight:500;
  width:auto; white-space:nowrap;
}
.btn.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:600; }
.btn.ghost { background:var(--chip); }
.btn.soft { background:var(--acc-soft); border-color:transparent; color:var(--acc); }
.btn.sm { min-height:2.05rem; padding:.3rem .7rem; font-size:.82rem; border-radius:.5rem; }
.btn.block { width:100%; }
.kpis { display:grid; gap:.65rem; grid-template-columns:repeat(4, 1fr); margin:.85rem 0; }
.kpi {
  display:flex; gap:.7rem; align-items:flex-start; text-align:left;
  border:1px solid var(--line); border-radius:.85rem; padding:.85rem .9rem;
  background:var(--card); box-shadow:var(--shadow); width:100%;
}
.kpi.on { outline:2px solid var(--acc); }
.kpi .mark {
  width:2.1rem; height:2.1rem; border-radius:.65rem; display:flex; align-items:center; justify-content:center; flex:0 0 auto;
}
.kpi b { display:block; font-size:.9rem; font-weight:600; }
.kpi span { display:block; font-size:.75rem; color:var(--muted); margin-top:.15rem; }
.kpi-all { background:var(--acc-soft); border-color:transparent; }
.kpi-all .mark { background:#dbeafe; color:var(--acc); }
.kpi-overdue { background:var(--down-bg); border-color:transparent; }
.kpi-overdue .mark { background:#fecaca; color:var(--down); }
.kpi-today { background:var(--warn-bg); border-color:transparent; }
.kpi-today .mark { background:#fed7aa; color:var(--warn); }
.kpi-soon { background:var(--soon-bg); border-color:transparent; }
.kpi-soon .mark { background:#bbf7d0; color:var(--soon); }
.table-wrap { overflow:auto; }
table { width:100%; border-collapse:collapse; min-width:40rem; }
th, td { padding:.85rem .75rem; text-align:left; border-bottom:1px solid var(--line); font-size:.9rem; }
th { font-size:.75rem; color:var(--muted); font-weight:600; letter-spacing:.02em; }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
.linkish {
  background:none; border:0; color:var(--acc); font-weight:600; padding:0; width:auto;
}
.badge {
  display:inline-flex; align-items:center; justify-content:center;
  border-radius:999px; padding:.18rem .65rem; font-size:.75rem; font-weight:600; white-space:nowrap;
}
.b-pending { background:var(--warn-bg); color:var(--warn); }
.b-overdue { background:var(--down-bg); color:var(--down); }
.b-paid { background:var(--ok-bg); color:var(--ok); }
.b-today { background:var(--warn-bg); color:var(--warn); }
.b-soon { background:var(--soon-bg); color:var(--soon); }
.b-wait { background:var(--proof-bg); color:var(--proof); }
.b-done { background:var(--ok-bg); color:var(--ok); }
.table-foot {
  display:flex; justify-content:space-between; align-items:center; gap:.75rem; flex-wrap:wrap;
  padding:.75rem .15rem 0; font-size:.8rem; color:var(--muted);
}
.pager { display:flex; gap:.3rem; align-items:center; }
.pager button {
  min-width:2rem; height:2rem; padding:0 .45rem; border-radius:.45rem;
  border:1px solid var(--line); background:var(--card); color:var(--text);
}
.pager button.on { border-color:var(--acc); color:var(--acc); font-weight:700; }
.hint {
  display:flex; align-items:center; gap:.4rem; font-size:.8rem; color:var(--muted);
}
.empty { text-align:center; color:var(--muted); padding:1.6rem .8rem; }
.err { color:var(--down); font-size:.85rem; margin:.35rem 0; }
.ok { color:var(--ok); font-size:.85rem; }
.row-actions { display:flex; gap:.4rem; justify-content:flex-end; flex-wrap:wrap; }
.step { display:flex; gap:.85rem; margin:0 0 1.15rem; }
.step-num {
  width:1.7rem; height:1.7rem; border-radius:50%; background:var(--acc); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.85rem; flex:0 0 auto; margin-top:.1rem;
}
.step-body { flex:1; min-width:0; }
.step h3 { margin:0 0 .55rem; font-size:.98rem; }
.step h3 .sub { font-weight:400; color:var(--muted); font-size:.82rem; }
.grid-3 { display:grid; grid-template-columns:repeat(3, 1fr); gap:.65rem; }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:.65rem; }
label.lbl { display:block; font-size:.78rem; color:var(--muted); margin:0 0 .25rem; }
.inp, .area {
  width:100%; border:1px solid var(--line); background:var(--inset); color:var(--text);
  border-radius:.55rem; padding:.5rem .65rem; outline:none;
}
.area { min-height:4rem; resize:vertical; }
.combo { position:relative; }
.combo-list {
  position:absolute; left:0; right:0; top:calc(100% + 4px); z-index:6;
  background:var(--card); border:1px solid var(--line); border-radius:.55rem;
  box-shadow:var(--shadow); max-height:16rem; overflow:auto;
}
.combo-list button {
  display:block; width:100%; text-align:left; border:0; background:none;
  padding:.55rem .75rem; color:var(--text);
}
.combo-list button:hover { background:var(--acc-soft); }
.picked {
  margin-top:.45rem; display:inline-flex; align-items:center; gap:.4rem;
  background:var(--acc-soft); color:var(--acc); border-radius:999px; padding:.2rem .7rem; font-size:.82rem; font-weight:600;
}
.bill-head, .bill-foot {
  display:flex; justify-content:space-between; align-items:center; gap:.5rem; flex-wrap:wrap;
  font-size:.82rem; color:var(--muted); margin-bottom:.4rem;
}
.bill-foot { margin:0; padding:.55rem .75rem; background:var(--chip); border-radius:0 0 .55rem .55rem; }
.seg { display:inline-flex; background:var(--chip); border-radius:.5rem; padding:.15rem; gap:.15rem; }
.seg button {
  border:0; background:transparent; color:var(--muted); border-radius:.4rem;
  padding:.35rem .7rem; width:auto; font-weight:500;
}
.seg button.on { background:var(--acc); color:#fff; font-weight:600; }
.disc-layout { display:grid; grid-template-columns:1.1fr .9fr; gap:1rem; align-items:start; }
.disc-sum {
  background:var(--inset); border-radius:.65rem; padding:.7rem .85rem;
}
.pay-line { display:flex; justify-content:space-between; gap:.5rem; margin:.2rem 0; font-size:.9rem; }
.pay-net { margin-top:.35rem; padding-top:.4rem; border-top:1px solid var(--line); font-weight:700; }
.drop {
  border:1.5px dashed var(--line); border-radius:.75rem; padding:1.4rem 1rem; text-align:center;
  background:var(--inset); color:var(--muted); cursor:pointer;
}
.drop.drag { border-color:var(--acc); background:var(--acc-soft); color:var(--acc); }
.thumbs { display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.5rem; }
.thumbs img { width:72px; height:72px; object-fit:cover; border-radius:.4rem; border:1px solid var(--line); }
.file-chip {
  display:inline-flex; align-items:center; gap:.3rem; padding:.35rem .55rem;
  border:1px solid var(--line); border-radius:.45rem; font-size:.78rem; background:var(--card);
}
.create-head { display:flex; justify-content:space-between; align-items:flex-start; gap:.75rem; margin-bottom:1rem; }
.create-head h2 { margin:.1rem 0 0; font-size:1.15rem; }
.dlg {
  border:0; border-radius:.9rem; background:var(--card); color:var(--text);
  padding:0; max-width:40rem; width:calc(100% - 2rem);
  max-height:min(92dvh, 46rem); overflow:auto; box-shadow:0 16px 40px rgba(16,24,40,.18);
}
.dlg::backdrop { background:rgba(15,23,42,.45); }
.dlg-head {
  display:flex; justify-content:space-between; align-items:center;
  padding:1rem 1.1rem .4rem;
}
.dlg-head h2 { margin:0; font-size:1.05rem; }
.dlg-x { border:0; background:none; color:var(--muted); font-size:1.2rem; width:auto; padding:.2rem .4rem; }
.dlg-body { padding:.4rem 1.1rem 1.1rem; }
.dlg-foot {
  display:flex; justify-content:flex-end; gap:.45rem; padding:0 1.1rem 1.1rem;
}
.sum-box {
  display:grid; grid-template-columns:1fr 1fr; gap:.35rem 1.2rem;
  background:var(--acc-soft); border-radius:.7rem; padding:.85rem .95rem; margin:.4rem 0 1rem;
  font-size:.88rem;
}
.sum-box .k { color:var(--muted); font-size:.75rem; }
.sum-box .v { margin-top:.1rem; }
.sum-box .net .k, .sum-box .net .v { font-weight:700; }
.sum-box .net .v { color:var(--acc); }
.methods { display:grid; grid-template-columns:repeat(3, 1fr); gap:.45rem; margin:.25rem 0 .75rem; }
.method {
  border:1px solid var(--line); background:var(--card); border-radius:.65rem;
  padding:.65rem .4rem; color:var(--muted); display:flex; flex-direction:column; align-items:center; gap:.25rem;
}
.method.on { border-color:var(--acc); color:var(--acc); background:var(--acc-soft); font-weight:600; }
.date-hint { font-size:.72rem; color:var(--muted); margin:.1rem 0 .35rem; }
.remark {
  margin:.4rem 0 0; padding:.45rem .55rem; border-radius:.45rem;
  border:1px dashed var(--line); background:var(--inset); font-size:.88rem; white-space:pre-wrap;
}
input[type="date"] { min-height:2.4rem; cursor:pointer; }
.sec-title { display:flex; justify-content:space-between; align-items:baseline; gap:.5rem; margin-bottom:.7rem; }
.sec-title h2 { margin:0; font-size:1.05rem; }
.muted { color:var(--muted); font-size:.82rem; }
.toggle { display:flex; align-items:center; gap:.35rem; font-size:.82rem; color:var(--muted); }
@media (max-width: 900px) {
  .kpis, .grid-3, .disc-layout, .sum-box { grid-template-columns:1fr 1fr; }
}
@media (max-width: 640px) {
  .kpis, .grid-3, .grid-2, .disc-layout, .sum-box, .methods { grid-template-columns:1fr; }
  table { min-width:32rem; }
}
</style>
</head>
<body>
<header>
  <div class="topbar">
    <div>
      <h1 id="pageTitle">ชำระเจ้าหนี้ · __SITE__</h1>
      <div class="crumb" id="pageCrumb">__USER__ · HQ only</div>
    </div>
    <button type="button" class="avatar" id="themeBtn" title="สลับธีม" aria-label="สลับธีม">__INITIALS__</button>
  </div>
  <nav class="tabs">
    <button type="button" id="tabNotes" class="on">ใบวางบิล</button>
    <button type="button" id="tabPending">รอชำระ</button>
    <button type="button" id="tabVouchers">ใบสำคัญจ่าย</button>
  </nav>
</header>
<main>
  <section id="panelNotes" class="panel on">
    <div id="viewNotesList">
      <div class="card toolbar">
        <div class="field grow">
          <span class="ico">⌕</span>
          <input id="nfQ" placeholder="ค้นหาเลขที่ใบวางบิล / เจ้าหนี้ / เลขบิล" autocomplete="off"/>
        </div>
        <div class="field" style="min-width:9.5rem">
          <span class="ico">⚙</span>
          <select id="nfStatus" aria-label="สถานะ">
            <option value="">สถานะ</option>
            <option value="pending">รอชำระ</option>
            <option value="overdue">ค้างชำระ</option>
            <option value="paid">จ่ายแล้ว</option>
          </select>
        </div>
        <div class="field" style="min-width:10.5rem">
          <span class="ico">▦</span>
          <input id="nfDue" class="date-ce" type="date" lang="en" inputmode="none" aria-label="กำหนดชำระ"/>
        </div>
        <button type="button" class="btn primary" id="btnOpenCreate">+ สร้างใบวางบิล</button>
      </div>
      <div class="card" style="padding:.35rem 0 0">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>เลขที่ใบวางบิล</th>
                <th>เจ้าหนี้</th>
                <th class="num">ยอด</th>
                <th>กำหนดชำระ</th>
                <th>สถานะ</th>
              </tr>
            </thead>
            <tbody id="notesBody"></tbody>
          </table>
        </div>
        <div id="notesEmpty" class="empty hidden">ยังไม่มีรายการ</div>
        <div class="table-foot">
          <div id="notesCount">แสดง 0 รายการ</div>
          <div class="pager" id="notesPager"></div>
        </div>
      </div>
    </div>

    <div id="viewNotesCreate" class="hidden">
      <div class="card">
        <div class="create-head">
          <div>
            <div class="crumb">__USER__ · HQ only → ใบวางบิล → สร้างใบวางบิล</div>
            <h2>สร้างใบวางบิล · __SITE__</h2>
          </div>
          <button type="button" class="btn ghost" id="btnCancelCreate">ยกเลิก</button>
        </div>

        <div class="step">
          <div class="step-num">1</div>
          <div class="step-body">
            <h3>เลือกเจ้าหนี้</h3>
            <div class="combo">
              <div class="field">
                <span class="ico">⌕</span>
                <input id="vendorQ" placeholder="ค้นหา รหัส / ชื่อเจ้าหนี้" autocomplete="off"/>
              </div>
              <div id="vendorResults" class="combo-list hidden"></div>
            </div>
            <div id="pickedVendor" class="picked hidden"></div>
          </div>
        </div>

        <div class="step">
          <div class="step-num">2</div>
          <div class="step-body">
            <h3>ข้อมูลใบวางบิล</h3>
            <div class="grid-3">
              <div>
                <label class="lbl" for="noteno">เลขที่ใบวางบิล</label>
                <input class="inp" id="noteno" maxlength="15" placeholder="สูงสุด 15 ตัวอักษร"/>
              </div>
              <div>
                <label class="lbl" for="dueDate">วันครบกำหนดชำระ</label>
                <input class="inp date-ce" id="dueDate" type="date" lang="en" inputmode="none"/>
              </div>
              <div>
                <label class="lbl" for="bankSelect">บัญชีธนาคารปลายทาง</label>
                <select class="inp" id="bankSelect"><option value="">— เลือกบัญชี —</option></select>
              </div>
            </div>
            <p class="date-hint">แตะวันที่เพื่อเปิดปฏิทิน · ใช้ปี ค.ศ. เช่น 2026</p>
            <details style="margin-top:.35rem">
              <summary class="muted">เพิ่มบัญชีใหม่</summary>
              <div class="grid-3" style="margin-top:.45rem">
                <div><label class="lbl">ธนาคาร</label><input class="inp" id="newBankName"/></div>
                <div><label class="lbl">ชื่อบัญชี</label><input class="inp" id="newAcctName"/></div>
                <div><label class="lbl">เลขบัญชี</label><input class="inp" id="newAcctNo"/></div>
              </div>
              <button type="button" class="btn sm" id="btnAddBank" style="margin-top:.45rem">บันทึกบัญชี</button>
            </details>
            <div style="margin-top:.65rem">
              <label class="lbl" for="noteRemark">หมายเหตุ (optional)</label>
              <textarea class="area" id="noteRemark" maxlength="500" placeholder="เช่น รอใบลดหนี้ / นัดโอนวันศุกร์"></textarea>
              <p class="date-hint">เก็บในระบบชำระเจ้าหนี้เท่านั้น · ไม่เขียนลง KSS</p>
            </div>
          </div>
        </div>

        <div class="step">
          <div class="step-num">3</div>
          <div class="step-body">
            <div class="bill-head">
              <h3 style="margin:0">เลือกบิล <span class="sub">(เลือกได้มากกว่า 1 บิล)</span></h3>
              <div class="toggle">
                <input type="checkbox" checked disabled/>
                แสดงบิลที่ยังไม่ถูกวางบิลเท่านั้น
                <button type="button" class="linkish" id="btnRefreshBills">รีเฟรช</button>
              </div>
            </div>
            <div class="table-wrap" style="border:1px solid var(--line); border-radius:.55rem .55rem 0 0">
              <table>
                <thead>
                  <tr>
                    <th style="width:2.4rem"></th>
                    <th>เลขที่บิล</th>
                    <th>วันที่</th>
                    <th class="num">ยอดค้างชำระ (บาท)</th>
                  </tr>
                </thead>
                <tbody id="billList"></tbody>
              </table>
            </div>
            <div class="bill-foot">
              <span id="billSelectStatus">เลือก 0 บิล</span>
              <strong id="billSelectTotal">ยอดรวม 0.00 บาท</strong>
            </div>
          </div>
        </div>

        <div class="step">
          <div class="step-num">4</div>
          <div class="step-body">
            <h3>ส่วนลด (ถ้ามี)</h3>
            <div class="disc-layout">
              <div>
                <div class="seg" role="group" aria-label="ประเภทส่วนลด">
                  <button type="button" class="on" id="discModeAmount" data-mode="amount">จำนวนเงิน (บาท)</button>
                  <button type="button" id="discModePercent" data-mode="percent">% จากยอดรวม</button>
                </div>
                <label class="lbl" id="discInputLabel" for="discInput" style="margin-top:.65rem">ส่วนลด (บาท)</label>
                <input class="inp" id="discInput" type="number" inputmode="decimal" step="0.01" min="0" value="0.00"/>
              </div>
              <div class="disc-sum">
                <div class="pay-line"><span>ยอดรวมก่อนส่วนลด</span><strong id="discBillAmt">0.00</strong></div>
                <div class="pay-line"><span>ส่วนลด</span><strong id="discResolved">0.00</strong></div>
                <div class="pay-line pay-net"><span>ยอดสุทธิ</span><strong id="discNetAmt">0.00</strong></div>
              </div>
            </div>
          </div>
        </div>

        <div class="step">
          <div class="step-num">5</div>
          <div class="step-body">
            <h3>เอกสารแนบ</h3>
            <div class="drop" id="dropBill" tabindex="0">
              <div style="font-size:1.4rem;margin-bottom:.25rem">☁</div>
              <div>คลิกหรือลากไฟล์มาวางที่นี่</div>
              <div class="date-hint">รองรับไฟล์ JPG, PNG, PDF (ขนาดไม่เกิน 10 MB)</div>
            </div>
            <input id="billImages" class="hidden" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf" multiple/>
            <div class="thumbs" id="billThumbs"></div>
          </div>
        </div>

        <button type="button" class="btn primary block" id="btnCreateNote">บันทึกใบวางบิล</button>
        <div id="createMsg"></div>
      </div>
    </div>
  </section>

  <section id="panelPending" class="panel">
    <div class="card toolbar">
      <div class="field grow">
        <span class="ico">⌕</span>
        <input id="pfQ" placeholder="ค้นหาเจ้าหนี้ / เลขใบวางบิล" autocomplete="off"/>
      </div>
      <div class="field" style="min-width:11rem">
        <span class="ico">▦</span>
        <input id="pfDue" class="date-ce" type="date" lang="en" inputmode="none" aria-label="กำหนดชำระ"/>
      </div>
      <button type="button" class="btn soft" id="btnRefreshPending">↻ รีเฟรช</button>
    </div>
    <div class="kpis">
      <button type="button" class="kpi kpi-all on" data-bucket="all">
        <span class="mark">▤</span>
        <span><b>รอชำระทั้งหมด</b><span id="kpiAll">0 รายการ · 0.00 บาท</span></span>
      </button>
      <button type="button" class="kpi kpi-overdue" data-bucket="overdue">
        <span class="mark">!</span>
        <span><b>เกินกำหนด</b><span id="kpiOverdue">0 รายการ · 0.00 บาท</span></span>
      </button>
      <button type="button" class="kpi kpi-today" data-bucket="today">
        <span class="mark">▦</span>
        <span><b>ครบกำหนดวันนี้</b><span id="kpiToday">0 รายการ · 0.00 บาท</span></span>
      </button>
      <button type="button" class="kpi kpi-soon" data-bucket="soon">
        <span class="mark">◷</span>
        <span><b>ใกล้ครบกำหนด</b><span id="kpiSoon">0 รายการ · 0.00 บาท</span></span>
      </button>
    </div>
    <div class="card" style="padding:.35rem 0 0">
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>รหัสเจ้าหนี้</th>
              <th>เลขใบวางบิล</th>
              <th class="num">ยอดที่ต้องจ่าย</th>
              <th>กำหนดชำระ</th>
              <th>สถานะ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="pendingBody"></tbody>
        </table>
      </div>
      <div id="pendingEmpty" class="empty hidden">ยังไม่มีรายการรอชำระ</div>
      <div class="table-foot">
        <div class="hint">ⓘ จ่ายแล้วจะย้ายไปในใบสำคัญจ่ายอัตโนมัติ</div>
        <div class="pager" id="pendingPager"></div>
      </div>
    </div>
  </section>

  <section id="panelVouchers" class="panel">
    <div class="card">
      <div class="sec-title">
        <h2>ใบสำคัญจ่าย</h2>
        <div class="muted" id="voucherTotal">ทั้งหมด 0 รายการ</div>
      </div>
      <div class="toolbar" style="margin-bottom:.75rem">
        <div class="field grow">
          <span class="ico">⌕</span>
          <input id="vfQ" placeholder="เลขใบสำคัญจ่าย / รหัสเจ้าหนี้ / เลขใบวางบิล" autocomplete="off"/>
        </div>
        <div class="field" style="min-width:12rem">
          <span class="ico">▦</span>
          <input id="vfFrom" class="date-ce" type="date" lang="en" inputmode="none" aria-label="ตั้งแต่"/>
          <span>–</span>
          <input id="vfTo" class="date-ce" type="date" lang="en" inputmode="none" aria-label="ถึง"/>
        </div>
        <div class="field" style="min-width:9.5rem">
          <select id="vfMethod" aria-label="วิธีชำระ">
            <option value="">วิธีชำระ: ทั้งหมด</option>
            <option value="transfer">โอนเงิน</option>
            <option value="cheque">เช็ค</option>
            <option value="cash">เงินสด</option>
          </select>
        </div>
        <div class="field" style="min-width:10.5rem">
          <select id="vfProof" aria-label="สถานะหลักฐาน">
            <option value="">สถานะหลักฐาน: ทั้งหมด</option>
            <option value="awaiting">รอแนบหลักฐาน</option>
            <option value="done">แนบแล้ว</option>
          </select>
        </div>
        <button type="button" class="btn ghost" id="btnClearVoucherFilters">↻ ล้างตัวกรอง</button>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>เลขใบสำคัญจ่าย</th>
              <th>รหัสเจ้าหนี้</th>
              <th>เลขใบวางบิล</th>
              <th>วันที่จ่าย</th>
              <th class="num">ยอดจ่าย (บาท)</th>
              <th>วิธีชำระ</th>
              <th>สถานะหลักฐาน</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="voucherBody"></tbody>
        </table>
      </div>
      <div id="voucherEmpty" class="empty hidden">ยังไม่มีใบสำคัญจ่าย</div>
      <div class="table-foot">
        <div id="voucherCount">แสดง 0 รายการ</div>
        <div style="display:flex;gap:.55rem;align-items:center;flex-wrap:wrap">
          <label class="muted" style="display:flex;align-items:center;gap:.35rem">แสดงต่อหน้า
            <select id="vfSize" class="inp" style="width:auto;padding:.25rem .4rem">
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </label>
          <div class="pager" id="voucherPager"></div>
        </div>
      </div>
    </div>
  </section>
</main>

<dialog id="dlgPay" class="dlg">
  <div class="dlg-head">
    <h2>บันทึกการจ่าย</h2>
    <button type="button" class="dlg-x" id="btnClosePay" aria-label="ปิด">×</button>
  </div>
  <div class="dlg-body">
    <div class="sum-box">
      <div><div class="k">รหัสเจ้าหนี้</div><div class="v" id="payAcct">—</div></div>
      <div><div class="k">ยอดบิล</div><div class="v" id="payBillAmt">0.00</div></div>
      <div><div class="k">เลขใบวางบิล</div><div class="v" id="payNote">—</div></div>
      <div><div class="k">ส่วนลด (จากใบวางบิล)</div><div class="v" id="payDiscountAmt">0.00</div></div>
      <div><div class="k">บัญชีปลายทาง</div><div class="v" id="payBankLine">—</div></div>
      <div class="net"><div class="k">ยอดสุทธิ</div><div class="v" id="payNetAmt">0.00</div></div>
    </div>
    <h3 style="margin:.2rem 0 .45rem;font-size:.95rem">ข้อมูลการจ่าย</h3>
    <label class="lbl">วิธีชำระ</label>
    <div class="methods" role="group" aria-label="วิธีชำระ">
      <button type="button" class="method on" id="settleTransfer" data-settle="transfer">🏦<span>โอนเงิน</span></button>
      <button type="button" class="method" id="settleCheque" data-settle="cheque">✎<span>เช็ค</span></button>
      <button type="button" class="method" id="settleCash" data-settle="cash">💵<span>เงินสด</span></button>
    </div>
    <div class="grid-2">
      <div>
        <label class="lbl" for="payChkamt">จำนวนเงินที่จ่าย (บาท)</label>
        <input class="inp" id="payChkamt" type="number" inputmode="decimal" step="0.01" min="0"/>
      </div>
      <div>
        <label class="lbl" for="payChkdate">วันที่จ่าย</label>
        <input class="inp date-ce" id="payChkdate" type="date" lang="en" inputmode="none"/>
      </div>
    </div>
    <div id="payChknoWrap" class="hidden" style="margin-top:.65rem">
      <label class="lbl" id="payChknoLabel" for="payChkno">เลขที่เช็ค</label>
      <input class="inp" id="payChkno" maxlength="15"/>
    </div>
    <div style="margin-top:.65rem">
      <label class="lbl" for="payBankGl">บัญชีที่ใช้จ่าย</label>
      <select class="inp" id="payBankGl">
        <option value="2101.7">2101.7 - ธนาคารกรุงไทย กระแสรายวัน</option>
        <option value="2101.1">2101.1 - ธนาคารไทยพาณิชย์</option>
        <option value="2101.2">2101.2 - ธนาคารกสิกรไทย</option>
        <option value="2101.3">2101.3 - ธนาคารกรุงเทพ</option>
      </select>
    </div>
    <div id="payMsg"></div>
  </div>
  <div class="dlg-foot">
    <button type="button" class="btn ghost" id="btnCancelPay">ยกเลิก</button>
    <button type="button" class="btn primary" id="btnConfirmPay">บันทึกการจ่าย</button>
  </div>
</dialog>

<dialog id="dlgDetail" class="dlg">
  <div class="dlg-head">
    <h2 id="detTitle">รายละเอียด</h2>
    <button type="button" class="dlg-x" id="btnCloseDetail" aria-label="ปิด">×</button>
  </div>
  <div class="dlg-body">
    <div id="detMeta" class="muted"></div>
    <div id="detRemark"></div>
    <div id="detDueWrap" class="hidden" style="margin-top:.75rem">
      <label class="lbl">วันครบกำหนดชำระ</label>
      <div style="display:flex;gap:.4rem;align-items:center;flex-wrap:wrap">
        <span id="detDueView"></span>
        <button type="button" class="linkish" id="detDueEdit">แก้ไข</button>
        <input type="date" class="inp date-ce hidden" id="detDueInput" lang="en" inputmode="none" style="width:auto"/>
        <button type="button" class="btn sm primary hidden" id="detDueSave">บันทึก</button>
        <button type="button" class="linkish hidden" id="detDueCancel">ยกเลิก</button>
      </div>
    </div>
    <h3 style="margin:1rem 0 .4rem;font-size:.95rem">รูปใบวางบิล</h3>
    <div class="thumbs" id="detBillThumbs"></div>
    <div id="detProofWrap" class="hidden">
      <h3 style="margin:1rem 0 .4rem;font-size:.95rem">หลักฐานชำระ</h3>
      <div class="thumbs" id="detProofThumbs"></div>
      <div id="detUploadWrap" class="hidden" style="margin-top:.55rem">
        <label class="lbl">อัปโหลดหลักฐาน</label>
        <input class="inp" id="detProofFiles" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf" multiple/>
      </div>
    </div>
  </div>
  <div class="dlg-foot">
    <button type="button" class="btn ghost" id="btnCloseDetail2">ปิด</button>
    <button type="button" class="btn primary hidden" id="detPayBtn">บันทึกการจ่าย</button>
  </div>
</dialog>

<script>
const WRITE_ENABLED = __WRITE__;
const USER_NAME = __USER_JSON__;
const SITE = "__SITE__";
const PAGE_SIZE = 10;
const DUE_SOON_DAYS = 7;
const MAX_FILE_BYTES = 10 * 1024 * 1024;

let picked = null;
let uploadedPaths = [];
let payTarget = null;
let discMode = 'amount';
let settleMethod = 'transfer';
let pendingRows = [];
let voucherRows = [];
let notesPage = 1;
let pendingPage = 1;
let voucherPage = 1;
let voucherPageSize = 10;
let pendingBucket = 'all';
let notesView = 'list';
let detailRow = null;

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
  ));
}
function fmtMoney(n) {
  return Number(n || 0).toLocaleString('th-TH', {minimumFractionDigits:2, maximumFractionDigits:2});
}
function fmtDate(iso, short) {
  const s = String(iso || '').slice(0, 10);
  if (!s || s.length < 10) return '—';
  const [y, m, d] = s.split('-');
  return short ? `${d}/${m}/${y.slice(2)}` : `${d}/${m}/${y}`;
}
function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function addDaysISO(iso, days) {
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + days);
  return `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')}`;
}
function remDue(r) { return String(((r.reminder || {}).due_date) || '').slice(0, 10); }
function netAmt(r) {
  const bill = Number(r.NETAMT != null ? r.NETAMT : r.BILLAMT || 0);
  if (r.stage === 'pending' || !r.voucno) {
    const disc = Number((r.reminder || {}).discount_amount || 0);
    return Math.max(0, Number(r.BILLAMT || 0) - disc);
  }
  return Number(r.NETAMT != null ? r.NETAMT : bill);
}
function dueBucket(due) {
  const today = todayISO();
  if (!due) return 'later';
  if (due < today) return 'overdue';
  if (due === today) return 'today';
  if (due <= addDaysISO(today, DUE_SOON_DAYS)) return 'soon';
  return 'later';
}
function noteStatus(r) {
  if (r.voucno || r.stage === 'paid' || r.stage === 'await_proof' || r.has_proof) return 'paid';
  return dueBucket(remDue(r)) === 'overdue' ? 'overdue' : 'pending';
}
function pendingStatus(r) {
  const b = dueBucket(remDue(r));
  if (b === 'overdue') return {cls:'b-overdue', label:'เกินกำหนด', bucket:'overdue'};
  if (b === 'today') return {cls:'b-today', label:'ครบกำหนดวันนี้', bucket:'today'};
  if (b === 'soon') return {cls:'b-soon', label:'ใกล้ครบกำหนด', bucket:'soon'};
  return {cls:'b-pending', label:'รอชำระ', bucket:'later'};
}
function settleLabel(m) {
  return m === 'cheque' ? 'เช็ค' : (m === 'cash' ? 'เงินสด' : (m === 'transfer' ? 'โอนเงิน' : '—'));
}
function keyOf(r) { return `${r.acctno}|${r.noteno}`; }

async function api(path, opts) {
  const r = await fetch('/pay-notes/api' + path, opts || {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || j.error || r.statusText);
  return j;
}

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

function applyTheme(t) {
  const next = t === 'dark' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  const meta = $('themeColor');
  if (meta) meta.setAttribute('content', next === 'light' ? '#f3f5f9' : '#0c1014');
  try { localStorage.setItem('kcw.pay_notes.theme', next); } catch (e) {}
}
$('themeBtn').onclick = () => {
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
};
applyTheme(document.documentElement.getAttribute('data-theme') || 'light');

function setCrumb(tab, extra) {
  const base = `${USER_NAME} · HQ only`;
  if (extra) { $('pageCrumb').textContent = `${base} → ใบวางบิล → ${extra}`; return; }
  if (tab === 'pending') { $('pageCrumb').textContent = `${base} → ใบวางบิล → รอชำระ`; return; }
  if (tab === 'vouchers') { $('pageCrumb').textContent = `${base} → ใบวางบิล → รอชำระ → ใบสำคัญจ่าย`; return; }
  $('pageCrumb').textContent = base;
}

function showNotesView(view) {
  notesView = view;
  $('viewNotesList').classList.toggle('hidden', view !== 'list');
  $('viewNotesCreate').classList.toggle('hidden', view !== 'create');
  if (view === 'create') {
    $('pageTitle').textContent = `สร้างใบวางบิล · ${SITE}`;
    setCrumb('notes', 'สร้างใบวางบิล');
    if (!$('dueDate').value) $('dueDate').value = todayISO();
  } else {
    $('pageTitle').textContent = `ชำระเจ้าหนี้ · ${SITE}`;
    setCrumb('notes');
  }
}

function showTab(name) {
  const map = {notes:'Notes', pending:'Pending', vouchers:'Vouchers'};
  Object.keys(map).forEach(k => {
    $('tab' + map[k]).classList.toggle('on', name === k);
    $('panel' + map[k]).classList.toggle('on', name === k);
  });
  if (name !== 'notes') showNotesView('list');
  $('pageTitle').textContent = `ชำระเจ้าหนี้ · ${SITE}`;
  setCrumb(name);
  if (name === 'notes') loadNotes();
  if (name === 'pending') loadPending();
  if (name === 'vouchers') loadVouchers();
  try { history.replaceState(null, '', name === 'notes' ? '#' : '#' + name); } catch (e) {}
}
$('tabNotes').onclick = () => { showNotesView('list'); showTab('notes'); };
$('tabPending').onclick = () => showTab('pending');
$('tabVouchers').onclick = () => showTab('vouchers');
$('btnOpenCreate').onclick = () => { showTab('notes'); showNotesView('create'); };
$('btnCancelCreate').onclick = () => showNotesView('list');

function pageItems(page, pages) {
  if (pages <= 1) return [1];
  if (pages <= 7) return [...Array(pages)].map((_, i) => i + 1);
  const items = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(pages - 1, page + 1);
  if (start > 2) items.push('…');
  for (let i = start; i <= end; i++) items.push(i);
  if (end < pages - 1) items.push('…');
  items.push(pages);
  return items;
}
function renderPager(el, page, pages, onPage) {
  if (!el) return;
  const prev = `<button type="button" data-p="${page-1}" ${page<=1?'disabled':''}>&lt;</button>`;
  const next = `<button type="button" data-p="${page+1}" ${page>=pages?'disabled':''}>&gt;</button>`;
  const nums = pageItems(page, pages).map(n => n === '…'
    ? `<span style="padding:0 .2rem">…</span>`
    : `<button type="button" data-p="${n}" class="${n===page?'on':''}">${n}</button>`
  ).join('');
  el.innerHTML = prev + nums + next;
  el.querySelectorAll('button[data-p]').forEach(btn => {
    btn.onclick = () => {
      const p = Number(btn.dataset.p);
      if (p >= 1 && p <= pages) onPage(p);
    };
  });
}
function slicePage(rows, page, size) {
  const pages = Math.max(1, Math.ceil(rows.length / size) || 1);
  const p = Math.min(Math.max(1, page), pages);
  const start = (p - 1) * size;
  return { rows: rows.slice(start, start + size), page: p, pages, start, end: Math.min(start + size, rows.length), total: rows.length };
}

async function loadNotes() {
  if (notesView === 'create') return;
  $('notesBody').innerHTML = `<tr><td colspan="5" class="empty">กำลังโหลด…</td></tr>`;
  try {
    const [p, v] = await Promise.all([api('/pending'), api('/vouchered?proof=all')]);
    pendingRows = p || [];
    voucherRows = v || [];
    renderNotes();
  } catch (e) {
    $('notesBody').innerHTML = `<tr><td colspan="5" class="err">${esc(e.message)}</td></tr>`;
  }
}
function allNoteRows() {
  return [...pendingRows.map(r => ({...r, stage:'pending'})), ...voucherRows];
}
function filteredNotes() {
  const q = ($('nfQ').value || '').trim().toLowerCase();
  const st = $('nfStatus').value;
  const due = ($('nfDue').value || '').trim();
  let rows = allNoteRows().filter(r => {
    const status = noteStatus(r);
    if (st && status !== st) return false;
    if (due && remDue(r) !== due) return false;
    if (q) {
      const hay = [r.acctno, r.acctname, r.noteno, r.voucno, remDue(r), (r.reminder||{}).remark]
        .map(x => String(x||'').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort((a, b) => String(remDue(b)).localeCompare(String(remDue(a))) || String(a.noteno).localeCompare(String(b.noteno)));
  return rows;
}
function statusBadge(status) {
  if (status === 'paid') return '<span class="badge b-paid">จ่ายแล้ว</span>';
  if (status === 'overdue') return '<span class="badge b-overdue">ค้างชำระ</span>';
  return '<span class="badge b-pending">รอชำระ</span>';
}
function renderNotes() {
  const all = filteredNotes();
  const pg = slicePage(all, notesPage, PAGE_SIZE);
  notesPage = pg.page;
  $('notesEmpty').classList.toggle('hidden', pg.total !== 0);
  $('notesCount').textContent = pg.total
    ? `แสดง ${pg.start + 1} - ${pg.end} จาก ${pg.total} รายการ`
    : 'แสดง 0 รายการ';
  $('notesBody').innerHTML = pg.rows.map(r => {
    const vendor = `${esc(r.acctno || '')}${r.acctname ? ' - ' + esc(r.acctname) : ''}`;
    return `<tr>
      <td><button type="button" class="linkish" data-open="${esc(keyOf(r))}">${esc(r.noteno)}</button></td>
      <td>${vendor}</td>
      <td class="num">${fmtMoney(r.BILLAMT)}</td>
      <td>${fmtDate(remDue(r), true)}</td>
      <td>${statusBadge(noteStatus(r))}</td>
    </tr>`;
  }).join('');
  renderPager($('notesPager'), pg.page, pg.pages, p => { notesPage = p; renderNotes(); });
}
['nfQ','nfStatus','nfDue'].forEach(id => {
  const el = $(id);
  el.addEventListener(el.tagName === 'SELECT' || el.type === 'date' ? 'change' : 'input', () => { notesPage = 1; renderNotes(); });
});
$('notesBody').addEventListener('click', (e) => {
  const btn = e.target.closest('[data-open]');
  if (btn) openDetailByKey(btn.dataset.open);
});

async function loadPending() {
  $('pendingBody').innerHTML = `<tr><td colspan="6" class="empty">กำลังโหลด…</td></tr>`;
  try {
    pendingRows = await api('/pending');
    renderPending();
  } catch (e) {
    $('pendingBody').innerHTML = `<tr><td colspan="6" class="err">${esc(e.message)}</td></tr>`;
  }
}
function pendingNet(r) {
  return Math.max(0, Number(r.BILLAMT || 0) - Number((r.reminder || {}).discount_amount || 0));
}
function filteredPending() {
  const q = ($('pfQ').value || '').trim().toLowerCase();
  const due = ($('pfDue').value || '').trim();
  let rows = pendingRows.filter(r => {
    const st = pendingStatus(r);
    if (pendingBucket !== 'all' && st.bucket !== pendingBucket) return false;
    if (due && remDue(r) !== due) return false;
    if (q) {
      const hay = [r.acctno, r.acctname, r.noteno, remDue(r)].map(x => String(x||'').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort((a, b) => String(remDue(a)).localeCompare(String(remDue(b))) || String(a.acctno).localeCompare(String(b.acctno)));
  return rows;
}
function renderKpis() {
  const groups = {all: pendingRows, overdue: [], today: [], soon: []};
  pendingRows.forEach(r => {
    const b = pendingStatus(r).bucket;
    if (groups[b]) groups[b].push(r);
  });
  const line = (rows) => `${rows.length} รายการ · ${fmtMoney(rows.reduce((s, r) => s + pendingNet(r), 0))} บาท`;
  $('kpiAll').textContent = line(groups.all);
  $('kpiOverdue').textContent = line(groups.overdue);
  $('kpiToday').textContent = line(groups.today);
  $('kpiSoon').textContent = line(groups.soon);
  document.querySelectorAll('.kpi[data-bucket]').forEach(el => {
    el.classList.toggle('on', el.dataset.bucket === pendingBucket);
  });
}
function renderPending() {
  renderKpis();
  const all = filteredPending();
  const pg = slicePage(all, pendingPage, PAGE_SIZE);
  pendingPage = pg.page;
  $('pendingEmpty').classList.toggle('hidden', pg.total !== 0);
  $('pendingBody').innerHTML = pg.rows.map(r => {
    const st = pendingStatus(r);
    const bank = ((r.reminder || {}).vendor_bank || {});
    const bankname = `${bank.bank_name || ''} ${bank.bank_account_name || ''} # ${bank.bank_account_number || ''}`.trim();
    return `<tr>
      <td>${esc(r.acctno)}</td>
      <td>${esc(r.noteno)}</td>
      <td class="num">${fmtMoney(pendingNet(r))} บาท</td>
      <td>${fmtDate(remDue(r))}</td>
      <td><span class="badge ${st.cls}">${st.label}</span></td>
      <td><div class="row-actions">
        <button type="button" class="btn sm" data-open="${esc(keyOf(r))}">ดูรายละเอียด</button>
        <button type="button" class="btn sm primary"
          data-pay-acct="${esc(r.acctno)}" data-pay-note="${esc(r.noteno)}"
          data-pay-amt="${Number(r.BILLAMT||0)}" data-pay-disc="${Number((r.reminder||{}).discount_amount||0)}"
          data-pay-bank="${esc(bankname)}">บันทึกการจ่าย</button>
      </div></td>
    </tr>`;
  }).join('');
  renderPager($('pendingPager'), pg.page, pg.pages, p => { pendingPage = p; renderPending(); });
}
document.querySelectorAll('.kpi[data-bucket]').forEach(btn => {
  btn.onclick = () => { pendingBucket = btn.dataset.bucket; pendingPage = 1; renderPending(); };
});
$('btnRefreshPending').onclick = loadPending;
['pfQ','pfDue'].forEach(id => {
  const el = $(id);
  el.addEventListener(el.type === 'date' ? 'change' : 'input', () => { pendingPage = 1; renderPending(); });
});
$('pendingBody').addEventListener('click', (e) => {
  const pay = e.target.closest('[data-pay-acct]');
  if (pay) {
    openPay(pay.dataset.payAcct, pay.dataset.payNote, pay.dataset.payAmt, pay.dataset.payDisc, pay.dataset.payBank || '');
    return;
  }
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {canPay: true});
});

async function loadVouchers() {
  $('voucherBody').innerHTML = `<tr><td colspan="8" class="empty">กำลังโหลด…</td></tr>`;
  try {
    voucherRows = await api('/vouchered?proof=all');
    renderVouchers();
  } catch (e) {
    $('voucherBody').innerHTML = `<tr><td colspan="8" class="err">${esc(e.message)}</td></tr>`;
  }
}
function voucDate(r) { return String(r.VOUCDATE || '').slice(0, 10); }
function filteredVouchers() {
  const q = ($('vfQ').value || '').trim().toLowerCase();
  const from = ($('vfFrom').value || '').trim();
  const to = ($('vfTo').value || '').trim();
  const method = $('vfMethod').value;
  const proof = $('vfProof').value;
  let rows = voucherRows.filter(r => {
    const d = voucDate(r);
    if (from && (!d || d < from)) return false;
    if (to && (!d || d > to)) return false;
    if (method && (r.settle_method || '') !== method) return false;
    if (proof === 'awaiting' && r.has_proof) return false;
    if (proof === 'done' && !r.has_proof) return false;
    if (q) {
      const hay = [r.acctno, r.acctname, r.noteno, r.voucno, d].map(x => String(x||'').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort((a, b) => String(voucDate(b)).localeCompare(String(voucDate(a))) || String(b.voucno||'').localeCompare(String(a.voucno||'')));
  return rows;
}
function renderVouchers() {
  const all = filteredVouchers();
  const pg = slicePage(all, voucherPage, voucherPageSize);
  voucherPage = pg.page;
  $('voucherTotal').textContent = `ทั้งหมด ${voucherRows.length} รายการ`;
  $('voucherEmpty').classList.toggle('hidden', pg.total !== 0);
  $('voucherCount').textContent = pg.total
    ? `แสดง ${pg.start + 1} - ${pg.end} จาก ${pg.total} รายการ`
    : 'แสดง 0 รายการ';
  $('voucherBody').innerHTML = pg.rows.map(r => {
    const proof = r.has_proof
      ? '<span class="badge b-done">แนบแล้ว</span>'
      : '<span class="badge b-wait">รอแนบหลักฐาน</span>';
    return `<tr data-open="${esc(keyOf(r))}" style="cursor:pointer">
      <td><button type="button" class="linkish" data-open="${esc(keyOf(r))}">${esc(r.voucno || '—')}</button></td>
      <td>${esc(r.acctno)}</td>
      <td>${esc(r.noteno)}</td>
      <td>${fmtDate(voucDate(r))}</td>
      <td class="num">${fmtMoney(r.NETAMT != null ? r.NETAMT : r.BILLAMT)}</td>
      <td>${esc(settleLabel(r.settle_method))}</td>
      <td>${proof}</td>
      <td style="text-align:right;color:var(--muted)">›</td>
    </tr>`;
  }).join('');
  renderPager($('voucherPager'), pg.page, pg.pages, p => { voucherPage = p; renderVouchers(); });
}
function clearVoucherFilters() {
  $('vfQ').value = ''; $('vfFrom').value = ''; $('vfTo').value = '';
  $('vfMethod').value = ''; $('vfProof').value = '';
  voucherPage = 1; renderVouchers();
}
$('btnClearVoucherFilters').onclick = clearVoucherFilters;
$('vfSize').onchange = () => { voucherPageSize = Number($('vfSize').value || 10); voucherPage = 1; renderVouchers(); };
['vfQ','vfFrom','vfTo','vfMethod','vfProof'].forEach(id => {
  const el = $(id);
  el.addEventListener(el.tagName === 'SELECT' || el.type === 'date' ? 'change' : 'input', () => { voucherPage = 1; renderVouchers(); });
});
$('voucherBody').addEventListener('click', (e) => {
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {voucher: true});
});

function findRow(key) {
  return allNoteRows().find(r => keyOf(r) === key);
}
function thumbsHtml(images) {
  const list = (images || []).filter(x => x && (x.url || x.path));
  if (!list.length) return '<p class="muted">ไม่มีรูป</p>';
  return list.map(img => {
    const url = esc(img.url || '');
    const name = String(img.name || img.path || '');
    if (/\.pdf$/i.test(name)) return `<a class="file-chip" href="${url}" target="_blank" rel="noopener">${esc(name)}</a>`;
    return url ? `<a href="${url}" target="_blank" rel="noopener"><img src="${url}" alt=""/></a>` : '';
  }).join('');
}
async function openDetailByKey(key, opts) {
  opts = opts || {};
  const row = findRow(key) || pendingRows.find(r => keyOf(r) === key) || voucherRows.find(r => keyOf(r) === key);
  if (!row) return;
  detailRow = row;
  const rem = row.reminder || {};
  $('detTitle').textContent = row.voucno ? `ใบสำคัญจ่าย ${row.voucno}` : `ใบวางบิล ${row.noteno}`;
  $('detMeta').textContent = `${row.acctno} · ${row.acctname || ''} · ${row.noteno}`;
  const remark = String(rem.remark || '').trim();
  $('detRemark').innerHTML = remark ? `<div class="remark">${esc(remark)}</div>` : '';
  const canEditDue = !row.voucno && row.stage !== 'paid' && row.stage !== 'await_proof';
  $('detDueWrap').classList.toggle('hidden', !canEditDue && !remDue(row));
  $('detDueView').textContent = remDue(row) || '—';
  $('detDueInput').value = remDue(row);
  $('detDueInput').dataset.orig = remDue(row);
  setDueEdit(false);
  $('detPayBtn').classList.toggle('hidden', !(opts.canPay && canEditDue && WRITE_ENABLED));
  $('detProofWrap').classList.toggle('hidden', !row.voucno);
  $('detUploadWrap').classList.toggle('hidden', !(row.voucno && !row.has_proof));
  $('detBillThumbs').innerHTML = 'กำลังโหลด…';
  $('detProofThumbs').innerHTML = thumbsHtml(row.payment_images || []);
  $('dlgDetail').showModal();
  try {
    const det = await api(`/notes/${encodeURIComponent(row.acctno)}/${encodeURIComponent(row.noteno)}`);
    $('detBillThumbs').innerHTML = thumbsHtml(det.bill_images || []);
    if (det.payment_images) $('detProofThumbs').innerHTML = thumbsHtml(det.payment_images);
  } catch (e) {
    $('detBillThumbs').innerHTML = `<p class="err">${esc(e.message)}</p>`;
  }
}
function setDueEdit(on) {
  $('detDueView').classList.toggle('hidden', on);
  $('detDueEdit').classList.toggle('hidden', on);
  $('detDueInput').classList.toggle('hidden', !on);
  $('detDueSave').classList.toggle('hidden', !on);
  $('detDueCancel').classList.toggle('hidden', !on);
  if (on) {
    $('detDueInput').value = $('detDueInput').dataset.orig || '';
    try { $('detDueInput').focus(); } catch (_) {}
  }
}
$('detDueEdit').onclick = () => setDueEdit(true);
$('detDueCancel').onclick = () => setDueEdit(false);
$('detDueSave').onclick = async () => {
  if (!detailRow) return;
  const next = ($('detDueInput').value || '').trim();
  if (!next) { alert('เลือกวันครบกำหนด'); return; }
  try {
    await api(`/reminder/${encodeURIComponent(detailRow.acctno)}/${encodeURIComponent(detailRow.noteno)}`, {
      method: 'PATCH', headers: {'Content-Type':'application/json'},
      body: JSON.stringify({due_date: next})
    });
    if (detailRow.reminder) detailRow.reminder.due_date = next;
    const row = pendingRows.find(x => keyOf(x) === keyOf(detailRow));
    if (row && row.reminder) row.reminder.due_date = next;
    $('detDueInput').dataset.orig = next;
    $('detDueView').textContent = next;
    setDueEdit(false);
    renderPending();
    renderNotes();
  } catch (e) { alert(e.message); }
};
$('detPayBtn').onclick = () => {
  if (!detailRow) return;
  const bank = (detailRow.reminder || {}).vendor_bank || {};
  $('dlgDetail').close();
  openPay(
    detailRow.acctno, detailRow.noteno, detailRow.BILLAMT,
    (detailRow.reminder || {}).discount_amount || 0,
    `${bank.bank_name || ''} ${bank.bank_account_name || ''} # ${bank.bank_account_number || ''}`
  );
};
$('btnCloseDetail').onclick = () => $('dlgDetail').close();
$('btnCloseDetail2').onclick = () => $('dlgDetail').close();
$('detProofFiles').onchange = async (ev) => {
  if (!detailRow || !detailRow.voucno) return;
  for (const file of ev.target.files) {
    if (file.size > MAX_FILE_BYTES) { alert('ไฟล์เกิน 10 MB'); continue; }
    const fd = new FormData();
    fd.append('voucno', detailRow.voucno);
    fd.append('file', file);
    const r = await fetch('/pay-notes/api/images/payment', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { alert(j.detail || j.error); return; }
  }
  ev.target.value = '';
  await loadVouchers();
  const fresh = voucherRows.find(x => keyOf(x) === keyOf(detailRow));
  if (fresh) openDetailByKey(keyOf(fresh), {voucher: true});
};

function setSettleMethod(method) {
  settleMethod = method === 'cheque' ? 'cheque' : (method === 'cash' ? 'cash' : 'transfer');
  ['transfer','cheque','cash'].forEach(m => {
    const el = $('settle' + m.charAt(0).toUpperCase() + m.slice(1));
    if (el) el.classList.toggle('on', settleMethod === m);
  });
  $('payChknoWrap').classList.toggle('hidden', settleMethod !== 'cheque');
  if (settleMethod === 'transfer') {
    if (!$('payChkno').value.trim() || $('payChkno').dataset.auto === '1') {
      $('payChkno').value = 'โอน';
      $('payChkno').dataset.auto = '1';
    }
  } else if ($('payChkno').value.trim() === 'โอน' || $('payChkno').dataset.auto === '1') {
    $('payChkno').value = '';
    $('payChkno').dataset.auto = '1';
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
  $('payAcct').textContent = acct;
  $('payNote').textContent = note;
  $('payBillAmt').textContent = fmtMoney(bill);
  $('payDiscountAmt').textContent = fmtMoney(disc);
  $('payNetAmt').textContent = fmtMoney(net);
  $('payBankLine').textContent = (bankname || '').replace(/\s+#\s+$/,'').trim() || '— ไม่พบบัญชีธนาคาร —';
  $('payChkamt').value = String(net);
  $('payChkdate').value = todayISO();
  $('payBankGl').value = '2101.7';
  $('payMsg').innerHTML = '';
  $('payChkno').dataset.auto = '1';
  setSettleMethod('transfer');
  wireDatePickers($('dlgPay'));
  $('dlgPay').showModal();
}
$('btnClosePay').onclick = () => $('dlgPay').close();
$('btnCancelPay').onclick = () => $('dlgPay').close();
$('btnConfirmPay').onclick = async () => {
  if (!WRITE_ENABLED) { $('payMsg').innerHTML = '<p class="err">KSS write ปิดอยู่</p>'; return; }
  if (!payTarget) return;
  const chkno = settleMethod === 'transfer' ? ($('payChkno').value.trim() || 'โอน')
    : settleMethod === 'cash' ? $('payChkno').value.trim()
    : $('payChkno').value.trim();
  const chkamt = Number($('payChkamt').value || 0);
  if (settleMethod === 'cheque' && !chkno) {
    $('payMsg').innerHTML = '<p class="err">กรอกเลขที่เช็ค</p>'; return;
  }
  if (chkamt <= 0 && payTarget.netamt > 0) {
    $('payMsg').innerHTML = '<p class="err">กรอกจำนวนเงินที่จ่าย</p>'; return;
  }
  try {
    const res = await api('/vouchers', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: payTarget.acctno, noteno: payTarget.noteno,
        settle_method: settleMethod, chkno, chkamt,
        chkdate: $('payChkdate').value, bank_gl: $('payBankGl').value.trim()
      })
    });
    $('payMsg').innerHTML = `<p class="ok">บันทึกแล้ว · ${esc(res.voucno)}</p>`;
    setTimeout(() => { $('dlgPay').close(); showTab('vouchers'); }, 700);
  } catch (e) { $('payMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`; }
};

let vendorTimer = null;
async function searchVendors() {
  const q = $('vendorQ').value.trim();
  if (!q) { $('vendorResults').classList.add('hidden'); return; }
  $('vendorResults').classList.remove('hidden');
  $('vendorResults').innerHTML = '<div class="muted" style="padding:.6rem">กำลังค้นหา…</div>';
  try {
    const rows = await api('/vendors?q=' + encodeURIComponent(q));
    $('vendorResults').innerHTML = rows.map(v =>
      `<button type="button" data-acct="${esc(v.acctno)}" data-name="${esc(v.acctname)}">${esc(v.acctno)} — ${esc(v.acctname)}</button>`
    ).join('') || '<div class="muted" style="padding:.6rem">ไม่พบ</div>';
    $('vendorResults').querySelectorAll('button[data-acct]').forEach(b => {
      b.onclick = () => pickVendor(b.dataset.acct, b.dataset.name);
    });
  } catch (e) { $('vendorResults').innerHTML = `<div class="err" style="padding:.6rem">${esc(e.message)}</div>`; }
}
$('vendorQ').addEventListener('input', () => {
  clearTimeout(vendorTimer);
  vendorTimer = setTimeout(searchVendors, 280);
});
$('vendorQ').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); searchVendors(); }
});
document.addEventListener('click', (e) => {
  if (!e.target.closest('.combo')) $('vendorResults').classList.add('hidden');
});

async function pickVendor(acctno, acctname) {
  picked = {acctno, acctname};
  $('vendorQ').value = `${acctno} — ${acctname}`;
  $('pickedVendor').textContent = `${acctno} — ${acctname}`;
  $('pickedVendor').classList.remove('hidden');
  $('vendorResults').classList.add('hidden');
  if (!$('dueDate').value) $('dueDate').value = todayISO();
  uploadedPaths = [];
  $('billThumbs').innerHTML = '';
  await loadBanks();
  await loadBills();
}

async function loadBanks() {
  if (!picked) return;
  const rows = await api('/banks?acctno=' + encodeURIComponent(picked.acctno));
  $('bankSelect').innerHTML = (rows.length ? '' : '<option value="">— เพิ่มบัญชี —</option>') + rows.map(b =>
    `<option value="${esc(b.bank_id)}">${esc(b.bank_name)} · ${esc(b.bank_account_number)}${b.is_default?' ★':''}</option>`
  ).join('');
}

async function loadBills() {
  if (!picked) {
    $('billList').innerHTML = `<tr><td colspan="4" class="empty">เลือกเจ้าหนี้ก่อน</td></tr>`;
    updateBillSelectStatus();
    return;
  }
  $('billList').innerHTML = `<tr><td colspan="4" class="empty">กำลังโหลดบิล…</td></tr>`;
  try {
    const rows = await api('/bills?acctno=' + encodeURIComponent(picked.acctno));
    $('billList').innerHTML = rows.map(b =>
      `<tr>
        <td><input type="checkbox" value="${esc(b.BILLNO)}" data-amt="${Number(b.AFTERTAX)||0}"/></td>
        <td>${esc(b.BILLNO)}</td>
        <td>${fmtDate(b.BILLDATE)}</td>
        <td class="num">${fmtMoney(b.AFTERTAX)}</td>
      </tr>`
    ).join('') || `<tr><td colspan="4" class="empty">ไม่มีบิลว่าง (บิลที่ผูกโน้ตแล้วจะไม่แสดง)</td></tr>`;
    $('billList').querySelectorAll('input[type=checkbox]').forEach(cb => {
      cb.addEventListener('change', updateBillSelectStatus);
    });
  } catch (e) {
    $('billList').innerHTML = `<tr><td colspan="4" class="err">${esc(e.message)}</td></tr>`;
  }
  updateBillSelectStatus();
}
function selectedBillTotal() {
  const checked = [...$('billList').querySelectorAll('input[type=checkbox]:checked')];
  return { n: checked.length, total: checked.reduce((s, cb) => s + (Number(cb.dataset.amt) || 0), 0) };
}
function resolveDiscAmount(bill) {
  const raw = Math.max(0, Number($('discInput').value || 0));
  if (discMode === 'percent') return Math.round(bill * Math.min(raw, 100) / 100 * 100) / 100;
  return Math.round(raw * 100) / 100;
}
function syncDiscPreview() {
  const { total } = selectedBillTotal();
  const disc = resolveDiscAmount(total);
  $('discBillAmt').textContent = fmtMoney(total);
  $('discResolved').textContent = fmtMoney(disc);
  $('discNetAmt').textContent = fmtMoney(Math.max(0, total - disc));
  $('discResolved').style.color = (disc - total > 1e-9) ? 'var(--down)' : '';
}
function setDiscMode(mode) {
  discMode = mode === 'percent' ? 'percent' : 'amount';
  $('discModeAmount').classList.toggle('on', discMode === 'amount');
  $('discModePercent').classList.toggle('on', discMode === 'percent');
  $('discInputLabel').textContent = discMode === 'percent' ? 'ส่วนลด (%)' : 'ส่วนลด (บาท)';
  $('discInput').max = discMode === 'percent' ? '100' : '';
  syncDiscPreview();
}
$('discModeAmount').onclick = () => setDiscMode('amount');
$('discModePercent').onclick = () => setDiscMode('percent');
$('discInput').addEventListener('input', syncDiscPreview);
function updateBillSelectStatus() {
  const { n, total } = selectedBillTotal();
  $('billSelectStatus').textContent = `เลือก ${n} บิล`;
  $('billSelectTotal').textContent = `ยอดรวม ${fmtMoney(total)} บาท`;
  syncDiscPreview();
}
$('btnRefreshBills').onclick = () => loadBills();
$('btnAddBank').onclick = async () => {
  if (!picked) { alert('เลือกเจ้าหนี้ก่อน'); return; }
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

async function uploadBillFiles(files) {
  const noteno = $('noteno').value.trim();
  if (!picked || !noteno) { alert('เลือกเจ้าหนี้และกรอกเลขที่ใบวางบิลก่อน'); return; }
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); continue; }
    const fd = new FormData();
    fd.append('acctno', picked.acctno);
    fd.append('noteno', noteno);
    fd.append('file', file);
    const r = await fetch('/pay-notes/api/images/bill', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { alert(j.detail || j.error); continue; }
    uploadedPaths.push(j.path);
    if (j.url && !/\.pdf$/i.test(file.name)) {
      $('billThumbs').innerHTML += `<img src="${esc(j.url)}" alt=""/>`;
    } else {
      $('billThumbs').innerHTML += `<span class="file-chip">${esc(file.name)}</span>`;
    }
  }
}
$('billImages').onchange = async (ev) => {
  await uploadBillFiles(ev.target.files);
  ev.target.value = '';
};
const drop = $('dropBill');
drop.onclick = () => $('billImages').click();
drop.addEventListener('dragover', (e) => { e.preventDefault(); drop.classList.add('drag'); });
drop.addEventListener('dragleave', () => drop.classList.remove('drag'));
drop.addEventListener('drop', async (e) => {
  e.preventDefault(); drop.classList.remove('drag');
  await uploadBillFiles(e.dataTransfer.files);
});

$('btnCreateNote').onclick = async () => {
  const noteno = $('noteno').value.trim();
  const due = $('dueDate').value;
  const bank_id = $('bankSelect').value;
  const billnos = [...$('billList').querySelectorAll('input:checked')].map(x => x.value);
  $('createMsg').innerHTML = '';
  if (!WRITE_ENABLED) { $('createMsg').innerHTML = '<p class="err">KSS write ปิดอยู่ (PAY_NOTES_WRITE_ENABLED)</p>'; return; }
  if (!picked) { $('createMsg').innerHTML = '<p class="err">เลือกเจ้าหนี้</p>'; return; }
  if (!noteno || !due || !bank_id) { $('createMsg').innerHTML = '<p class="err">กรอกเลขใบวางบิล เลือกวันครบกำหนด และบัญชีธนาคาร</p>'; return; }
  if (!billnos.length) { $('createMsg').innerHTML = '<p class="err">เลือกบิลอย่างน้อย 1</p>'; return; }
  if (!uploadedPaths.length) { $('createMsg').innerHTML = '<p class="err">อัปโหลดเอกสารอย่างน้อย 1</p>'; return; }
  const { total } = selectedBillTotal();
  if (resolveDiscAmount(total) - total > 1e-9) {
    $('createMsg').innerHTML = '<p class="err">ส่วนลดมากกว่ายอดบิล</p>'; return;
  }
  try {
    const res = await api('/notes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: picked.acctno, acctname: picked.acctname, noteno, due_date: due,
        bank_id, billnos, discount_mode: discMode,
        discount_input: Number($('discInput').value || 0),
        remark: ($('noteRemark').value || '').trim()
      })
    });
    const rem = res.reminder || {};
    const discShow = Number(rem.discount_amount != null ? rem.discount_amount : resolveDiscAmount(total));
    const netShow = Math.max(0, Number(res.billamt || total) - discShow);
    $('createMsg').innerHTML = `<p class="ok">บันทึกใบวางบิลแล้ว · ${esc(res.noteno)} · จ่าย ${fmtMoney(netShow)}</p>`;
    uploadedPaths = [];
    $('billThumbs').innerHTML = '';
    $('discInput').value = '0.00';
    $('noteRemark').value = '';
    setDiscMode('amount');
    await loadBills();
    setTimeout(() => { showNotesView('list'); showTab('pending'); }, 600);
  } catch (e) {
    $('createMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    await loadBills();
  }
};

wireDatePickers(document);
setDiscMode('amount');
$('billList').innerHTML = `<tr><td colspan="4" class="empty">เลือกเจ้าหนี้ก่อน</td></tr>`;
(function boot() {
  const h = (location.hash || '').replace('#','');
  if (h === 'pending') showTab('pending');
  else if (h === 'vouchers' || h === 'awaitproof' || h === 'paid') showTab('vouchers');
  else if (h === 'create') { showTab('notes'); showNotesView('create'); }
  else showTab('notes');
})();
</script>
</body>
</html>
"""

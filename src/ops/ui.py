from __future__ import annotations

APP = "kcw-ops"
SESSION_COOKIE = "kcw_ops"

_HTML = r"""<!doctype html>
<html lang="th" data-theme="dark">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="theme-color" content="#0c1014"/>
<title>ใบสั่งซื้อ</title>
<script>
(function () {
  try {
    var t = localStorage.getItem("kcw.ops.theme");
    if (t !== "light" && t !== "dark") {
      t = window.matchMedia("(prefers-color-scheme: light)").matches ? "light" : "dark";
    }
    document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
</script>
<link rel="preconnect" href="https://fonts.googleapis.com"/>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin/>
<link href="https://fonts.googleapis.com/css2?family=Prompt:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap" rel="stylesheet"/>
<style>
:root { --acc:#3d9cf0; --ok:#3ecf8e; --down:#e25c5c; --warn:#e6b450; --on-acc:#071018; }
html[data-theme="dark"] {
  color-scheme: dark;
  --bg:#0c1014; --header:rgba(12,16,20,.96); --card:#161d26; --line:#2a3542;
  --text:#e8eef4; --muted:#8b9aab; --heading:#c5d0da; --chip:#243040; --inset:#0a0e12;
  --hl:#1e3a5f; --link:#6eb6ff;
}
html[data-theme="light"] {
  color-scheme: light;
  --bg:#f4f6f8; --header:rgba(244,246,248,.96); --card:#ffffff; --line:#d5dde6;
  --text:#1b2430; --muted:#5b6b7c; --heading:#334155; --chip:#e8eef4; --inset:#eef2f6;
  --hl:#dbeafe; --link:#1565c0;
}
* { box-sizing:border-box; }
body { margin:0; font-family: Prompt, ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
header { position:sticky; top:0; z-index:5; background:var(--header); border-bottom:1px solid var(--line); padding:.7rem 1rem .85rem; }
.brand { display:flex; align-items:center; justify-content:space-between; gap:.6rem; margin:0 0 .5rem; }
h1 { font-size:1.05rem; margin:0; }
.row { display:flex; gap:.45rem; flex-wrap:wrap; align-items:center; }
input, select, button { font: inherit; font-size:.92rem; padding:.55rem .7rem; border-radius:.55rem; border:1px solid var(--line); background:var(--chip); color:var(--text); }
input[type=search], input[type=date] { background:var(--inset); }
#q { flex: 1 1 16rem; min-width: 12rem; }
#prepare { min-width: 9rem; }
#dates { display:flex; gap:.4rem; flex: 1 1 14rem; }
#dates input { flex:1; min-width: 0; }
#lookback { gap:.3rem; }
#lookback button { padding:.4rem .55rem; font-size:.78rem; }
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:650; }
button.theme { min-width:2.6rem; }
button.linkish {
  background:none; border:none; padding:0; color:var(--link); font:inherit; font-family:ui-monospace,monospace;
  font-size:inherit; cursor:pointer; text-align:left; text-decoration:underline; text-underline-offset:2px;
}
.sites { display:flex; gap:.3rem; margin:.35rem 0 .45rem; }
.sites button { flex:1; font-weight:600; }
.sites button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); }
.modes { display:flex; gap:.3rem; overflow-x:auto; margin-top:.35rem; -webkit-overflow-scrolling:touch; scrollbar-width:none; }
.modes::-webkit-scrollbar { display:none; }
.modes button { white-space:nowrap; padding:.4rem .7rem; font-size:.8rem; border-radius:999px; flex:0 0 auto; }
.modes button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:700; }
#lookback button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); }
.badge { font-size:.72rem; padding:.15rem .45rem; border-radius:.4rem; background:var(--chip); color:var(--muted); display:inline-block; }
.badge.ok { color:var(--ok); } .badge.down { color:var(--down); }
.badge.open { background:#163328; color:var(--ok); }
.badge.billed { background:#2a3140; color:var(--muted); }
.badge.prep { background:#163328; color:var(--ok); }
.badge.part { background:#3a2a18; color:var(--warn); }
.badge.noprep { background:#2a3140; color:var(--muted); }
html[data-theme="light"] .badge.open, html[data-theme="light"] .badge.prep { background:#e8f6ee; }
html[data-theme="light"] .badge.part { background:#fff3e0; }
html[data-theme="light"] .badge.billed, html[data-theme="light"] .badge.noprep { background:#e8eef4; }
main { max-width:1200px; margin:0 auto; padding:.75rem 1rem 2.5rem; }
.meta { font-size:.8rem; color:var(--muted); margin:.15rem 0; word-break:break-word; }
.hint { font-size:.85rem; color:var(--muted); margin:0 0 .5rem; }
.list-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; border:1px solid var(--line); border-radius:.7rem; background:var(--card); }
table.list { width:100%; border-collapse:collapse; font-size:.84rem; min-width:42rem; }
table.list th, table.list td { border-bottom:1px solid var(--line); padding:.45rem .5rem; text-align:left; vertical-align:top; }
table.list th { white-space:nowrap; color:var(--muted); font-weight:600; background:var(--chip); position:sticky; top:0; z-index:1; }
table.list tr.rowclick { cursor:pointer; }
table.list tr.rowclick:hover { background:var(--inset); }
table.list td.num { text-align:right; white-space:nowrap; font-variant-numeric:tabular-nums; }
table.list td.mono { font-family:ui-monospace,monospace; white-space:nowrap; }
.product .mcode { display:block; margin-top:.15rem; font-family:ui-monospace,monospace; font-size:.72rem; color:var(--muted); }
.who { font-size:.75rem; color:var(--muted); }
.empty, .err { color:var(--muted); padding:1rem 0; }
.err { color:var(--down); }
.pager { display:flex; gap:.4rem; align-items:center; margin-top:.8rem; }
h2 { font-size:1.05rem; margin:0; }
dialog {
  width: min(960px, calc(100vw - 1.2rem));
  max-height: min(90dvh, 920px);
  margin: auto;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: .85rem;
  background: var(--card);
  color: var(--text);
  box-shadow: 0 18px 50px rgba(0,0,0,.35);
}
dialog::backdrop { background: rgba(7,10,14,.62); }
dialog.narrow { width: min(520px, calc(100vw - 1.2rem)); }
.dlg-head {
  display:flex; justify-content:space-between; align-items:flex-start; gap:.6rem;
  padding:.85rem 1rem; border-bottom:1px solid var(--line); position:sticky; top:0;
  background:var(--card); z-index:1;
}
.dlg-actions { display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }
.dlg-close { min-width: 3.2rem; }
.dlg-body { padding:.75rem 1rem 1.15rem; overflow:auto; max-height: calc(90dvh - 4.2rem); }
.tbl-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; margin-top:.55rem; }
.tbl-wrap table { min-width: 36rem; width:100%; border-collapse:collapse; font-size:.84rem; }
.tbl-wrap th, .tbl-wrap td { border-bottom:1px solid var(--line); padding:.4rem .35rem; text-align:left; vertical-align:top; }
.tbl-wrap th { white-space:nowrap; color:var(--muted); font-weight:600; }
tr.hl { background:var(--hl); }
.fields { display:grid; gap:.55rem; }
.field { display:grid; grid-template-columns:7.5rem 1fr; gap:.5rem; font-size:.9rem; }
.field .lbl { color:var(--muted); }
.field .val { min-width:0; word-break:break-word; }
.sub { border-top:1px solid var(--line); margin-top:.75rem; padding-top:.75rem; }
@media (max-width: 900px) {
  header { padding:.55rem .75rem .65rem; }
  h1 { font-size:.98rem; }
  #q { flex: 1 1 100%; min-width: 0; }
  #prepare { flex: 1 1 100%; min-width: 0; }
  #dates { flex: 1 1 100%; }
  #lookback { flex: 1 1 100%; }
  button.primary { width: 100%; }
  main { padding:.6rem .75rem 2rem; }
  dialog { width: calc(100vw - .7rem); max-height: 92dvh; border-radius:.7rem; }
  .tbl-wrap table { min-width: 40rem; }
  .field { grid-template-columns:6.5rem 1fr; }
}
@media print {
  body > *:not([data-po-print-root]) { display:none !important; }
  [data-po-print-root] {
    display:block !important; position:static !important; inset:auto !important;
    width:auto !important; max-width:none !important; max-height:none !important;
    margin:0 !important; padding:0 !important; border:0 !important; box-shadow:none !important;
    background:#fff !important; color:#000 !important; overflow:visible !important;
  }
  [data-po-print-root] .dlg-head, [data-po-print-root] .print-hide { display:none !important; }
  [data-po-print-root] .dlg-body { max-height:none !important; overflow:visible !important; padding:0 !important; }
  [data-po-print-root] .tbl-wrap { overflow:visible !important; }
  [data-po-print-root] table { min-width:0 !important; font-size:11pt; }
  [data-po-print-root] th, [data-po-print-root] td { border-color:#ccc; color:#000; }
}
</style>
</head>
<body>
<header>
  <div class="brand">
    <h1>จัดการ PO</h1>
    <span>
      <button type="button" class="theme" id="themeBtn">มืด</button>
    </span>
  </div>
  <div class="sites" id="sites">
    <button type="button" data-site="syp" id="tabSyp">PO สาขา</button>
    <button type="button" data-site="hq" id="tabHq">PO จัดซื้อ (HQ)</button>
  </div>
  <form class="row" id="f" onsubmit="go(event); return false;">
    <input id="q" type="search" placeholder="เลข PO / รหัสสินค้า / ชื่อร้าน / ACCTNO" enterkeyhint="search"/>
    <select id="prepare" onchange="go()">
      <option value="all">สถานะจัด: ทั้งหมด</option>
      <option value="not_prepared">ยังไม่จัด</option>
      <option value="partially_prepared">จัดของบางส่วน</option>
      <option value="prepared">จัดแล้ว</option>
    </select>
    <span id="dates">
      <input id="from" type="date" onchange="go()"/>
      <input id="to" type="date" onchange="go()"/>
    </span>
    <span class="row" id="lookback">
      <button type="button" data-days="30">30 วัน</button>
      <button type="button" data-days="60">60 วัน</button>
      <button type="button" data-months="3">3 เดือน</button>
      <button type="button" data-months="6">6 เดือน</button>
      <button type="button" data-months="12">1 ปี</button>
    </span>
    <button class="primary" type="submit">ค้นหา</button>
  </form>
  <div class="modes" id="modes">
    <button type="button" data-k="list" class="on">PO</button>
    <button type="button" data-k="to_be_ordered">รอสั่งซื้อ</button>
    <button type="button" data-k="pending_receive">ค้างรับ</button>
    <button type="button" data-k="partially_received">รับบางส่วน</button>
  </div>
  <div class="row" style="margin-top:.45rem">
    <span class="badge __HQBADGE__">HQ SQL __HQSQL__ · สด</span>
    <span class="badge __SYPBADGE__">SYP SQL __SYPSQL__ · สด</span>
    <span class="who">__WHO__ · ไม่ต้องอัปเดตข้อมูล</span>
  </div>
</header>
<main>
  <p class="hint" id="siteHint"></p>
  <div id="list"></div>
</main>

<dialog id="dlgPo" data-po-print-root aria-labelledby="dlgPoTitle">
  <div class="dlg-head">
    <h2 id="dlgPoTitle">ใบสั่งซื้อ</h2>
    <div class="dlg-actions print-hide">
      <select id="dlgPrepare" style="display:none">
        <option value="all">ทั้งหมด</option>
        <option value="not_prepared">ยังไม่จัด</option>
        <option value="partially_prepared">จัดของบางส่วน</option>
        <option value="prepared">จัดแล้ว</option>
      </select>
      <button type="button" id="dlgPrint" style="display:none">พิมพ์ตาราง</button>
      <button type="button" class="dlg-close" id="dlgPoClose">ปิด</button>
    </div>
  </div>
  <div class="dlg-body" id="dlgPoBody"></div>
</dialog>

<dialog id="dlgAccount" class="narrow" aria-labelledby="dlgAccountTitle">
  <div class="dlg-head">
    <h2 id="dlgAccountTitle">บัญชี</h2>
    <button type="button" class="dlg-close" id="dlgAccountClose">ปิด</button>
  </div>
  <div class="dlg-body" id="dlgAccountBody"></div>
</dialog>

<dialog id="dlgPi" aria-labelledby="dlgPiTitle">
  <div class="dlg-head">
    <h2 id="dlgPiTitle">ใบรับสินค้า</h2>
    <button type="button" class="dlg-close" id="dlgPiClose">ปิด</button>
  </div>
  <div class="dlg-body" id="dlgPiBody"></div>
</dialog>

<script>
const $ = (id) => document.getElementById(id);
let site = "__SITE__";
let mode = "list";
let offset = 0;
const limit = 50;
let poDetailCache = null;
let highlightBcode = "";

function themeLabel(t) { return t === "light" ? "สว่าง" : "มืด"; }
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  $("themeBtn").textContent = themeLabel(t);
  try { localStorage.setItem("kcw.ops.theme", t); } catch (e) {}
}
$("themeBtn").onclick = () => {
  applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
};
applyTheme(document.documentElement.getAttribute("data-theme") || "dark");

function setSite(next) {
  site = next === "hq" ? "hq" : "syp";
  $("tabSyp").classList.toggle("on", site === "syp");
  $("tabHq").classList.toggle("on", site === "hq");
  $("siteHint").textContent = site === "syp"
    ? "ใบสั่งซื้อสาขา (SYP) จาก HQ · สดจาก PARTS9"
    : "ใบสั่งซื้อที่สั่งจากซัพพลายเออร์เข้ามาที่ HQ · สดจาก PARTS9";
  syncDates();
}

document.querySelectorAll("#sites button").forEach((b) => {
  b.onclick = () => { setSite(b.dataset.site); offset = 0; load(); };
});
document.querySelectorAll("#modes button").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll("#modes button").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    mode = b.dataset.k;
    offset = 0;
    syncDates();
    load();
  };
});
document.querySelectorAll("#lookback button").forEach((b) => {
  b.onclick = () => {
    const d = new Date();
    const from = new Date(d);
    if (b.dataset.days) from.setDate(from.getDate() - Number(b.dataset.days));
    if (b.dataset.months) from.setMonth(from.getMonth() - Number(b.dataset.months));
    $("from").value = isoLocal(from);
    $("to").value = isoLocal(d);
    document.querySelectorAll("#lookback button").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    go();
  };
});
function syncDates() {
  const show = mode !== "to_be_ordered";
  $("dates").style.display = show ? "" : "none";
  $("lookback").style.display = show ? "" : "none";
  $("prepare").style.display = site === "syp" ? "" : "none";
}
function iclowLabel(st) {
  if (st === "to_be_ordered") return "รอสั่งซื้อ";
  if (st === "partially_received") return "รับบางส่วน";
  return "ค้างรับ";
}
function fmtAmt(v) {
  const n = Number(v);
  if (v === null || v === undefined || v === "" || Number.isNaN(n)) return "—";
  return n.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtQty(v) {
  const n = Number(v);
  if (v === null || v === undefined || v === "" || Number.isNaN(n)) return "—";
  if (Math.abs(n - Math.round(n)) < 1e-9) return String(Math.round(n));
  return n.toLocaleString("th-TH", { maximumFractionDigits: 3 });
}
function fmtQtyUi(qty, ui) {
  const q = fmtQty(qty);
  const u = (ui || "").trim();
  if (q === "—") return q;
  return u ? (q + " " + u) : q;
}
function billedLabel(b) { return b === "Y" ? "รับแล้ว" : "เปิด"; }
function esc(s) {
  return String(s ?? "").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function prepBadge(status) {
  const prepLabel = { prepared: "จัดแล้ว", partially_prepared: "จัดของบางส่วน", not_prepared: "ยังไม่จัด" };
  const prepClass = { prepared: "prep", partially_prepared: "part", not_prepared: "noprep" };
  const ps = status || "not_prepared";
  return "<span class='badge " + (prepClass[ps] || "noprep") + "'>" + (prepLabel[ps] || "ยังไม่จัด") + "</span>";
}
function productCell(descr, mcode) {
  const d = (descr || "").trim();
  const m = (mcode || "").trim();
  if (!d && !m) return "—";
  return "<span class='product'>" + esc(d || "—") + (m ? "<span class='mcode'>" + esc(m) + "</span>" : "") + "</span>";
}
function go(ev) {
  if (ev) ev.preventDefault();
  offset = 0;
  syncDates();
  load();
}
async function load() {
  closeAllDlg();
  $("list").innerHTML = "<div class='empty'>กำลังโหลดจาก PARTS9…</div>";
  const q = $("q").value.trim();
  const from = $("from").value;
  const to = $("to").value;
  const prepare = $("prepare").value;
  const params = new URLSearchParams({ site, limit: String(limit), offset: String(offset) });
  if (q) params.set("q", q);
  if (mode !== "to_be_ordered") {
    if (from) params.set("from", from);
    if (to) params.set("to", to);
  }
  if (mode === "list") params.set("status", "all");
  else params.set("status", mode);
  if (site === "syp") params.set("prepare", prepare);
  const url = (mode === "list" ? "/ops/api/po?" : "/ops/api/po/pending?") + params.toString();
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    renderList(data);
  } catch (e) {
    $("list").innerHTML = "<div class='err'>" + esc(e.message || e) + "</div>";
  }
}
function renderList(data) {
  const rows = data.rows || [];
  if (!rows.length) {
    $("list").innerHTML = "<div class='empty'>ไม่พบรายการในช่วงนี้</div>";
    return;
  }
  const count = data.count ?? rows.length;
  let html = "<div class='meta'>สดจาก PARTS9 · " + count + " รายการ</div><div class='list-wrap'>";
  if (mode === "list") html += renderPoTable(rows, data.site || site.toUpperCase());
  else html += renderIclowTable(rows, data.site || site.toUpperCase());
  html += "</div><div class='pager'><button " + (offset<=0?"disabled":"") + " onclick='page(-1)'>ก่อนหน้า</button>"
    + "<span class='meta'>" + (offset+1) + "–" + (offset+rows.length) + "</span>"
    + "<button " + (offset+rows.length>=count?"disabled":"") + " onclick='page(1)'>ถัดไป</button></div>";
  $("list").innerHTML = html;
}
function renderPoTable(rows, siteU) {
  const syp = siteU === "SYP";
  let h = "<table class='list'><thead><tr>"
    + "<th>DOCNO</th><th>วันที่</th><th>ACCTNO</th><th>ชื่อ</th><th class='num'>ยอด</th>";
  if (syp) h += "<th>สถานะ</th>";
  else h += "<th>สถานะ</th>";
  h += "</tr></thead><tbody>";
  rows.forEach((r, i) => {
    const ps = r.prepare_status || (r.prepared ? "prepared" : "not_prepared");
    const st = syp
      ? (prepBadge(ps) + (r.tf_billnos || r.prepare_tf_billnos
          ? "<div class='meta mono'>" + esc(r.tf_billnos || r.prepare_tf_billnos) + "</div>" : ""))
      : ("<span class='badge " + (r.open ? "open" : "billed") + "'>" + billedLabel(r.billed) + "</span>");
    h += "<tr class='rowclick' onclick='openPo(" + JSON.stringify(r.docno) + ")'>"
      + "<td class='mono'>" + esc(r.docno) + "</td>"
      + "<td>" + esc(r.docdate || "") + "</td>"
      + "<td>" + acctBtn(r.acctno, r.docno, r.acctname) + "</td>"
      + "<td>" + esc(r.acctname || "") + "</td>"
      + "<td class='num'>" + fmtAmt(r.aftertax) + "</td>"
      + "<td>" + st + "</td></tr>";
  });
  return h + "</tbody></table>";
}
function renderIclowTable(rows, siteU) {
  const hq = siteU === "HQ";
  let h = "<table class='list'><thead><tr>"
    + "<th>สถานะ</th><th>DOCNO</th><th>วันที่</th><th>BCODE</th><th>รายละเอียด</th>"
    + "<th class='num'>สั่ง</th>";
  if (mode !== "to_be_ordered") h += "<th class='num'>รับแล้ว</th>";
  h += "<th>VENDOR</th>";
  if (mode !== "to_be_ordered") h += "<th>RCVDNO</th>";
  if (siteU === "SYP") h += "<th>จัด</th>";
  h += "</tr></thead><tbody>";
  rows.forEach((r) => {
    const st = "<span class='badge open'>" + iclowLabel(r.status || mode) + "</span>";
    h += "<tr>"
      + "<td>" + st + "</td>"
      + "<td class='mono'><button type='button' class='linkish' onclick='openPo(" + JSON.stringify(r.docno)
           + "," + JSON.stringify(r.bcode || "") + ")'>" + esc(r.docno) + "</button></td>"
      + "<td>" + esc(r.docdate || "") + "</td>"
      + "<td class='mono'>" + esc(r.bcode || "") + "</td>"
      + "<td>" + productCell(r.descr || r.detail, r.mcode) + "</td>"
      + "<td class='num'>" + fmtQtyUi(r.ordered_qty || r.qty, r.ui) + "</td>";
    if (mode !== "to_be_ordered") h += "<td class='num'>" + fmtQty(r.received_qty) + "</td>";
    h += "<td>" + acctBtn(r.vendor, r.docno, null) + "</td>";
    if (mode !== "to_be_ordered") h += "<td>" + rcvdnoCell(r, hq) + "</td>";
    if (siteU === "SYP") h += "<td>" + prepBadge(r.prepare_status) + "</td>";
    h += "</tr>";
  });
  return h + "</tbody></table>";
}
function acctBtn(acctno, docno, fallbackName) {
  const a = (acctno || "").trim();
  if (!a) return "—";
  return "<button type='button' class='linkish' onclick='event.stopPropagation(); openAccount("
    + JSON.stringify(a) + "," + JSON.stringify(docno || "") + "," + JSON.stringify(fallbackName || "")
    + ")'>" + esc(a) + "</button>";
}
function rcvdnoCell(r, hq) {
  const val = (r.rcvdno || r.billno || "").trim();
  if (!val) return "—";
  const missing = !!r.pimas_link_missing;
  const matched = (r.pimas_matched_billno || "").trim();
  const method = r.pimas_match_method || "";
  const pattern = method === "pattern" || method === "mixed";
  if (!hq || missing) {
    return "<span class='mono'>" + esc(val)
      + (hq && missing ? "<div class='meta'>(ไม่พบลิงก์ PIMAS)</div>" : "")
      + "</span>";
  }
  const key = matched || val;
  const tip = pattern && matched
    ? ("เปิดใบรับที่จับคู่แบบ implied: " + matched)
    : "เปิดรายละเอียดใบรับ (PIMAS/PIDET)";
  return "<button type='button' class='linkish' title='" + esc(tip) + "' onclick='openPi("
    + JSON.stringify(key) + ")'>" + esc(val) + "</button>"
    + (pattern && matched ? "<div class='meta'>→ " + esc(matched) + "</div>" : "");
}
function page(dir) {
  offset = Math.max(0, offset + dir * limit);
  load();
}
function closeDlg(el) {
  if (el && el.open) el.close();
}
function closeAllDlg() {
  closeDlg($("dlgPo"));
  closeDlg($("dlgAccount"));
  closeDlg($("dlgPi"));
}
function openModal(el) {
  if (el && !el.open && typeof el.showModal === "function") el.showModal();
}
function bindOutsideClose(dlg) {
  dlg.addEventListener("click", (ev) => {
    const box = dlg.getBoundingClientRect();
    const outside = ev.clientX < box.left || ev.clientX > box.right || ev.clientY < box.top || ev.clientY > box.bottom;
    if (ev.target === dlg || outside) closeDlg(dlg);
  });
}
bindOutsideClose($("dlgPo"));
bindOutsideClose($("dlgAccount"));
bindOutsideClose($("dlgPi"));
$("dlgPoClose").onclick = () => closeDlg($("dlgPo"));
$("dlgAccountClose").onclick = () => closeDlg($("dlgAccount"));
$("dlgPiClose").onclick = () => closeDlg($("dlgPi"));

async function openPo(docno, bcode) {
  if (!docno) return;
  highlightBcode = (bcode || "").trim();
  $("dlgPoTitle").textContent = docno;
  $("dlgPoBody").innerHTML = "<div class='empty'>กำลังเปิด " + esc(docno) + "…</div>";
  $("dlgPrepare").style.display = "none";
  $("dlgPrint").style.display = "none";
  openModal($("dlgPo"));
  try {
    const res = await fetch("/ops/api/po/" + encodeURIComponent(docno) + "?site=" + site, { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    poDetailCache = data;
    $("dlgPrepare").value = "all";
    renderPoDetail();
  } catch (e) {
    poDetailCache = null;
    $("dlgPoBody").innerHTML = "<div class='err'>" + esc(e.message || e) + "</div>";
  }
}
$("dlgPrepare").onchange = () => renderPoDetail();
$("dlgPrint").onclick = () => {
  window.print();
};
function renderPoDetail() {
  const data = poDetailCache;
  if (!data) return;
  const h = data.header || {};
  const allLines = data.lines || [];
  const pf = $("dlgPrepare").value;
  const lines = pf === "all" ? allLines : allLines.filter((ln) => (ln.prepare_line_status || "not_prepared") === pf);
  $("dlgPoTitle").textContent = h.docno || data.docno || "ใบสั่งซื้อ";
  const isSyp = (data.site || site.toUpperCase()) === "SYP";
  $("dlgPrepare").style.display = isSyp ? "" : "none";
  $("dlgPrint").style.display = isSyp ? "" : "none";

  let html = "<div class='meta'>" + esc(h.docdate||"") + " · " + esc(h.acctname||"") + " · " + billedLabel(h.billed);
  if (isSyp) {
    html += " · " + prepBadge(data.prepare_status);
    const n = data.prepared_line_count, t = data.prepare_line_count;
    if (t) html += " · จัดแล้ว " + n + "/" + t + " รายการ";
    if (highlightBcode) {
      const hl = allLines.find((ln) => (ln.bcode || "") === highlightBcode);
      html += "<div class='meta'>สถานะ BCODE <span class='mono'>" + esc(highlightBcode) + "</span> "
        + prepBadge(hl && hl.prepare_line_status) + "</div>";
    }
    if (pf !== "all") html += "<div class='meta'>แสดง " + lines.length + " จาก " + allLines.length + " รายการ</div>";
    html += "</div>";
    html += data.tf_billnos
      ? "<div class='meta'>เลขที่บิลโอน: <span class='mono'>" + esc(data.tf_billnos) + "</span></div>"
      : "<div class='meta'>ยังไม่พบบิล TF/TFV ที่ REMARKS อ้างเลข PO นี้</div>";
  } else {
    html += " · ยอด " + fmtAmt(h.aftertax) + "</div>";
    if (h.acctno) html += "<div class='meta'>ACCTNO " + acctBtn(h.acctno, h.docno, h.acctname) + "</div>";
  }
  html += "<div class='tbl-wrap'>";
  if (isSyp) {
    html += "<table><thead><tr><th>สถานะ</th><th>BCODE</th><th>รายละเอียด</th><th>ที่เก็บ HQ</th><th>คงเหลือ HQ</th><th>จำนวน TF</th><th>จำนวนสั่ง</th></tr></thead><tbody>";
    lines.forEach((ln) => {
      const loc = [ln.hq_location1 || ln.location1, ln.hq_location2 || ln.location2].filter(Boolean).join(" / ");
      const hqQty = ln.hq_qty != null && ln.hq_qty !== "" ? ln.hq_qty : ln.qtyoh2;
      const tfQty = ln.tf_qty != null && ln.tf_qty !== "" ? ln.tf_qty : ln.prepared_qty;
      const hl = highlightBcode && (ln.bcode || "") === highlightBcode;
      html += "<tr" + (hl ? " class='hl' id='hlRow'" : "") + "><td>" + prepBadge(ln.prepare_line_status) + "</td><td class='mono'>" + esc(ln.bcode||"")
        + "</td><td>" + productCell(ln.detail, ln.mcode) + "</td><td>" + esc(loc||"—") + "</td><td>" + fmtQty(hqQty)
        + "</td><td>" + fmtQty(tfQty) + "</td><td>" + fmtQtyUi(ln.qty, ln.ui) + "</td></tr>";
    });
  } else {
    html += "<table><thead><tr><th>BCODE</th><th>รายละเอียด</th><th>จำนวน</th><th>ราคา</th><th>จำนวนเงิน</th></tr></thead><tbody>";
    lines.forEach((ln) => {
      html += "<tr><td class='mono'>" + esc(ln.bcode||"") + "</td><td>" + productCell(ln.detail, ln.mcode) + "</td><td>" + fmtQtyUi(ln.qty, ln.ui)
        + "</td><td>" + fmtAmt(ln.price) + "</td><td>" + fmtAmt(ln.amount) + "</td></tr>";
    });
  }
  html += "</tbody></table></div>";
  $("dlgPoBody").innerHTML = html;
  const hlEl = document.getElementById("hlRow");
  if (hlEl && typeof hlEl.scrollIntoView === "function") {
    setTimeout(() => hlEl.scrollIntoView({ block: "center", behavior: "smooth" }), 50);
  }
}

async function openAccount(acctno, docno, fallbackName) {
  if (!acctno) return;
  $("dlgAccountTitle").textContent = "บัญชี " + acctno;
  $("dlgAccountBody").innerHTML = "<div class='empty'>กำลังโหลด…</div>";
  openModal($("dlgAccount"));
  try {
    const params = new URLSearchParams({ site });
    if (docno) params.set("docno", docno);
    const res = await fetch("/ops/api/po/account/" + encodeURIComponent(acctno) + "?" + params, { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    const a = data.account || {};
    const name = a.acctname || fallbackName || (a.po_snapshot && a.po_snapshot.acctname) || "";
    $("dlgAccountTitle").innerHTML = "บัญชี " + esc(acctno)
      + (name ? "<div class='meta' style='font-weight:400;margin-top:.25rem'>" + esc(name) + "</div>" : "");
    let html = "<div class='fields'>";
    const fields = [
      ["รหัสบัญชี", a.acctno || acctno],
      ["ชื่อ", a.acctname || fallbackName],
      ["ที่อยู่ 1", a.addr1],
      ["ที่อยู่ 2", a.addr2],
      ["โทรศัพท์", a.phone],
      ["เลขผู้เสียภาษี", a.tax_id],
      ["แฟ็กซ์", a.fax],
      ["ผู้ติดต่อ", a.contact],
      ["อีเมล", a.email],
      ["เครดิต (วัน)", a.term],
      ["หมายเหตุ", a.remarks],
    ];
    fields.forEach(([lbl, val]) => {
      html += "<div class='field'><div class='lbl'>" + esc(lbl) + "</div><div class='val'>" + esc(val || "—") + "</div></div>";
    });
    if (a.source === "po_only") {
      html += "<p class='meta'>ไม่พบใน APMAS — แสดงจากข้อมูลบนใบ PO</p>";
    }
    if (a.po_snapshot) {
      const s = a.po_snapshot;
      html += "<div class='sub'><div class='meta' style='font-weight:600;margin-bottom:.4rem'>บนใบ PO " + esc(s.docno) + "</div>";
      [["ชื่อบนใบ", s.acctname], ["ที่อยู่ 1", s.addr1], ["ที่อยู่ 2", s.addr2], ["ATTN", s.attn]].forEach(([lbl, val]) => {
        html += "<div class='field'><div class='lbl'>" + esc(lbl) + "</div><div class='val'>" + esc(val || "—") + "</div></div>";
      });
      html += "</div>";
    }
    html += "</div>";
    $("dlgAccountBody").innerHTML = html;
  } catch (e) {
    $("dlgAccountBody").innerHTML = "<div class='err'>" + esc(e.message || e) + "</div>";
  }
}

async function openPi(billno) {
  if (!billno) return;
  $("dlgPiTitle").textContent = billno;
  $("dlgPiBody").innerHTML = "<div class='empty'>กำลังเปิดใบรับ…</div>";
  openModal($("dlgPi"));
  try {
    const res = await fetch("/ops/api/po/pi/" + encodeURIComponent(billno), { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    const h = data.header || {};
    $("dlgPiTitle").textContent = "ใบรับ " + (h.billno || billno);
    let html = "<div class='meta'>" + esc(h.billdate||"") + " · " + esc(h.acctname||h.acctno||"")
      + " · ยอด " + fmtAmt(h.aftertax);
    if (h.po) html += " · PO " + esc(h.po);
    if (h.matched_rcvdno) html += " · จับคู่จาก RCVDNO " + esc(h.matched_rcvdno);
    if (h.match_method) html += " (" + esc(h.match_method) + ")";
    html += "</div><div class='tbl-wrap'><table><thead><tr><th>BCODE</th><th>รายละเอียด</th><th>จำนวน</th><th>ราคา</th><th>จำนวนเงิน</th></tr></thead><tbody>";
    (data.lines || []).forEach((ln) => {
      html += "<tr><td class='mono'>" + esc(ln.bcode||"") + "</td><td>" + productCell(ln.detail, ln.mcode)
        + "</td><td>" + fmtQtyUi(ln.qty, ln.ui) + "</td><td>" + fmtAmt(ln.price) + "</td><td>" + fmtAmt(ln.amount) + "</td></tr>";
    });
    html += "</tbody></table></div>";
    $("dlgPiBody").innerHTML = html;
  } catch (e) {
    $("dlgPiBody").innerHTML = "<div class='err'>" + esc(e.message || e) + "</div>";
  }
}

function isoLocal(d) {
  const y = d.getFullYear();
  const m = String(d.getMonth()+1).padStart(2,'0');
  const day = String(d.getDate()).padStart(2,'0');
  return y + "-" + m + "-" + day;
}
const today = new Date();
const from = new Date(today); from.setDate(from.getDate()-30);
$("from").value = isoLocal(from);
$("to").value = isoLocal(today);
document.querySelector('#lookback button[data-days="30"]').classList.add("on");
setSite(site);
load();
</script>
</body>
</html>
"""


def page(*, user_name: str, site: str, probes: dict) -> str:
    site_key = (site or "syp").strip().lower()
    if site_key not in ("hq", "syp"):
        site_key = "syp"
    hq = (probes or {}).get("hq") or {}
    syp = (probes or {}).get("syp") or {}
    html = _HTML
    html = html.replace("__SITE__", site_key)
    html = html.replace("__HQBADGE__", "ok" if hq.get("ok") else "down")
    html = html.replace("__SYPBADGE__", "ok" if syp.get("ok") else "down")
    html = html.replace("__HQSQL__", "ok" if hq.get("ok") else "down")
    html = html.replace("__SYPSQL__", "ok" if syp.get("ok") else "down")
    html = html.replace("__WHO__", user_name or "")
    return html

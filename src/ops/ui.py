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
}
html[data-theme="light"] {
  color-scheme: light;
  --bg:#f4f6f8; --header:rgba(244,246,248,.96); --card:#ffffff; --line:#d5dde6;
  --text:#1b2430; --muted:#5b6b7c; --heading:#334155; --chip:#e8eef4; --inset:#eef2f6;
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
#site, #prepare { min-width: 7.5rem; }
#dates { display:flex; gap:.4rem; flex: 1 1 14rem; }
#dates input { flex:1; min-width: 0; }
#lookback { gap:.3rem; }
#lookback button { padding:.4rem .55rem; font-size:.78rem; }
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:650; }
button.theme { min-width:2.6rem; }
.modes { display:flex; gap:.3rem; overflow-x:auto; margin-top:.5rem; -webkit-overflow-scrolling:touch; scrollbar-width:none; }
.modes::-webkit-scrollbar { display:none; }
.modes button { white-space:nowrap; padding:.4rem .7rem; font-size:.8rem; border-radius:999px; flex:0 0 auto; }
.modes button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:700; }
#lookback button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); }
.badge { font-size:.72rem; padding:.15rem .45rem; border-radius:.4rem; background:var(--chip); color:var(--muted); }
.badge.ok { color:var(--ok); } .badge.down { color:var(--down); }
.badge.open { background:#163328; color:var(--ok); }
.badge.billed { background:#2a3140; color:var(--muted); }
.badge.prep { background:#163328; color:var(--ok); }
.badge.part { background:#3a2a18; color:var(--warn); }
.badge.noprep { background:#2a3140; color:var(--muted); }
html[data-theme="light"] .badge.open { background:#e8f6ee; }
html[data-theme="light"] .badge.prep { background:#e8f6ee; }
html[data-theme="light"] .badge.part { background:#fff3e0; }
main { max-width:1100px; margin:0 auto; padding:.75rem 1rem 2.5rem; }
.cards { display:grid; grid-template-columns:1fr; gap:.5rem; margin-top:.45rem; }
.card { display:block; width:100%; text-align:left; padding:.75rem; background:var(--card); border:1px solid var(--line); border-radius:.7rem; color:inherit; cursor:pointer; }
.card .t { font-weight:650; display:flex; flex-wrap:wrap; gap:.25rem .4rem; align-items:center; }
.meta { font-size:.8rem; color:var(--muted); margin-top:.15rem; word-break:break-word; }
table { width:100%; border-collapse:collapse; font-size:.84rem; }
th, td { border-bottom:1px solid var(--line); padding:.4rem .35rem; text-align:left; vertical-align:top; }
th { white-space:nowrap; color:var(--muted); font-weight:600; }
.who { font-size:.75rem; color:var(--muted); }
.empty, .err { color:var(--muted); padding:1rem 0; }
.err { color:var(--down); }
.pager { display:flex; gap:.4rem; align-items:center; margin-top:.8rem; }
h2 { font-size:1.05rem; margin:0; }
dialog#dlg {
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
dialog#dlg::backdrop { background: rgba(7,10,14,.62); }
.dlg-head {
  display:flex; justify-content:space-between; align-items:flex-start; gap:.6rem;
  padding:.85rem 1rem; border-bottom:1px solid var(--line); position:sticky; top:0;
  background:var(--card); z-index:1;
}
.dlg-close { min-width: 3.2rem; }
.dlg-body { padding:.75rem 1rem 1.15rem; overflow:auto; max-height: calc(90dvh - 4.2rem); }
.tbl-wrap { overflow-x:auto; -webkit-overflow-scrolling:touch; margin-top:.55rem; }
.tbl-wrap table { min-width: 36rem; }
@media (min-width: 720px) and (max-width: 1100px) {
  .cards { grid-template-columns: 1fr 1fr; }
}
@media (max-width: 900px) {
  header { padding:.55rem .75rem .65rem; }
  h1 { font-size:.98rem; }
  #q { flex: 1 1 100%; min-width: 0; }
  #site, #prepare { flex: 1 1 calc(50% - .3rem); min-width: 0; }
  #dates { flex: 1 1 100%; }
  #lookback { flex: 1 1 100%; }
  button.primary { width: 100%; }
  main { padding:.6rem .75rem 2rem; }
  .card { padding:.7rem .75rem; }
  dialog#dlg { width: calc(100vw - .7rem); max-height: 92dvh; border-radius:.7rem; }
  .tbl-wrap table { min-width: 40rem; }
}
</style>
</head>
<body>
<header>
  <div class="brand">
    <h1>ใบสั่งซื้อ</h1>
    <span>
      <button type="button" class="theme" id="themeBtn">มืด</button>
    </span>
  </div>
  <form class="row" id="f" onsubmit="go(event); return false;">
    <input id="q" type="search" placeholder="เลข PO / รหัสสินค้า / ชื่อร้าน" enterkeyhint="search"/>
    <select id="site" onchange="go()">
      <option value="hq" __HQSEL__>HQ</option>
      <option value="syp" __SYPSEL__>SYP</option>
    </select>
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
  <div id="list"></div>
</main>
<dialog id="dlg" aria-labelledby="dlgTitle">
  <div class="dlg-head">
    <h2 id="dlgTitle">ใบสั่งซื้อ</h2>
    <button type="button" class="dlg-close" id="dlgClose">ปิด</button>
  </div>
  <div class="dlg-body" id="dlgBody"></div>
</dialog>
<script>
const $ = (id) => document.getElementById(id);
let mode = "list";
let offset = 0;
const limit = 50;

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
  $("prepare").style.display = $("site").value === "syp" ? "" : "none";
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

function go(ev) {
  if (ev) ev.preventDefault();
  offset = 0;
  syncDates();
  load();
}

async function load() {
  closeDlg();
  $("list").innerHTML = "<div class='empty'>กำลังโหลดจาก PARTS9…</div>";
  const site = $("site").value;
  const q = $("q").value.trim();
  const from = $("from").value;
  const to = $("to").value;
  const status = "all";
  const prepare = $("prepare").value;
  const params = new URLSearchParams({ site, limit: String(limit), offset: String(offset) });
  if (q) params.set("q", q);
  if (mode !== "to_be_ordered") {
    if (from) params.set("from", from);
    if (to) params.set("to", to);
  }
  if (mode === "list") params.set("status", status);
  else params.set("status", mode);
  if (site === "syp") params.set("prepare", prepare);
  const url = (mode === "list" ? "/ops/api/po?" : "/ops/api/po/pending?") + params.toString();
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    renderList(data);
  } catch (e) {
    $("list").innerHTML = "<div class='err'>" + (e.message || e) + "</div>";
  }
}

function renderList(data) {
  const rows = data.rows || [];
  if (!rows.length) {
    $("list").innerHTML = "<div class='empty'>ไม่พบรายการในช่วงนี้</div>";
    return;
  }
  const count = data.count ?? rows.length;
  let html = "<div class='meta'>สดจาก PARTS9 · " + count + " รายการ</div><div class='cards'>";
    const prepLabel = {
      prepared: "จัดแล้ว",
      partially_prepared: "จัดของบางส่วน",
      not_prepared: "ยังไม่จัด",
    };
    const prepClass = {
      prepared: "prep",
      partially_prepared: "part",
      not_prepared: "noprep",
    };
    rows.forEach((r) => {
      const ps = r.prepare_status || (r.prepared ? "prepared" : "not_prepared");
      const prep = (data.site === "SYP")
        ? "<span class='badge " + (prepClass[ps] || "noprep") + "'>" + (prepLabel[ps] || "ยังไม่จัด") + "</span>"
        : "";
      const st = mode === "list"
        ? (data.site === "SYP" ? "" : "<span class='badge " + (r.open ? "open" : "billed") + "'>" + billedLabel(r.billed) + "</span>")
        : "<span class='badge open'>" + iclowLabel(r.status || mode) + "</span>";
      const tf = r.tf_billnos || r.prepare_tf_billnos ? " · TF " + (r.tf_billnos || r.prepare_tf_billnos) : "";
      const lineBits = mode === "list"
        ? ""
        : (" · " + (r.bcode || "") + " · " + (r.descr || "") + " · สั่ง " + fmtQtyUi(r.ordered_qty || r.qty, r.ui)
           + (mode === "partially_received" ? " รับแล้ว " + fmtQty(r.received_qty) : ""));
      html += "<button class='card' onclick='openDoc(" + JSON.stringify(r.docno) + ")'>"
        + "<div class='t'>" + (r.docno || "") + " " + st + " " + prep + "</div>"
        + "<div class='meta'>" + (r.docdate || "") + " · " + (r.acctname || r.vendor || "") + " · " + fmtAmt(r.aftertax || r.amount) + tf + lineBits + "</div>"
        + "</button>";
    });
  html += "</div><div class='pager'><button " + (offset<=0?"disabled":"") + " onclick='page(-1)'>ก่อนหน้า</button>"
    + "<span class='meta'>" + (offset+1) + "–" + (offset+rows.length) + "</span>"
    + "<button " + (offset+rows.length>=count?"disabled":"") + " onclick='page(1)'>ถัดไป</button></div>";
  $("list").innerHTML = html;
}

function page(dir) {
  offset = Math.max(0, offset + dir * limit);
  load();
}

function closeDlg() {
  const dlg = $("dlg");
  if (dlg && dlg.open) dlg.close();
}

function openDlg() {
  const dlg = $("dlg");
  if (dlg && !dlg.open && typeof dlg.showModal === "function") dlg.showModal();
}

async function openDoc(docno) {
  if (!docno) return;
  $("dlgTitle").textContent = docno;
  $("dlgBody").innerHTML = "<div class='empty'>กำลังเปิด " + docno + "…</div>";
  openDlg();
  const site = $("site").value;
  try {
    const res = await fetch("/ops/api/po/" + encodeURIComponent(docno) + "?site=" + site, { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    renderDetail(data);
  } catch (e) {
    $("dlgBody").innerHTML = "<div class='err'>" + (e.message || e) + "</div>";
  }
}

function prepBadge(status) {
  const prepLabel = { prepared: "จัดแล้ว", partially_prepared: "จัดของบางส่วน", not_prepared: "ยังไม่จัด" };
  const prepClass = { prepared: "prep", partially_prepared: "part", not_prepared: "noprep" };
  const ps = status || "not_prepared";
  return "<span class='badge " + (prepClass[ps] || "noprep") + "'>" + (prepLabel[ps] || "ยังไม่จัด") + "</span>";
}

function renderDetail(data) {
  const h = data.header || {};
  const lines = data.lines || [];
  $("dlgTitle").textContent = h.docno || data.docno || "ใบสั่งซื้อ";
  let html = "<div class='meta'>" + (h.docdate||"") + " · " + (h.acctname||"") + " · " + billedLabel(h.billed);
  if (data.site === "SYP") {
    html += " · " + prepBadge(data.prepare_status);
    const n = data.prepared_line_count, t = data.prepare_line_count;
    if (t) html += " · จัดแล้ว " + n + "/" + t + " รายการ";
    html += "</div>";
    html += data.tf_billnos
      ? "<div class='meta'>เลขที่บิลโอน: " + data.tf_billnos + "</div>"
      : "<div class='meta'>ยังไม่พบบิล TF/TFV ที่ REMARKS อ้างเลข PO นี้</div>";
  } else {
    html += " · ยอด " + fmtAmt(h.aftertax) + "</div>";
  }
  html += "<div class='tbl-wrap'>";
  if (data.site === "SYP") {
    html += "<table><thead><tr><th>สถานะ</th><th>รหัส</th><th>รายการ</th><th>ที่เก็บ HQ</th><th>คงเหลือ HQ</th><th>จำนวน TF</th><th>จำนวนสั่ง</th></tr></thead><tbody>";
    lines.forEach((ln) => {
      const loc = [ln.hq_location1 || ln.location1, ln.hq_location2 || ln.location2].filter(Boolean).join(" / ");
      const hqQty = ln.hq_qty != null && ln.hq_qty !== "" ? ln.hq_qty : ln.qtyoh2;
      const tfQty = ln.tf_qty != null && ln.tf_qty !== "" ? ln.tf_qty : ln.prepared_qty;
      html += "<tr><td>" + prepBadge(ln.prepare_line_status) + "</td><td>" + (ln.bcode||"")
        + "</td><td>" + (ln.detail||"") + "</td><td>" + (loc||"—") + "</td><td>" + fmtQty(hqQty)
        + "</td><td>" + fmtQty(tfQty) + "</td><td>" + fmtQtyUi(ln.qty, ln.ui) + "</td></tr>";
    });
  } else {
    html += "<table><thead><tr><th>รหัส</th><th>รายการ</th><th>จำนวน</th><th>ราคา</th><th>จำนวนเงิน</th></tr></thead><tbody>";
    lines.forEach((ln) => {
      html += "<tr><td>" + (ln.bcode||"") + "</td><td>" + (ln.detail||"") + "</td><td>" + fmtQtyUi(ln.qty, ln.ui)
        + "</td><td>" + fmtAmt(ln.price) + "</td><td>" + fmtAmt(ln.amount) + "</td></tr>";
    });
  }
  html += "</tbody></table></div>";
  $("dlgBody").innerHTML = html;
}

$("dlgClose").onclick = closeDlg;
$("dlg").addEventListener("click", (ev) => {
  const box = $("dlg").getBoundingClientRect();
  const outside = ev.clientX < box.left || ev.clientX > box.right || ev.clientY < box.top || ev.clientY > box.bottom;
  if (ev.target === $("dlg") || outside) closeDlg();
});

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
syncDates();
load();
</script>
</body>
</html>
"""


def page(*, user_name: str, site: str, probes: dict) -> str:
    site_key = (site or "syp").strip().lower()
    hq = (probes or {}).get("hq") or {}
    syp = (probes or {}).get("syp") or {}
    html = _HTML
    html = html.replace("__HQSEL__", "selected" if site_key != "syp" else "")
    html = html.replace("__SYPSEL__", "selected" if site_key == "syp" else "")
    html = html.replace("__HQBADGE__", "ok" if hq.get("ok") else "down")
    html = html.replace("__SYPBADGE__", "ok" if syp.get("ok") else "down")
    html = html.replace("__HQSQL__", "ok" if hq.get("ok") else "down")
    html = html.replace("__SYPSQL__", "ok" if syp.get("ok") else "down")
    html = html.replace("__WHO__", user_name or "")
    return html

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
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:650; }
button.theme { min-width:2.6rem; }
.modes { display:flex; gap:.3rem; overflow-x:auto; margin-top:.5rem; }
.modes button { white-space:nowrap; padding:.4rem .7rem; font-size:.8rem; border-radius:999px; }
.modes button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:700; }
.badge { font-size:.72rem; padding:.15rem .45rem; border-radius:.4rem; background:var(--chip); color:var(--muted); }
.badge.ok { color:var(--ok); } .badge.down { color:var(--down); }
.badge.open { background:#163328; color:var(--ok); }
.badge.billed { background:#2a3140; color:var(--muted); }
.badge.prep { background:#163328; color:var(--ok); }
.badge.noprep { background:#2a3140; color:var(--muted); }
html[data-theme="light"] .badge.open { background:#e8f6ee; }
html[data-theme="light"] .badge.prep { background:#e8f6ee; }
main { max-width:1100px; margin:0 auto; padding:.75rem 1rem 2.5rem; }
.card { display:block; width:100%; text-align:left; padding:.75rem; margin-bottom:.5rem; background:var(--card); border:1px solid var(--line); border-radius:.7rem; color:inherit; cursor:pointer; }
.card .t { font-weight:650; }
.meta { font-size:.8rem; color:var(--muted); margin-top:.15rem; }
table { width:100%; border-collapse:collapse; font-size:.84rem; }
th, td { border-bottom:1px solid var(--line); padding:.35rem .25rem; text-align:left; vertical-align:top; }
.who { font-size:.75rem; color:var(--muted); }
.empty, .err { color:var(--muted); padding:1rem 0; }
.err { color:var(--down); }
.pager { display:flex; gap:.4rem; align-items:center; margin-top:.8rem; }
h2 { font-size:1.05rem; margin:.2rem 0 .5rem; }
.detail-head { display:flex; justify-content:space-between; gap:.5rem; flex-wrap:wrap; align-items:center; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <h1>ใบสั่งซื้อ</h1>
    <button type="button" class="theme" id="themeBtn">มืด</button>
  </div>
  <form class="row" id="f" onsubmit="go(event); return false;">
    <input id="q" type="search" placeholder="เลข PO / ชื่อร้าน / รหัสลูกค้า" enterkeyhint="search"/>
    <select id="site">
      <option value="hq" __HQSEL__>HQ</option>
      <option value="syp" __SYPSEL__>SYP</option>
    </select>
    <select id="status">
      <option value="open">เปิด</option>
      <option value="all">ทั้งหมด</option>
      <option value="billed">รับแล้ว</option>
    </select>
    <input id="from" type="date"/>
    <input id="to" type="date"/>
    <button class="primary" type="submit">ค้นหา</button>
  </form>
  <div class="modes" id="modes">
    <button type="button" data-k="list" class="on">ใบสั่งซื้อ</button>
    <button type="button" data-k="pending">ค้างรับ</button>
  </div>
  <div class="row" style="margin-top:.45rem">
    <span class="badge __HQBADGE__">HQ SQL __HQSQL__ · สด</span>
    <span class="badge __SYPBADGE__">SYP SQL __SYPSQL__ · สด</span>
    <span class="who">__WHO__ · ไม่ต้องอัปเดตข้อมูล</span>
  </div>
</header>
<main>
  <div id="list"></div>
  <div id="detail"></div>
</main>
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
    load();
  };
});

function fmtAmt(v) {
  const n = Number(v);
  if (v === null || v === undefined || v === "" || Number.isNaN(n)) return "—";
  return n.toLocaleString("th-TH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function fmtQty(v) {
  const n = Number(v);
  if (v === null || v === undefined || v === "" || Number.isNaN(n)) return "—";
  return n.toLocaleString("th-TH", { maximumFractionDigits: 3 });
}
function billedLabel(b) { return b === "Y" ? "รับแล้ว" : "เปิด"; }

function go(ev) {
  if (ev) ev.preventDefault();
  offset = 0;
  load();
}

async function load() {
  $("detail").innerHTML = "";
  $("list").innerHTML = "<div class='empty'>กำลังโหลดจาก PARTS9…</div>";
  const site = $("site").value;
  const q = $("q").value.trim();
  const from = $("from").value;
  const to = $("to").value;
  const status = $("status").value;
  const params = new URLSearchParams({ site, limit: String(limit), offset: String(offset) });
  if (q) params.set("q", q);
  if (from) params.set("from", from);
  if (to) params.set("to", to);
  if (mode === "list") params.set("status", status);
  const url = (mode === "pending" ? "/ops/api/po/pending?" : "/ops/api/po?") + params.toString();
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
  let html = "<div class='meta'>สดจาก PARTS9 · " + count + " รายการ</div>";
  rows.forEach((r) => {
    const prep = r.prepared ? "<span class='badge prep'>จัดแล้ว</span>" : (data.site === "SYP" && mode === "list" ? "<span class='badge noprep'>ยังไม่จัด</span>" : "");
    const st = mode === "pending"
      ? "<span class='badge open'>ค้างรับ</span>"
      : "<span class='badge " + (r.open ? "open" : "billed") + "'>" + billedLabel(r.billed) + "</span>";
    html += "<button class='card' onclick='openDoc(" + JSON.stringify(r.docno) + ")'>"
      + "<div class='t'>" + (r.docno || "") + " " + st + " " + prep + "</div>"
      + "<div class='meta'>" + (r.docdate || "") + " · " + (r.acctname || r.vendor || "") + " · " + fmtAmt(r.aftertax || r.amount) + "</div>"
      + "</button>";
  });
  html += "<div class='pager'><button " + (offset<=0?"disabled":"") + " onclick='page(-1)'>ก่อนหน้า</button>"
    + "<span class='meta'>" + (offset+1) + "–" + (offset+rows.length) + "</span>"
    + "<button " + (offset+rows.length>=count?"disabled":"") + " onclick='page(1)'>ถัดไป</button></div>";
  $("list").innerHTML = html;
}

function page(dir) {
  offset = Math.max(0, offset + dir * limit);
  load();
}

async function openDoc(docno) {
  $("detail").innerHTML = "<div class='empty'>กำลังเปิด " + docno + "…</div>";
  const site = $("site").value;
  try {
    const res = await fetch("/ops/api/po/" + encodeURIComponent(docno) + "?site=" + site, { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    renderDetail(data);
  } catch (e) {
    $("detail").innerHTML = "<div class='err'>" + (e.message || e) + "</div>";
  }
}

async function togglePrep(docno, prepared) {
  const site = $("site").value;
  try {
    const res = await fetch("/ops/api/po/" + encodeURIComponent(docno) + "/prepare?site=" + site, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "same-origin",
      body: JSON.stringify({ prepared }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    openDoc(docno);
    load();
  } catch (e) {
    alert(e.message || e);
  }
}

function renderDetail(data) {
  const h = data.header || {};
  const lines = data.lines || [];
  let html = "<div class='detail-head'><h2>" + (h.docno || data.docno) + "</h2>";
  if (data.site === "SYP") {
    const on = !!data.prepared;
    html += "<button class='primary' onclick='togglePrep(" + JSON.stringify(data.docno) + "," + (!on) + ")'>"
      + (on ? "ยกเลิกจัดแล้ว" : "ทำเครื่องหมายจัดแล้ว") + "</button>";
  }
  html += "</div>";
  html += "<div class='meta'>" + (h.docdate||"") + " · " + (h.acctname||"") + " · " + billedLabel(h.billed)
    + (data.prepared ? " · จัดแล้ว" : "") + "</div>";
  html += "<table><thead><tr><th>รหัส</th><th>รายการ</th><th>จำนวน</th><th>ที่เก็บ HQ</th><th>คงเหลือ HQ</th><th>เงิน</th></tr></thead><tbody>";
  lines.forEach((ln) => {
    const loc = [ln.hq_location1 || ln.location1, ln.hq_location2 || ln.location2].filter(Boolean).join(" / ");
    const qty = ln.hq_qty != null && ln.hq_qty !== "" ? ln.hq_qty : ln.qtyoh2;
    html += "<tr><td>" + (ln.bcode||"") + "</td><td>" + (ln.detail||"") + "</td><td>" + fmtQty(ln.qty)
      + "</td><td>" + (loc||"—") + "</td><td>" + fmtQty(qty) + "</td><td>" + fmtAmt(ln.amount) + "</td></tr>";
  });
  html += "</tbody></table>";
  $("detail").innerHTML = html;
  $("detail").scrollIntoView({ behavior: "smooth", block: "start" });
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
load();
</script>
</body>
</html>
"""


def page(*, user_name: str, site: str, probes: dict) -> str:
    site_key = (site or "hq").strip().lower()
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

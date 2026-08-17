from __future__ import annotations

_HTML = r"""<!doctype html>
<html lang="th" data-theme="dark">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="theme-color" content="#0c1014"/>
<title>ภาพรวมยอดขาย</title>
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
  --text:#e8eef4; --muted:#8b9aab; --chip:#243040; --inset:#0a0e12;
}
html[data-theme="light"] {
  color-scheme: light;
  --bg:#f4f6f8; --header:rgba(244,246,248,.96); --card:#ffffff; --line:#d5dde6;
  --text:#1b2430; --muted:#5b6b7c; --chip:#e8eef4; --inset:#eef2f6;
}
* { box-sizing:border-box; }
body { margin:0; font-family: Prompt, ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
header { position:sticky; top:0; z-index:5; background:var(--header); border-bottom:1px solid var(--line); padding:.7rem 1rem .85rem; }
.brand { display:flex; align-items:center; justify-content:space-between; gap:.6rem; margin:0 0 .5rem; }
h1 { font-size:1.05rem; margin:0; }
nav a { color:var(--acc); text-decoration:none; font-size:.86rem; margin-right:.7rem; }
.row { display:flex; gap:.45rem; flex-wrap:wrap; align-items:center; }
input, select, button { font: inherit; font-size:.92rem; padding:.55rem .7rem; border-radius:.55rem; border:1px solid var(--line); background:var(--chip); color:var(--text); }
input[type=date] { background:var(--inset); }
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:650; }
.modes { display:flex; gap:.3rem; overflow-x:auto; margin-top:.5rem; }
.modes button { white-space:nowrap; padding:.4rem .7rem; font-size:.8rem; border-radius:999px; }
.modes button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:700; }
.badge { font-size:.72rem; padding:.15rem .45rem; border-radius:.4rem; background:var(--chip); color:var(--muted); }
.badge.ok { color:var(--ok); }
main { max-width:1100px; margin:0 auto; padding:.75rem 1rem 2.5rem; }
.kpis { display:grid; grid-template-columns:repeat(auto-fit,minmax(10rem,1fr)); gap:.5rem; margin:.6rem 0; }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:.7rem; padding:.75rem; }
.kpi .l { font-size:.75rem; color:var(--muted); }
.kpi .v { font-size:1.15rem; font-weight:700; margin-top:.15rem; }
table { width:100%; border-collapse:collapse; font-size:.84rem; }
th, td { border-bottom:1px solid var(--line); padding:.35rem .25rem; text-align:left; }
.num { text-align:right; font-variant-numeric:tabular-nums; }
.empty, .err { color:var(--muted); padding:1rem 0; }
.err { color:var(--down); }
.note { font-size:.8rem; color:var(--muted); margin:.4rem 0 0; }
.card { background:var(--card); border:1px solid var(--line); border-radius:.7rem; padding:.75rem; margin:.5rem 0; }
h2 { font-size:.95rem; margin:1rem 0 .4rem; }
</style>
</head>
<body>
<header>
  <div class="brand">
    <h1>ภาพรวมยอดขาย</h1>
    <span>
      <a href="/ops/">ใบสั่งซื้อ</a>
      <button type="button" id="themeBtn">มืด</button>
    </span>
  </div>
  <form class="row" id="f" onsubmit="go(event); return false;">
    <select id="preset" onchange="applyPreset(); go();">
      <option value="month">เดือนนี้</option>
      <option value="7">7 วัน</option>
      <option value="30">30 วัน</option>
      <option value="custom">กำหนดเอง</option>
    </select>
    <select id="branch" onchange="go()">
      <option value="ALL">สาขา: ทั้งหมด</option>
      <option value="HQ">HQ</option>
      <option value="SYP">SYP</option>
      <option value="ONLINE">ออนไลน์</option>
    </select>
    <input id="from" type="date" onchange="go()"/>
    <input id="to" type="date" onchange="go()"/>
    <button class="primary" type="submit">โหลด</button>
  </form>
  <div class="modes" id="modes">
    <button type="button" data-k="sales" class="on">ภาพรวมยอดขาย</button>
    <button type="button" data-k="customers">อันดับลูกค้า</button>
    <button type="button" data-k="products">อันดับสินค้า</button>
    <button type="button" data-k="movement">การเคลื่อนไหวสินค้า</button>
    <button type="button" data-k="copied">การเงิน (สำเนา)</button>
  </div>
  <div class="row" style="margin-top:.45rem">
    <span class="badge ok">PARTS9 สด</span>
    <span class="badge">ช่วงสูงสุด 92 วัน · ไม่ยิงประวัติหลายปี</span>
    <span class="badge __HQBADGE__">HQ __HQSQL__</span>
    <span class="badge __SYPBADGE__">SYP __SYPSQL__</span>
  </div>
</header>
<main id="main"><div class="empty">กำลังโหลดจาก PARTS9…</div></main>
<script>
const $ = (id) => document.getElementById(id);
let mode = "sales";
const BILLTYPE = { UNKNOWN:"หน้าร้าน (K/C)", TAD:"ออนไลน์ (TAD)", TD:"เครดิต VAT (TD)", TR:"เงินสด VAT (TR)", CN:"ใบลดหนี้ (CN)", DN:"ใบเพิ่มหนี้ (DN)" };
const BRANCH = { HQ:"HQ", SYP:"SYP", ONLINE:"ออนไลน์" };
function themeLabel(t) { return t === "light" ? "สว่าง" : "มืด"; }
function applyTheme(t) {
  document.documentElement.setAttribute("data-theme", t);
  $("themeBtn").textContent = themeLabel(t);
  try { localStorage.setItem("kcw.ops.theme", t); } catch (e) {}
}
$("themeBtn").onclick = () => applyTheme(document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark");
applyTheme(document.documentElement.getAttribute("data-theme") || "dark");
function isoLocal(d) {
  return d.getFullYear() + "-" + String(d.getMonth()+1).padStart(2,"0") + "-" + String(d.getDate()).padStart(2,"0");
}
function monthStart() {
  const d = new Date();
  return isoLocal(new Date(d.getFullYear(), d.getMonth(), 1));
}
function applyPreset() {
  const p = $("preset").value;
  const today = new Date();
  $("to").value = isoLocal(today);
  if (p === "month") $("from").value = monthStart();
  else if (p === "7") { const f = new Date(today); f.setDate(f.getDate()-6); $("from").value = isoLocal(f); }
  else if (p === "30") { const f = new Date(today); f.setDate(f.getDate()-29); $("from").value = isoLocal(f); }
}
function baht(v) {
  const n = Number(v||0);
  return "฿" + n.toLocaleString("th-TH", { maximumFractionDigits: 0 });
}
function qty(v) {
  return Number(v||0).toLocaleString("th-TH", { maximumFractionDigits: 2 });
}
function pct(cur, prev) {
  if (!prev) return "—";
  return ((cur-prev)/Math.abs(prev)*100).toFixed(1) + "%";
}
document.querySelectorAll("#modes button").forEach((b) => {
  b.onclick = () => {
    document.querySelectorAll("#modes button").forEach((x) => x.classList.remove("on"));
    b.classList.add("on");
    mode = b.dataset.k;
    load();
  };
});
function go(ev) { if (ev) ev.preventDefault(); load(); }
function kpis(items) {
  return "<div class='kpis'>" + items.map((it) => "<div class='kpi'><div class='l'>"+it[0]+"</div><div class='v'>"+it[1]+"</div></div>").join("") + "</div>";
}
function table(headers, rows) {
  if (!rows.length) return "<div class='empty'>ไม่พบรายการ</div>";
  let h = "<div style='overflow:auto'><table><thead><tr>" + headers.map((x)=>"<th>"+x+"</th>").join("") + "</tr></thead><tbody>";
  rows.forEach((r) => { h += "<tr>" + r.map((c,i)=> "<td"+(i?" class='num'":"")+">"+c+"</td>").join("") + "</tr>"; });
  return h + "</tbody></table></div>";
}
async function load() {
  $("main").innerHTML = "<div class='empty'>กำลังโหลดจาก PARTS9…</div>";
  if (mode === "copied") {
    $("main").innerHTML = "<div class='card'><h2>การเงินยังอยู่บนสำเนา</h2><p class='note'>กำไรขาดทุน / งบเฉพาะส่งบัญชี / กระแสเงินสด / VAT / ค่าใช้จ่าย และเปรียบเทียบยอดขาย YoY ยังอ่าน Supabase ตามแผน — ไม่ยิง SIDET ย้อน 3 ปีบน PARTS9</p><p class='note'>ใช้ cloud kcw-v2 สำหรับหน้าเหล่านี้จนกว่าจะ sign-off ทีละรายงาน</p></div>";
    return;
  }
  const params = new URLSearchParams({ from: $("from").value, to: $("to").value, branch: $("branch").value });
  const url = "/ops/api/bi/" + mode + "?" + params.toString();
  try {
    const res = await fetch(url, { credentials: "same-origin" });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || data.error || res.status);
    render(data);
  } catch (e) {
    $("main").innerHTML = "<div class='err'>" + (e.message || e) + "</div>";
  }
}
function render(data) {
  const chip = "<div class='note'>" + (data.freshness || "PARTS9 live") + " · " + data.from + " ถึง " + data.to + "</div>";
  if (mode === "sales") {
    const s = data.summary || {}, p = data.previous_summary || {};
    $("main").innerHTML = chip + kpis([
      ["ยอดสุทธิ", baht(s.revenue_net)],
      ["เทียบช่วงก่อน", pct(s.revenue_net, p.revenue_net)],
      ["จำนวนบิล", qty(s.bill_count)],
      ["เฉลี่ย/บิล", baht(s.avg_bill)],
    ]) + "<h2>สาขา</h2>" + table(["สาขา","ยอด","บิล"], (data.by_branch||[]).map((r)=>[BRANCH[r.key]||r.key, baht(r.revenue_net), qty(r.bill_count)]))
      + "<h2>ช่องทาง</h2>" + table(["ช่องทาง","ยอด","บิล"], (data.by_channel||[]).map((r)=>[r.key==="ONLINE"?"ออนไลน์":"หน้าร้าน", baht(r.revenue_net), qty(r.bill_count)]))
      + "<h2>ประเภทบิล</h2>" + table(["ประเภท","ยอด","บิล"], (data.by_billtype||[]).map((r)=>[BILLTYPE[r.key]||r.key, baht(r.revenue_net), qty(r.bill_count)]))
      + "<h2>รายวัน</h2>" + table(["วันที่","ยอด","บิล","HQ","SYP","ออนไลน์"], (data.trend_daily||[]).map((r)=>[r.period, baht(r.revenue_net), qty(r.bill_count), baht(r.hq_revenue_net), baht(r.syp_revenue_net), baht(r.online_revenue_net)]));
    return;
  }
  if (mode === "customers") {
    const s = data.summary || {}, w = data.walkin_summary || {};
    $("main").innerHTML = chip + kpis([
      ["ยอดสุทธิ", baht(s.revenue_net)],
      ["ลูกค้ามีรหัส", qty(s.customer_count)],
      ["บิล", qty(s.bill_count)],
      ["ขาจร", baht(w.revenue_net)],
    ]) + "<h2>อันดับลูกค้า</h2>" + table(["รหัส","ชื่อ","ยอด","บิล"], (data.top_customers||[]).map((r)=>[r.acctno, r.customer_name||"—", baht(r.revenue_net), qty(r.bill_count)]));
    return;
  }
  if (mode === "products") {
    const s = data.summary || {};
    $("main").innerHTML = chip + kpis([
      ["ยอดบรรทัด", baht(s.revenue_net)],
      ["จำนวนขาย", qty(s.base_qty)],
      ["SKU", qty(s.sku_count)],
      ["บิล", qty(s.bill_count)],
    ]) + "<h2>อันดับสินค้า</h2>" + table(["รหัส","รายการ","ยอด","จำนวน","คงเหลือ HQ"], (data.top_products||[]).map((r)=>[r.bcode, r.detail||"", baht(r.revenue_net), qty(r.base_qty), qty(r.on_hand_qty)]));
    return;
  }
  if (mode === "movement") {
    const s = data.summary || {};
    $("main").innerHTML = chip + kpis([
      ["SKU ที่ขาย", qty(s.sold_sku_count)],
      ["จำนวนขาย", qty(s.sell_qty)],
      ["SKU ที่ซื้อ", qty(s.bought_sku_count)],
      ["จำนวนซื้อ HQ", qty(s.buy_qty)],
    ]) + "<p class='note'>" + (data.dead_note || "") + "</p>"
      + "<h2>ขายดีช่วงนี้ + คงเหลือสด</h2>" + table(["รหัส","รายการ","ขาย","บิล","ซื้อ","คงเหลือ"], (data.stock_more||[]).map((r)=>[r.bcode, r.detail||"", qty(r.sell_qty), qty(r.sell_bills), qty(r.buy_qty), qty(r.on_hand_qty)]));
  }
}
applyPreset();
load();
</script>
</body>
</html>
"""


def page(*, probes: dict) -> str:
    hq = (probes or {}).get("hq") or {}
    syp = (probes or {}).get("syp") or {}
    html = _HTML
    html = html.replace("__HQBADGE__", "ok" if hq.get("ok") else "down")
    html = html.replace("__SYPBADGE__", "ok" if syp.get("ok") else "down")
    html = html.replace("__HQSQL__", "ok" if hq.get("ok") else "down")
    html = html.replace("__SYPSQL__", "ok" if syp.get("ok") else "down")
    return html

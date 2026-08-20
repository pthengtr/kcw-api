from __future__ import annotations

APP = "parts9-explorer"
SESSION_COOKIE = "kcw_parts9_explorer"
_HTML = r"""<!doctype html>
<html lang="th" data-theme="dark">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="theme-color" content="#0c1014" id="themeColor"/>
<title>PARTS9 explorer</title>
<script>
(function () {
  try {
    var t = localStorage.getItem("kcw.parts9.theme");
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
:root {
  --acc:#3d9cf0; --ok:#3ecf8e; --down:#e25c5c; --warn:#e6b450; --pend:#f0a35a;
  --on-acc:#071018;
}
html[data-theme="dark"] {
  color-scheme: dark;
  --bg:#0c1014; --header:rgba(12,16,20,.96); --card:#161d26; --line:#2a3542;
  --text:#e8eef4; --muted:#8b9aab; --heading:#c5d0da; --chip:#243040; --inset:#0a0e12;
  --si:#7ec8ff; --pi:#f0c36e; --po:#9ad7b5; --pv:#d7a6ff; --rv:#8fe3d2;
  --st-pend-bg:#3a2a18; --st-ok-bg:#163328; --st-no-bg:#3a1c1c; --st-wait-bg:#2a3140;
}
html[data-theme="light"] {
  color-scheme: light;
  --bg:#f4f6f8; --header:rgba(244,246,248,.96); --card:#ffffff; --line:#d5dde6;
  --text:#1b2430; --muted:#5b6b7c; --heading:#334155; --chip:#e8eef4; --inset:#eef2f6;
  --si:#1565c0; --pi:#b45309; --po:#0f7a4a; --pv:#7c3aed; --rv:#0f766e;
  --st-pend-bg:#fff3e0; --st-ok-bg:#e8f6ee; --st-no-bg:#fde8e8; --st-wait-bg:#e8eef4;
}
* { box-sizing:border-box; }
body { margin:0; font-family: Prompt, ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
header { position:sticky; top:0; z-index:5; background:var(--header); border-bottom:1px solid var(--line); padding:.7rem 1rem .8rem; }
.brand { display:flex; align-items:center; justify-content:space-between; gap:.6rem; margin:0 0 .5rem; }
h1 { font-size:1.02rem; margin:0; letter-spacing:.02em; }
.row { display:flex; gap:.45rem; flex-wrap:wrap; align-items:center; }
input[type=search] { flex:1; min-width:12rem; font: inherit; font-size:1.05rem; padding:.7rem .8rem; border-radius:.6rem; border:1px solid var(--line); background:var(--inset); color:var(--text); }
button, select { font: inherit; font-size:.92rem; padding:.6rem .75rem; border-radius:.55rem; border:1px solid var(--line); background:var(--chip); color:var(--text); }
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:650; }
button.theme { min-width:2.6rem; padding:.55rem .65rem; }
.modes { display:flex; gap:.3rem; overflow-x:auto; padding:.15rem 0 .15rem; margin-top:.5rem; -webkit-overflow-scrolling:touch; }
.modes button { white-space:nowrap; padding:.4rem .7rem; font-size:.8rem; border-radius:999px; }
.modes button.on { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:700; }
.badge { font-size:.72rem; padding:.15rem .45rem; border-radius:.4rem; background:var(--chip); color:var(--muted); }
.badge.ok { color:var(--ok); } .badge.down { color:var(--down); }
.badge.si { color:var(--si); } .badge.pi { color:var(--pi); } .badge.po { color:var(--po); }
.badge.pv { color:var(--pv); } .badge.rv { color:var(--rv); } .badge.iclow { color:var(--pend); }
.badge.pending { background:var(--st-pend-bg); color:var(--pend); }
.badge.received { background:var(--st-ok-bg); color:var(--ok); }
.badge.canceled { background:var(--st-no-bg); color:var(--down); }
.badge.to_order { background:var(--st-wait-bg); color:var(--muted); }
main { display:grid; grid-template-columns:1fr; max-width:1180px; margin:0 auto; }
@media (min-width:880px) { main { grid-template-columns: minmax(280px,40%) 1fr; min-height:calc(100vh - 9rem);} .list{border-right:1px solid var(--line);} }
.list, .detail { padding:.75rem 1rem 2rem; }
.card { display:flex; gap:.75rem; padding:.7rem; margin-bottom:.5rem; background:var(--card); border:1px solid var(--line); border-radius:.7rem; text-align:left; width:100%; cursor:pointer; color:inherit; }
.card.active { outline:2px solid var(--acc); }
.thumb { width:64px; height:64px; object-fit:cover; border-radius:.45rem; background:var(--inset); flex-shrink:0; }
.meta { font-size:.8rem; color:var(--muted); }
.prices { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.25rem; }
.prices span { font-size:.75rem; background:var(--inset); padding:.12rem .35rem; border-radius:.35rem; }
.photos { display:flex; gap:.4rem; overflow-x:auto; margin:.6rem 0; }
.photos img { height:140px; border-radius:.5rem; background:var(--inset); }
table { width:100%; border-collapse:collapse; font-size:.84rem; }
th, td { border-bottom:1px solid var(--line); padding:.35rem .25rem; text-align:left; vertical-align:top; }
.who { font-size:.75rem; color:var(--muted); margin-top:.35rem; }
.empty { color:var(--muted); padding:1rem 0; }
label.chk { font-size:.8rem; color:var(--muted); display:flex; gap:.35rem; align-items:center; }
.kpis { display:grid; grid-template-columns:repeat(2,1fr); gap:.45rem; margin:.2rem 0 .8rem; }
@media (min-width:560px) { .kpis { grid-template-columns:repeat(4,1fr);} }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:.65rem; padding:.65rem .7rem; }
.kpi .n { font-size:1.25rem; font-weight:700; }
.kpi .l { font-size:.72rem; color:var(--muted); margin-top:.1rem; }
.kpi.warn .n { color:var(--pend); }
.kpi.ok .n { color:var(--ok); }
.linkish { color:var(--acc); cursor:pointer; text-decoration:underline; background:none; border:0; padding:0; font:inherit; }
h2 { font-size:1.15rem; margin:.15rem 0 .4rem; }
h3 { font-size:.95rem; margin:1rem 0 .35rem; color:var(--heading); }
</style>
</head>
<body>
<header>
  <div class="brand">
    <h1>PARTS9 explorer</h1>
    <button type="button" class="theme" id="themeBtn" aria-label="สลับธีม">มืด</button>
  </div>
  <form class="row" id="f" onsubmit="go(event); return false;">
    <input id="q" type="search" enterkeyhint="search" autocomplete="off" placeholder="รหัส / เบอร์แท้ / เบอร์โรงงาน / I K ซีล / PO เลขบิล" autofocus />
    <select id="site">
      <option value="hq" __HQSEL__>HQ</option>
      <option value="syp" __SYPSEL__>SYP</option>
    </select>
    <button class="primary" type="submit">ค้นหา</button>
    <label class="chk"><input type="checkbox" id="skip"/> รวมไม่สั่งซ้ำ</label>
  </form>
  <div class="modes" id="modes">
    <button type="button" data-k="all" class="on">ทั้งหมด</button>
    <button type="button" data-k="product">สินค้า</button>
    <button type="button" data-k="si">SI บิลขาย</button>
    <button type="button" data-k="pi">PI บิลซื้อ</button>
    <button type="button" data-k="po">PO สั่งซื้อ</button>
    <button type="button" data-k="pv">PV จ่าย</button>
    <button type="button" data-k="rv">RV รับ</button>
    <button type="button" data-k="iclow">ICLOW ค้างรับ</button>
  </div>
  <div class="row" style="margin-top:.45rem">
    <span class="badge __HQBADGE__">HQ SQL __HQSQL__</span>
    <span class="badge __SYPBADGE__">SYP SQL __SYPSQL__</span>
    <span class="who">__USER__</span>
  </div>
</header>
<main>
  <section class="list" id="list"><div class="empty">เลือกประเภทด้านบน แล้วพิมพ์ค้นหา</div></section>
  <section class="detail" id="detail"></section>
</main>
<script>
const $ = (id) => document.getElementById(id);
const MODES = [
  {id:"all", label:"ทั้งหมด"},
  {id:"product", label:"สินค้า"},
  {id:"si", label:"SI บิลขาย"},
  {id:"pi", label:"PI บิลซื้อ"},
  {id:"po", label:"PO สั่งซื้อ"},
  {id:"pv", label:"PV จ่าย"},
  {id:"rv", label:"RV รับ"},
  {id:"iclow", label:"ICLOW ค้างรับ"},
];
const PLACE = {
  all: "รหัส / เบอร์แท้ PCODE / เบอร์โรงงาน MCODE / I K ซีล 31 46 / PO เลขบิล",
  product: "รหัสสินค้า / เบอร์แท้ / เบอร์โรงงาน / I K C ซีล 31 46 / ยี่ห้อ",
  si: "เลขบิลขาย เช่น 8K69-0013225",
  pi: "เลขบิลซื้อ / เลขโน้ต / เลขใบสำคัญจ่าย",
  po: "เลขใบสั่งซื้อ เช่น PO6905-392",
  pv: "เลขใบสำคัญจ่าย KCPN / P… หรือเลขโน้ต",
  rv: "เลขใบสำคัญรับ RC / RVI",
  iclow: "เลข PO / รหัสสินค้า / ผู้ขาย — ว่าง = สรุปค้างรับ",
};
const STATUS_TH = {pending:"ค้างรับ", received:"รับแล้ว", canceled:"ยกเลิก", to_order:"รอสั่ง"};
let KIND = "all";
let ITEMS = [];
let DOCS = [];
let SUMMARY = null;
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function(c) {
    if (c === "&") return "&amp;";
    if (c === "<") return "&lt;";
    if (c === ">") return "&gt;";
    if (c === '"') return "&quot;";
    return "&#39;";
  });
}
function money(v) {
  const n = Number(String(v == null ? "" : v).replace(/,/g,""));
  if (!isFinite(n) || String(v).trim() === "") return esc(v || "");
  return n.toLocaleString("th-TH", {maximumFractionDigits: 2});
}
function fmtPrices(p) {
  if (!p) return "";
  return Object.entries(p).map(([k,v]) => `<span>${k} ${Number(v).toLocaleString()}</span>`).join("");
}
function codeBits(p) {
  const bits = [];
  if (p.code1) bits.push((p.code1_label ? p.code1+" "+p.code1_label : p.code1));
  if (p.pcode) bits.push("แท้ "+p.pcode);
  if (p.mcode) bits.push("โรงงาน "+p.mcode);
  return bits.length ? "<div class='meta'>"+esc(bits.join(" · "))+"</div>" : "";
}
function imgErr(el) { el.style.display="none"; }
function setKind(k) {
  KIND = k;
  document.querySelectorAll("#modes button").forEach(b => b.classList.toggle("on", b.dataset.k === k));
  $("q").placeholder = PLACE[k] || PLACE.all;
  if (k === "iclow" || $("q").value.trim()) go();
  else { $("list").innerHTML = "<div class='empty'>พิมพ์ค้นหาด้านบน</div>"; $("detail").innerHTML = ""; }
}
function drawModes() {
  document.querySelectorAll("#modes button").forEach(b => b.classList.toggle("on", b.dataset.k === KIND));
}
let _t = null;
function scheduleGo() {
  clearTimeout(_t);
  _t = setTimeout(() => go(), 380);
}
async function go(ev) {
  if (ev) ev.preventDefault();
  const q = $("q").value.trim();
  const site = $("site").value;
  const skip = $("skip").checked ? "1" : "0";
  if (!q && KIND !== "iclow") return false;
  $("list").innerHTML = "<div class='empty'>กำลังค้น…</div>";
  $("detail").innerHTML = "";
  try {
    const r = await fetch("/parts9/api/search?site="+encodeURIComponent(site)+"&include_skip="+skip+"&kind="+encodeURIComponent(KIND)+"&q="+encodeURIComponent(q));
    const data = await r.json();
    if (!r.ok) {
      $("list").innerHTML = "<div class='empty'>"+esc(data.detail || ("HTTP "+r.status))+"</div>";
      return false;
    }
    render(data);
  } catch (e) {
    $("list").innerHTML = "<div class='empty'>ค้นไม่สำเร็จ "+esc(e && e.message ? e.message : e)+"</div>";
  }
  return false;
}
function stBadge(st) {
  const k = st || "";
  return "<span class='badge "+esc(k)+"'>"+esc(STATUS_TH[k] || k)+"</span>";
}
function render(data) {
  const products = data.products || [];
  DOCS = data.documents || (data.document ? [data.document] : []);
  ITEMS = products;
  SUMMARY = data.iclow_summary || null;
  if (!products.length && !DOCS.length && !SUMMARY) {
    $("list").innerHTML = "<div class='empty'>ไม่พบ "+esc(data.error||"")+"</div>";
    $("detail").innerHTML = "";
    return;
  }
  let html = "";
  if (SUMMARY && KIND === "iclow") {
    html += "<button class='card' onclick='showSummary()'><div><strong>สรุปค้างรับ "+esc(SUMMARY.site||"")+"</strong>"
      +"<div class='meta'>ค้างรับ "+esc((SUMMARY.totals||{}).pending_lines)+" บรรทัด · "
      +esc((SUMMARY.totals||{}).pending_pos)+" ใบ PO</div></div></button>";
  }
  DOCS.forEach((d,i) => {
    const h = d.header || {};
    const counts = (d.iclow && d.iclow.counts) || {};
    const extra = d.kind === "iclow"
      ? ("ค้างรับ "+(counts.pending||0)+" · รับแล้ว "+(counts.received||0))
      : (h.ACCTNAME || h.VENDOR || "");
    const when = h.BILLDATE||h.DOCDATE||h.VOUCDATE||h.NOTEDATE||"";
    const noteBit = (h.NOTENO && h.NOTENO !== (d.docno||"")) ? (" · โน้ต "+h.NOTENO) : "";
    html += "<button class='card' id='d"+i+"' onclick='showDoc("+i+")'><div>"
      +"<span class='badge "+esc(d.kind)+"'>"+esc(d.kind_label || d.kind)+"</span> "
      +"<strong>"+esc(d.docno || h.BILLNO||h.DOCNO||h.VOUCNO||h.NOTENO||"")+"</strong>"
      +"<div class='meta'>"+esc(extra)+" · "+esc(when)+esc(noteBit)+"</div></div></button>";
  });
  products.forEach((p,i) => {
    const src = (p.photos && p.photos[0]) || "";
    html += "<button class='card' id='c"+i+"' onclick='showP("+i+")'><img class='thumb' src='"+src+"' onerror='imgErr(this)'/><div><strong>"+esc(p.bcode)+"</strong>"
      +(p.do_not_restock?" <span class='badge'>ไม่สั่งซ้ำ</span>":"")
      +"<div>"+esc(p.descr||p.pcode||p.mcode||"")+"</div>"+codeBits(p)+"<div class='meta'>"+esc(p.category||"")+" · คงเหลือ "+p.qtyoh2+" "+esc(p.ui1||"")+"</div><div class='prices'>"+fmtPrices(p.prices)+"</div></div></button>";
  });
  $("list").innerHTML = html || "<div class='empty'>ไม่พบ</div>";
  if (KIND === "iclow" && SUMMARY && !DOCS.length) showSummary();
  else if (DOCS.length && !products.length) showDoc(0);
  else if (products[0]) showP(0);
  else if (DOCS.length) showDoc(0);
}
function kvTable(obj) {
  const skip = new Set(["ID"]);
  return "<table>"+Object.keys(obj).filter(k => !skip.has(k) && String(obj[k]||"").trim() !== "").map(k =>
    "<tr><th>"+esc(k)+"</th><td>"+esc(obj[k])+"</td></tr>"
  ).join("")+"</table>";
}
function lineTable(rows, cols) {
  if (!rows || !rows.length) return "<p class='meta'>ไม่มีบรรทัด</p>";
  const use = cols || Object.keys(rows[0]);
  const head = use.map(c => "<th>"+esc(c)+"</th>").join("");
  const moneyCols = new Set(["PRICE","AMOUNT","CHKAMT","QTY","AFTERTAX","BILLAMT","NETAMT"]);
  const body = rows.map(row => "<tr>"+use.map(c => {
    let v = row[c] || "";
    if (c === "status") return "<td>"+stBadge(v)+"</td>";
    if (c === "BCODE" && v) return "<td><button class='linkish' data-jump='product' data-q='"+esc(v)+"'>"+esc(v)+"</button></td>";
    if (moneyCols.has(c)) return "<td>"+money(v)+"</td>";
    return "<td>"+esc(v)+"</td>";
  }).join("")+"</tr>").join("");
  return "<table><thead><tr>"+head+"</tr></thead><tbody>"+body+"</tbody></table>";
}
function jumpProduct(bcode) {
  KIND = "product";
  drawModes();
  $("q").placeholder = PLACE.product;
  $("q").value = bcode;
  go();
}
function jumpIclow(q) {
  KIND = "iclow";
  drawModes();
  $("q").placeholder = PLACE.iclow;
  $("q").value = q;
  go();
}
function showSummary() {
  document.querySelectorAll(".card").forEach(el => el.classList.remove("active"));
  const s = SUMMARY;
  if (!s) return;
  const t = s.totals || {};
  const vendors = s.vendors || [];
  const recent = s.recent_pending || [];
  $("detail").innerHTML =
    "<h2>สรุปค้างรับ · "+esc(s.site)+"</h2>"
    +"<p class='meta'>ORDERED=Y · ยังไม่ RECEIVED · ไม่ยกเลิก — ตามรายงาน PARTS9</p>"
    +"<div class='kpis'>"
    +"<div class='kpi warn'><div class='n'>"+esc(t.pending_lines||"0")+"</div><div class='l'>บรรทัดค้างรับ</div></div>"
    +"<div class='kpi warn'><div class='n'>"+esc(t.pending_pos||"0")+"</div><div class='l'>ใบ PO ค้างรับ</div></div>"
    +"<div class='kpi'><div class='n'>"+money(t.pending_amount)+"</div><div class='l'>มูลค่าค้างรับ</div></div>"
    +"<div class='kpi ok'><div class='n'>"+esc(t.received_lines||"0")+"</div><div class='l'>บรรทัดรับแล้ว</div></div>"
    +"</div>"
    +"<div class='meta'>รอสั่งซื้อ "+esc(t.to_order_lines||"0")+" · ยกเลิก "+esc(t.canceled_lines||"0")+" · ทั้งตาราง "+esc(t.total_lines||"0")+"</div>"
    +"<h3>ผู้ขายค้างรับสูงสุด</h3>"
    +(vendors.length ? "<table><thead><tr><th>VENDOR</th><th>ชื่อ</th><th>บรรทัด</th><th>มูลค่า</th></tr></thead><tbody>"
      +vendors.map(v => "<tr><td><button class='linkish' data-jump='iclow' data-q='"+esc(v.VENDOR)+"'>"+esc(v.VENDOR)+"</button></td>"
        +"<td>"+esc(v.ACCTNAME)+"</td><td>"+esc(v.lines)+"</td><td>"+money(v.amount)+"</td></tr>").join("")
      +"</tbody></table>" : "<p class='meta'>—</p>")
    +"<h3>ค้างรับล่าสุด</h3>"
    +lineTable(recent, ["DOCNO","DOCDATE","VENDOR","BCODE","DESCR","QTY","UI","AMOUNT"]);
}
function showDoc(i) {
  const doc = DOCS[i];
  if (!doc) return;
  document.querySelectorAll(".card").forEach(el => el.classList.remove("active"));
  const el = document.getElementById("d"+i); if (el) el.classList.add("active");
  const h = doc.header || {};
  const rows = doc.lines || [];
  const ic = doc.iclow;
  let extra = "";
  if (doc.po) extra += "<p class='meta'>ผูก PO <button class='linkish' data-jump='po' data-q='"+esc(doc.po)+"'>"+esc(doc.po)+"</button></p>";
  const bills = doc.bills || [];
  if (bills.length) {
    extra += "<h3>บิลซื้อที่เกี่ยวข้อง</h3>";
    bills.forEach(function(b) {
      const bh = b.header || {};
      extra += "<p class='meta'><button class='linkish' data-jump='pi' data-q='"+esc(b.docno || bh.BILLNO || "")+"'>"+esc(b.docno || bh.BILLNO || "")+"</button>"
        +" · "+esc(bh.BILLDATE||"")+" · "+money(bh.AFTERTAX)+" · "+esc(bh.ACCTNAME||"")+"</p>"
        +lineTable(b.lines || [], ["LINE","BCODE","DETAIL","QTY","UI","PRICE","AMOUNT"]);
    });
  }
  const vouchers = doc.vouchers || [];
  if (vouchers.length) {
    extra += "<h3>โน้ต / ใบสำคัญจ่าย</h3><table><thead><tr><th>เลขที่</th><th>วันที่</th><th>โน้ต</th><th>ยอดบิล</th><th>สถานะ</th></tr></thead><tbody>";
    extra += vouchers.map(function(v) {
      const vh = v.header || {};
      const no = v.docno || vh.VOUCNO || vh.NOTENO || "";
      const dt = vh.VOUCDATE || vh.NOTEDATE || "";
      const st = vh.VOUCNO ? "voucher" : "note";
      return "<tr><td><button class='linkish' data-jump='pv' data-q='"+esc(no)+"'>"+esc(no)+"</button></td>"
        +"<td>"+esc(dt)+"</td><td>"+esc(vh.NOTENO||"")+"</td><td>"+money(vh.BILLAMT)+"</td><td>"+esc(st)+"</td></tr>";
    }).join("")+"</tbody></table>";
  }
  if (ic && ic.counts) {
    extra += "<p>"+stBadge("pending")+" "+(ic.counts.pending||0)+" "
      +stBadge("received")+" "+(ic.counts.received||0)+" "
      +stBadge("canceled")+" "+(ic.counts.canceled||0)+"</p>";
  }
  const lineCols = rows[0] && rows[0].status
    ? ["status","BCODE","DESCR","QTY","UI","AMOUNT","RCVDNO","RCVDDATE"]
    : null;
  $("detail").innerHTML = "<h2><span class='badge "+esc(doc.kind)+"'>"+esc(doc.kind_label||doc.kind)+"</span> "+esc(doc.docno)+"</h2>"
    +kvTable(h)+extra
    +"<h3>บรรทัด</h3>"+lineTable(rows, lineCols)
    +(ic && ic.lines && doc.kind === "po" ? "<h3>ICLOW ของใบนี้</h3>"+lineTable(ic.lines, ["status","BCODE","DESCR","QTY","UI","AMOUNT","RCVDNO"]) : "");
}
function jumpKind(kind, qv) {
  KIND = kind;
  drawModes();
  $("q").placeholder = PLACE[kind] || PLACE.all;
  $("q").value = qv;
  go();
}
function jumpPo(docno) { jumpKind("po", docno); }
function showP(i) {
  const p = ITEMS[i];
  if (!p) return;
  document.querySelectorAll(".card").forEach(el => el.classList.remove("active"));
  const el = document.getElementById("c"+i); if (el) el.classList.add("active");
  const L = p.size_labels || {};
  const sizes = [];
  if (p.size1) sizes.push((L.size1||"SIZE1")+": "+p.size1);
  if (p.size2) sizes.push((L.size2||"SIZE2")+": "+p.size2);
  if (p.size3) sizes.push((L.size3||"SIZE3")+": "+p.size3);
  const photos = (p.photos||[]).map(u => "<img src='"+u+"' onerror='imgErr(this)'/>").join("");
  $("detail").innerHTML = "<h2 style='margin:.2rem 0'>"+esc(p.bcode)+"</h2><div>"+esc(p.descr)+"</div>"
    +"<div class='meta'>เบอร์แท้ "+esc(p.pcode||"—")+" · เบอร์โรงงาน "+esc(p.mcode||"—")
    +" · "+esc(p.brand)+" "+esc(p.model)+"</div>"
    +"<div class='meta'>"+esc(p.category)+" · "+esc(p.code1 ? (p.code1+" "+(p.code1_label||"")) : (p.code1_label||""))+" · "+esc(sizes.join(" / "))+"</div>"
    +"<div class='meta'>ที่เก็บ "+esc(p.location1)+" "+esc(p.location2)+" · "+esc(p.ui1)+"/"+esc(p.ui2)+"</div>"
    +"<div class='prices'>"+fmtPrices(p.prices)+"</div><div class='photos'>"+photos+"</div>"
    +"<p class='meta'>คงเหลือ QTYOH2 = "+p.qtyoh2+" "+esc(p.ui1)+(p.do_not_restock?" (ไม่สั่งซ้ำ)":"")+"</p>"
    +"<div id='more' class='empty'>โหลดความเคลื่อนไหว…</div>";
  fetch("/parts9/api/product/"+encodeURIComponent(p.bcode)+"?site="+encodeURIComponent($("site").value))
    .then(r => r.json()).then(d => {
      const m = d.movement || {};
      function tbl(title, rows, cols) {
        if (!rows || !rows.length) return "<p class='meta'>"+title+": —</p>";
        return "<h3>"+title+"</h3>"+lineTable(rows, cols);
      }
      $("more").innerHTML =
        tbl("ขายล่าสุด SI", m.sales, ["BILLNO","BILLDATE","QTY","UI","PRICE","AMOUNT"]) +
        tbl("บิลซื้อ PI", m.pi, ["BILLNO","BILLDATE","QTY","UI","PRICE","AMOUNT"]) +
        tbl("PO", m.po, ["DOCNO","DOCDATE","QTY","UI","PRICE","AMOUNT"]) +
        tbl("ICLOW", m.iclow, ["DOCNO","DOCDATE","ORDERED","RECEIVED","CANCELED","RCVDNO","QTY"]);
    }).catch(() => { $("more").innerHTML = ""; });
}
$("modes").addEventListener("click", (ev) => {
  const b = ev.target.closest("button[data-k]");
  if (b) setKind(b.dataset.k);
});
document.addEventListener("click", (ev) => {
  const b = ev.target.closest("[data-jump]");
  if (!b) return;
  const kind = b.getAttribute("data-jump");
  const qv = b.getAttribute("data-q") || "";
  if (kind === "product") jumpProduct(qv);
  else if (kind === "iclow") jumpIclow(qv);
  else jumpKind(kind, qv);
});
$("site").addEventListener("change", () => { if ($("q").value.trim() || KIND==="iclow") go(); });
$("q").addEventListener("input", scheduleGo);
$("q").addEventListener("search", () => go());
$("skip").addEventListener("change", () => { if ($("q").value.trim()) go(); });
const THEME_KEY = "kcw.parts9.theme";
function currentTheme() {
  const t = document.documentElement.getAttribute("data-theme");
  return t === "light" ? "light" : "dark";
}
function applyTheme(t) {
  const theme = t === "light" ? "light" : "dark";
  document.documentElement.setAttribute("data-theme", theme);
  try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
  const btn = $("themeBtn");
  if (btn) {
    btn.textContent = theme === "light" ? "สว่าง" : "มืด";
    btn.setAttribute("aria-label", theme === "light" ? "สลับเป็นธีมมืด" : "สลับเป็นธีมสว่าง");
  }
  const meta = document.getElementById("themeColor");
  if (meta) meta.setAttribute("content", theme === "light" ? "#f4f6f8" : "#0c1014");
}
$("themeBtn").addEventListener("click", () => applyTheme(currentTheme() === "light" ? "dark" : "light"));
applyTheme(currentTheme());
drawModes();
</script>
</body>
</html>
"""


def page(*, user_name: str, site: str, probes: dict) -> str:
    hq = probes.get("hq") or {}
    syp = probes.get("syp") or {}
    return (
        _HTML.replace("__USER__", user_name or "")
        .replace("__HQSEL__", "selected" if site.lower()=="hq" else "")
        .replace("__SYPSEL__", "selected" if site.lower()=="syp" else "")
        .replace("__HQBADGE__", "ok" if hq.get("ok") else "down")
        .replace("__SYPBADGE__", "ok" if syp.get("ok") else "down")
        .replace("__HQSQL__", str(hq.get("server") or hq.get("error") or ""))
        .replace("__SYPSQL__", str(syp.get("server") or syp.get("error") or ""))
    )

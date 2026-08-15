from __future__ import annotations

APP = "parts9-explorer"
SESSION_COOKIE = "kcw_parts9_explorer"
_HTML = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<title>PARTS9 explorer</title>
<style>
:root { --bg:#0f1419; --card:#1a222c; --line:#2a3542; --text:#e8eef4; --muted:#9aa8b5; --acc:#3d9cf0; --ok:#3ecf8e; --down:#e25c5c; --chip:#243040; }
* { box-sizing:border-box; }
body { margin:0; font-family: ui-sans-serif, system-ui, sans-serif; background:var(--bg); color:var(--text); }
header { position:sticky; top:0; z-index:5; background:rgba(15,20,25,.94); border-bottom:1px solid var(--line); padding:.75rem 1rem; }
h1 { font-size:1.05rem; margin:0 0 .55rem; }
.row { display:flex; gap:.5rem; flex-wrap:wrap; align-items:center; }
input[type=search] { flex:1; min-width:12rem; font-size:1.05rem; padding:.7rem .8rem; border-radius:.6rem; border:1px solid var(--line); background:#0c1116; color:var(--text); }
button, select { font-size:.95rem; padding:.65rem .8rem; border-radius:.55rem; border:1px solid var(--line); background:var(--chip); color:var(--text); }
button.primary { background:var(--acc); border-color:var(--acc); color:#071018; font-weight:650; }
.badge { font-size:.75rem; padding:.15rem .45rem; border-radius:.4rem; background:var(--chip); color:var(--muted); }
.badge.ok { color:var(--ok); }
.badge.down { color:var(--down); }
main { display:grid; grid-template-columns:1fr; max-width:1100px; margin:0 auto; }
@media (min-width:880px) { main { grid-template-columns: minmax(280px,42%) 1fr; min-height:calc(100vh - 7rem);} .list{border-right:1px solid var(--line);} }
.list, .detail { padding:.75rem 1rem 2rem; }
.card { display:flex; gap:.75rem; padding:.7rem; margin-bottom:.55rem; background:var(--card); border:1px solid var(--line); border-radius:.7rem; text-align:left; width:100%; cursor:pointer; color:inherit; }
.card.active { outline:2px solid var(--acc); }
.thumb { width:64px; height:64px; object-fit:cover; border-radius:.45rem; background:#0c1116; flex-shrink:0; }
.meta { font-size:.8rem; color:var(--muted); }
.prices { display:flex; flex-wrap:wrap; gap:.35rem; margin-top:.25rem; }
.prices span { font-size:.75rem; background:#0c1116; padding:.12rem .35rem; border-radius:.35rem; }
.photos { display:flex; gap:.4rem; overflow-x:auto; margin:.6rem 0; }
.photos img { height:140px; border-radius:.5rem; background:#0c1116; }
table { width:100%; border-collapse:collapse; font-size:.85rem; }
th, td { border-bottom:1px solid var(--line); padding:.35rem .25rem; text-align:left; }
.who { font-size:.75rem; color:var(--muted); margin-top:.35rem; }
.empty { color:var(--muted); padding:1rem 0; }
label.chk { font-size:.8rem; color:var(--muted); display:flex; gap:.35rem; align-items:center; }
</style>
</head>
<body>
<header>
  <h1>PARTS9 explorer</h1>
  <form class="row" id="f" onsubmit="go(event); return false;">
    <input id="q" type="search" enterkeyhint="search" autocomplete="off" placeholder="รหัส / ซีล 31 46 / ยี่ห้อ / เลขบิล PO PV" autofocus />
    <select id="site">
      <option value="hq" __HQSEL__>HQ</option>
      <option value="syp" __SYPSEL__>SYP</option>
    </select>
    <button class="primary" type="submit">ค้นหา</button>
    <label class="chk"><input type="checkbox" id="skip"/> รวมไม่สั่งซ้ำ</label>
  </form>
  <div class="row" style="margin-top:.45rem">
    <span class="badge __HQBADGE__">HQ SQL __HQSQL__</span>
    <span class="badge __SYPBADGE__">SYP SQL __SYPSQL__</span>
    <span class="who">__USER__</span>
  </div>
</header>
<main>
  <section class="list" id="list"><div class="empty">พิมพ์ค้นหาด้านบน</div></section>
  <section class="detail" id="detail"></section>
</main>
<script>
const $ = (id) => document.getElementById(id);
let ITEMS = [];
let DOC = null;
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, function(c) {
    if (c === "&") return "&amp;";
    if (c === "<") return "&lt;";
    if (c === ">") return "&gt;";
    if (c === '"') return "&quot;";
    return "&#39;";
  });
}
function fmtPrices(p) {
  if (!p) return "";
  return Object.entries(p).map(([k,v]) => `<span>${k} ${Number(v).toLocaleString()}</span>`).join("");
}
function imgErr(el) { el.style.display="none"; }
let _t = null;
function scheduleGo() {
  clearTimeout(_t);
  _t = setTimeout(() => go(), 350);
}
async function go(ev) {
  if (ev) ev.preventDefault();
  const q = $("q").value.trim();
  const site = $("site").value;
  const skip = $("skip").checked ? "1" : "0";
  if (!q) return false;
  $("list").innerHTML = "<div class='empty'>กำลังค้น…</div>";
  $("detail").innerHTML = "";
  try {
    const r = await fetch("/parts9/api/search?site="+encodeURIComponent(site)+"&include_skip="+skip+"&q="+encodeURIComponent(q));
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
function render(data) {
  const products = data.products || [];
  DOC = data.document || null;
  ITEMS = products;
  if (!products.length && !DOC) {
    $("list").innerHTML = "<div class='empty'>ไม่พบ "+esc(data.error||"")+"</div>";
    return;
  }
  let html = "";
  if (DOC) {
    const h = DOC.header || {};
    html += "<button class='card' onclick='showDoc()'><div><strong>"+esc(DOC.kind)+" "+esc(h.BILLNO||h.DOCNO||h.VOUCNO||"")+"</strong><div class='meta'>"+esc(h.ACCTNAME||"")+"</div></div></button>";
  }
  products.forEach((p,i) => {
    const src = (p.photos && p.photos[0]) || "";
    html += "<button class='card' id='c"+i+"' onclick='showP("+i+")'><img class='thumb' src='"+src+"' onerror='imgErr(this)'/><div><strong>"+esc(p.bcode)+"</strong>"
      +(p.do_not_restock?" <span class='badge'>ไม่สั่งซ้ำ</span>":"")
      +"<div>"+esc(p.descr||p.pcode||"")+"</div><div class='meta'>"+esc(p.category||"")+" "+esc(p.code1_label||"")+" · คงเหลือ "+p.qtyoh2+" "+esc(p.ui1||"")+"</div><div class='prices'>"+fmtPrices(p.prices)+"</div></div></button>";
  });
  $("list").innerHTML = html || "<div class='empty'>ไม่พบ</div>";
  if (DOC && !products.length) showDoc();
  else if (products[0]) showP(0);
}
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
    +"<div class='meta'>"+esc(p.pcode)+" "+esc(p.mcode)+" · "+esc(p.brand)+" "+esc(p.model)+"</div>"
    +"<div class='meta'>"+esc(p.category)+" · "+esc(p.code1_label||"")+" · "+esc(sizes.join(" / "))+"</div>"
    +"<div class='meta'>ที่เก็บ "+esc(p.location1)+" "+esc(p.location2)+" · "+esc(p.ui1)+"/"+esc(p.ui2)+"</div>"
    +"<div class='prices'>"+fmtPrices(p.prices)+"</div><div class='photos'>"+photos+"</div>"
    +"<p class='meta'>คงเหลือ QTYOH2 = "+p.qtyoh2+" "+esc(p.ui1)+(p.do_not_restock?" (ไม่สั่งซ้ำ)":"")+"</p>"
    +"<div id='more' class='empty'>โหลดความเคลื่อนไหว…</div>";
  fetch("/parts9/api/product/"+encodeURIComponent(p.bcode)+"?site="+encodeURIComponent($("site").value))
    .then(r => r.json()).then(d => {
      const m = d.movement || {};
      function tbl(title, rows, cols) {
        if (!rows || !rows.length) return "<p class='meta'>"+title+": —</p>";
        const head = cols.map(c => "<th>"+c+"</th>").join("");
        const body = rows.map(row => "<tr>"+cols.map(c => "<td>"+esc(row[c]||"")+"</td>").join("")+"</tr>").join("");
        return "<h3>"+title+"</h3><table><thead><tr>"+head+"</tr></thead><tbody>"+body+"</tbody></table>";
      }
      $("more").innerHTML =
        tbl("ขายล่าสุด", m.sales, ["BILLNO","BILLDATE","QTY","UI","PRICE","AMOUNT"]) +
        tbl("PO", m.po, ["DOCNO","DOCDATE","QTY","UI","PRICE","AMOUNT"]) +
        tbl("ICLOW", m.iclow, ["DOCNO","DOCDATE","ORDERED","RECEIVED","CANCELED"]);
    }).catch(() => { $("more").innerHTML = ""; });
}
function showDoc() {
  const doc = DOC;
  if (!doc) return;
  const h = doc.header || {};
  const keys = Object.keys(h);
  const rows = (doc.lines||[]);
  const cols = rows[0] ? Object.keys(rows[0]) : [];
  $("detail").innerHTML = "<h2>"+esc(doc.kind).toUpperCase()+"</h2><table>"
    +keys.map(k => "<tr><th>"+esc(k)+"</th><td>"+esc(h[k]||"")+"</td></tr>").join("")+"</table>"
    +(rows.length ? "<h3>บรรทัด</h3><table><thead><tr>"+cols.map(c=>"<th>"+esc(c)+"</th>").join("")+"</tr></thead><tbody>"
      +rows.map(r=>"<tr>"+cols.map(c=>"<td>"+esc(r[c]||"")+"</td>").join("")+"</tr>").join("")+"</tbody></table>" : "");
}
$("site").addEventListener("change", () => { if ($("q").value.trim()) go(); });
$("q").addEventListener("input", scheduleGo);
$("q").addEventListener("search", () => go());
$("skip").addEventListener("change", () => { if ($("q").value.trim()) go(); });
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

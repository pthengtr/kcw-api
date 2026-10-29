from __future__ import annotations

APP = "kcw-to-bill"
SESSION_COOKIE = "kcw_to_bill"

_PAGE = """<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ใบเต็มออนไลน์</title>
<style>
:root { color-scheme: light; }
body { margin:0; font-family: Prompt, "Noto Sans Thai", sans-serif; color:#111; background:#f6f7f9; }
header { display:flex; justify-content:space-between; gap:12px; align-items:center; padding:14px 16px; background:#fff; border-bottom:3px solid #9b1c2c; }
h1 { margin:0; font-size:20px; }
header p { margin:2px 0 0; color:#667085; font-size:13px; }
main { max-width:1100px; margin:0 auto; padding:16px; display:grid; gap:14px; }
.panel { background:#fff; border:1px solid #e4e7ec; border-radius:12px; padding:14px; }
.row { display:flex; gap:8px; flex-wrap:wrap; }
input, select, textarea, button { font:inherit; }
input, select, textarea { border:1px solid #d0d5dd; border-radius:8px; padding:8px 10px; background:#fff; }
textarea { min-height:5.5rem; width:100%; box-sizing:border-box; }
button, .btn { border:0; border-radius:8px; padding:8px 12px; background:#9b1c2c; color:#fff; cursor:pointer; text-decoration:none; display:inline-block; }
button.ghost, a.ghost { background:#fff; color:#344054; border:1px solid #d0d5dd; }
button:disabled { opacity:.55; cursor:default; }
.hit, .inv { border:1px solid #eaecf0; border-radius:10px; padding:10px 12px; margin-top:8px; }
.meta { color:#667085; font-size:13px; margin-top:4px; }
.chip { display:inline-block; border-radius:999px; padding:2px 8px; font-size:12px; background:#f2f4f7; margin-right:6px; }
.chip.warn { background:#fef0c7; }
.chip.bad { background:#fee4e2; }
.chip.ok { background:#dcfae6; }
.grid { display:grid; grid-template-columns:1.1fr .9fr; gap:14px; }
.lines { width:100%; border-collapse:collapse; font-size:13px; }
.lines th, .lines td { border-bottom:1px solid #eaecf0; padding:6px 4px; text-align:left; vertical-align:top; }
.num { text-align:right; white-space:nowrap; }
.banner { background:#fef0c7; border-radius:8px; padding:8px 10px; margin-bottom:10px; }
.err { color:#b42318; }
.field { display:grid; gap:4px; margin-bottom:8px; font-size:14px; }
.field span { color:#475467; font-size:12px; }
.actions { display:flex; gap:8px; flex-wrap:wrap; margin-top:10px; }
@media (max-width:800px) { .grid { grid-template-columns:1fr; } }
.tof { font-family: Prompt, "Noto Sans Thai", sans-serif; color:#111; background:#fff; padding:18px 16px 22px; max-width:860px; margin:0 auto; position:relative; line-height:1.45; }
.tof + .tof { margin-top:28px; border-top:1px dashed #d0d5dd; padding-top:28px; }
.tof .top { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }
.tof .brand { min-width:0; flex:1; }
.tof .logo { font-weight:800; font-size:34px; color:#9b1c2c; letter-spacing:-.03em; line-height:.9; }
.tof .co { font-weight:700; font-size:15px; margin-top:2px; }
.tof .addr { font-size:12px; line-height:1.45; }
.tof .doc { text-align:right; flex:0 0 auto; }
.tof h1 { margin:0; color:#9b1c2c; font-size:17px; line-height:1.25; font-weight:800; white-space:nowrap; }
.tof .mark { margin:2px 0 0; color:#344054; font-size:14px; font-weight:700; }
.tof .doc .no { display:block; margin:6px 0 0; font-size:20px; font-weight:800; }
.tof .rule { height:3px; background:#9b1c2c; margin:8px 0 12px; }
.tof .boxes, .tof .foot { display:grid; grid-template-columns:1.2fr .8fr; gap:10px 12px; align-items:start; }
.tof .box { border:1px solid #d0d5dd; border-radius:8px; padding:8px 10px; min-height:8rem; font-size:13px; }
.tof .who, .tof .fields, .tof .sig-fields { display:grid; grid-template-columns:max-content minmax(0, 1fr); column-gap:12px; row-gap:4px; align-items:baseline; }
.tof .fields { margin-top:4px; }
.tof .k, .tof .sig-fields > span:nth-child(odd) { color:#344054; font-weight:650; white-space:nowrap; }
.tof .name, .tof .fields .no { font-weight:800; }
.tof .wide-v { white-space:nowrap; }
.tof .pre { white-space:pre-line; }
.tof table { width:100%; border-collapse:collapse; font-size:12px; margin-top:12px; }
.tof th { background:#7a1f33; color:#fff; text-align:left; padding:6px; white-space:nowrap; }
.tof td { border-bottom:1px solid #eadfe3; padding:6px; vertical-align:top; }
.tof td.num, .tof th.num { text-align:right; white-space:nowrap; }
.tof td.ctr, .tof th.ctr { text-align:center; }
.tof .foot { margin-top:12px; }
.tof .note { font-size:13px; line-height:1.5; }
.tof .note .keep { white-space:nowrap; }
.tof .tot .row { display:flex; justify-content:space-between; gap:12px; font-size:13px; }
.tof .net { background:#f2f4f7; font-weight:800; font-size:15px; padding:6px 8px; margin-top:4px; }
.tof .words { text-align:right; font-size:12px; margin-top:4px; }
.tof .sign { display:grid; grid-template-columns:1fr 1fr 1fr; gap:16px; margin-top:28px; font-size:12px; break-inside:avoid; page-break-inside:avoid; }
.tof .sign h3 { margin:0 0 4px; font-size:12px; font-weight:700; text-align:center; line-height:1.35; }
.tof .hand { height:28px; }
.tof .sig-fields { row-gap:7px; align-items:end; }
.tof .sig-fields .line { border-bottom:1px solid #111; min-height:1.15rem; }
.tof .void { position:absolute; inset:30% 8% auto; text-align:center; font-size:64px; color:rgba(180,35,24,.28); font-weight:800; transform:rotate(-12deg); pointer-events:none; }
.tof .reason { color:#b42318; }
@media screen and (max-width:700px) {
  .tof .top, .tof .boxes, .tof .foot, .tof .sign { display:grid; grid-template-columns:1fr; }
  .tof .doc { text-align:left; max-width:none; }
}
@media print {
  @page { size:A4 portrait; margin:0; }
  header, .noprint, #searchPanel, #listPanel { display:none !important; }
  body { background:#fff; margin:0; }
  main { max-width:none; margin:0; padding:0; }
  .panel { border:0; padding:0; border-radius:0; }
  .tof { max-width:none; margin:0; padding:12mm 12mm 10mm; box-sizing:border-box; }
  .tof + .tof { margin-top:0; border-top:0; break-before:page; page-break-before:always; padding:12mm 12mm 10mm; }
}
</style>
</head>
<body>
<header>
  <div>
    <h1>ใบเต็มออนไลน์</h1>
    <p id="who"></p>
  </div>
  <div class="row noprint">
    <button type="button" class="ghost" id="showSearch">ค้นหา</button>
    <button type="button" class="ghost" id="showList">รายการเดือนนี้</button>
  </div>
</header>
<main>
  <section class="panel noprint" id="searchPanel">
    <form id="searchForm" class="row">
      <input id="q" placeholder="TAD6910-014 หรือเลขออเดอร์" autocomplete="off" style="flex:1; min-width:16rem">
      <button type="submit">ค้นหา</button>
    </form>
    <div id="hits"></div>
  </section>
  <section class="panel noprint" id="listPanel" hidden>
    <form id="listForm" class="row">
      <input id="yymm" placeholder="6910" maxlength="4" style="width:6rem">
      <select id="status">
        <option value="">ทั้งหมด</option>
        <option value="draft">ฉบับร่าง</option>
        <option value="issued">ออกแล้ว</option>
        <option value="void">ยกเลิก</option>
      </select>
      <input id="lq" placeholder="เลขที่ หรือชื่อผู้ซื้อ" style="flex:1; min-width:12rem">
      <button type="submit">แสดง</button>
    </form>
    <div id="list"></div>
  </section>
  <section class="panel" id="editor" hidden></section>
</main>
<script>
const who = document.getElementById("who");
who.textContent = __USER__;
const editor = document.getElementById("editor");
const hits = document.getElementById("hits");
const list = document.getElementById("list");
let current = null;

function esc(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}
function money(value) {
  const n = Number(value || 0);
  return n.toLocaleString("th-TH", {minimumFractionDigits:2, maximumFractionDigits:2});
}
async function api(path, options) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.message || data.error || "ไม่สำเร็จ");
  return data;
}
function chip(hit) {
  const parts = [];
  if (hit.canceled) parts.push("<span class='chip bad'>ยกเลิกใน KSS</span>");
  if (hit.open && hit.open.status === "issued") parts.push(`<span class="chip ok">ออกแล้ว ${esc(hit.open.docno)}</span>`);
  else if (hit.open && hit.open.status === "draft") parts.push("<span class='chip warn'>ฉบับร่าง</span>");
  else if (!hit.canceled) parts.push("<span class='chip'>ยังไม่มีใบเต็ม</span>");
  return parts.join(" ");
}
function renderHits(rows) {
  if (!rows.length) { hits.innerHTML = "<p class='meta'>ไม่พบ TAD</p>"; return; }
  hits.innerHTML = rows.map(hit => `
    <article class="hit">
      <strong>${esc(hit.billno)}</strong>
      ${chip(hit)}
      <div class="meta">${esc(hit.bill_date || "")} · ${money(hit.aftertax)} บาท
        ${hit.online_po ? " · ออเดอร์ " + esc(hit.online_po) : ""}</div>
      <div class="meta">ชื่อใน KSS ${esc(hit.acctname || "—")}</div>
      ${hit.shop_label ? `<div class="meta">ร้านค้า ${esc(hit.shop_label)}</div>` : ""}
      <div class="actions"><button type="button" data-open="${esc(hit.billno)}" ${hit.canceled && !hit.open ? "disabled" : ""}>${hit.open ? "เปิด" : "สร้างใบเต็ม"}</button></div>
    </article>
  `).join("");
}
function branchFields(inv) {
  const branch = inv.branch_label || "สำนักงานใหญ่";
  const isBranch = branch.startsWith("สาขาที่");
  const no = isBranch ? branch.replace(/[^0-9]/g, "") : "";
  return `
    <label class="field"><span>สาขา</span>
      <select id="branch">
        <option value="hq" ${isBranch ? "" : "selected"}>สำนักงานใหญ่</option>
        <option value="branch" ${isBranch ? "selected" : ""}>สาขาที่</option>
      </select>
    </label>
    <label class="field" id="branchNoField" ${isBranch ? "" : "hidden"}><span>เลขสาขา</span>
      <input id="branchNo" value="${esc(no)}" inputmode="numeric">
    </label>`;
}
function renderEditor(inv) {
  current = inv;
  editor.hidden = false;
  if (inv.status !== "draft") {
    editor.innerHTML = `
      <div class="noprint actions">
        <strong style="font-size:22px">${esc(inv.docno || "")}</strong>
        <button type="button" id="printBtn">พิมพ์</button>
        ${inv.status === "issued" ? "<button type='button' class='ghost' id='voidBtn'>ยกเลิกเอกสาร</button>" : ""}
      </div>
      ${inv.kss_canceled_now ? "<p class='banner noprint'>TAD ถูกยกเลิกใน KSS หลังออกเอกสาร เอกสารนี้ไม่ถูกยกเลิกอัตโนมัติ</p>" : ""}
      <div id="sheet">${inv.sheet_html || ""}</div>`;
    return;
  }
  const prefill = inv.armas_prefill;
  editor.innerHTML = `
    <div class="grid">
      <div>
        <h2 style="margin:0 0 8px">${esc(inv.tad_billno)} <span class="chip">ฉบับร่าง</span></h2>
        ${inv.kss_canceled ? "<p class='banner'>บิลนี้ถูกยกเลิกใน KSS ออกเอกสารไม่ได้</p>" : ""}
        ${inv.kss_changed ? "<p class='banner'>ยอดใน KSS เปลี่ยนจากฉบับร่าง กดดึงจาก KSS อีกครั้งก่อนออกเอกสาร</p>" : ""}
        <p class="meta">ชื่อใน KSS ${esc(inv.acctname_kss || "—")}
          ${inv.online_po ? " · ออเดอร์ " + esc(inv.online_po) : ""}</p>
        ${inv.shop_label ? `<p class="meta">ร้านค้า ${esc(inv.shop_label)}</p>` : ""}
        <table class="lines">
          <thead><tr><th>รหัส</th><th>รายละเอียด</th><th class="num">จำนวน</th><th class="num">ราคา</th><th class="num">จำนวนเงิน</th></tr></thead>
          <tbody>
            ${(inv.lines || []).map(line => `<tr>
              <td>${esc(line.bcode)}</td><td>${esc(line.detail)}</td>
              <td class="num">${esc(line.qty)} ${esc(line.ui)}</td>
              <td class="num">${money(line.price)}</td>
              <td class="num">${money(line.amount)}</td></tr>`).join("") || "<tr><td colspan='5'>ไม่มีรายการ</td></tr>"}
          </tbody>
        </table>
        <p class="meta">ก่อนภาษี ${money(inv.beforetax)} · ภาษี ${money(inv.tax)} · รวม ${money(inv.aftertax)}</p>
        <div class="actions">
          <button type="button" class="ghost" id="refreshBtn">ดึงจาก KSS อีกครั้ง</button>
          ${prefill ? "<button type='button' class='ghost' id='prefillBtn'>เติมจากบัญชี KSS</button>" : ""}
        </div>
      </div>
      <form id="buyerForm">
        <label class="field"><span>ชื่อผู้ซื้อ</span><input id="customerName" required value="${esc(inv.customer_name)}"></label>
        <label class="field"><span>ที่อยู่</span><textarea id="address" required>${esc(inv.address)}</textarea></label>
        <label class="field"><span>เลขประจำตัวผู้เสียภาษี</span><input id="taxId" inputmode="numeric" maxlength="17" value="${esc(inv.tax_id)}" autocomplete="off"></label>
        <div id="buyerHits"></div>
        ${branchFields(inv)}
        <label class="field"><span>โทร</span><input id="phone" value="${esc(inv.phone)}"></label>
        <label class="field"><span>อีเมล</span><input id="email" value="${esc(inv.email)}"></label>
        <p class="meta" id="nextNo">${inv.seller_ready ? "เลขถัดไปโดยประมาณ " + esc(inv.next_docno || "") + " — เลขจริงจองตอนออกเอกสาร" : "ยังตั้งเลขผู้เสียภาษีผู้ขายไม่ได้ จึงออกเอกสารไม่ได้"}</p>
        <p class="err" id="formErr"></p>
        <div class="actions">
          <button type="button" class="ghost" id="saveBtn">บันทึกฉบับร่าง</button>
          <button type="button" id="issueBtn" ${inv.kss_canceled ? "disabled" : ""}>ออกเอกสาร</button>
        </div>
      </form>
    </div>`;
  const branch = document.getElementById("branch");
  branch.addEventListener("change", () => {
    document.getElementById("branchNoField").hidden = branch.value !== "branch";
  });
  document.getElementById("taxId").addEventListener("input", suggestBuyers);
}
function payload() {
  const branch = document.getElementById("branch").value;
  return {
    customer_name: document.getElementById("customerName").value,
    address: document.getElementById("address").value,
    tax_id: document.getElementById("taxId").value,
    branch_label: branch === "branch" ? "สาขาที่" : "สำนักงานใหญ่",
    branch_no: branch === "branch" ? document.getElementById("branchNo").value : "",
    phone: document.getElementById("phone").value,
    email: document.getElementById("email").value
  };
}
function applyBuyer(row) {
  document.getElementById("customerName").value = row.customer_name || "";
  document.getElementById("address").value = row.address || "";
  document.getElementById("taxId").value = row.tax_id || "";
  document.getElementById("phone").value = row.phone || "";
  document.getElementById("email").value = row.email || "";
}
async function suggestBuyers() {
  const q = document.getElementById("taxId").value.trim();
  const host = document.getElementById("buyerHits");
  if (q.length < 3) { host.innerHTML = ""; return; }
  const data = await api("/to-bill/api/buyers?q=" + encodeURIComponent(q));
  host.innerHTML = (data.buyers || []).map((row, i) =>
    `<button type="button" class="ghost" data-buyer="${i}">${esc(row.customer_name)} · ${esc(row.tax_id)}</button>`
  ).join(" ");
  host.querySelectorAll("[data-buyer]").forEach(btn => {
    btn.addEventListener("click", () => applyBuyer(data.buyers[Number(btn.dataset.buyer)]));
  });
}
async function openBill(billno) {
  editor.hidden = false;
  editor.innerHTML = "<p class='meta'>กำลังเปิด</p>";
  try {
    const inv = await api("/to-bill/api/drafts", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify({tad_billno: billno})
    });
    renderEditor(inv);
  } catch (err) {
    editor.innerHTML = `<p class="err">${esc(err.message)}</p>`;
  }
}
async function openId(id) {
  editor.hidden = false;
  editor.innerHTML = "<p class='meta'>กำลังเปิด</p>";
  try { renderEditor(await api("/to-bill/api/invoices/" + id)); }
  catch (err) { editor.innerHTML = `<p class="err">${esc(err.message)}</p>`; }
}
document.getElementById("searchForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  hits.innerHTML = "<p class='meta'>กำลังค้นหา</p>";
  try {
    const data = await api("/to-bill/api/search?q=" + encodeURIComponent(document.getElementById("q").value));
    renderHits(data.hits || []);
  } catch (err) {
    hits.innerHTML = `<p class="err">${esc(err.message)}</p>`;
  }
});
hits.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-open]");
  if (btn) openBill(btn.dataset.open);
});
document.getElementById("showSearch").addEventListener("click", () => {
  document.getElementById("searchPanel").hidden = false;
  document.getElementById("listPanel").hidden = true;
});
document.getElementById("showList").addEventListener("click", () => {
  document.getElementById("searchPanel").hidden = true;
  document.getElementById("listPanel").hidden = false;
  document.getElementById("listForm").requestSubmit();
});
document.getElementById("listForm").addEventListener("submit", async (event) => {
  event.preventDefault();
  const params = new URLSearchParams({
    yymm: document.getElementById("yymm").value,
    status: document.getElementById("status").value,
    q: document.getElementById("lq").value
  });
  list.innerHTML = "<p class='meta'>กำลังโหลด</p>";
  try {
    const data = await api("/to-bill/api/invoices?" + params.toString());
    document.getElementById("yymm").value = data.yymm || "";
    const rows = data.rows || [];
    list.innerHTML = rows.length ? rows.map(row => `
      <article class="inv">
        <button type="button" class="ghost" data-id="${esc(row.invoice_id)}">${esc(row.docno || row.tad_billno)}</button>
        <span class="chip">${esc(row.status)}</span>
        <div class="meta">${esc(row.customer_name || "ยังไม่ระบุผู้ซื้อ")} · ${esc(row.tad_billno)} · ${money(row.aftertax)}</div>
      </article>`).join("") : "<p class='meta'>ไม่มีเอกสารในเดือนนี้</p>";
  } catch (err) {
    list.innerHTML = `<p class="err">${esc(err.message)}</p>`;
  }
});
list.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-id]");
  if (btn) openId(btn.dataset.id);
});
editor.addEventListener("click", async (event) => {
  const id = current && current.invoice_id;
  if (!id) return;
  if (event.target.id === "refreshBtn") {
    try { renderEditor(await api(`/to-bill/api/invoices/${id}/refresh`, {method:"POST"})); }
    catch (err) { document.getElementById("formErr").textContent = err.message; }
  }
  if (event.target.id === "prefillBtn" && current.armas_prefill) applyBuyer(current.armas_prefill);
  if (event.target.id === "saveBtn") {
    try { renderEditor(await api(`/to-bill/api/invoices/${id}/buyer`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload())})); }
    catch (err) { document.getElementById("formErr").textContent = err.message; }
  }
  if (event.target.id === "issueBtn") {
    const next = current.next_docno ? ("ออกเอกสารเลขประมาณ " + current.next_docno + String.fromCharCode(10) + "เลขจริงจองตอนบันทึก") : "ออกเอกสาร";
    if (!confirm(next)) return;
    try { renderEditor(await api(`/to-bill/api/invoices/${id}/issue`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify(payload())})); }
    catch (err) { const el = document.getElementById("formErr"); if (el) el.textContent = err.message; }
  }
  if (event.target.id === "printBtn") {
    try { await api(`/to-bill/api/invoices/${id}/printed`, {method:"POST"}); } catch (err) {}
    window.print();
  }
  if (event.target.id === "voidBtn") {
    const reason = prompt("เหตุผลที่ยกเลิก");
    if (!reason) return;
    try { renderEditor(await api(`/to-bill/api/invoices/${id}/void`, {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({reason})})); }
    catch (err) { alert(err.message); }
  }
});
const params = new URLSearchParams(location.search);
if (params.get("tad")) openBill(params.get("tad"));
</script>
</body>
</html>
"""


def page(*, user_name: str) -> str:
    safe = (user_name or "").replace("\\", "\\\\").replace("</", "<\\/").replace('"', '\\"')
    return _PAGE.replace("__USER__", f'"{safe}"')

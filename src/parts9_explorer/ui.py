from __future__ import annotations

import json

from src.bot.branch_link_buttons import BRANCH_LABEL
from src.parts9_explorer.query import CATEGORY_LABELS, CODE1_LABELS, SIZE_LABELS

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
  --field-h:2.75rem; --field-pad-y:.62rem; --field-pad-x:.75rem;
  --field-radius:.6rem; --field-font:1rem;
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
.brand { display:flex; align-items:flex-start; justify-content:space-between; gap:.6rem; margin:0 0 .5rem; }
.brand-title { flex:1; min-width:0; }
.brand-actions { display:flex; gap:.35rem; align-items:center; flex-shrink:0; }
.search-summary { font-size:.78rem; color:var(--muted); margin:.2rem 0 0; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; display:none; }
header.search-collapsed .search-summary { display:block; }
button.search-toggle { font-size:.82rem; padding:.45rem .65rem; white-space:nowrap; }
h1 { font-size:1.02rem; margin:0; letter-spacing:.02em; }
.row { display:flex; gap:.45rem; flex-wrap:wrap; align-items:center; }
.search-form { display:grid; gap:.5rem; align-items:end; grid-template-columns:1fr; }
.search-main { min-width:0; width:100%; display:flex; flex-direction:column; gap:.35rem; }
.search-main #productFilters { display:none; }
.search-main.mode-product #productFilters { display:grid; }
.product-filters { gap:.45rem; grid-template-columns:1fr; width:100%; }
@media (min-width:560px) {
  .product-filters { grid-template-columns:1fr 1fr; }
}
.search-main #codeSizePanel { display:none; }
.search-main.mode-code-size #q { display:none; }
.search-main.mode-code-size #codeSizePanel { display:flex; }
.search-actions { display:flex; flex-wrap:wrap; gap:.45rem; align-items:center; }
#site { min-width:5.5rem; }
#searchBtn { flex:1; min-width:6.5rem; }
input[type=search], .field-inp, #code1, #category, #sort, #site, #searchBtn {
  font: inherit; font-size:var(--field-font); line-height:1.25;
  min-height:var(--field-h); padding:var(--field-pad-y) var(--field-pad-x);
  border-radius:var(--field-radius); border:1px solid var(--line); background:var(--inset); color:var(--text);
}
input[type=search], .field-inp, #code1, #category, #sort, #site { width:100%; }
button, select { font: inherit; font-size:.92rem; padding:.6rem .75rem; border-radius:.55rem; border:1px solid var(--line); background:var(--chip); color:var(--text); }
#searchBtn { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:650; font-size:var(--field-font); }
input[type=search] { -webkit-appearance:none; appearance:none; }
#q { width:100%; min-width:0; }
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:650; }
button.theme { min-width:2.6rem; padding:.55rem .65rem; }
.code-size-panel { flex-direction:column; gap:.35rem; width:100%; }
.code-size-fields { display:grid; gap:.45rem; align-items:end; width:100%; grid-template-columns:1fr; }
.code-field { min-width:0; }
.size-fields { display:grid; gap:.45rem; grid-template-columns:1fr; min-width:0; }
.field { display:flex; flex-direction:column; gap:.2rem; min-width:0; }
.field-lbl { font-size:.75rem; color:var(--muted); line-height:1.2; }
.size-slot[hidden] { display:none !important; }
.code-size-hint { font-size:.78rem; margin:0; color:var(--muted); line-height:1.35; }
button.primary:disabled { opacity:.45; cursor:not-allowed; }
@media (min-width:560px) {
  .search-form { grid-template-columns:1fr auto; }
  .search-actions { flex-wrap:nowrap; }
  #searchBtn { flex:0 0 auto; min-width:5.5rem; }
  .code-size-fields { grid-template-columns:1fr 1fr; }
  .code-field { grid-column:1 / -1; }
  .size-fields { grid-column:1 / -1; grid-template-columns:repeat(3,1fr); }
}
@media (min-width:768px) {
  .code-size-fields { grid-template-columns:minmax(9rem,1.1fr) repeat(3,minmax(4.5rem,1fr)); }
  .code-field { grid-column:auto; }
  .size-fields { display:contents; grid-column:auto; grid-template-columns:none; }
}
@media (min-width:880px) {
  .search-form { gap:.55rem; }
  .code-size-fields { grid-template-columns:minmax(11rem,1.15fr) repeat(3,minmax(5rem,1fr)); }
}
@media (max-width:879px) {
  .search-actions { width:100%; }
  label.chk { flex:1 1 100%; }
  header.search-collapsed { padding-bottom:.55rem; }
  header.search-collapsed .search-panel { display:none; }
  button.search-toggle { display:inline-flex; }
}
@media (min-width:880px) {
  button.search-toggle { display:none; }
  .search-summary { display:none !important; }
}
@media (max-width:559px) {
  .search-actions { width:100%; }
}
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
<header id="hdr">
  <div class="brand">
    <div class="brand-title">
      <h1>PARTS9 explorer</h1>
      <p class="search-summary" id="searchSummary" aria-live="polite"></p>
    </div>
    <div class="brand-actions">
      <button type="button" class="search-toggle" id="searchToggle" aria-expanded="true" aria-controls="searchPanel">ซ่อน</button>
      <button type="button" class="theme" id="themeBtn" aria-label="สลับธีม">มืด</button>
    </div>
  </div>
  <div class="search-panel" id="searchPanel">
  <form class="search-form" id="f" onsubmit="go(event); return false;">
    <div class="search-main">
      <div class="product-filters" id="productFilters">
        <label class="field" id="categoryField" for="category">
          <span class="field-lbl">หมวดสินค้า</span>
          <select id="category" aria-label="หมวดสินค้า">
            <option value="">— ทุกหมวด —</option>
          </select>
        </label>
        <label class="field" id="sortField" for="sort">
          <span class="field-lbl">เรียงตาม</span>
          <select id="sort" aria-label="เรียงตาม">
            <option value="relevance">ตรงที่สุด</option>
            <option value="bcode">รหัส A→Z</option>
            <option value="bcode_desc">รหัส Z→A</option>
            <option value="price">ราคาต่ำ→สูง</option>
            <option value="price_desc">ราคาสูง→ต่ำ</option>
            <option value="descr">ชื่อสินค้า</option>
            <option value="qty_desc">คงเหลือมาก→น้อย</option>
            <option value="qty">คงเหลือน้อย→มาก</option>
          </select>
        </label>
      </div>
      <input id="q" type="search" enterkeyhint="search" autocomplete="off" placeholder="รหัส / เบอร์แท้ / เบอร์โรงงาน / ชื่อย่อ นมฮPT / I K ซีล / PO เลขบิล" autofocus />
      <div id="codeSizePanel" class="code-size-panel" aria-hidden="true">
        <div class="code-size-fields">
          <label class="field code-field" for="code1">
            <span class="field-lbl">ประเภท</span>
            <select id="code1" aria-label="ประเภทชิ้นส่วน">
              <option value="">— เลือกประเภท —</option>
            </select>
          </label>
          <div class="size-fields" id="sizeFields" aria-live="polite">
            <label class="field size-slot" data-slot="1" hidden><span class="field-lbl size-lbl"></span><input class="field-inp size-inp" type="text" inputmode="decimal" autocomplete="off" enterkeyhint="next"/></label>
            <label class="field size-slot" data-slot="2" hidden><span class="field-lbl size-lbl"></span><input class="field-inp size-inp" type="text" inputmode="decimal" autocomplete="off" enterkeyhint="next"/></label>
            <label class="field size-slot" data-slot="3" hidden><span class="field-lbl size-lbl"></span><input class="field-inp size-inp" type="text" inputmode="decimal" autocomplete="off" enterkeyhint="search"/></label>
          </div>
        </div>
        <p class="code-size-hint" id="codeSizeHint">เลือกประเภทชิ้นส่วน แล้วกรอกขนาด (กรอกบางช่องก็ค้นได้)</p>
      </div>
    </div>
    <div class="search-actions">
      <select id="site">
        <option value="hq" __HQSEL__>__HQ_LABEL__</option>
        <option value="syp" __SYPSEL__>__SYP_LABEL__</option>
      </select>
      <button class="primary" type="submit" id="searchBtn">ค้นหา</button>
      <label class="chk"><input type="checkbox" id="skip"/> รวมไม่สั่งซ้ำ</label>
    </div>
  </form>
  <div class="modes" id="modes">
    <button type="button" data-k="all" class="on">ทั้งหมด</button>
    <button type="button" data-k="product">สินค้า</button>
    <button type="button" data-k="code_size">รหัส+ขนาด</button>
    <button type="button" data-k="si">SI บิลขาย</button>
    <button type="button" data-k="pi">PI บิลซื้อ</button>
    <button type="button" data-k="po">PO สั่งซื้อ</button>
    <button type="button" data-k="pv">PV จ่าย</button>
    <button type="button" data-k="rv">RV รับ</button>
    <button type="button" data-k="iclow">ICLOW ค้างรับ</button>
  </div>
  <div class="row" style="margin-top:.45rem">
    <span class="badge __HQBADGE__">__HQ_LABEL__ SQL __HQSQL__</span>
    <span class="badge __SYPBADGE__">__SYP_LABEL__ SQL __SYPSQL__</span>
    <span class="who">__USER__</span>
  </div>
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
  {id:"code_size", label:"รหัส+ขนาด"},
  {id:"si", label:"SI บิลขาย"},
  {id:"pi", label:"PI บิลซื้อ"},
  {id:"po", label:"PO สั่งซื้อ"},
  {id:"pv", label:"PV จ่าย"},
  {id:"rv", label:"RV รับ"},
  {id:"iclow", label:"ICLOW ค้างรับ"},
];
const PLACE = {
  all: "รหัส / เบอร์แท้ PCODE / เบอร์โรงงาน MCODE / ชื่อย่อ นมฮPT ลป / I K ซีล 31 46 / PO เลขบิล",
  product: "รหัสสินค้า / เบอร์แท้ / เบอร์โรงงาน / ชื่อย่อ ACODE / I K C ซีล 31 46 / ยี่ห้อ",
  code_size: "ประเภท + ขนาด — C หรือ ซีล 31×46×7 · I นอก 72 หนา 17",
  si: "เลขบิลขาย เช่น 8K69-0013225",
  pi: "เลขบิลซื้อ / เลขโน้ต / เลขใบสำคัญจ่าย",
  po: "เลขใบสั่งซื้อ เช่น PO6905-392",
  pv: "เลขใบสำคัญจ่าย KCPN / P… หรือเลขโน้ต",
  rv: "เลขใบสำคัญรับ RC / RVI",
  iclow: "เลข PO / รหัสสินค้า / ผู้ขาย — ว่าง = สรุปค้างรับ",
};
const STATUS_TH = {pending:"ค้างรับ", received:"รับแล้ว", canceled:"ยกเลิก", to_order:"รอสั่ง"};
const COL_TH = {
  JOURTYPE:"ประเภทสมุด", VOUCED:"ผ่านใบสำคัญ", VOUCDATE:"วันที่ใบสำคัญ", VOUCNO:"เลขใบสำคัญ",
  NOTED:"ผ่านโน้ต", NOTEDATE:"วันที่โน้ต", NOTENO:"เลขโน้ต", RCPTNO:"เลขใบเสร็จ",
  ACCTNO:"รหัสบัญชี", ACCTNAME:"ชื่อบัญชี", BILLCNT:"จำนวนบิล", BILLAMT:"ยอดบิล",
  CHKAMT:"ยอดเช็ค", CASHAMT:"ยอดเงินสด", NETAMT:"ยอดสุทธิ", PAYAMT:"ยอดจ่าย",
  PAID:"ชำระแล้ว", CANCELED:"ยกเลิก", BILLNO:"เลขบิล", BILLDATE:"วันที่บิล",
  AFTERTAX:"ยอดหลังภาษี", CASHED:"รับเงินสด", SALE:"พนักงานขาย", PO:"เลข PO",
  BILLTYPE:"ประเภทบิล", REMARKS:"หมายเหตุ", VOUCNO1:"ใบสำคัญ 1", VOUCNO2:"ใบสำคัญ 2",
  DOCNO:"เลขเอกสาร", DOCDATE:"วันที่เอกสาร", BILLED:"ออกบิลแล้ว", VENDOR:"ผู้ขาย",
  DESCR:"รายละเอียด", DETAIL:"รายละเอียด", RCVDNO:"เลขใบรับ", RCVDDATE:"วันที่รับ",
  CHKNO:"เลขเช็ค", CHKDATE:"วันที่เช็ค", BANKNAME:"ธนาคาร", PAYTYPE:"ประเภทจ่าย",
  STATUS:"สถานะ", CARDNAME:"ชื่อบัตร", ORDERED:"สั่งแล้ว", RECEIVED:"รับแล้ว",
  LINE:"ลำดับ", BCODE:"รหัสสินค้า", QTY:"จำนวน", UI:"หน่วย", PRICE:"ราคา", AMOUNT:"จำนวนเงิน",
  status:"สถานะ",
  PRICE1:"ราคา 1", PRICE2:"ราคา 2", PRICE3:"ราคา 3", PRICE4:"ราคา 4", PRICE5:"ราคา 5",
  PRICEM1:"ราคาสมาชิก 1", PRICEM2:"ราคาสมาชิก 2", PRICEM3:"ราคาสมาชิก 3",
  PRICEM4:"ราคาสมาชิก 4", PRICEM5:"ราคาสมาชิก 5"
};
const MONEY_KEYS = new Set(["PRICE","AMOUNT","CHKAMT","AFTERTAX","BILLAMT","NETAMT","CASHAMT","PAYAMT"]);
const CODE1_LABELS = __CODE1_LABELS_JSON__;
const SIZE_LABELS = __SIZE_LABELS_JSON__;
const CATEGORY_LABELS = __CATEGORY_LABELS_JSON__;
const SORT_LABELS = {
  relevance: "ตรงที่สุด",
  bcode: "รหัส A→Z",
  bcode_desc: "รหัส Z→A",
  price: "ราคาต่ำ→สูง",
  price_desc: "ราคาสูง→ต่ำ",
  descr: "ชื่อสินค้า",
  qty_desc: "คงเหลือมาก→น้อย",
  qty: "คงเหลือน้อย→มาก",
};
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
function colTh(k) { return COL_TH[k] || k; }
function money(v) {
  const n = Number(String(v == null ? "" : v).replace(/,/g,""));
  if (!isFinite(n) || String(v).trim() === "") return esc(v || "");
  return n.toLocaleString("th-TH", {minimumFractionDigits: 2, maximumFractionDigits: 2});
}
function qty(v) {
  const n = Number(String(v == null ? "" : v).replace(/,/g,""));
  if (!isFinite(n) || String(v).trim() === "") return esc(v || "");
  return n.toLocaleString("th-TH", {maximumFractionDigits: 2});
}
function fmtPrices(p) {
  if (!p) return "";
  return Object.entries(p).map(([k,v]) => `<span>${esc(colTh(k))} ${Number(v).toLocaleString("th-TH")}</span>`).join("");
}
function codeBits(p) {
  const bits = [];
  if (p.code1) bits.push((p.code1_label ? p.code1+" "+p.code1_label : p.code1));
  if (p.acode) bits.push("ชื่อย่อ "+p.acode);
  if (p.pcode) bits.push("แท้ "+p.pcode);
  if (p.mcode) bits.push("โรงงาน "+p.mcode);
  if (p.brand || p.model) {
    const bm = [p.brand, p.model].filter(Boolean).join(" ");
    if (bm) bits.push(bm);
  }
  return bits.length ? "<div class='meta'>"+esc(bits.join(" · "))+"</div>" : "";
}
function sizeBits(p) {
  const line = p.size_display || "";
  return line ? "<div class='meta'>"+esc(line)+"</div>" : "";
}
function locBits(p) {
  const hq = (p.location_hq || "").trim();
  const syp = (p.location_syp || "").trim();
  const cur = (p.location || "").trim();
  if (hq || syp) {
    const bits = [];
    if (hq) bits.push("สนญ "+hq);
    if (syp) bits.push("สาขา "+syp);
    return "<div class='meta'>ที่เก็บ "+esc(bits.join(" · "))+"</div>";
  }
  return cur ? "<div class='meta'>ที่เก็บ "+esc(cur)+"</div>" : "";
}
function imgErr(el) { el.style.display="none"; }
const SEARCH_PANEL_KEY = "kcw.parts9.searchPanel";
function isMobileLayout() { return window.matchMedia("(max-width:879px)").matches; }
function searchSummaryText() {
  const mode = (MODES.find((m) => m.id === KIND) || {}).label || KIND;
  const q = currentQuery();
  const site = $("site") ? $("site").options[$("site").selectedIndex].text : "";
  const cat = $("category");
  const catLabel = cat && cat.value ? (CATEGORY_LABELS[cat.value] || cat.value) : "";
  const sort = $("sort");
  const sortKey = sort && sort.value ? sort.value : "relevance";
  const sortLabel = (sortKey !== "relevance") ? (SORT_LABELS[sortKey] || sortKey) : "";
  const parts = [mode];
  if (catLabel) parts.push(catLabel);
  if (sortLabel) parts.push("เรียง "+sortLabel);
  if (q) parts.push(q);
  if (site) parts.push(site);
  return parts.join(" · ");
}
function updateSearchSummary() {
  const el = $("searchSummary");
  if (el) el.textContent = searchSummaryText();
}
function setSearchPanelOpen(open) {
  const hdr = $("hdr");
  const btn = $("searchToggle");
  if (!hdr || !btn) return;
  if (!isMobileLayout()) {
    hdr.classList.remove("search-collapsed");
    btn.setAttribute("aria-expanded", "true");
    btn.textContent = "ซ่อน";
    return;
  }
  const show = !!open;
  hdr.classList.toggle("search-collapsed", !show);
  btn.setAttribute("aria-expanded", show ? "true" : "false");
  btn.textContent = show ? "ซ่อน" : "ค้นหา";
  updateSearchSummary();
  try { localStorage.setItem(SEARCH_PANEL_KEY, show ? "1" : "0"); } catch (e) {}
}
function collapseSearchPanelIfMobile() {
  if (isMobileLayout()) setSearchPanelOpen(false);
}
function expandSearchPanel() {
  setSearchPanelOpen(true);
}
function isCodeSizeMode() { return KIND === "code_size"; }
function isProductMode() { return KIND === "all" || KIND === "product" || KIND === "code_size"; }
function initCategorySelect() {
  const sel = $("category");
  if (!sel) return;
  Object.keys(CATEGORY_LABELS).sort().forEach((code) => {
    const opt = document.createElement("option");
    opt.value = code;
    opt.textContent = code + " — " + CATEGORY_LABELS[code];
    sel.appendChild(opt);
  });
}
function initCode1Select() {
  const sel = $("code1");
  if (!sel) return;
  Object.keys(CODE1_LABELS).sort().forEach((letter) => {
    const opt = document.createElement("option");
    opt.value = letter;
    opt.textContent = letter + " — " + CODE1_LABELS[letter];
    sel.appendChild(opt);
  });
}
function resetCodeSizeForm() {
  const sel = $("code1");
  if (sel) sel.value = "";
  document.querySelectorAll("#sizeFields .size-slot").forEach((slot) => {
    slot.hidden = true;
    const inp = slot.querySelector(".size-inp");
    if (inp) inp.value = "";
  });
  const hint = $("codeSizeHint");
  if (hint) hint.hidden = false;
  const panel = $("codeSizePanel");
  if (panel) panel.setAttribute("aria-hidden", "true");
}
function toggleSearchChrome() {
  const main = document.querySelector(".search-main");
  const panel = $("codeSizePanel");
  const q = $("q");
  if (!main || !panel || !q) return;
  main.classList.toggle("mode-product", isProductMode());
  if (isCodeSizeMode()) {
    main.classList.add("mode-code-size");
    panel.setAttribute("aria-hidden", "false");
    q.setAttribute("aria-hidden", "true");
    updateSearchButton();
  } else {
    main.classList.remove("mode-code-size");
    panel.setAttribute("aria-hidden", "true");
    q.setAttribute("aria-hidden", "false");
    resetCodeSizeForm();
    const btn = $("searchBtn");
    if (btn) btn.disabled = false;
  }
}
function renderSizeFields(code) {
  const labels = SIZE_LABELS[code] || [null, null, null];
  document.querySelectorAll("#sizeFields .size-slot").forEach((slot) => {
    const idx = parseInt(slot.dataset.slot, 10) - 1;
    const lbl = labels[idx];
    const inp = slot.querySelector(".size-inp");
    const lblEl = slot.querySelector(".size-lbl");
    if (lbl) {
      slot.hidden = false;
      lblEl.textContent = lbl;
      inp.setAttribute("aria-label", lbl + " ขนาด");
      inp.placeholder = lbl;
    } else {
      slot.hidden = true;
      inp.value = "";
    }
  });
  const hint = $("codeSizeHint");
  if (hint) hint.hidden = !!code;
  updateSearchButton();
  if (code) {
    const first = document.querySelector("#sizeFields .size-slot:not([hidden]) .size-inp");
    if (first) first.focus();
  }
}
function codeSizeValid() {
  const code = ($("code1") && $("code1").value) || "";
  if (!code) return false;
  return Array.from(document.querySelectorAll("#sizeFields .size-inp")).some((inp) => {
    const slot = inp.closest(".size-slot");
    return slot && !slot.hidden && inp.value.trim();
  });
}
function buildCodeSizeQuery() {
  const code = (($("code1") && $("code1").value) || "").trim();
  if (!code) return "";
  const labels = SIZE_LABELS[code] || [];
  const parts = [code];
  document.querySelectorAll("#sizeFields .size-slot").forEach((slot) => {
    if (slot.hidden) return;
    const idx = parseInt(slot.dataset.slot, 10) - 1;
    const lbl = labels[idx];
    const val = slot.querySelector(".size-inp").value.trim();
    if (lbl && val) parts.push(lbl, val);
  });
  return parts.join(" ");
}
function updateSearchButton() {
  const btn = $("searchBtn");
  if (!btn) return;
  btn.disabled = isCodeSizeMode() && !codeSizeValid();
}
function currentQuery() {
  if (isCodeSizeMode()) return buildCodeSizeQuery();
  return $("q").value.trim();
}
function setKind(k) {
  KIND = k;
  document.querySelectorAll("#modes button").forEach(b => b.classList.toggle("on", b.dataset.k === k));
  toggleSearchChrome();
  if (!isCodeSizeMode()) $("q").placeholder = PLACE[k] || PLACE.all;
  if (isMobileLayout()) setSearchPanelOpen(true);
  updateSearchSummary();
  if (k === "iclow" || currentQuery()) go();
  else if (k === "code_size") {
    $("list").innerHTML = "<div class='empty'>เลือกประเภทชิ้นส่วน แล้วกรอกขนาด (กรอกบางช่องก็ค้นได้)</div>";
    $("detail").innerHTML = "";
  }
  else { $("list").innerHTML = "<div class='empty'>พิมพ์ค้นหาด้านบน</div>"; $("detail").innerHTML = ""; }
}
function drawModes() {
  document.querySelectorAll("#modes button").forEach(b => b.classList.toggle("on", b.dataset.k === KIND));
}
let _t = null;
function scheduleGo() {
  clearTimeout(_t);
  // Live typing must not auto-hide the mobile search panel.
  _t = setTimeout(() => go(null, { collapse: false }), 380);
}
async function go(ev, opts) {
  if (ev && typeof ev.preventDefault === "function") ev.preventDefault();
  const collapse = !!(opts && opts.collapse) || !!(ev && ev.type === "submit");
  const q = currentQuery();
  const site = $("site").value;
  const skip = $("skip").checked ? "1" : "0";
  if (!q && KIND !== "iclow") return false;
  $("list").innerHTML = "<div class='empty'>กำลังค้น…</div>";
  $("detail").innerHTML = "";
  try {
    let url = "/parts9/api/search?site="+encodeURIComponent(site)+"&include_skip="+skip+"&kind="+encodeURIComponent(KIND)+"&q="+encodeURIComponent(q);
    const cat = $("category");
    if (cat && cat.value && isProductMode()) url += "&category="+encodeURIComponent(cat.value);
    const sort = $("sort");
    if (sort && sort.value && sort.value !== "relevance" && isProductMode()) {
      url += "&sort="+encodeURIComponent(sort.value);
    }
    const r = await fetch(url);
    const data = await r.json();
    if (!r.ok) {
      $("list").innerHTML = "<div class='empty'>"+esc(data.detail || ("HTTP "+r.status))+"</div>";
      return false;
    }
    render(data, { collapse });
  } catch (e) {
    $("list").innerHTML = "<div class='empty'>ค้นไม่สำเร็จ "+esc(e && e.message ? e.message : e)+"</div>";
  }
  return false;
}
function stBadge(st) {
  const k = st || "";
  return "<span class='badge "+esc(k)+"'>"+esc(STATUS_TH[k] || k)+"</span>";
}
function render(data, opts) {
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
      +"<div>"+esc(p.descr||p.pcode||p.mcode||"")+"</div>"+codeBits(p)+sizeBits(p)+locBits(p)+"<div class='meta'>"+esc(p.category||"")+" · คงเหลือ "+p.qtyoh2+" "+esc(p.ui1||"")+"</div><div class='prices'>"+fmtPrices(p.prices)+"</div></div></button>";
  });
  $("list").innerHTML = html || "<div class='empty'>ไม่พบ</div>";
  if (KIND === "iclow" && SUMMARY && !DOCS.length) showSummary();
  else if (DOCS.length && !products.length) showDoc(0);
  else if (products[0]) showP(0);
  else if (DOCS.length) showDoc(0);
  updateSearchSummary();
  // Only collapse on explicit search submit / Enter — not live typing debounce.
  if (opts && opts.collapse && (products.length || DOCS.length || SUMMARY)) collapseSearchPanelIfMobile();
}
function kvTable(obj) {
  const skip = new Set(["ID"]);
  return "<table>"+Object.keys(obj).filter(k => !skip.has(k) && String(obj[k]||"").trim() !== "").map(k =>
    "<tr><th>"+esc(colTh(k))+"</th><td>"+(MONEY_KEYS.has(k) ? money(obj[k]) : esc(obj[k]))+"</td></tr>"
  ).join("")+"</table>";
}
function lineTable(rows, cols) {
  if (!rows || !rows.length) return "<p class='meta'>ไม่มีบรรทัด</p>";
  const use = cols || Object.keys(rows[0]);
  const head = use.map(c => "<th>"+esc(colTh(c))+"</th>").join("");
  const body = rows.map((row, i) => "<tr>"+use.map(c => {
    let v = row[c] || "";
    if (c === "LINE") return "<td>"+(i+1)+"</td>";
    if (c === "status") return "<td>"+stBadge(v)+"</td>";
    if (c === "BCODE" && v) return "<td><button class='linkish' data-jump='product' data-q='"+esc(v)+"'>"+esc(v)+"</button></td>";
    if (c === "QTY") return "<td>"+qty(v)+"</td>";
    if (MONEY_KEYS.has(c)) return "<td>"+money(v)+"</td>";
    return "<td>"+esc(v)+"</td>";
  }).join("")+"</tr>").join("");
  return "<table><thead><tr>"+head+"</tr></thead><tbody>"+body+"</tbody></table>";
}
function jumpProduct(bcode) {
  KIND = "product";
  drawModes();
  toggleSearchChrome();
  $("q").placeholder = PLACE.product;
  $("q").value = bcode;
  go();
}
function jumpIclow(q) {
  KIND = "iclow";
  drawModes();
  toggleSearchChrome();
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
    +(vendors.length ? "<table><thead><tr><th>ผู้ขาย</th><th>ชื่อ</th><th>บรรทัด</th><th>มูลค่า</th></tr></thead><tbody>"
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
  toggleSearchChrome();
  if (!isCodeSizeMode()) $("q").placeholder = PLACE[kind] || PLACE.all;
  $("q").value = qv;
  go();
}
function jumpPo(docno) { jumpKind("po", docno); }
function showP(i) {
  const p = ITEMS[i];
  if (!p) return;
  document.querySelectorAll(".card").forEach(el => el.classList.remove("active"));
  const el = document.getElementById("c"+i); if (el) el.classList.add("active");
  const sizes = p.size_display || "";
  const photos = (p.photos||[]).map(u => "<img src='"+u+"' onerror='imgErr(this)'/>").join("");
  const locHq = (p.location_hq || "").trim();
  const locSyp = (p.location_syp || "").trim();
  const locCur = (p.location || [p.location1, p.location2].filter(Boolean).join(" / ") || "").trim();
  let locHtml = "";
  if (locHq || locSyp) {
    locHtml = "<div class='meta'>ที่เก็บ สนญ "+esc(locHq || "—")+" · สาขา "+esc(locSyp || "—")+"</div>";
  } else if (locCur) {
    locHtml = "<div class='meta'>ที่เก็บ "+esc(locCur)+"</div>";
  }
  const qtyHq = p.qtyoh2_hq != null ? p.qtyoh2_hq : (String(p.site||"").toUpperCase()==="HQ" ? p.qtyoh2 : null);
  const qtySyp = p.qtyoh2_syp != null ? p.qtyoh2_syp : (String(p.site||"").toUpperCase()==="SYP" ? p.qtyoh2 : null);
  const stockHtml = (qtyHq != null || qtySyp != null)
    ? "<p class='meta'>คงเหลือ สนญ "+(qtyHq != null ? qtyHq : "—")+" · สาขา "+(qtySyp != null ? qtySyp : "—")+" "+esc(p.ui1)+(p.do_not_restock?" (ไม่สั่งซ้ำ)":"")+"</p>"
    : "<p class='meta'>คงเหลือ QTYOH2 = "+p.qtyoh2+" "+esc(p.ui1)+(p.do_not_restock?" (ไม่สั่งซ้ำ)":"")+"</p>";
  $("detail").innerHTML = "<h2 style='margin:.2rem 0'>"+esc(p.bcode)+"</h2><div>"+esc(p.descr)+"</div>"
    +"<div class='meta'>เบอร์แท้ "+esc(p.pcode||"—")+" · เบอร์โรงงาน "+esc(p.mcode||"—")
    +(p.acode ? " · ชื่อย่อ "+esc(p.acode) : "")
    +" · "+esc(p.brand)+" "+esc(p.model)+"</div>"
    +"<div class='meta'>"+esc(p.category)+" · "+esc(p.code1 ? (p.code1+" "+(p.code1_label||"")) : (p.code1_label||""))+(sizes ? " · "+esc(sizes) : "")+"</div>"
    +locHtml
    +"<div class='meta'>"+esc(p.ui1)+"/"+esc(p.ui2)+"</div>"
    +"<div class='prices'>"+fmtPrices(p.prices)+"</div><div class='photos'>"+photos+"</div>"
    +stockHtml
    +"<div id='subPanel'></div>"
    +"<div id='more' class='empty'>โหลดความเคลื่อนไหว…</div>";
  loadSubPanels(p.bcode);
  fetch("/parts9/api/product/"+encodeURIComponent(p.bcode)+"?site="+encodeURIComponent($("site").value))
    .then(r => r.json()).then(d => {
      const m = d.movement || {};
      function tbl(title, rows, cols) {
        if (!rows || !rows.length) return "<p class='meta'>"+title+": —</p>";
        return "<h3>"+title+"</h3>"+lineTable(rows, cols);
      }
      $("more").innerHTML =
        tbl("ประวัติการขาย", m.sales, ["BILLNO","BILLDATE","QTY","UI","PRICE","AMOUNT"]) +
        tbl("ประวัติการซื้อ", m.pi, ["BILLNO","BILLDATE","QTY","UI","PRICE","AMOUNT"]) +
        tbl("ICLOW", m.iclow, ["DOCNO","DOCDATE","ORDERED","RECEIVED","CANCELED","RCVDNO","QTY"]);
    }).catch(() => { $("more").innerHTML = ""; });
}
function peerLine(p, badge) {
  const hq = p.hq_qtyoh2 != null ? p.hq_qtyoh2 : "—";
  const syp = p.syp_qtyoh2 != null ? p.syp_qtyoh2 : "—";
  const l1 = p.hq_l1 ? " <span class='badge'>L-1</span>" : "";
  const src = badge || p.source_label || p.source || "";
  const srcHtml = src ? " <span class='badge'>"+esc(src)+"</span>" : "";
  return "<div class='meta'><button class='linkish' data-jump='product' data-q='"+esc(p.bcode)+"'>"+esc(p.bcode)+"</button>"
    +srcHtml+" "+esc((p.descr||"").slice(0,40))+" · สนญ "+hq+" / สาขา "+syp+l1+"</div>";
}
function loadSubPanels(bcode) {
  const el = $("subPanel");
  if (!el) return;
  el.innerHTML = "<p class='meta'>โหลดทดแทน…</p>";
  Promise.all([
    fetch("/parts9/api/substitutes/suggest/"+encodeURIComponent(bcode)).then(r=>r.json()).catch(()=>({suggestions:[]})),
    fetch("/parts9/api/substitutes/by-bcode/"+encodeURIComponent(bcode)).then(r=>r.json()).catch(()=>({peers:[]})),
  ]).then(([sug, cat]) => {
    let html = "";
    const suggestions = sug.suggestions || [];
    if (suggestions.length) {
      html += "<h3>แนะนำทดแทน (ยังไม่ยืนยัน)</h3>"
        + suggestions.map(p => peerLine(p)).join("")
        + "<p class='meta'><a href='/parts9/substitutes?bcode="+encodeURIComponent(bcode)+"'>ยืนยันเข้ากลุ่มทดแทน…</a></p>";
    }
    const peers = cat.peers || [];
    if (peers.length) {
      html += "<h3>ทดแทนในกลุ่ม (ยืนยันแล้ว)</h3>"
        + peers.map(p => peerLine(p, "กลุ่ม")).join("")
        + "<p class='meta'><a href='/parts9/substitutes?bcode="+encodeURIComponent(bcode)+"'>จัดการกลุ่ม</a></p>";
    } else if (!suggestions.length) {
      html += "<p class='meta'>ยังไม่มีแนะนำ/กลุ่มทดแทน · <a href='/parts9/substitutes?bcode="+encodeURIComponent(bcode)+"'>สร้างกลุ่ม</a></p>";
    } else {
      html += "<p class='meta'><a href='/parts9/substitutes?bcode="+encodeURIComponent(bcode)+"'>จัดการกลุ่มทดแทน</a></p>";
    }
    el.innerHTML = html;
  }).catch(() => { el.innerHTML = ""; });
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
$("searchToggle").addEventListener("click", () => {
  const hdr = $("hdr");
  if (!hdr) return;
  setSearchPanelOpen(hdr.classList.contains("search-collapsed"));
});
window.addEventListener("resize", () => {
  if (!isMobileLayout()) setSearchPanelOpen(true);
  else updateSearchSummary();
});
$("site").addEventListener("change", () => {
  updateSearchSummary();
  if (currentQuery() || KIND==="iclow") go();
});
$("q").addEventListener("input", scheduleGo);
$("q").addEventListener("search", (e) => go(e, { collapse: true }));
$("skip").addEventListener("change", () => { if (currentQuery()) go(); });
$("category").addEventListener("change", () => {
  updateSearchSummary();
  if (currentQuery()) go();
});
$("sort").addEventListener("change", () => {
  updateSearchSummary();
  if (currentQuery()) go();
});
$("code1").addEventListener("change", () => {
  renderSizeFields($("code1").value);
  if (codeSizeValid()) scheduleGo();
  else {
    $("list").innerHTML = "<div class='empty'>เลือกประเภทชิ้นส่วน แล้วกรอกขนาด (กรอกบางช่องก็ค้นได้)</div>";
    $("detail").innerHTML = "";
  }
});
document.querySelectorAll("#sizeFields .size-inp").forEach((inp) => {
  inp.addEventListener("input", () => {
    updateSearchButton();
    if (codeSizeValid()) scheduleGo();
  });
  inp.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter" && codeSizeValid()) go(ev, { collapse: true });
  });
});
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
initCategorySelect();
initCode1Select();
toggleSearchChrome();
drawModes();
updateSearchSummary();
try {
  if (isMobileLayout() && localStorage.getItem(SEARCH_PANEL_KEY) === "0") setSearchPanelOpen(false);
} catch (e) {}
</script>
</body>
</html>
"""


def _sql_badge_text(probe: dict) -> str:
    if probe.get("ok"):
        return str(probe.get("server") or "ok")
    return "down"


def page(*, user_name: str, site: str, probes: dict) -> str:
    hq = probes.get("hq") or {}
    syp = probes.get("syp") or {}
    return (
        _HTML.replace("__CODE1_LABELS_JSON__", json.dumps(CODE1_LABELS, ensure_ascii=False))
        .replace("__SIZE_LABELS_JSON__", json.dumps(SIZE_LABELS, ensure_ascii=False))
        .replace("__CATEGORY_LABELS_JSON__", json.dumps(CATEGORY_LABELS, ensure_ascii=False))
        .replace("__USER__", user_name or "")
        .replace("__HQ_LABEL__", BRANCH_LABEL["HQ"])
        .replace("__SYP_LABEL__", BRANCH_LABEL["SYP"])
        .replace("__HQSEL__", "selected" if site.lower()=="hq" else "")
        .replace("__SYPSEL__", "selected" if site.lower()=="syp" else "")
        .replace("__HQBADGE__", "ok" if hq.get("ok") else "down")
        .replace("__SYPBADGE__", "ok" if syp.get("ok") else "down")
        .replace("__HQSQL__", _sql_badge_text(hq))
        .replace("__SYPSQL__", _sql_badge_text(syp))
    )


_SUBS_MANAGE_HTML = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<title>กลุ่มทดแทน — PARTS9</title>
<style>
:root { --bg:#0c1014; --text:#e8eef4; --muted:#9aa7b5; --line:#243040; --chip:#1a2430; --acc:#3d8bfd; --on-acc:#fff; --inset:#141c26; }
body { margin:0; font:15px/1.45 system-ui,sans-serif; background:var(--bg); color:var(--text); }
header { padding:.75rem 1rem; border-bottom:1px solid var(--line); display:flex; gap:.75rem; align-items:center; flex-wrap:wrap; }
header a { color:var(--acc); text-decoration:none; }
main { padding:1rem; max-width:52rem; margin:0 auto; }
label { display:block; font-size:.8rem; color:var(--muted); margin-bottom:.25rem; }
input, button, textarea { font:inherit; padding:.55rem .7rem; border-radius:.45rem; border:1px solid var(--line); background:var(--chip); color:var(--text); }
button.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:600; }
.row { display:flex; gap:.5rem; flex-wrap:wrap; align-items:end; margin-bottom:.75rem; }
.row > * { flex:1; min-width:8rem; }
.meta { color:var(--muted); font-size:.85rem; }
.card { background:var(--inset); border:1px solid var(--line); border-radius:.55rem; padding:.75rem; margin:.75rem 0; }
.badge { font-size:.72rem; padding:.1rem .4rem; border-radius:.35rem; background:var(--chip); color:var(--muted); }
.member { display:flex; justify-content:space-between; gap:.5rem; padding:.4rem 0; border-bottom:1px solid var(--line); }
.member:last-child { border-bottom:0; }
.error { color:#f87171; }
.ok { color:#4ade80; }
</style>
</head>
<body>
<header>
  <a href="/parts9/">← Explorer</a>
  <strong>กลุ่มทดแทน</strong>
  <span class="meta">__USER__</span>
</header>
<main>
  <form id="loadForm" class="row">
    <div>
      <label for="bcode">รหัสสินค้า (BCODE)</label>
      <input id="bcode" name="bcode" value="__BCODE__" autocomplete="off" required/>
    </div>
    <div style="flex:0">
      <label>&nbsp;</label>
      <button class="primary" type="submit">โหลด</button>
    </div>
  </form>
  <p id="msg" class="meta"></p>
  <div id="panel"></div>
</main>
<script>
const API = "/parts9/api/substitutes";
const BY_BCODE = "/parts9/api/substitutes/by-bcode/";
function $(id){ return document.getElementById(id); }
function esc(s){ return String(s??"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function stockLine(m){
  const hq = m.hq_qtyoh2 != null ? m.hq_qtyoh2 : "—";
  const syp = m.syp_qtyoh2 != null ? m.syp_qtyoh2 : "—";
  const l1 = m.hq_l1 ? " <span class='badge'>L-1</span>" : "";
  return "สนญ "+hq+" / สาขา "+syp+l1;
}
async function loadSuggest(bcode){
  const r = await fetch(API+"/suggest/"+encodeURIComponent(bcode));
  if(!r.ok) return [];
  const d = await r.json();
  return d.suggestions || [];
}
async function loadByBcode(bcode){
  const r = await fetch(BY_BCODE+encodeURIComponent(bcode));
  if(!r.ok) throw new Error("โหลดไม่สำเร็จ");
  return r.json();
}
function render(data, suggestions){
  const bcode = ($("bcode").value||"").trim();
  const group = data.group;
  const peers = data.peers || [];
  let html = "";
  if(suggestions && suggestions.length){
    html += "<div class='card'><h3 style='margin:.2rem 0'>แนะนำทดแทน (ยังไม่ยืนยัน)</h3>"
      + suggestions.map(s => "<div class='member'><div><strong>"+esc(s.bcode)+"</strong> "
        +"<span class='badge'>"+esc(s.source_label||s.source||"")+"</span><div class='meta'>"
        +esc(s.descr||"")+" · "+stockLine(s)+"</div></div>"
        +"<button type='button' data-promote='"+esc(s.bcode)+"'>เพิ่มเข้ากลุ่ม</button></div>").join("")
      +"</div>";
  }
  if(!group){
    html += "<div class='card'><p>ยังไม่มีกลุ่มทดแทนที่ยืนยันสำหรับ <strong>"+esc(bcode)+"</strong></p>"
      +"<div class='row'><div><label>ชื่อกลุ่ม (ถ้ามี)</label><input id='newName'/></div>"
      +"<div><label>หมายเหตุ</label><input id='newNote'/></div></div>"
      +"<div class='row'><div><label>สมาชิกเริ่มต้น (คั่นด้วย comma)</label>"
      +"<input id='newMembers' value='"+esc(bcode)+"'/></div></div>"
      +"<button class='primary' type='button' id='createBtn'>สร้างกลุ่ม</button></div>";
  } else {
    const members = group.members || [];
    html += "<div class='card'><div class='meta'>group "+esc(group.group_id)+"</div>"
      +"<div class='row'><div><label>ชื่อ</label><input id='gName' value='"+esc(group.name||"")+"'/></div>"
      +"<div><label>หมายเหตุ</label><input id='gNote' value='"+esc(group.note||"")+"'/></div>"
      +"<div style='flex:0'><label>&nbsp;</label><button type='button' id='saveMeta'>บันทึก</button></div></div>"
      +"<h3>สมาชิก</h3>"
      + members.map(m => "<div class='member'><div><strong>"+esc(m.bcode)+"</strong> "
        +"<div class='meta'>"+esc(m.descr||"")+" · "+stockLine(m)+"</div></div>"
        +"<button type='button' data-remove='"+esc(m.bcode)+"'>ลบ</button></div>").join("")
      +"<div class='row' style='margin-top:.75rem'><div><label>เพิ่ม BCODE</label>"
      +"<input id='addBcode'/></div><div style='flex:0'><label>&nbsp;</label>"
      +"<button class='primary' type='button' id='addBtn'>เพิ่ม</button></div></div>"
      +"<p class='meta'><button type='button' id='delGroup' style='margin-top:.5rem'>ลบทั้งกลุ่ม</button></p></div>";
  }
  $("panel").innerHTML = html;
  const createBtn = $("createBtn");
  if(createBtn) createBtn.onclick = async () => {
    const members = ($("newMembers").value||"").split(/[,\\s]+/).filter(Boolean).map(b=>({bcode:b}));
    const r = await fetch(API+"/groups", {method:"POST", headers:{"Content-Type":"application/json"},
      body: JSON.stringify({name:$("newName").value||null, note:$("newNote").value||null, members})});
    const d = await r.json();
    if(!r.ok){ $("msg").innerHTML = "<span class='error'>"+esc(d.detail||d.error||"สร้างไม่สำเร็จ")+"</span>"; return; }
    $("msg").innerHTML = "<span class='ok'>สร้างกลุ่มแล้ว</span>";
    refresh();
  };
  const saveMeta = $("saveMeta");
  if(saveMeta) saveMeta.onclick = async () => {
    const r = await fetch(API+"/groups/"+encodeURIComponent(group.group_id), {method:"PATCH",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify({name:$("gName").value, note:$("gNote").value})});
    if(!r.ok){ const d=await r.json(); $("msg").innerHTML="<span class='error'>"+esc(d.detail||"บันทึกไม่สำเร็จ")+"</span>"; return; }
    $("msg").innerHTML = "<span class='ok'>บันทึกแล้ว</span>";
  };
  const addBtn = $("addBtn");
  if(addBtn) addBtn.onclick = async () => {
    const code = ($("addBcode").value||"").trim();
    if(!code) return;
    const r = await fetch(API+"/groups/"+encodeURIComponent(group.group_id)+"/members", {method:"POST",
      headers:{"Content-Type":"application/json"}, body: JSON.stringify({bcode:code})});
    const d = await r.json();
    if(!r.ok){ $("msg").innerHTML="<span class='error'>"+esc(d.detail||d.error||"เพิ่มไม่สำเร็จ")+"</span>"; return; }
    $("msg").innerHTML = "<span class='ok'>เพิ่ม "+esc(code)+" แล้ว</span>";
    refresh();
  };
  document.querySelectorAll("[data-remove]").forEach(btn => {
    btn.onclick = async () => {
      const code = btn.getAttribute("data-remove");
      const r = await fetch(API+"/groups/"+encodeURIComponent(group.group_id)+"/members/"+encodeURIComponent(code), {method:"DELETE"});
      if(!r.ok){ const d=await r.json(); $("msg").innerHTML="<span class='error'>"+esc(d.detail||"ลบไม่สำเร็จ")+"</span>"; return; }
      refresh();
    };
  });
  document.querySelectorAll("[data-promote]").forEach(btn => {
    btn.onclick = async () => {
      const peer = btn.getAttribute("data-promote");
      if(!group){
        const r = await fetch(API+"/groups", {method:"POST", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({members:[{bcode:bcode},{bcode:peer}], note:"from suggestion"})});
        const d = await r.json();
        if(!r.ok){ $("msg").innerHTML="<span class='error'>"+esc(d.detail||"สร้างไม่สำเร็จ")+"</span>"; return; }
      } else {
        const r = await fetch(API+"/groups/"+encodeURIComponent(group.group_id)+"/members", {method:"POST",
          headers:{"Content-Type":"application/json"}, body: JSON.stringify({bcode:peer})});
        const d = await r.json();
        if(!r.ok){ $("msg").innerHTML="<span class='error'>"+esc(d.detail||"เพิ่มไม่สำเร็จ")+"</span>"; return; }
      }
      $("msg").innerHTML = "<span class='ok'>ยืนยัน "+esc(peer)+" เข้ากลุ่มแล้ว</span>";
      refresh();
    };
  });
  const delGroup = $("delGroup");
  if(delGroup) delGroup.onclick = async () => {
    if(!confirm("ลบทั้งกลุ่ม?")) return;
    const r = await fetch(API+"/groups/"+encodeURIComponent(group.group_id), {method:"DELETE"});
    if(!r.ok){ const d=await r.json(); $("msg").innerHTML="<span class='error'>"+esc(d.detail||"ลบไม่สำเร็จ")+"</span>"; return; }
    $("msg").innerHTML = "<span class='ok'>ลบกลุ่มแล้ว</span>";
    refresh();
  };
}
async function refresh(){
  const bcode = ($("bcode").value||"").trim();
  if(!bcode) return;
  $("msg").textContent = "กำลังโหลด…";
  try {
    const [data, suggestions] = await Promise.all([loadByBcode(bcode), loadSuggest(bcode)]);
    $("msg").textContent = "";
    render(data, suggestions);
  } catch(e) {
    $("msg").innerHTML = "<span class='error'>"+esc(e.message||e)+"</span>";
  }
}
$("loadForm").addEventListener("submit", (ev) => { ev.preventDefault(); refresh(); });
if(($("bcode").value||"").trim()) refresh();
</script>
</body>
</html>
"""


def substitutes_manage_page(*, user_name: str, bcode: str = "") -> str:
    return (
        _SUBS_MANAGE_HTML.replace("__USER__", user_name or "")
        .replace("__BCODE__", bcode or "")
    )

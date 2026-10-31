from __future__ import annotations

import html as html_lib
import json

APP = "kcw-hq-po"
SESSION_COOKIE = "kcw_hq_po"


def page(*, user_name: str = "", stamp_enabled: bool = False) -> str:
    who = (user_name or "operator").strip()
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__STAMP__", "true" if stamp_enabled else "false")
    )


_HTML = r"""<!doctype html>
<html lang="th">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light"/>
<title>สั่งซื้อ HQ</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet" media="print" onload="this.media='all'"/>
<style>
:root{
  --blue:#1d4ed8;--blue-deep:#1e3a8a;--blue-soft:#dbeafe;--blue-wash:#eff6ff;
  --line:#dbe3ef;--muted:#64748b;--text:#0f172a;--bg:#f4f7fb;--card:#fff;
  --warn:#9a3412;--warn-bg:#fff7ed;--ok:#166534;--ok-bg:#dcfce7;--wait:#9a3412;--wait-bg:#ffedd5;
}
*{box-sizing:border-box}
html,body{margin:0;min-height:100%}
body{font-family:Prompt,"Noto Sans Thai",system-ui,sans-serif;background:var(--bg);color:var(--text);-webkit-tap-highlight-color:transparent}
button,input{font-family:inherit;touch-action:manipulation}
header{position:sticky;top:0;z-index:8;background:linear-gradient(180deg,#1e40af 0%,#1d4ed8 100%);color:#fff;padding:max(14px,env(safe-area-inset-top)) 14px 12px}
header h1{margin:0;font-size:18px;font-weight:650;letter-spacing:-.01em}
header p{margin:2px 0 10px;font-size:13px;opacity:.9}
.tabs{display:flex;gap:8px}
.tabs button{flex:1;min-height:40px;border:1px solid rgba(255,255,255,.45);background:transparent;color:#fff;border-radius:999px;padding:8px 12px;font-size:14px;font-weight:600}
.tabs button.on{background:#fff;color:var(--blue);border-color:#fff}
main{padding:12px 12px calc(20px + env(safe-area-inset-bottom));max-width:860px;margin:0 auto}
body.has-dock main{padding-bottom:calc(92px + env(safe-area-inset-bottom))}
.note{background:var(--warn-bg);color:var(--warn);border-radius:12px;padding:10px 12px;font-size:13px;line-height:1.45;margin-bottom:12px}
.toolbar{display:flex;flex-direction:column;gap:8px;margin-bottom:12px}
.order-filters{display:grid;grid-template-columns:1fr;gap:8px}
.toggle{display:flex;gap:6px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:4px}
.toggle button{flex:1;min-height:38px;border:0;background:transparent;border-radius:9px;padding:7px 8px;font-size:13px;color:var(--muted);font-weight:600}
.toggle button.on{background:var(--blue);color:#fff}
.bar{display:flex;gap:8px}
.bar input[type=search]{flex:1;width:auto;min-width:0}
#addProduct{flex:none;min-height:44px;border:0;border-radius:12px;background:var(--blue);color:#fff;font-weight:700;padding:8px 12px;font-size:14px}
.search-status{display:flex;align-items:center;gap:8px;margin:0;color:var(--blue-deep);font-size:13px;font-weight:650}
.search-status[hidden]{display:none}
input[type=search]{width:100%;min-height:44px;border:1px solid var(--line);border-radius:12px;padding:10px 12px;font-size:16px;background:#fff;color:var(--text)}
input[type=search]:focus{outline:2px solid #93c5fd;border-color:var(--blue)}
.count{font-size:12px;color:var(--muted);padding:0 2px}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;margin-bottom:10px;overflow:hidden;box-shadow:0 1px 2px rgba(15,23,42,.04)}
.card h2{margin:0;padding:12px;font-size:15px;background:var(--blue-wash);display:flex;justify-content:space-between;gap:8px;align-items:flex-start;line-height:1.35}
.card h2 .title{min-width:0;overflow-wrap:anywhere}
.card h2 .count{flex:none;margin-top:2px}
.select-all{display:flex;align-items:center;gap:8px;min-height:44px;padding:10px 12px;border-top:1px solid var(--line);background:#fff;font-size:14px;font-weight:650;color:var(--blue-deep)}
.select-all input{margin:0;flex:none}
.line{display:grid;grid-template-columns:32px minmax(0,1fr) auto;gap:8px;padding:12px;border-top:1px solid var(--line);align-items:start}
.line.plain{grid-template-columns:minmax(0,1fr) auto}
.line .code{font-weight:600;line-height:1.4;overflow-wrap:anywhere}
.sku{display:inline-block;background:var(--blue-soft);color:var(--blue-deep);border-radius:6px;padding:0 6px;font-size:12px;font-weight:700;margin-right:4px;vertical-align:1px}
.line .meta{color:var(--muted);font-size:12px;margin-top:3px;line-height:1.4;overflow-wrap:anywhere}
.line-main{display:flex;gap:8px;min-width:0}
.line-main > div{min-width:0;flex:1}
.thumb{width:52px;height:52px;object-fit:cover;border-radius:8px;background:#e2e8f0;flex:none}
.flag{display:inline-block;margin-top:6px;border-radius:999px;padding:3px 8px;font-size:12px;font-weight:700;line-height:1.35}
.flag.switch{background:#ffedd5;color:#9a3412}
.flag.reorder{background:#dbeafe;color:#1e3a8a}
#hist{position:fixed;inset:0;z-index:40;background:rgba(15,23,42,.45);display:flex;align-items:flex-end;justify-content:center}
#hist[hidden]{display:none}
.hist-card{background:#fff;width:min(720px,100%);max-height:86vh;overflow:auto;border-radius:16px 16px 0 0;padding:14px 14px calc(16px + env(safe-area-inset-bottom))}
.hist-card h2{margin:8px 0;font-size:16px}
.hist-card h3{margin:14px 0 6px;font-size:13px;color:var(--blue-deep)}
.hist-top{display:flex;justify-content:space-between;align-items:center;gap:8px}
.hist-site{margin:10px 0 4px}
.istatus{display:inline-block;border-radius:999px;padding:4px 8px;font-size:12px;font-weight:700}
.istatus.ok{background:var(--ok-bg);color:var(--ok)}
.istatus.warn{background:var(--warn-bg);color:var(--warn)}
.istatus.bad{background:#fee2e2;color:#991b1b}
.istatus.order{background:var(--blue-soft);color:var(--blue-deep)}
.ikpis,.istock{display:grid;grid-template-columns:1fr 1fr;gap:6px}
.ikpi{background:var(--blue-wash);border-radius:10px;padding:8px}
.ikpi .l{color:var(--muted);font-size:11px}
.ikpi .v{font-weight:700;color:var(--blue-deep);font-size:14px}
.ibars{display:flex;align-items:flex-end;gap:3px;height:88px;margin-top:8px}
.ibar{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;min-width:0;height:100%}
.ibar span{display:block;width:100%;max-width:16px;background:var(--blue);border-radius:4px 4px 0 0}
.ibar em{font-style:normal;font-size:9px;color:var(--muted);margin-top:2px}
.itable{width:100%;border-collapse:collapse;font-size:12px}
.itable th,.itable td{padding:6px 4px;border-bottom:1px solid var(--line);text-align:left}
.itable th{color:var(--muted);font-weight:650}
.itable .num{text-align:right;font-variant-numeric:tabular-nums}
.hist-top button{min-height:36px;border:0;background:transparent;color:var(--blue);font-weight:700}
.ai{color:var(--blue);font-size:12px;margin-top:6px;padding:6px 8px;background:var(--blue-wash);border-radius:8px;line-height:1.4}
.qty{text-align:right;font-weight:700;font-size:16px;color:var(--blue-deep);white-space:nowrap}
.line button.ghost{display:block;margin-top:8px;min-height:36px;background:#fff;color:var(--warn);border:1px solid #fdba74;border-radius:10px;padding:6px 10px;font-size:13px;font-weight:650}
.recs{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}
.rec{border:1px solid var(--line);background:#fff;color:var(--blue-deep);border-radius:999px;padding:4px 8px;font-size:12px;font-weight:650}
.rec.off{border:0;background:transparent;color:var(--muted);padding:4px 0}
.qty-edit{display:flex;align-items:center;justify-content:flex-end;gap:6px}
.qty-in{width:84px;min-height:40px;border:1px solid var(--line);border-radius:10px;padding:6px 8px;font-size:16px;font-weight:700;text-align:right;color:var(--blue-deep);background:#fff}
.qty-in:focus{outline:2px solid #93c5fd;border-color:var(--blue)}
.vendor-pick{display:flex;flex-direction:column;gap:4px;margin-top:8px;font-size:12px;color:var(--muted);font-weight:650}
.vendor-pick select{width:100%;max-width:100%;min-height:40px;border:1px solid var(--line);border-radius:10px;padding:6px 8px;font:650 14px Prompt,"Noto Sans Thai",sans-serif;color:var(--text);background:#fff}
.unit-pick{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.unit-pick button,.peer-btn{min-height:36px;border:1px solid var(--line);background:#fff;border-radius:999px;padding:4px 10px;font-size:13px;font-weight:650;color:var(--blue-deep)}
.unit-pick button.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.peer-btn{border-radius:10px;margin-top:8px}
.line-actions{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
.line-actions .peer-btn{margin-top:0}
.order-btn,.history-btn{display:block;width:100%;min-height:42px;margin-top:8px;border:0;border-radius:10px;background:var(--blue);color:#fff;font-weight:700;font-size:14px}
.history-btn{background:#fff;color:var(--blue-deep);border:1px solid var(--blue)}
.add-quiet{display:block;width:100%;margin:4px 0 12px;background:transparent;border:0;color:var(--blue);font-weight:650;font-size:13px;min-height:40px}
.ap-search{margin-top:8px}
.ap-search input{width:100%;min-height:40px;border:1px solid var(--line);border-radius:10px;padding:8px 10px;font-size:16px;background:#fff;color:var(--text)}
.ap-hit{display:block;width:100%;text-align:left;border:1px solid var(--line);background:#fff;border-radius:10px;padding:8px 10px;margin-top:4px;font:600 13px Prompt,"Noto Sans Thai",sans-serif;color:var(--text)}
.pick-row{display:flex;gap:8px;align-items:flex-start;background:#fff;border:1px solid var(--line);border-radius:14px;padding:12px;margin-top:8px}
.pick-row .grow{flex:1;min-width:0}
.pick-row button.choose{flex:none;min-height:40px;border:0;border-radius:10px;background:var(--blue);color:#fff;font-weight:700;padding:8px 12px}
#catalog{position:fixed;inset:0;z-index:18;background:var(--bg);overflow:auto;padding:12px 12px calc(24px + env(safe-area-inset-bottom))}
#catalog[hidden]{display:none}
.catalog-top{display:flex;gap:8px;margin-bottom:10px}
.catalog-top button{min-height:42px;border-radius:12px;border:1px solid var(--line);background:#fff;font-weight:650;padding:8px 14px;color:var(--blue-deep)}
.catalog-head{margin:0;font-size:18px}
.catalog-sub{margin:4px 0 12px;color:var(--muted);font-size:13px}
.line.picked{background:var(--blue-wash)}
.vendor-card{display:flex;width:100%;justify-content:space-between;align-items:center;gap:8px;text-align:left;background:#fff;border:1px solid var(--line);border-radius:14px;margin-bottom:10px;padding:14px 12px;font:650 15px Prompt,"Noto Sans Thai",sans-serif;color:var(--text);box-shadow:0 1px 2px rgba(15,23,42,.04)}
.vendor-card .title{min-width:0;overflow-wrap:anywhere}
.back{display:block;width:100%;min-height:42px;margin-bottom:10px;border:1px solid var(--line);background:#fff;border-radius:12px;font-weight:650;color:var(--blue-deep)}
.peers{margin-top:8px}
.peer-sec{margin-top:6px}
.peer{display:block;width:100%;text-align:left;border:1px solid var(--line);background:#fff;border-radius:10px;padding:8px 10px;margin-top:4px;font:600 13px Prompt,"Noto Sans Thai",sans-serif;color:var(--text)}
.peer .meta{display:block;font-weight:500}
#sheet{position:fixed;inset:0;z-index:20;background:#eef2f7;overflow:auto;padding:12px 12px calc(118px + env(safe-area-inset-bottom))}
#sheet[hidden]{display:none}
.sheet-top{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:12px}
.sheet-top button{flex:1 1 40%;min-height:42px;border-radius:12px;border:1px solid var(--line);background:#fff;font-weight:650;font-size:14px}
.sheet-top button.on{background:var(--blue);color:#fff;border-color:var(--blue)}
.sheet-preview{overflow:auto;-webkit-overflow-scrolling:touch}
#printSheet{display:none}
.doc{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px 14px;margin:0 auto 12px;max-width:640px}
.doc h2{margin:0;font-size:20px}
.doc .who{margin:4px 0 12px;color:var(--muted);font-size:13px}
.doc table{width:100%;border-collapse:collapse}
.doc th{text-align:left;font-size:12px;color:var(--muted);font-weight:650;border-bottom:1px solid var(--line);padding:6px 4px}
.doc td{border-bottom:1px solid var(--line);padding:8px 4px;vertical-align:top;font-size:14px}
.doc td.num{text-align:right;font-weight:700;white-space:nowrap}
.sheet-foot{position:fixed;left:0;right:0;bottom:0;background:#fff;border-top:1px solid var(--line);padding:10px 12px calc(10px + env(safe-area-inset-bottom))}
.sheet-foot p{margin:0 0 8px;font-size:12px;color:var(--muted);text-align:center}
.sheet-foot button{width:100%;min-height:46px;border:0;border-radius:12px;background:var(--blue);color:#fff;font-weight:700;font-size:15px}
input[type=checkbox]{width:22px;height:22px;margin:2px 0 0;accent-color:var(--blue)}
.card h2 .when{display:block;margin-top:2px;font-size:12px;font-weight:500;color:var(--muted)}
.po-lines{border-top:1px solid var(--line)}
.po-lines summary{cursor:pointer;list-style:none;min-height:44px;padding:12px;font-size:14px;font-weight:650;color:var(--blue-deep);display:flex;align-items:center;gap:8px;user-select:none}
.po-lines summary::-webkit-details-marker{display:none}
.po-lines summary::before{content:"▸";font-size:12px;color:var(--muted);transition:transform .15s}
.po-lines[open] summary::before{transform:rotate(90deg)}
.actions{padding:10px 12px;border-top:1px solid var(--line);display:flex;flex-direction:column;gap:8px}
.actions button{width:100%;min-height:44px;background:var(--blue);color:#fff;border:0;border-radius:12px;padding:10px 12px;font-weight:650;font-size:14px}
.actions button.ghost{background:#fff;color:var(--warn);border:1px solid #fdba74}
.actions button:disabled{opacity:.6}
.empty,.spin-wrap{color:var(--muted);padding:28px 16px;text-align:center}
.spin-wrap{display:flex;flex-direction:column;align-items:center;gap:10px}
.spin{width:22px;height:22px;border:2.5px solid var(--blue-soft);border-top-color:var(--blue);border-radius:50%;animation:spin .7s linear infinite;display:inline-block}
.spin.sm{width:16px;height:16px;border-width:2px}
@keyframes spin{to{transform:rotate(360deg)}}
.insight{display:flex;align-items:center;gap:8px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:10px 12px;margin-bottom:10px;color:var(--blue-deep);font-size:13px}
.insight[hidden]{display:none}
#vendorSort[hidden]{display:none}
.badge{flex:none;font-size:12px;font-weight:650;border-radius:999px;padding:3px 8px;background:var(--blue-soft);color:var(--blue-deep)}
.badge.wait{background:var(--wait-bg);color:var(--wait)}
.badge.done{background:var(--ok-bg);color:var(--ok)}
#dock{position:fixed;left:0;right:0;bottom:0;z-index:9;background:#fff;border-top:1px solid var(--line);box-shadow:0 -8px 24px rgba(15,23,42,.08);padding:10px 12px calc(10px + env(safe-area-inset-bottom))}
#dock[hidden]{display:none}
#dock button{width:100%;min-height:46px;border:0;border-radius:12px;background:var(--blue);color:#fff;font-weight:700;font-size:15px}
#busy{position:fixed;inset:0;z-index:30;background:rgba(15,23,42,.38);display:flex;align-items:center;justify-content:center;padding:24px}
#busy[hidden]{display:none}
.busy-card{background:#fff;border-radius:16px;padding:22px 26px;display:flex;flex-direction:column;align-items:center;gap:12px;min-width:180px;box-shadow:0 12px 40px rgba(15,23,42,.18);color:var(--blue-deep);font-weight:600}
@media print{
  body[data-print="po"] > *:not(#printSheet){display:none !important}
  body[data-print="po"] #printSheet{display:block !important;background:#fff;color:#111}
}
@media (min-width:720px){
  header{padding-left:24px;padding-right:24px}
  .tabs{max-width:420px}
  main{padding-left:20px;padding-right:20px}
  .toolbar{display:grid;grid-template-columns:1fr 1fr;gap:8px}
  .bar,#vendorSort,#doneMode,#doneSort,#holdQ{grid-column:1 / -1}
  .order-filters{grid-template-columns:1fr 1fr}
  .line{padding:12px 14px}
}
</style>
</head>
<body>
<header>
  <h1>สั่งซื้อ HQ</h1>
  <p id="who"></p>
  <div class="tabs">
    <button type="button" id="tabOrder" class="on">รอสั่ง</button>
    <button type="button" id="tabDone">สั่งแล้ว</button>
  </div>
</header>
<main>
  <div id="banner"></div>
  <section id="orderView">
    <div class="toolbar">
      <div class="toggle">
        <button type="button" id="viewProduct" class="on">ตามสินค้า</button>
        <button type="button" id="viewVendor">ตามเจ้าหนี้</button>
      </div>
      <div class="toggle">
        <button type="button" id="srcAll" class="on">ทั้งหมด</button>
        <button type="button" id="srcIclow">ICLOW</button>
        <button type="button" id="srcAi">AI</button>
      </div>
      <div class="toggle" id="vendorSort" hidden>
        <button type="button" id="sortCount" class="on">จำนวนสินค้า</button>
        <button type="button" id="sortName">ตามชื่อ</button>
      </div>
      <div class="bar"><input id="q" type="search" placeholder="ค้นรหัส ชื่อสินค้า ชื่อรุ่น เบอร์แท้ เบอร์โรงงาน ยี่ห้อ หรือเจ้าหนี้" enterkeyhint="search" autocomplete="off"/><button type="button" id="addProduct">เพิ่มสินค้า</button></div>
      <p id="qStatus" class="search-status" role="status"><span class="spin sm" aria-hidden="true"></span><span id="qStatusText">กำลังโหลดรายการรอสั่ง…</span></p>
    </div>
    <div id="insightNote" class="insight" hidden></div>
    <div id="list"><div class="spin-wrap"><span class="spin" aria-hidden="true"></span><span>กำลังโหลดรายการรอสั่ง…</span></div></div>
  </section>
  <section id="doneView" hidden>
    <div class="toolbar">
      <div class="toggle" id="doneMode">
        <button type="button" id="doneBill" class="on">ตามบิล</button>
        <button type="button" id="doneProduct">ตามสินค้า</button>
      </div>
      <div class="toggle" id="doneSort">
        <button type="button" id="sortOld">เก่าสุดก่อน</button>
        <button type="button" id="sortNew" class="on">ใหม่สุดก่อน</button>
      </div>
      <div class="order-filters" id="billFilters">
        <input id="orderVendor" type="search" placeholder="กรองเจ้าหนี้" aria-label="กรองเจ้าหนี้" enterkeyhint="search" autocomplete="off"/>
        <input id="orderBcode" type="search" placeholder="กรองรหัสสินค้า" aria-label="กรองรหัสสินค้า" enterkeyhint="search" autocomplete="off"/>
      </div>
      <input id="holdQ" type="search" placeholder="ค้นรหัส ชื่อสินค้า หรือเจ้าหนี้" aria-label="ค้นสินค้าที่สั่งแล้ว" enterkeyhint="search" autocomplete="off" hidden/>
    </div>
    <div id="orders"></div>
    <div id="holdList" hidden></div>
  </section>
</main>
<div id="dock" hidden><button type="button" id="dockConfirm">ดูใบส่งเจ้าหนี้</button></div>
<div id="sheet" hidden>
  <div class="sheet-top">
    <button type="button" id="sheetClose">ปิด</button>
    <button type="button" id="varSimple" class="on">แบบย่อ</button>
    <button type="button" id="varFull">แบบเต็ม</button>
    <button type="button" id="sheetPrint">พิมพ์</button>
    <button type="button" id="sheetCopy">คัดลอกส่งฝ่ายขาย</button>
  </div>
  <div id="sheetBody"></div>
  <div class="sheet-foot">
    <p id="sheetFootNote">ส่งให้ฝ่ายขายก่อน แล้วค่อยบันทึกว่าสั่งแล้ว</p>
    <button type="button" id="sheetCommit">บันทึกว่าสั่งแล้ว</button>
  </div>
</div>
<div id="catalog" hidden>
  <div class="catalog-top">
    <button type="button" id="catalogClose">กลับ</button>
    <button type="button" id="catalogBack" hidden>เลือกสินค้าอื่น</button>
  </div>
  <h2 class="catalog-head">เพิ่มสินค้า</h2>
  <p class="catalog-sub" id="catalogSub">ค้นจากรหัสสินค้าใน PARTS9</p>
  <div class="bar"><input id="catalogQ" type="search" placeholder="รหัส ชื่อ ชื่อรุ่น เบอร์แท้ เบอร์โรงงาน" enterkeyhint="search" autocomplete="off"/></div>
  <div id="catalogBody"></div>
</div>
<div id="printSheet" aria-hidden="true"></div>
<div id="hist" hidden>
  <div class="hist-card">
    <div class="hist-top"><strong id="histTitle">Insight</strong><button type="button" id="histClose">ปิด</button></div>
    <div class="toggle hist-site" id="histSite">
      <button type="button" id="histHq" class="on">HQ</button>
      <button type="button" id="histSyp">SYP</button>
    </div>
    <div id="histBody"></div>
  </div>
</div>
<div id="busy" hidden>
  <div class="busy-card"><span class="spin" aria-hidden="true"></span><div id="busyText">กำลังดำเนินการ…</div></div>
</div>
<script>
const USER = __USER_JSON__;
const STAMP = __STAMP__;
const state = {items:[], view:"product", tab:"order", doneMode:"bill", orderSort:"new", holdSort:"old", vendorKey:null, vendorName:"", vendorSort:"count", historyOnly:false, vendorHits:[], vendorQuery:"", historyLoaded:{}, historyLoading:false, vendorInsight:"", source:"all", q:"", orders:[], ordersLoaded:false, orderVendor:"", orderBcode:"", hold:[], holdLoaded:false, holdQ:"", busy:false, loading:true, sheet:[], forms:null, variant:"simple", sheetSaved:false, insightLoaded:false, insightLoading:false, catalogQ:"", catalogHits:[], catalogQuery:"", catalogLoading:false, catalogPick:null, catalogVendor:"", catalogVendorName:""};
let insightGen = 0;
let searchTimer = 0;
let vendorTimer = 0;
let catalogTimer = 0;
let apTimer = 0;
document.getElementById("who").textContent = USER;
if(!STAMP){
  document.getElementById("banner").innerHTML = '<div class="note">ยังไม่เปิดบันทึกลง ICLOW (HQ_PO_ICLOW_STAMP_ENABLED) — ดูรายการและคำแนะนำ AI ได้ แต่ยืนยันสั่งซื้อยังไม่ได้</div>';
}

function esc(s){return String(s??"").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function spinner(text){
  return `<div class="spin-wrap" role="status"><span class="spin" aria-hidden="true"></span><span>${esc(text)}</span></div>`;
}
function setBusy(on, text){
  state.busy = !!on;
  const el = document.getElementById("busy");
  document.getElementById("busyText").textContent = text || "กำลังดำเนินการ…";
  el.hidden = !on;
}
function showSearchStatus(text){
  const el = document.getElementById("qStatus");
  document.getElementById("qStatusText").textContent = text;
  el.hidden = false;
}
function hideSearchStatus(){
  document.getElementById("qStatus").hidden = true;
}
function setInsight(text){
  const el = document.getElementById("insightNote");
  if(!text){ el.hidden = true; el.innerHTML = ""; return; }
  el.hidden = false;
  el.innerHTML = `<span class="spin sm" aria-hidden="true"></span><span>${esc(text)}</span>`;
}
function qtyText(n){
  const v = Number(n);
  if(!Number.isFinite(v)) return "—";
  return Math.abs(v-Math.round(v))<1e-9 ? String(Math.round(v)) : String(Math.round(v*100)/100);
}
function vendorTitle(row){
  const name = row.vendor_name || "";
  const code = row.vendor || "";
  if(!code) return "ไม่ระบุเจ้าหนี้";
  return name ? `${name} · ${code}` : code;
}
function haystack(row){
  row._hay = [row.bcode, row.descr, row.model, row.pcode, row.mcode, row.brand, row.vendor, row.vendor_name].join(" ").toLowerCase();
  return row._hay;
}
function validBcode(row){
  return /\d/.test(String(row && row.bcode || "").trim());
}
function match(row){
  if(!validBcode(row)) return false;
  if(state.source==="iclow" && row.source==="insight") return false;
  if(state.source==="ai" && !(row.propose_meta || row.source==="insight")) return false;
  const q = state.q.trim().toLowerCase();
  if(!q) return true;
  return (row._hay || haystack(row)).includes(q);
}
function rowKey(row){
  if(row.iclow_id) return "iclow:" + row.iclow_id;
  return "ai:" + (row.bcode || "");
}
function findRow(key){
  return state.items.find(row => rowKey(row)===key);
}
function orderQty(row){
  const raw = row.order_qty != null && row.order_qty !== "" ? row.order_qty : row.qty;
  const v = Number(raw);
  return Number.isFinite(v) && v > 0 ? v : 0;
}
function aiQty(row){
  const m = row.propose_meta;
  if(m && m.ai_qty) return Number(m.ai_qty);
  if(row.source==="insight") return Number(row.qty) || 0;
  return 0;
}
function recHtml(row){
  const key = rowKey(row);
  const p9 = Number(row.parts9_qty);
  const ai = aiQty(row);
  const p9el = p9 > 0
    ? `<button type="button" class="rec" data-fill="${esc(key)}" data-fillq="${esc(String(p9))}">PARTS9 ${esc(qtyText(p9))}</button>`
    : `<span class="rec off">PARTS9 —</span>`;
  const aiel = ai > 0
    ? `<button type="button" class="rec" data-fill="${esc(key)}" data-fillq="${esc(String(ai))}">AI ${esc(qtyText(ai))}</button>`
    : `<span class="rec off">AI —</span>`;
  const reason = row.propose_meta && row.propose_meta.reason
    ? `<div class="ai">${esc(row.propose_meta.reason)}</div>` : "";
  return `<div class="recs">${p9el}${aiel}</div>${reason}`;
}
function moneyText(n){
  const v = Number(n);
  if(!Number.isFinite(v) || v <= 0) return "";
  const rounded = Math.round(v * 100) / 100;
  if(Math.abs(rounded - Math.round(rounded)) < 1e-9) return Math.round(rounded).toLocaleString("en-US") + ".-";
  return rounded.toLocaleString("en-US", {minimumFractionDigits:2, maximumFractionDigits:2});
}
function thumbHtml(row){
  if(!row || !row.photo) return "";
  return `<img class="thumb" alt="" loading="lazy" src="${esc(row.photo)}" onerror="this.remove()"/>`;
}
function flagHtml(row){
  const mark = row && row.release;
  if(!mark || !mark.label) return "";
  const kind = mark.kind === "reorder" ? "reorder" : "switch";
  const dot = kind === "reorder" ? "🔵" : "🟠";
  return `<div class="flag ${kind}">${dot} ${esc(mark.label)}</div>`;
}
function tradeButton(bcode){
  const code = String(bcode || "").trim();
  if(!code) return "";
  return `<button type="button" class="peer-btn" data-trade="${esc(code)}">Insight</button>`;
}
function productMeta(row){
  const id = [];
  const model = String(row.model || "").trim();
  const pcode = String(row.pcode || "").trim();
  const mcode = String(row.mcode || "").trim();
  const brand = String(row.brand || "").trim();
  if(model) id.push("ชื่อรุ่น " + esc(model));
  if(pcode) id.push("เบอร์แท้ " + esc(pcode));
  if(mcode) id.push("เบอร์โรงงาน " + esc(mcode));
  if(brand) id.push("ยี่ห้อ " + esc(brand));
  const money = [];
  const price = moneyText(row.price);
  const cost = moneyText(row.cost);
  if(price) money.push("ราคา " + price);
  if(cost) money.push("ค่า " + cost);
  return (id.length ? `<div class="meta">${id.join(" · ")}</div>` : "")
    + (money.length ? `<div class="meta">${money.join(" · ")}</div>` : "");
}
function supplierLabel(s){
  const name = String(s.name || "").trim();
  const acct = String(s.acctno || "").trim();
  const bits = [];
  if(name) bits.push(name);
  if(acct && acct !== name) bits.push(acct);
  if(!bits.length) bits.push(acct || "—");
  if(s.fresh) bits.push("เจ้าหนี้ใหม่");
  else if(Number(s.bills) > 0) bits.push(String(s.bills) + " บิล");
  if(!s.fresh && s.last_date) bits.push(String(s.last_date));
  return bits.join(" · ");
}
function vendorFresh(row){
  return (row.suppliers || []).some(s => s.fresh && String(s.acctno || "") === String(row.vendor || ""));
}
function selectedUnit(row){
  return String(row.order_ui || row.ui || row.ui1 || "").trim();
}
function unitHtml(row){
  const ui1 = String(row.ui1 || "").trim();
  const ui2 = String(row.ui2 || "").trim();
  const mtp = Number(row.mtp2);
  const current = selectedUnit(row);
  if(!ui1 || !ui2 || !(mtp > 1) || ui1 === ui2) return "";
  const smallOn = current === ui1 || !current ? " on" : "";
  const largeOn = current === ui2 ? " on" : "";
  return `<div class="unit-pick" role="group" aria-label="หน่วย ${esc(row.bcode || "")}">
    <button type="button" class="unit${smallOn}" data-unit="${esc(rowKey(row))}" data-u="${esc(ui1)}">${esc(ui1)}</button>
    <button type="button" class="unit${largeOn}" data-unit="${esc(rowKey(row))}" data-u="${esc(ui2)}">${esc(ui2)} ×${esc(qtyText(mtp))}</button>
  </div>`;
}
function supplierSelect(row){
  const key = esc(rowKey(row));
  const options = row.suppliers || [];
  const opts = options.map(s => {
    const selected = String(row.vendor || "") === String(s.acctno || "") ? " selected" : "";
    return `<option value="${esc(s.acctno || "")}"${selected}>${esc(supplierLabel(s))}</option>`;
  }).join("");
  const empty = options.length ? "" : `<option value="">เลือกเจ้าหนี้</option>`;
  const ap = row.apOpen
    ? apEditorHtml(rowKey(row), row)
    : `<button type="button" class="peer-btn" data-new-ap="${key}">เลือกเจ้าหนี้ใหม่</button>`;
  return `<label class="vendor-pick">เจ้าหนี้<select data-pick="${key}" aria-label="เจ้าหนี้ ${esc(row.bcode || "")}">${empty}${opts}</select></label>${ap}`;
}
function apEditorHtml(key, row){
  return `<div class="ap-search"><input type="search" data-apq="${esc(key)}" placeholder="ค้นรหัสหรือชื่อเจ้าหนี้" value="${esc(row.apQ || "")}" enterkeyhint="search" autocomplete="off"/><div data-aphits="${esc(key)}">${apHitsHtml(row, key)}</div></div>`;
}
function apHitsHtml(row, key){
  const q = String(row.apQ || "").trim();
  if(q.length < 2) return `<div class="meta">พิมพ์อย่างน้อย 2 ตัว</div>`;
  if(row.apQuery !== q) return spinner("กำลังหาเจ้าหนี้…");
  if(!(row.apHits || []).length) return `<div class="meta">ไม่พบเจ้าหนี้</div>`;
  return row.apHits.map(v => `<button type="button" class="ap-hit" data-ap-use="${esc(key)}" data-acct="${esc(v.acctno || "")}" data-name="${esc(v.name || "")}"><span class="sku">${esc(v.acctno || "")}</span>${esc(v.name || "")}</button>`).join("");
}
function apRowFromKey(key){
  if(key === "catalog") return state.catalogPick;
  return findRow(key);
}
function productTools(row){
  const key = esc(rowKey(row));
  const order = (row.confirmable && STAMP)
    ? (row.vendor
        ? `<button type="button" class="order-btn" data-order="${key}">สั่งกับเจ้าหนี้นี้</button>`
        : `<button type="button" class="order-btn" data-vendors="${key}">เลือกเจ้าหนี้ก่อนสั่ง</button>`)
    : "";
  const trade = tradeButton(row.bcode);
  if(!row.bcode) return order;
  return `${order}<div class="line-actions"><button type="button" class="peer-btn" data-vendors="${key}">เปลี่ยนเจ้าหนี้</button><button type="button" class="peer-btn" data-peers="${key}">สินค้าแทน</button>${trade}</div><div class="peers" data-vendorbox="${key}" hidden></div><div class="peers" data-peerbox="${key}" hidden></div>`;
}
function qtyCell(row){
  if(!(row.confirmable && STAMP)){
    return `<div class="qty">${esc(qtyText(row.qty))}<div class="meta">${esc(row.ui||"")}</div></div>`;
  }
  return `<div class="qty-edit"><input class="qty-in" data-qty="${esc(rowKey(row))}" inputmode="decimal" enterkeyhint="done" value="${esc(qtyText(orderQty(row)))}" aria-label="จำนวน ${esc(row.bcode||"")}"/><span class="meta">${esc(selectedUnit(row))}</span></div>`;
}
function lineHtml(row, mode){
  const pick = mode === "pick";
  const check = !pick ? "" : (row.confirmable && STAMP
    ? `<input type="checkbox" data-key="${esc(rowKey(row))}" data-vendor="${esc(row.vendor||"")}" aria-label="เลือก ${esc(row.bcode||"")}"${row.picked ? " checked" : ""}/>`
    : `<input type="checkbox" disabled/>`);
  const incoming = Number(row.incoming_qty);
  const incomingText = incoming > 0 ? ` · ค้างรับ ${esc(qtyText(incoming))}` : "";
  const packs = Number(row.mtp2);
  const ui2 = String(row.ui2 || "").trim();
  const packText = row.company_qtyoh2 != null && packs > 1 && ui2
    ? ` · ${esc(qtyText(Number(row.company_qtyoh2) / packs))} ${esc(ui2)}` : "";
  const stock = (row.company_qtyoh2==null) ? "" : `คงเหลือรวม ${esc(qtyText(row.company_qtyoh2))} · HQ ${esc(qtyText(row.hq_qtyoh2))} / SYP ${esc(qtyText(row.syp_qtyoh2))}${packText}${incomingText}`;
  const fresh = !pick && vendorFresh(row) ? " · เจ้าหนี้ใหม่" : "";
  const vendorLine = pick ? "" : `<div class="meta" data-vendor-label>${esc(vendorTitle(row))}${fresh}</div>`;
  const tools = pick ? "" : productTools(row);
  return `<div class="line${pick ? "" : " plain"}${pick && row.picked ? " picked" : ""}" id="line-${esc(rowKey(row))}">
    ${check}
    <div class="line-main">
      ${thumbHtml(row)}
      <div>
      <div class="code"><span class="sku">${esc(row.bcode||"—")}</span>${esc(row.descr||"")}</div>
      ${productMeta(row)}
      ${flagHtml(row)}
      ${vendorLine}
      ${unitHtml(row)}
      ${stock ? `<div class="meta">${stock}</div>` : ""}
      ${row.last_date ? `<div class="meta">เคยสั่ง ${esc(row.last_date)}${Number(row.bills) > 0 ? " · " + esc(String(row.bills)) + " บิล" : ""}</div>` : ""}
      ${recHtml(row)}
      ${tools}
      </div>
    </div>
    ${qtyCell(row)}
  </div>`;
}
function selectAllHtml(rows){
  const selectable = (rows || []).filter(row => row.confirmable && STAMP);
  if(!selectable.length) return "";
  const all = selectable.every(row => row.picked);
  return `<label class="select-all"><input type="checkbox" data-select-all aria-label="เลือกทั้งหมด"${all ? " checked" : ""}/>เลือกทั้งหมด</label>`;
}
function applyPicked(box, on){
  box.checked = on;
  const row = findRow(box.dataset.key || "");
  if(row) row.picked = on;
  const line = box.closest(".line");
  if(line) line.classList.toggle("picked", on);
}
function syncSelectAll(){
  document.querySelectorAll("#list input[data-select-all]").forEach(box => {
    const card = box.closest(".card");
    if(!card) return;
    const boxes = [...card.querySelectorAll("input[type=checkbox][data-key]:not(:disabled)")];
    const n = boxes.filter(item => item.checked).length;
    box.checked = boxes.length > 0 && n === boxes.length;
    box.indeterminate = n > 0 && n < boxes.length;
  });
}
function syncDock(){
  const open = state.view === "vendor" && state.vendorKey != null;
  const n = open ? document.querySelectorAll("#list input[type=checkbox][data-key]:checked").length : 0;
  const dock = document.getElementById("dock");
  const show = !!(STAMP && n && !state.busy);
  dock.hidden = !show;
  document.body.classList.toggle("has-dock", show);
  if(show) document.getElementById("dockConfirm").textContent = `ดูใบส่งเจ้าหนี้ ${n} รายการ`;
}
function scheduleRender(label, delay){
  clearTimeout(searchTimer);
  if(state.loading){
    showSearchStatus("กำลังโหลดรายการรอสั่ง…");
    document.getElementById("list").innerHTML = spinner("กำลังโหลดรายการรอสั่ง…");
    syncDock();
    return;
  }
  if(label){
    showSearchStatus(label);
    document.getElementById("list").innerHTML = spinner(label);
    syncDock();
  }
  searchTimer = setTimeout(() => {
    requestAnimationFrame(() => {
      renderList();
      hideSearchStatus();
    });
  }, delay || 0);
}
function vendorGroups(items){
  const groups = new Map();
  for(const row of items){
    const key = row.vendor || "";
    if(!groups.has(key)) groups.set(key, {vendor:key, vendor_name:row.vendor_name || "", lines:[]});
    const g = groups.get(key);
    if(!g.vendor_name && row.vendor_name) g.vendor_name = row.vendor_name;
    g.lines.push(row);
  }
  return [...groups.values()].sort((a,b) => {
    const blank = (a.vendor?0:1) - (b.vendor?0:1);
    if(blank) return blank;
    if(state.vendorSort === "count"){
      const byCount = b.lines.length - a.lines.length;
      if(byCount) return byCount;
    }
    return vendorTitle(a).localeCompare(vendorTitle(b),"th");
  });
}
function syncVendorSort(){
  document.getElementById("vendorSort").hidden = !(state.view === "vendor" && state.vendorKey == null);
}
function setVendorSort(sort){
  state.vendorSort = sort === "name" ? "name" : "count";
  document.getElementById("sortCount").classList.toggle("on", state.vendorSort === "count");
  document.getElementById("sortName").classList.toggle("on", state.vendorSort === "name");
  if(state.view === "vendor" && state.vendorKey == null) scheduleRender("กำลังจัดรายการ…", 0);
}
function sameVendor(row, acct, name){
  const v = String(row.vendor || "").trim();
  const n = String(row.vendor_name || "").trim();
  if(acct && (v === acct || n === acct)) return true;
  if(name && (v === name || n === name)) return true;
  return false;
}
function vendorHitHtml(){
  const q = state.q.trim();
  if(state.vendorQuery !== q) return spinner("กำลังหาเจ้าหนี้…");
  if(!state.vendorHits.length) return '<div class="empty">ไม่พบเจ้าหนี้</div>';
  return state.vendorHits.map(v => `<button type="button" class="vendor-card" data-vendor-history="${esc(v.acctno || "")}" data-vendor-name="${esc(v.name || "")}"><span class="title">${esc(v.name ? v.name + " · " + v.acctno : v.acctno)}</span><span class="badge">เคยสั่ง</span></button>`).join("");
}
function scheduleVendorSearch(){
  clearTimeout(vendorTimer);
  const q = state.q.trim();
  if(q.length < 2){ state.vendorHits = []; state.vendorQuery = ""; return; }
  vendorTimer = setTimeout(() => lookupVendors(q), 200);
}
async function lookupVendors(q){
  state.vendorQuery = q;
  try {
    const res = await fetch("/hq-po/api/vendors?q=" + encodeURIComponent(q));
    const data = await res.json().catch(() => ({}));
    if(state.q.trim() !== q) return;
    state.vendorHits = res.ok ? (data.vendors || []) : [];
  } catch (err) {
    if(state.q.trim() !== q) return;
    state.vendorHits = [];
  }
  renderList();
}
function historyButton(){
  if(!state.vendorKey || state.historyLoaded[state.vendorKey]) return "";
  const label = state.historyLoading ? "กำลังโหลดสินค้าที่เคยสั่ง…" : "ดูสินค้าที่เคยสั่งจากเจ้าหนี้นี้";
  return `<button type="button" class="history-btn" data-load-history="${esc(state.vendorKey)}"${state.historyLoading ? " disabled" : ""}>${esc(label)}</button>`;
}
function addProductControl(kind){
  if(kind === "primary") return `<button type="button" class="order-btn" data-add-product>เพิ่มสินค้าจากรหัสนี้</button>`;
  if(kind === "vendor") return `<button type="button" class="history-btn" data-add-product>เพิ่มสินค้าที่ไม่อยู่ในรายการ</button>`;
  return `<button type="button" class="add-quiet" data-add-product>ไม่ใช่สินค้าที่ต้องการ? เพิ่มจากรหัสอื่น</button>`;
}
function mergeRows(rows){
  const have = new Set(state.items.map(row => String(row.bcode || "")).filter(Boolean));
  const add = (rows || []).filter(row => row.bcode && !have.has(String(row.bcode)));
  for(const row of add) haystack(row);
  if(add.length) state.items = state.items.concat(add);
  return add.length;
}
async function loadVendorInsight(acct){
  if(!acct || state.insightLoaded || state.vendorInsight === acct) return;
  state.vendorInsight = acct;
  try {
    const res = await fetch("/hq-po/api/vendors/" + encodeURIComponent(acct) + "/insight");
    if(!res.ok || state.vendorKey !== acct) return;
    const data = await res.json();
    if(mergeRows(data.items || [])) renderList();
  } catch (err) {
  }
}
async function loadVendorHistory(acct){
  if(!acct || state.historyLoaded[acct] || state.historyLoading) return;
  state.historyLoading = true;
  renderList();
  try {
    const res = await fetch("/hq-po/api/vendors/" + encodeURIComponent(acct) + "/ordered");
    const data = await res.json().catch(() => ({}));
    if(!res.ok) throw new Error(data.message || "โหลดสินค้าที่เคยสั่งไม่ได้");
    if(data.vendor_name) state.vendorName = state.vendorName || data.vendor_name;
    mergeRows(data.items || []);
    state.historyLoaded[acct] = true;
  } catch (err) {
    alert(err.message || "โหลดสินค้าที่เคยสั่งไม่ได้");
  } finally {
    state.historyLoading = false;
    renderList();
  }
}
function showVendor(acct, name, historyOnly){
  state.view = "vendor";
  state.vendorKey = acct || "";
  state.vendorName = name || "";
  state.historyOnly = !!historyOnly;
  document.getElementById("viewVendor").classList.add("on");
  document.getElementById("viewProduct").classList.remove("on");
  syncVendorSort();
  renderList();
  if(acct && !historyOnly) loadVendorInsight(acct);
  if(acct && historyOnly) loadVendorHistory(acct);
}
function renderList(){
  syncVendorSort();
  const y = window.scrollY;
  const host = document.getElementById("list");
  if(state.loading){
    showSearchStatus("กำลังโหลดรายการรอสั่ง…");
    host.innerHTML = spinner("กำลังโหลดรายการรอสั่ง…");
    syncDock();
    return;
  }
  const items = state.items.filter(match);
  const typing = document.activeElement && document.activeElement.id === "q";
  const q = state.q.trim();
  if(state.view==="product"){
    if(!items.length && q.length >= 2){
      if(state.vendorQuery !== q) scheduleVendorSearch();
      host.innerHTML = `<div class="card" style="padding:12px"><div class="meta">ไม่พบในรายการรอสั่ง</div>${addProductControl("primary")}</div>${vendorHitHtml()}`;
    } else {
      const extra = items.length && q ? addProductControl("quiet") : (!items.length ? addProductControl("vendor") : "");
      host.innerHTML = items.length
        ? `<div class="card"><h2><span class="title">สินค้า</span><span class="count">${items.length} รายการ</span></h2>${items.map(row => lineHtml(row, "product")).join("")}</div>${extra}`
        : `<div class="empty">ไม่มีรายการ</div>${extra}`;
    }
    syncDock();
    if(!typing) window.scrollTo(0, y);
    return;
  }
  if(state.vendorKey == null){
    const groups = vendorGroups(items);
    if(!groups.length && q.length >= 2){
      if(state.vendorQuery !== q) scheduleVendorSearch();
      host.innerHTML = `<div class="card" style="padding:12px"><div class="meta">ไม่พบในรายการรอสั่ง</div>${addProductControl("primary")}</div>${vendorHitHtml()}`;
    } else {
      host.innerHTML = groups.length
        ? groups.map(g => `<button type="button" class="vendor-card" data-open-vendor="${esc(g.vendor)}"><span class="title">${esc(vendorTitle(g))}</span><span class="badge">${g.lines.length}</span></button>`).join("")
        : `<div class="empty">ไม่มีรายการ</div>${addProductControl("vendor")}`;
    }
    syncDock();
    if(!typing) window.scrollTo(0, y);
    return;
  }
  const lines = items.filter(row => sameVendor(row, state.vendorKey, state.vendorName) && match(row));
  const named = state.items.find(row => sameVendor(row, state.vendorKey, state.vendorName));
  const title = state.vendorName
    ? (state.vendorName + (state.vendorKey ? " · " + state.vendorKey : ""))
    : (named ? vendorTitle(named) : (state.vendorKey || "ไม่ระบุเจ้าหนี้"));
  const waiting = lines.filter(row => row.source !== "insight" && row.source !== "history");
  const ai = lines.filter(row => row.source === "insight");
  const past = lines.filter(row => row.source === "history");
  const section = (label, rows) => rows.length
    ? `<div class="card"><h2><span class="title">${esc(label)}</span><span class="count">${rows.length} รายการ</span></h2>${selectAllHtml(rows)}${rows.map(row => lineHtml(row, "pick")).join("")}</div>`
    : "";
  const body = state.historyOnly
    ? (past.length ? section("เคยสั่ง", past) : (state.historyLoading ? spinner("กำลังโหลดสินค้าที่เคยสั่ง…") : ""))
    : `${section("รอสั่ง", waiting)}${section("AI", ai)}${past.length ? section("เคยสั่ง", past) : ""}`;
  host.innerHTML = `<button type="button" class="back" data-vendor-back>เจ้าหนี้ทั้งหมด</button><div class="card"><h2><span class="title">${esc(title)}</span></h2></div>${body}${historyButton()}${addProductControl("vendor")}`;
  syncSelectAll();
  syncDock();
  if(!typing) window.scrollTo(0, y);
}
function setView(view){
  state.view = view;
  state.vendorKey = null;
  state.vendorName = "";
  state.historyOnly = false;
  document.getElementById("viewVendor").classList.toggle("on", view==="vendor");
  document.getElementById("viewProduct").classList.toggle("on", view==="product");
  syncVendorSort();
  scheduleRender("กำลังจัดรายการ…", 0);
}
function openVendorOrder(row){
  if(!row || !row.vendor) return;
  row.picked = true;
  state.q = "";
  state.vendorHits = [];
  state.vendorQuery = "";
  const q = document.getElementById("q");
  if(q) q.value = "";
  showVendor(row.vendor || "", row.vendor_name || "", false);
  const line = document.getElementById("line-" + rowKey(row));
  if(line) line.scrollIntoView({block:"center"});
}
function setSource(source){
  state.source = source;
  for(const [id, val] of [["srcAll","all"],["srcIclow","iclow"],["srcAi","ai"]]){
    document.getElementById(id).classList.toggle("on", source===val);
  }
  if(source === "ai") loadInsight();
  else scheduleRender("กำลังจัดรายการ…", 0);
}
async function loadInsight(){
  if(state.insightLoaded){
    scheduleRender("กำลังจัดรายการ…", 0);
    return;
  }
  if(state.insightLoading) return;
  const gen = insightGen;
  state.insightLoading = true;
  setInsight("กำลังโหลดคำแนะนำ AI…");
  if(state.source === "ai"){
    document.getElementById("list").innerHTML = spinner("กำลังโหลดคำแนะนำ AI…");
  }
  try {
    const res = await fetch("/hq-po/api/insight");
    if(gen !== insightGen) return;
    if(!res.ok){ setInsight(""); return; }
    const data = await res.json();
    const extra = data.items || [];
    const have = new Set(state.items.filter(row => row.source==="insight").map(row => row.bcode));
    const add = extra.filter(row => row.bcode && !have.has(row.bcode));
    for(const row of add) haystack(row);
    if(add.length) state.items = state.items.concat(add);
    state.insightLoaded = true;
    renderList();
  } catch (err) {
  } finally {
    if(gen === insightGen){
      state.insightLoading = false;
      setInsight("");
    }
  }
}
async function loadSuggest(){
  const host = document.getElementById("list");
  state.loading = true;
  state.insightLoaded = false;
  state.insightLoading = false;
  insightGen += 1;
  clearTimeout(searchTimer);
  showSearchStatus("กำลังโหลดรายการรอสั่ง…");
  host.innerHTML = spinner("กำลังโหลดรายการรอสั่ง…");
  syncDock();
  try {
    const res = await fetch("/hq-po/api/suggest");
    if(!res.ok){
      state.loading = false;
      hideSearchStatus();
      host.innerHTML = '<div class="empty">โหลดรายการไม่ได้</div>';
      return;
    }
    const data = await res.json();
    state.items = (data.items || []).filter(validBcode);
    for(const row of state.items) haystack(row);
    state.loading = false;
    hideSearchStatus();
    renderList();
    if(state.source === "ai") loadInsight();
  } catch (err) {
    state.loading = false;
    hideSearchStatus();
    host.innerHTML = '<div class="empty">โหลดรายการไม่ได้</div>';
  }
}
function checkedRows(){
  return [...document.querySelectorAll("#list input[type=checkbox][data-key]:checked")]
    .map(box => findRow(box.dataset.key || ""))
    .filter(Boolean);
}
function linePayload(row){
  const meta = Object.assign({}, row.propose_meta || {});
  if(row.parts9_qty) meta.parts9_qty = row.parts9_qty;
  const body = {qty: orderQty(row), vendor: row.vendor || "", ui: selectedUnit(row), propose_meta: Object.keys(meta).length ? meta : null};
  if(row.iclow_id) body.iclow_id = row.iclow_id;
  else body.bcode = row.bcode;
  return body;
}
async function postVendor(vendor, picked){
  const sample = picked[0];
  const res = await fetch("/hq-po/api/orders", {
    method:"POST",
    headers:{"Content-Type":"application/json"},
    body: JSON.stringify({
      vendor: vendor,
      vendor_name: sample.vendor_name || "",
      lines: picked.map(linePayload),
    }),
  });
  const data = await res.json().catch(()=>({}));
  if(!res.ok) throw new Error(data.message || "สั่งซื้อไม่สำเร็จ");
  return data;
}
async function confirmRows(rows){
  if(state.busy) return;
  const byVendor = new Map();
  for(const row of rows){
    if(!row || !row.confirmable) continue;
    const key = row.vendor || "";
    if(!byVendor.has(key)) byVendor.set(key, []);
    byVendor.get(key).push(row);
  }
  if(!byVendor.size){ alert("เลือกรายการและใส่จำนวน"); return; }
  const docs = [];
  const skipped = [];
  let failed = null;
  setBusy(true, "กำลังบันทึกใบสั่งซื้อ…");
  try{
    for(const [vendor, picked] of byVendor){
      const data = await postVendor(vendor, picked);
      if(data.docno) docs.push(data.docno);
      for(const row of data.skipped || []) skipped.push(row);
    }
  }catch(err){
    failed = err;
  }finally{
    setBusy(false);
  }
  if(failed){
    alert(failed.message || "สั่งซื้อไม่สำเร็จ");
    await loadSuggest();
    return;
  }
  closeSheet();
  let msg = "สั่งแล้ว " + docs.filter(Boolean).join(", ");
  if(skipped.length){
    msg += "\nข้ามรายการที่อยู่ในใบสั่งซื้อแล้ว: " + skipped.map(row => {
      const code = row.bcode || "";
      return row.docno ? code + " (" + row.docno + ")" : code;
    }).join(", ");
  }
  alert(msg);
  await loadSuggest();
}
function groupsOf(rows){
  const groups = new Map();
  for(const row of rows){
    if(!row || !row.confirmable || orderQty(row) <= 0) continue;
    const key = row.vendor || "";
    if(!groups.has(key)) groups.set(key, {vendor:key, vendor_name:row.vendor_name, docno:row.docno||"", docdate:row.docdate||"", lines:[]});
    groups.get(key).lines.push(row);
  }
  return [...groups.values()];
}
function sheetPayload(){
  return {
    groups: groupsOf(state.sheet).map(g => ({
      vendor: g.vendor,
      vendor_name: g.vendor_name || "",
      docno: g.docno || "",
      docdate: g.docdate || "",
      lines: g.lines.map(row => ({
        bcode: row.bcode || "",
        descr: row.descr || "",
        qty: orderQty(row),
        ui: selectedUnit(row),
        model: row.model || "",
        brand: row.brand || "",
        pcode: row.pcode || "",
        mcode: row.mcode || "",
      })),
    })),
  };
}
function showVariant(variant){
  state.variant = variant === "full" ? "full" : "simple";
  document.getElementById("varSimple").classList.toggle("on", state.variant==="simple");
  document.getElementById("varFull").classList.toggle("on", state.variant==="full");
  const html = (state.forms && state.forms[state.variant + "_html"]) || "";
  document.getElementById("sheetBody").innerHTML = html
    ? `<div class="sheet-preview">${html}</div>`
    : '<div class="empty">ไม่มีแบบฟอร์ม</div>';
}
function setSheetMode(saved){
  state.sheetSaved = !!saved;
  document.getElementById("sheetCommit").hidden = !!saved;
  document.getElementById("sheetFootNote").textContent = saved
    ? "ใบที่บันทึกแล้ว — พิมพ์หรือคัดลอกส่งฝ่ายขายได้"
    : "ส่งให้ฝ่ายขายก่อน แล้วค่อยบันทึกว่าสั่งแล้ว";
}
async function loadSheetForms(){
  document.getElementById("sheetBody").innerHTML = spinner("กำลังจัดใบสั่งซื้อ…");
  state.forms = null;
  try {
    const res = await fetch("/hq-po/api/sheet", {
      method:"POST",
      headers:{"Content-Type":"application/json"},
      body: JSON.stringify(sheetPayload()),
    });
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.message || "จัดใบสั่งซื้อไม่สำเร็จ");
    state.forms = data;
    showVariant(state.variant);
  } catch (err) {
    document.getElementById("sheetBody").innerHTML = `<div class="empty">${esc(err.message || "จัดใบสั่งซื้อไม่สำเร็จ")}</div>`;
  }
}
function currentSheetText(){
  return (state.forms && state.forms[state.variant + "_text"]) || "";
}
function openSheet(rows, opts){
  const picked = (rows||[]).filter(row => row && row.confirmable && orderQty(row) > 0);
  if(!picked.length){ alert("เลือกรายการและใส่จำนวน"); return; }
  state.sheet = picked;
  setSheetMode(!!(opts && opts.saved));
  document.getElementById("sheet").hidden = false;
  window.scrollTo(0,0);
  loadSheetForms();
}
function closeSheet(){
  state.sheet = [];
  const el = document.getElementById("sheet");
  if(el) el.hidden = true;
}
function orderFilterText(value){
  return String(value || "").trim().toLowerCase();
}
function orderVisible(order){
  const vendorQ = orderFilterText(state.orderVendor);
  const codeQ = orderFilterText(state.orderBcode);
  if(vendorQ){
    const hay = [order.vendor_name, order.vendor_acctno].join(" ").toLowerCase();
    if(!hay.includes(vendorQ)) return false;
  }
  if(codeQ){
    return (order.lines || []).some(line => String(line.bcode || "").toLowerCase().includes(codeQ));
  }
  return true;
}
function orderVisibleLines(order){
  const codeQ = orderFilterText(state.orderBcode);
  const lines = order.lines || [];
  if(!codeQ) return lines;
  return lines.filter(line => String(line.bcode || "").toLowerCase().includes(codeQ));
}
function orderDateText(iso){
  const raw = String(iso || "").trim();
  if(!raw) return "";
  const d = new Date(raw);
  if(Number.isNaN(d.getTime())) return raw.slice(0, 10);
  return new Intl.DateTimeFormat("en-GB", {timeZone:"Asia/Bangkok", day:"2-digit", month:"2-digit", year:"numeric"}).format(d);
}
function bangkokDay(value){
  const raw = String(value || "").trim();
  if(/^\d{4}-\d{2}-\d{2}/.test(raw)) return raw.slice(0, 10);
  const d = new Date(raw);
  if(Number.isNaN(d.getTime())) return "";
  return new Intl.DateTimeFormat("en-CA", {timeZone:"Asia/Bangkok", year:"numeric", month:"2-digit", day:"2-digit"}).format(d);
}
function todayBangkok(){
  return new Intl.DateTimeFormat("en-CA", {timeZone:"Asia/Bangkok", year:"numeric", month:"2-digit", day:"2-digit"}).format(new Date());
}
function ageDays(value){
  const day = bangkokDay(value);
  if(!day) return null;
  const from = Date.parse(day + "T00:00:00Z");
  const today = Date.parse(todayBangkok() + "T00:00:00Z");
  if(Number.isNaN(from) || Number.isNaN(today)) return null;
  return Math.max(0, Math.round((today - from) / 86400000));
}
function ageText(days){
  if(days == null) return "";
  if(days === 0) return "ค้างวันนี้";
  return "ค้าง " + days + " วัน";
}
function sortByDay(rows, key, newest){
  return rows.slice().sort((a, b) => {
    const da = bangkokDay(a[key]);
    const db = bangkokDay(b[key]);
    if(!da && !db) return 0;
    if(!da) return 1;
    if(!db) return -1;
    if(da === db) return 0;
    return newest ? (da < db ? 1 : -1) : (da < db ? -1 : 1);
  });
}
function renderOrders(){
  const host = document.getElementById("orders");
  const all = state.orders || [];
  if(!all.length){
    host.innerHTML = '<div class="empty">ยังไม่มีใบสั่งซื้อ</div>';
    return;
  }
  const orders = sortByDay(all.filter(orderVisible), "ordered_at", state.orderSort !== "old");
  if(!orders.length){
    host.innerHTML = '<div class="empty">ไม่พบใบสั่งซื้อตามตัวกรอง</div>';
    return;
  }
  const filtering = orderFilterText(state.orderVendor) || orderFilterText(state.orderBcode);
  const summary = filtering ? `<p class="count">${orders.length} ใบ</p>` : "";
  host.innerHTML = summary + orders.map(order => {
    const badge = order.receive_label==="รับแล้ว" ? "done" : "wait";
    const lines = orderVisibleLines(order).map(line => {
      const rec = line.receive || {};
      const pi = rec.pimas_billno ? ` · PI ${esc(rec.pimas_billno)}` : (rec.rcvdno ? ` · ${esc(rec.rcvdno)}` : "");
      const canReturn = STAMP && line.line_id && !rec.received && !rec.unknown;
      const lineCancel = canReturn
        ? `<button type="button" class="ghost" data-cancel-line="${esc(order.order_id)}" data-line="${esc(line.line_id)}" data-bcode="${esc(line.bcode||"")}">ยกเลิกบรรทัด</button>`
        : "";
      return `<div class="line"><div></div><div><div class="code"><span class="sku">${esc(line.bcode||"—")}</span>${esc(line.descr||"")}</div>${productMeta(line)}<div class="meta">${esc(rec.label||"")}${pi}</div>${lineCancel}</div><div class="qty">${esc(qtyText(line.qty))}</div></div>`;
    }).join("");
    const anyReceived = (order.lines||[]).some(line => (line.receive||{}).received);
    const cancel = STAMP && !anyReceived && order.receive_label!=="รับแล้ว"
      ? `<button type="button" class="ghost" data-cancel="${esc(order.order_id)}">ยกเลิกใบนี้</button>` : "";
    const reprint = `<button type="button" data-sheet="${esc(order.order_id)}">พิมพ์ / คัดลอก</button>`;
    const actions = `<div class="actions">${reprint}${cancel}</div>`;
    const title = order.vendor_name || order.vendor_acctno || "ไม่ระบุเจ้าหนี้";
    const when = orderDateText(order.ordered_at);
    const whenHtml = when ? `<span class="when">วันที่สั่ง ${esc(when)}</span>` : "";
    const n = orderVisibleLines(order).length;
    const open = orderFilterText(state.orderBcode) ? " open" : "";
    const body = lines || '<div class="line plain"><div class="meta">ไม่มีรายการสินค้า</div></div>';
    const linesBlock = `<details class="po-lines"${open}><summary>รายการสินค้า ${n} รายการ</summary>${body}</details>`;
    return `<div class="card"><h2><span class="title">${esc(order.docno)} · ${esc(title)}${whenHtml}</span><span class="badge ${badge}">${esc(order.receive_label||"")}</span></h2>${linesBlock}${actions}</div>`;
  }).join("");
}
async function loadOrders(){
  const host = document.getElementById("orders");
  state.ordersLoaded = false;
  host.innerHTML = spinner("กำลังโหลดใบที่สั่งแล้ว…");
  try {
    const res = await fetch("/hq-po/api/orders");
    if(!res.ok){ host.innerHTML = '<div class="empty">โหลดใบที่สั่งแล้วไม่ได้</div>'; return; }
    const data = await res.json();
    state.orders = data.orders || [];
    state.ordersLoaded = true;
    renderOrders();
  } catch (err) {
    host.innerHTML = '<div class="empty">โหลดใบที่สั่งแล้วไม่ได้</div>';
  }
}
async function cancelLine(orderId, lineId, bcode){
  if(state.busy) return;
  const name = bcode ? ` ${bcode}` : "";
  if(!confirm(`ยกเลิก${name} และคืนไปรายการรอสั่ง?`)) return;
  setBusy(true, "กำลังยกเลิกบรรทัด…");
  let failed = null;
  try {
    const res = await fetch(`/hq-po/api/orders/${orderId}/lines/${lineId}/cancel`, {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"});
    const data = await res.json().catch(()=>({}));
    if(!res.ok) failed = new Error(data.message || "ยกเลิกบรรทัดไม่สำเร็จ");
  } catch (err) {
    failed = err;
  } finally {
    setBusy(false);
  }
  if(failed){ alert(failed.message || "ยกเลิกบรรทัดไม่สำเร็จ"); return; }
  await loadOrders();
  await loadSuggest();
}
async function cancelOrder(id){
  if(state.busy) return;
  if(!confirm("ยกเลิกใบนี้บน ICLOW?")) return;
  setBusy(true, "กำลังยกเลิก…");
  let failed = null;
  try {
    const res = await fetch(`/hq-po/api/orders/${id}/cancel`, {method:"POST", headers:{"Content-Type":"application/json"}, body:"{}"});
    const data = await res.json().catch(()=>({}));
    if(!res.ok) failed = new Error(data.message || "ยกเลิกไม่สำเร็จ");
  } catch (err) {
    failed = err;
  } finally {
    setBusy(false);
  }
  if(failed){ alert(failed.message || "ยกเลิกไม่สำเร็จ"); return; }
  await loadOrders();
  await loadSuggest();
}
document.getElementById("addProduct").onclick = () => openCatalog();
document.getElementById("viewVendor").onclick = () => setView("vendor");
document.getElementById("viewProduct").onclick = () => setView("product");
document.getElementById("sortCount").onclick = () => setVendorSort("count");
document.getElementById("sortName").onclick = () => setVendorSort("name");
document.getElementById("srcAll").onclick = () => setSource("all");
document.getElementById("srcIclow").onclick = () => setSource("iclow");
document.getElementById("srcAi").onclick = () => setSource("ai");
document.getElementById("q").oninput = (e) => {
  state.q = e.target.value;
  scheduleRender(state.loading ? "" : "กำลังค้นหา…", state.loading ? 0 : 180);
};
function setDoneMode(mode){
  const product = mode === "product";
  state.doneMode = product ? "product" : "bill";
  document.getElementById("doneBill").classList.toggle("on", !product);
  document.getElementById("doneProduct").classList.toggle("on", product);
  document.getElementById("billFilters").hidden = product;
  document.getElementById("holdQ").hidden = !product;
  syncDoneSort();
  document.getElementById("orders").hidden = product;
  document.getElementById("holdList").hidden = !product;
  if(product){
    if(!state.holdLoaded) loadHold();
    else renderHold();
  }else if(!state.ordersLoaded){
    loadOrders();
  }else{
    renderOrders();
  }
}
function setTab(name){
  state.tab = name;
  document.getElementById("tabOrder").classList.toggle("on", name === "order");
  document.getElementById("tabDone").classList.toggle("on", name === "done");
  document.getElementById("orderView").hidden = name !== "order";
  document.getElementById("doneView").hidden = name !== "done";
  syncDock();
  if(name === "done") setDoneMode(state.doneMode);
}
document.getElementById("tabOrder").onclick = () => setTab("order");
document.getElementById("tabDone").onclick = () => setTab("done");
document.getElementById("doneBill").onclick = () => setDoneMode("bill");
document.getElementById("doneProduct").onclick = () => setDoneMode("product");
function syncDoneSort(){
  const newest = (state.doneMode === "product" ? state.holdSort : state.orderSort) !== "old";
  document.getElementById("sortOld").classList.toggle("on", !newest);
  document.getElementById("sortNew").classList.toggle("on", newest);
}
function setDoneSort(dir){
  if(state.doneMode === "product") state.holdSort = dir;
  else state.orderSort = dir;
  syncDoneSort();
  if(state.doneMode === "product") renderHold();
  else if(state.ordersLoaded) renderOrders();
}
document.getElementById("sortOld").onclick = () => setDoneSort("old");
document.getElementById("sortNew").onclick = () => setDoneSort("new");
function holdMatch(row){
  const q = state.holdQ.trim().toLowerCase();
  if(!q) return true;
  return [row.bcode, row.descr, row.vendor, row.vendor_name, row.docno].join(" ").toLowerCase().includes(q);
}
function holdLineHtml(row){
  const id = row.iclow_id;
  const when = [row.docdate, row.docno].filter(Boolean).join(" · ");
  const age = ageText(ageDays(row.docdate));
  const actions = STAMP ? `<div class="line-actions"><button type="button" class="peer-btn" data-release="${esc(id)}" data-kind="switch">เปลี่ยนเจ้าสั่ง</button><button type="button" class="peer-btn" data-release="${esc(id)}" data-kind="reorder">สั่งย้ำเจ้าเดิม</button>${tradeButton(row.bcode)}</div>` : tradeButton(row.bcode);
  return `<div class="line plain">
    <div class="line-main">
      ${thumbHtml(row)}
      <div>
        <div class="code"><span class="sku">${esc(row.bcode||"—")}</span>${esc(row.descr||"")}</div>
        <div class="meta">${esc(row.vendor_name ? row.vendor_name + " · " + row.vendor : (row.vendor || "ไม่ระบุเจ้าหนี้"))}</div>
        ${when || age ? `<div class="meta">${esc(when)}${when && age ? " · " : ""}${age ? `<span class="badge wait">${esc(age)}</span>` : ""}</div>` : ""}
        ${actions}
      </div>
    </div>
    <div class="qty">${esc(qtyText(row.qty))}<div class="meta">${esc(row.ui||"")}</div></div>
  </div>`;
}
function renderHold(){
  const host = document.getElementById("holdList");
  const rows = sortByDay((state.hold || []).filter(holdMatch), "docdate", state.holdSort !== "old");
  if(!state.holdLoaded){
    host.innerHTML = spinner("กำลังโหลดสินค้าที่สั่งแล้ว…");
    return;
  }
  if(!rows.length){
    host.innerHTML = '<div class="empty">ไม่มีสินค้าที่สั่งแล้วและยังไม่รับ</div>';
    return;
  }
  host.innerHTML = `<div class="card">${rows.map(holdLineHtml).join("")}</div>`;
}
async function loadHold(){
  const host = document.getElementById("holdList");
  host.innerHTML = spinner("กำลังโหลดสินค้าที่สั่งแล้ว…");
  try {
    const res = await fetch("/hq-po/api/incoming");
    const data = await res.json().catch(() => ({}));
    if(!res.ok) throw new Error(data.message || "โหลดค้างรับไม่ได้");
    state.hold = data.items || [];
    state.holdLoaded = true;
    renderHold();
  } catch (err) {
    state.holdLoaded = true;
    host.innerHTML = '<div class="empty">โหลดค้างรับไม่ได้</div>';
  }
}
let histGen = 0;
let histCode = "";
let histSite = "hq";
function liveInsight(bcode){
  const code = String(bcode || "").trim();
  const row = (state.items || []).find(item => String(item.bcode || "").trim() === code)
    || (state.hold || []).find(item => String(item.bcode || "").trim() === code)
    || {};
  return {qtyHq: row.hq_qtyoh2, qtySyp: row.syp_qtyoh2, ui1: row.ui || row.ui1 || "", descr: row.descr || ""};
}
function insightHtml(ins, live){
  const st = (ins && ins.status) || "no_movement";
  if(st === "working") return '<div class="empty">กำลังสร้าง insight…</div>';
  if(st === "no_movement" || !ins || !ins.insight) return '<div class="empty">ไม่มีการเคลื่อนไหวใน 5 ปี</div>';
  const i = ins.insight || {};
  const pol = ins.policy || {};
  const der = i.derived || {};
  const dash = i.dashboard || der.dashboard || {};
  const num = (v) => {
    if(v == null || v === "") return null;
    const n = Number(v);
    return Number.isFinite(n) ? n : null;
  };
  const pick = (...vals) => {
    for(const v of vals){ if(v != null && v !== "") return v; }
    return null;
  };
  const sales = dash.sales || {};
  const ch = dash.channels_12m || {};
  const pm = dash.price_margin || {};
  const stk = dash.stock || {};
  const purch = i.purchase || {};
  const ic = i.icmas || {};
  const tr = i.trends || {};
  const mg = i.margin || {};
  const fl = der.flags || {};
  const dem = der.demand || {};
  const holdBlk = der.holding || {};
  const od = der.order || {};
  const mgDer = der.margin || {};
  const td = der.trend || {};
  const xfer = der.transfer || {};
  const unit = String(pick(stk.unit, purch.order_unit, pol.order_unit, live.ui1, od.ui1, "") || "");
  const qtyU = (n) => {
    if(n == null) return "—";
    return esc(qtyText(n)) + (unit ? " " + esc(unit) : "");
  };
  const moneyU = (n) => {
    if(n == null) return "—";
    const text = moneyText(n);
    if(!text) return "—";
    return esc(text) + (unit ? " บาท/" + esc(unit) : "");
  };
  const latestMo = num(pick(sales.latest_month, dem.qty_30d, pol.sales_qty_30d));
  const avg3 = num(pick(sales.avg_3m, dem.monthly_from_90d));
  const avg12 = num(pick(sales.avg_12m, dem.monthly_from_12m, i.typical_monthly_qty, pol.typical_monthly_qty));
  const tot12 = num(pick(sales.total_12m, dem.qty_12m, pol.sales_qty_12m));
  const trendMap = {hot:"ร้อน", growing:"เติบโต", flat:"คงที่", declining:"ลดลง", dead:"ตาย", lumpy:"กระจุก", seasonal:"ตามฤดูกาล", unknown:"ไม่ชัด"};
  const trend = String(pick(sales.trend, tr.m12, i.trend_label, pol.trend_12m, td["12m"]) || "");
  const trendTh = trendMap[trend.toLowerCase()] || trend || "—";
  const chHq = num(pick(ch.hq, (dem.by_channel_12m || {}).hq_store));
  const chSyp = num(pick(ch.syp, (dem.by_channel_12m || {}).syp_store));
  const chOn = num(pick(ch.online, (dem.by_channel_12m || {}).online));
  const chSum = (chHq || 0) + (chSyp || 0) + (chOn || 0);
  const pct = (part, given) => {
    const n = num(given);
    if(n != null) return n;
    return chSum ? (part || 0) / chSum * 100 : null;
  };
  const qtyHq = num(live.qtyHq);
  const qtySyp = num(live.qtySyp);
  const qtyTotal = (qtyHq != null || qtySyp != null) ? (qtyHq || 0) + (qtySyp || 0) : null;
  const target = num(pick(stk.target, i.safe_holding_qty, pol.safe_holding_qty, holdBlk.safe_holding_qty));
  const reorder = num(pick(stk.reorder_point, ic.rec_qtymin, pol.rec_qtymin, fl.rec_qtymin));
  const lot = num(pick(stk.suggested_lot, purch.suggested_order_qty, pol.suggested_order_qty, od.order_qty));
  const coverWeeks = num(pick(pol.suggested_cover_weeks, holdBlk.cover_weeks, i.suggested_cover_weeks));
  const coverDays = coverWeeks != null ? Math.round(coverWeeks * 7) : null;
  const dead = pick(dash.dead_stock, i.dead_stock, pol.dead_stock, fl.dead_stock);
  const orderOk = pick(purch.order_ok, pol.order_ok, fl.order_ok);
  let orderStatus = "caution";
  if(dead === "yes") orderStatus = "dead_stock";
  else if(qtyTotal != null && target != null && qtyTotal >= target) orderStatus = "no_order_needed";
  else if(qtyTotal != null && reorder != null && qtyTotal <= reorder) orderStatus = "should_order";
  else if(orderOk === "caution" || dead === "maybe" || orderOk === "no") orderStatus = "caution";
  else if(qtyTotal != null && target != null && qtyTotal < target) orderStatus = "should_order";
  else if(orderOk === "yes") orderStatus = "no_order_needed";
  const statusMap = {
    no_order_needed: ["ok", "🟢 ยังไม่ต้องสั่ง"],
    should_order: ["order", "🔵 ควรสั่ง"],
    caution: ["warn", "🟠 ระวัง"],
    dead_stock: ["bad", "🔴 Dead Stock"]
  };
  const stInfo = statusMap[orderStatus] || ["warn", orderStatus];
  const avgBuy = num(pick(pm.avg_buy, mgDer.avg_buy_12m));
  const avgSell = num(pick(pm.avg_sell, mgDer.avg_sell_12m));
  const marginPct = num(pick(pm.margin_pct, mgDer.realized_pct_12m, pol.margin_pct_12m, mg.list_pct, pol.margin_pct_list));
  const sypTarget = num(pick(xfer.syp_safe_holding, pol.rec_transfer_qty_to_syp));
  const suppliers = (dash.suppliers || der.suppliers_12m || []).slice(0, 3);
  const customers = (dash.customers || der.customers_12m || []).slice(0, 3);
  const kpi = (label, value) => `<div class="ikpi"><div class="l">${esc(label)}</div><div class="v">${value}</div></div>`;
  const series = ins.monthly_sales || [];
  const maxBar = Math.max(1, ...series.map(s => Number(s.qty) || 0));
  const bars = series.length ? `<div class="ibars">${series.map(s => {
    const n = Number(s.qty) || 0;
    const h = Math.max(2, Math.round(n / maxBar * 64));
    return `<div class="ibar"><span style="height:${h}px"></span><em>${esc(String(s.ym || "").slice(5))}</em></div>`;
  }).join("")}</div>` : "";
  const share = (n) => n == null ? "—" : esc(qtyText(n)) + "%";
  const people = (rows, price) => {
    if(!rows.length) return `<tr><td class="meta" colspan="3">—</td></tr>`;
    return rows.map(row => {
      const name = row.name || row.acctno || "—";
      const extra = price
        ? `<td class="num">${moneyU(num(row.avg_price))}</td>`
        : `<td class="num">${share(num(row.pct_of_sales))}</td>`;
      return `<tr><td>${esc(name)}</td><td class="num">${qtyU(num(row.qty))}</td>${extra}</tr>`;
    }).join("");
  };
  const photo = ins.photo ? `<img class="thumb" alt="" src="${esc(ins.photo)}" onerror="this.remove()"/>` : "";
  const summary = ins.summary ? `<div class="meta">${esc(ins.summary)}</div>` : "";
  const when = [ins.facts_as_of ? "ข้อมูลถึง " + ins.facts_as_of : "", ins.generated_at ? "สร้าง " + ins.generated_at : ""].filter(Boolean).join(" · ");
  return `${photo}<div style="margin-top:8px"><span class="istatus ${stInfo[0]}">${esc(stInfo[1])}</span></div>
    ${summary}
    <h3>ยอดขาย · ${esc(trendTh)}</h3>
    <div class="ikpis">${kpi("เดือนล่าสุด", qtyU(latestMo))}${kpi("เฉลี่ย 3 เดือน", qtyU(avg3))}${kpi("เฉลี่ยช่วงข้อมูล", qtyU(avg12))}${kpi("รวม 12 เดือน", qtyU(tot12))}</div>
    ${bars}
    <h3>Stock</h3>
    <div class="istock">${kpi("คงเหลือรวม", qtyU(qtyTotal))}${kpi("Safety Stock", qtyU(target) + (coverDays != null ? `<div class="l">ประมาณ ${esc(String(coverDays))} วัน</div>` : ""))}${kpi("จุดสั่งซื้อ", qtyU(reorder))}${kpi("ล็อตแนะนำ", qtyU(lot))}</div>
    <h3>ช่องทางขาย 12 เดือน</h3>
    <table class="itable"><thead><tr><th>ช่องทาง</th><th class="num">ยอดขาย</th><th class="num">สัดส่วน</th></tr></thead><tbody>
      <tr><td>HQ</td><td class="num">${qtyU(chHq)}</td><td class="num">${share(pct(chHq, ch.hq_pct))}</td></tr>
      <tr><td>SYP</td><td class="num">${qtyU(chSyp)}</td><td class="num">${share(pct(chSyp, ch.syp_pct))}</td></tr>
      <tr><td>Online</td><td class="num">${qtyU(chOn)}</td><td class="num">${share(pct(chOn, ch.online_pct))}</td></tr>
    </tbody></table>
    <h3>ราคาและมาร์จิ้น</h3>
    <table class="itable"><tbody>
      <tr><td>ราคาซื้อเฉลี่ย</td><td class="num">${moneyU(avgBuy)}</td></tr>
      <tr><td>ราคาขายเฉลี่ย</td><td class="num">${moneyU(avgSell)}</td></tr>
      <tr><td>Margin</td><td class="num">${marginPct == null ? "—" : esc(qtyText(marginPct)) + "%"}</td></tr>
    </tbody></table>
    <h3>SYP</h3>
    <div class="ikpis">${kpi("คงเหลือ SYP", qtyU(qtySyp))}${kpi("เป้าโอน", qtyU(sypTarget))}</div>
    <h3>เจ้าหลัก</h3>
    <table class="itable"><thead><tr><th>เจ้าหนี้</th><th class="num">ยอดซื้อ</th><th class="num">ราคาเฉลี่ย</th></tr></thead><tbody>${people(suppliers, true)}</tbody></table>
    <h3>ลูกค้าหลัก</h3>
    <table class="itable"><thead><tr><th>ลูกค้า</th><th class="num">ยอดซื้อ</th><th class="num">สัดส่วน</th></tr></thead><tbody>${people(customers, false)}</tbody></table>
    ${when ? `<div class="meta">${esc(when)}</div>` : ""}`;
}
async function openTrade(bcode, site){
  const code = String(bcode || "").trim();
  if(!code) return;
  histCode = code;
  histSite = site === "syp" ? "syp" : "hq";
  const gen = ++histGen;
  const box = document.getElementById("hist");
  document.getElementById("histTitle").textContent = code + " · " + histSite.toUpperCase();
  document.getElementById("histHq").classList.toggle("on", histSite !== "syp");
  document.getElementById("histSyp").classList.toggle("on", histSite === "syp");
  document.getElementById("histBody").innerHTML = spinner("กำลังโหลด insight…");
  box.hidden = false;
  try {
    const res = await fetch("/hq-po/api/history/" + encodeURIComponent(code) + "?site=" + histSite);
    const data = await res.json().catch(() => ({}));
    if(gen !== histGen) return;
    if(!res.ok) throw new Error(data.message || "โหลด insight ไม่ได้");
    document.getElementById("histBody").innerHTML = insightHtml(data, liveInsight(code));
  } catch (err) {
    if(gen !== histGen) return;
    document.getElementById("histBody").innerHTML = '<div class="empty">โหลด insight ไม่ได้</div>';
  }
}
async function releaseHold(id, kind){
  const word = kind === "reorder"
    ? "ยกเลิกค้างรับ แล้วส่งกลับหน้ารอสั่ง เป็นสั่งย้ำเจ้าเดิม"
    : "ยกเลิกค้างรับ แล้วส่งกลับหน้ารอสั่ง เป็นเปลี่ยนเจ้า";
  if(!confirm(word + "?")) return;
  setBusy(true, "กำลังยกเลิกค้างรับ…");
  let failed = null;
  try {
    const res = await fetch("/hq-po/api/incoming/" + encodeURIComponent(id) + "/release", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({kind: kind === "reorder" ? "reorder" : "switch"}),
    });
    const data = await res.json().catch(() => ({}));
    if(!res.ok) failed = new Error(data.message || "ยกเลิกค้างรับไม่สำเร็จ");
  } catch (err) {
    failed = err;
  } finally {
    setBusy(false);
  }
  if(failed){ alert(failed.message || "ยกเลิกค้างรับไม่สำเร็จ"); return; }
  await loadHold();
  await loadSuggest();
  setTab("order");
}
document.getElementById("holdQ").oninput = (e) => {
  state.holdQ = e.target.value;
  if(state.holdLoaded) renderHold();
};
document.getElementById("holdList").onclick = (e) => {
  const trade = e.target.closest("[data-trade]");
  if(trade){ openTrade(trade.getAttribute("data-trade") || ""); return; }
  const rel = e.target.closest("[data-release]");
  if(rel){ releaseHold(rel.getAttribute("data-release") || "", rel.getAttribute("data-kind") || ""); }
};
document.getElementById("histHq").onclick = () => { if(histCode) openTrade(histCode, "hq"); };
document.getElementById("histSyp").onclick = () => { if(histCode) openTrade(histCode, "syp"); };
document.getElementById("histClose").onclick = () => { document.getElementById("hist").hidden = true; };
document.getElementById("hist").onclick = (e) => { if(e.target.id === "hist") document.getElementById("hist").hidden = true; };
function onOrderFilter(key, value){
  state[key] = value;
  if(state.ordersLoaded) renderOrders();
}
document.getElementById("orderVendor").oninput = (e) => onOrderFilter("orderVendor", e.target.value);
document.getElementById("orderBcode").oninput = (e) => onOrderFilter("orderBcode", e.target.value);
function peerLineHtml(owner, line){
  const bits = [];
  const cost = moneyText(line.cost);
  if(line.brand) bits.push(line.brand);
  if(cost) bits.push("ค่า " + cost);
  if(line.company_qtyoh2 != null) bits.push("คงเหลือ " + qtyText(line.company_qtyoh2));
  if(line.vendor_name || line.vendor) bits.push(line.vendor_name || line.vendor);
  return `<button type="button" class="peer" data-use="${esc(rowKey(owner))}" data-peer="${esc(line.bcode)}"><span class="sku">${esc(line.bcode)}</span>${esc(line.descr||"")}<span class="meta">${esc(bits.join(" · "))}</span></button>`;
}
function peerPanelHtml(row){
  const groups = ((row.peers && row.peers.groups) || []).filter(g => (g.lines||[]).length);
  if(!groups.length) return `<div class="meta">ไม่พบสินค้าแทน</div>`;
  return groups.map(g => `<div class="peer-sec"><div class="meta">${esc(g.label||"")}</div>${(g.lines||[]).map(line => peerLineHtml(row, line)).join("")}</div>`).join("");
}
async function loadPeers(row){
  if(!row || !row.bcode) return;
  const box = document.querySelector(`[data-peerbox="${CSS.escape(rowKey(row))}"]`);
  if(!box) return;
  if(row.peers && box.dataset.open === "1"){
    box.hidden = true;
    box.dataset.open = "";
    return;
  }
  box.hidden = false;
  box.dataset.open = "1";
  if(row.peers){ box.innerHTML = peerPanelHtml(row); return; }
  box.innerHTML = spinner("กำลังหาสินค้าแทน…");
  try {
    const res = await fetch("/hq-po/api/peers/" + encodeURIComponent(row.bcode));
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.message || "หาสินค้าแทนไม่ได้");
    row.peers = data;
    box.innerHTML = peerPanelHtml(row);
  } catch (err) {
    box.innerHTML = `<div class="meta">${esc(err.message || "หาสินค้าแทนไม่ได้")}</div>`;
  }
}
function findPeer(row, bcode){
  const groups = (row.peers && row.peers.groups) || [];
  for(const group of groups){
    const hit = (group.lines||[]).find(line => String(line.bcode||"") === bcode);
    if(hit) return hit;
  }
  return null;
}
function scrollToRow(row){
  const el = document.getElementById("line-" + rowKey(row));
  if(el) el.scrollIntoView({block:"center"});
}
function usePeer(row, bcode){
  if(!row || !bcode) return;
  const hit = findPeer(row, bcode);
  if(!hit) return;
  const existing = state.items.find(item => String(item.bcode||"") === bcode);
  if(!existing && !hit.vendor){
    alert("สินค้านี้ยังไม่มีเจ้าหนี้ที่สั่งได้");
    return;
  }
  if(existing){
    renderList();
    scrollToRow(existing);
    return;
  }
  const added = {
    iclow_id: null,
    source: "peer",
    confirmable: !!hit.vendor,
    vendor: hit.vendor || "",
    vendor_name: hit.vendor_name || "",
    bcode: hit.bcode,
    descr: hit.descr || "",
    model: hit.model || "",
    brand: hit.brand || "",
    pcode: hit.pcode || "",
    mcode: hit.mcode || "",
    ui: hit.ui1 || hit.ui || "",
    ui1: hit.ui1 || hit.ui || "",
    ui2: hit.ui2 || "",
    mtp2: hit.mtp2 || 1,
    price: hit.price,
    cost: hit.cost,
    qty: orderQty(row) || 1,
    order_qty: orderQty(row) || 1,
    hq_qtyoh2: hit.hq_qtyoh2,
    syp_qtyoh2: hit.syp_qtyoh2,
    company_qtyoh2: hit.company_qtyoh2,
    propose_meta: {iclow_origin: "peer"},
  };
  const idx = state.items.indexOf(row);
  state.items.splice(idx < 0 ? state.items.length : idx + 1, 0, added);
  haystack(added);
  renderList();
  scrollToRow(added);
}
async function loadSuppliers(row){
  if(!row || !row.bcode) return;
  const box = document.querySelector(`[data-vendorbox="${CSS.escape(rowKey(row))}"]`);
  if(!box) return;
  if(row.suppliers && box.dataset.open === "1"){
    box.hidden = true;
    box.dataset.open = "";
    return;
  }
  box.hidden = false;
  box.dataset.open = "1";
  if(row.suppliers){ box.innerHTML = supplierSelect(row); return; }
  box.innerHTML = spinner("กำลังหาเจ้าหนี้…");
  try {
    const params = new URLSearchParams();
    if(row.vendor) params.set("current", row.vendor);
    if(row.vendor_name) params.set("current_name", row.vendor_name);
    const qs = params.toString();
    const res = await fetch("/hq-po/api/suppliers/" + encodeURIComponent(row.bcode) + (qs ? "?" + qs : ""));
    const data = await res.json().catch(()=>({}));
    if(!res.ok) throw new Error(data.message || "หาเจ้าหนี้ไม่ได้");
    row.suppliers = data.suppliers || [];
    box.innerHTML = supplierSelect(row);
  } catch (err) {
    box.innerHTML = `<div class="meta">${esc(err.message || "หาเจ้าหนี้ไม่ได้")}</div>`;
  }
}
function paintApHits(row, key){
  const host = document.querySelector(`[data-aphits="${CSS.escape(key)}"]`);
  if(host) host.innerHTML = apHitsHtml(row, key);
}
function scheduleAp(row, key){
  clearTimeout(apTimer);
  const q = String(row.apQ || "").trim();
  if(q.length < 2){
    row.apHits = [];
    row.apQuery = "";
    paintApHits(row, key);
    return;
  }
  const host = document.querySelector(`[data-aphits="${CSS.escape(key)}"]`);
  if(host) host.innerHTML = spinner("กำลังหาเจ้าหนี้…");
  apTimer = setTimeout(() => lookupAp(row, key, q), 200);
}
async function lookupAp(row, key, q){
  row.apQuery = q;
  try {
    const res = await fetch("/hq-po/api/vendors?q=" + encodeURIComponent(q));
    const data = await res.json().catch(() => ({}));
    if(String(row.apQ || "").trim() !== q) return;
    row.apHits = res.ok ? (data.vendors || []) : [];
  } catch (err) {
    if(String(row.apQ || "").trim() !== q) return;
    row.apHits = [];
  }
  paintApHits(row, key);
}
function applyNewVendor(row, acct, name){
  if(!row || !acct) return;
  row.suppliers = row.suppliers || [];
  let hit = row.suppliers.find(s => String(s.acctno || "") === acct);
  if(!hit){
    hit = {acctno: acct, name: name || "", bills: 0, last_date: "", fresh: true};
    row.suppliers.push(hit);
  } else if(name && !hit.name) hit.name = name;
  row.vendor = acct;
  row.vendor_name = hit.name || name || "";
  row.apOpen = false;
  row._hay = "";
  haystack(row);
  if(row === state.catalogPick){
    renderCatalog();
    return;
  }
  const key = rowKey(row);
  const box = document.querySelector(`[data-vendorbox="${CSS.escape(key)}"]`);
  if(box){
    box.hidden = false;
    box.dataset.open = "1";
    box.innerHTML = supplierSelect(row);
  }
  const line = document.getElementById("line-" + key);
  const shown = line && line.querySelector("[data-vendor-label]");
  if(shown) shown.textContent = vendorTitle(row) + (vendorFresh(row) ? " · เจ้าหนี้ใหม่" : "");
  const orderBtn = line && line.querySelector(".order-btn");
  if(orderBtn && row.vendor){
    orderBtn.textContent = "สั่งกับเจ้าหนี้นี้";
    orderBtn.removeAttribute("data-vendors");
    orderBtn.setAttribute("data-order", key);
  }
}
function toggleNewAp(key){
  const row = apRowFromKey(key);
  if(!row) return;
  row.apOpen = !row.apOpen;
  if(key === "catalog"){
    renderCatalog();
    const input = document.querySelector("#catalog input[data-apq]");
    if(input) input.focus();
    return;
  }
  const box = document.querySelector(`[data-vendorbox="${CSS.escape(key)}"]`);
  if(!box) return;
  box.innerHTML = supplierSelect(row);
  const input = box.querySelector("input[data-apq]");
  if(input) input.focus();
}
function openCatalog(){
  const fromVendor = state.view === "vendor" && state.vendorKey != null;
  state.catalogVendor = fromVendor ? (state.vendorKey || "") : "";
  state.catalogVendorName = fromVendor ? (state.vendorName || "") : "";
  state.catalogPick = null;
  state.catalogHits = [];
  state.catalogQuery = "";
  state.catalogLoading = false;
  state.catalogQ = state.q.trim();
  document.getElementById("catalog").hidden = false;
  const input = document.getElementById("catalogQ");
  input.value = state.catalogQ;
  renderCatalog();
  input.focus();
  if(state.catalogQ.length >= 2) lookupProducts(state.catalogQ);
}
function closeCatalog(){
  state.catalogPick = null;
  document.getElementById("catalog").hidden = true;
}
function renderCatalog(){
  const pick = state.catalogPick;
  document.getElementById("catalogBack").hidden = !pick;
  document.getElementById("catalogQ").hidden = !!pick;
  document.getElementById("catalogQ").parentElement.hidden = !!pick;
  const sub = document.getElementById("catalogSub");
  if(pick){
    sub.textContent = state.catalogVendorName
      ? "ใส่ในใบของ " + state.catalogVendorName
      : "เลือกจำนวนและเจ้าหนี้ แล้วใส่ในรายการ";
  } else {
    sub.textContent = "ค้นจากรหัสสินค้าใน PARTS9";
  }
  const host = document.getElementById("catalogBody");
  if(pick){
    host.innerHTML = catalogEditorHtml(pick);
    return;
  }
  const q = state.catalogQ.trim();
  if(q.length < 2){
    host.innerHTML = '<div class="empty">พิมพ์อย่างน้อย 2 ตัว</div>';
    return;
  }
  if(state.catalogLoading || state.catalogQuery !== q){
    host.innerHTML = spinner("กำลังหาสินค้า…");
    return;
  }
  if(!state.catalogHits.length){
    host.innerHTML = '<div class="empty">ไม่พบรหัสนี้ในสินค้า</div>';
    return;
  }
  host.innerHTML = state.catalogHits.map(catalogHitHtml).join("");
}
function catalogHitHtml(row){
  const stock = row.company_qtyoh2 == null ? "" : `<div class="meta">คงเหลือรวม ${esc(qtyText(row.company_qtyoh2))} · HQ ${esc(qtyText(row.hq_qtyoh2))} / SYP ${esc(qtyText(row.syp_qtyoh2))}</div>`;
  const last = row.last_vendor_name || row.last_vendor || "";
  const lastLine = last ? `<div class="meta">เจ้าหนี้ล่าสุด ${esc(last)}${row.last_date ? " · " + esc(row.last_date) : ""}</div>` : "";
  const wait = row.waiting ? `<div class="meta"><span class="badge wait">อยู่ในรายการรอสั่ง</span></div>` : "";
  return `<div class="pick-row"><div class="grow"><div class="code"><span class="sku">${esc(row.bcode || "—")}</span>${esc(row.descr || "")}</div>${productMeta(row)}${stock}${lastLine}${wait}</div><button type="button" class="choose" data-catalog-choose="${esc(row.bcode || "")}">${row.waiting ? "ไปที่รายการ" : "เลือก"}</button></div>`;
}
function catalogUnitHtml(row){
  const ui1 = String(row.ui1 || row.ui || "").trim();
  const ui2 = String(row.ui2 || "").trim();
  const mtp = Number(row.mtp2);
  const current = String(row.order_ui || ui1).trim();
  if(!ui1 || !ui2 || !(mtp > 1) || ui1 === ui2) return "";
  const smallOn = current === ui1 || !current ? " on" : "";
  const largeOn = current === ui2 ? " on" : "";
  return `<div class="unit-pick" role="group" aria-label="หน่วย ${esc(row.bcode || "")}"><button type="button" class="unit${smallOn}" data-catalog-unit="${esc(ui1)}">${esc(ui1)}</button><button type="button" class="unit${largeOn}" data-catalog-unit="${esc(ui2)}">${esc(ui2)} ×${esc(qtyText(mtp))}</button></div>`;
}
function catalogSupplierHtml(row){
  if(row.suppliersLoading) return spinner("กำลังหาเจ้าหนี้…");
  const options = row.suppliers || [];
  const opts = options.map(s => {
    const selected = String(row.vendor || "") === String(s.acctno || "") ? " selected" : "";
    return `<option value="${esc(s.acctno || "")}"${selected}>${esc(supplierLabel(s))}</option>`;
  }).join("");
  const empty = options.length ? "" : `<option value="">เลือกเจ้าหนี้</option>`;
  const ap = row.apOpen
    ? apEditorHtml("catalog", row)
    : `<button type="button" class="peer-btn" data-new-ap="catalog">เลือกเจ้าหนี้ใหม่</button>`;
  return `<label class="vendor-pick">เจ้าหนี้<select data-catalog-pick aria-label="เจ้าหนี้ ${esc(row.bcode || "")}">${empty}${opts}</select></label>${ap}`;
}
function catalogEditorHtml(row){
  const label = state.catalogVendor ? "ใส่ในใบของเจ้าหนี้นี้" : "ใส่รายการนี้";
  const stock = row.company_qtyoh2 == null ? "" : `<div class="meta">คงเหลือรวม ${esc(qtyText(row.company_qtyoh2))} · HQ ${esc(qtyText(row.hq_qtyoh2))} / SYP ${esc(qtyText(row.syp_qtyoh2))}</div>`;
  return `<div class="card"><div class="line plain"><div><div class="code"><span class="sku">${esc(row.bcode || "—")}</span>${esc(row.descr || "")}</div>${productMeta(row)}${catalogUnitHtml(row)}${stock}${catalogSupplierHtml(row)}<button type="button" class="order-btn" data-catalog-accept>${label}</button></div><div class="qty-edit"><input class="qty-in" data-catalog-qty inputmode="decimal" enterkeyhint="done" value="${esc(qtyText(row.order_qty || 1))}" aria-label="จำนวน ${esc(row.bcode || "")}"/><span class="meta">${esc(row.order_ui || row.ui || "")}</span></div></div></div>`;
}
function scheduleCatalogSearch(){
  clearTimeout(catalogTimer);
  const q = state.catalogQ.trim();
  if(q.length < 2){
    state.catalogHits = [];
    state.catalogQuery = "";
    state.catalogLoading = false;
    renderCatalog();
    return;
  }
  state.catalogLoading = true;
  renderCatalog();
  catalogTimer = setTimeout(() => lookupProducts(q), 200);
}
async function lookupProducts(q){
  state.catalogLoading = true;
  state.catalogQuery = "";
  try {
    const res = await fetch("/hq-po/api/products?q=" + encodeURIComponent(q));
    const data = await res.json().catch(() => ({}));
    if(state.catalogQ.trim() !== q) return;
    state.catalogHits = res.ok ? (data.products || []) : [];
    state.catalogQuery = q;
  } catch (err) {
    if(state.catalogQ.trim() !== q) return;
    state.catalogHits = [];
    state.catalogQuery = q;
  } finally {
    if(state.catalogQ.trim() === q){
      state.catalogLoading = false;
      renderCatalog();
    }
  }
}
function chooseCatalogProduct(bcode){
  const hit = state.catalogHits.find(row => String(row.bcode || "") === bcode);
  if(!hit) return;
  if(hit.waiting){
    const existing = state.items.find(item => String(item.bcode || "") === bcode);
    closeCatalog();
    if(!existing){
      alert("สินค้านี้อยู่ในรายการรอสั่งแล้ว");
      return;
    }
    state.q = "";
    const q = document.getElementById("q");
    if(q) q.value = "";
    if(existing.vendor) openVendorOrder(existing);
    else { renderList(); scrollToRow(existing); }
    return;
  }
  state.catalogPick = Object.assign({}, hit, {
    order_qty: 1,
    order_ui: hit.ui1 || hit.ui || "",
    suppliers: null,
    suppliersLoading: true,
    apOpen: false,
    apQ: "",
    apHits: [],
    apQuery: "",
  });
  if(state.catalogVendor){
    state.catalogPick.vendor = state.catalogVendor;
    state.catalogPick.vendor_name = state.catalogVendorName || "";
  }
  renderCatalog();
  loadCatalogSuppliers(state.catalogPick);
}
async function loadCatalogSuppliers(row){
  try {
    const params = new URLSearchParams();
    const current = state.catalogVendor || row.vendor || "";
    const currentName = state.catalogVendor ? state.catalogVendorName : (row.vendor_name || "");
    if(current) params.set("current", current);
    if(currentName) params.set("current_name", currentName);
    const qs = params.toString();
    const res = await fetch("/hq-po/api/suppliers/" + encodeURIComponent(row.bcode) + (qs ? "?" + qs : ""));
    const data = await res.json().catch(() => ({}));
    if(state.catalogPick !== row) return;
    if(!res.ok) throw new Error(data.message || "หาเจ้าหนี้ไม่ได้");
    row.suppliers = data.suppliers || [];
    const preset = state.catalogVendor || "";
    if(preset && !row.suppliers.some(s => String(s.acctno || "") === preset)){
      row.suppliers.push({acctno: preset, name: state.catalogVendorName || "", bills: 0, last_date: "", fresh: true});
    }
    if(preset){
      row.vendor = preset;
      const named = row.suppliers.find(s => String(s.acctno || "") === preset);
      row.vendor_name = (named && named.name) || state.catalogVendorName || "";
    } else if(row.vendor && !row.suppliers.some(s => String(s.acctno || "") === String(row.vendor))){
      row.suppliers.unshift({
        acctno: row.vendor,
        name: row.vendor_name || "",
        bills: 0,
        last_date: row.last_date || "",
        fresh: !row.last_vendor,
      });
    }
  } catch (err) {
    if(state.catalogPick !== row) return;
    row.suppliers = row.suppliers || [];
    alert(err.message || "หาเจ้าหนี้ไม่ได้");
  } finally {
    if(state.catalogPick === row){
      row.suppliersLoading = false;
      renderCatalog();
    }
  }
}
function acceptCatalog(){
  const row = state.catalogPick;
  if(!row) return;
  const qty = Number(row.order_qty);
  if(!(qty > 0)){ alert("ใส่จำนวน"); return; }
  if(!row.vendor){ alert("เลือกเจ้าหนี้ก่อน"); return; }
  const existing = state.items.find(item => String(item.bcode || "") === String(row.bcode || ""));
  if(existing){
    closeCatalog();
    if(existing.vendor) openVendorOrder(existing);
    else { renderList(); scrollToRow(existing); }
    return;
  }
  const added = {
    iclow_id: null,
    source: "catalog",
    confirmable: true,
    vendor: row.vendor,
    vendor_name: row.vendor_name || "",
    bcode: row.bcode,
    descr: row.descr || "",
    model: row.model || "",
    brand: row.brand || "",
    pcode: row.pcode || "",
    mcode: row.mcode || "",
    ui: row.ui1 || row.ui || "",
    ui1: row.ui1 || row.ui || "",
    ui2: row.ui2 || "",
    mtp2: row.mtp2 || 1,
    order_ui: row.order_ui || row.ui1 || row.ui || "",
    price: row.price,
    cost: row.cost,
    qty: qty,
    order_qty: qty,
    hq_qtyoh2: row.hq_qtyoh2,
    syp_qtyoh2: row.syp_qtyoh2,
    company_qtyoh2: row.company_qtyoh2,
    suppliers: row.suppliers || [],
    propose_meta: {iclow_origin: "catalog"},
    picked: true,
  };
  haystack(added);
  state.items.push(added);
  closeCatalog();
  openVendorOrder(added);
}
document.getElementById("catalogClose").onclick = () => closeCatalog();
document.getElementById("catalogBack").onclick = () => {
  state.catalogPick = null;
  renderCatalog();
  document.getElementById("catalogQ").focus();
};
document.getElementById("catalogQ").oninput = (e) => {
  state.catalogQ = e.target.value;
  scheduleCatalogSearch();
};
document.getElementById("catalog").onclick = (e) => {
  const choose = e.target.closest("[data-catalog-choose]");
  if(choose){ chooseCatalogProduct(choose.dataset.catalogChoose || ""); return; }
  const unit = e.target.closest("[data-catalog-unit]");
  if(unit && state.catalogPick){
    state.catalogPick.order_ui = unit.dataset.catalogUnit || "";
    renderCatalog();
    return;
  }
  const neu = e.target.closest("[data-new-ap]");
  if(neu){ toggleNewAp(neu.dataset.newAp || ""); return; }
  const apUse = e.target.closest("[data-ap-use]");
  if(apUse){
    applyNewVendor(apRowFromKey(apUse.dataset.apUse || ""), apUse.dataset.acct || "", apUse.dataset.name || "");
    return;
  }
  if(e.target.closest("[data-catalog-accept]")) acceptCatalog();
};
document.getElementById("catalog").oninput = (e) => {
  const qty = e.target.closest("input[data-catalog-qty]");
  if(qty && state.catalogPick){
    state.catalogPick.order_qty = qty.value;
    return;
  }
  const ap = e.target.closest("input[data-apq]");
  if(ap && state.catalogPick){
    state.catalogPick.apQ = ap.value;
    scheduleAp(state.catalogPick, "catalog");
  }
};
document.getElementById("catalog").onchange = (e) => {
  const pick = e.target.closest("select[data-catalog-pick]");
  if(!pick || !state.catalogPick) return;
  const hit = (state.catalogPick.suppliers || []).find(s => s.acctno === pick.value);
  if(!hit){
    state.catalogPick.vendor = "";
    state.catalogPick.vendor_name = "";
    return;
  }
  state.catalogPick.vendor = hit.acctno;
  state.catalogPick.vendor_name = hit.name || "";
};
document.getElementById("list").onclick = (e) => {
  const trade = e.target.closest("[data-trade]");
  if(trade){ openTrade(trade.getAttribute("data-trade") || ""); return; }
  const unit = e.target.closest("[data-unit]");
  if(unit){
    const row = findRow(unit.dataset.unit || "");
    const u = unit.dataset.u || "";
    if(row && u){
      row.order_ui = u;
      const line = unit.closest(".line");
      if(line){
        line.querySelectorAll("[data-unit]").forEach(btn => btn.classList.toggle("on", btn.dataset.u === u));
        const meta = line.querySelector(".qty-edit .meta");
        if(meta) meta.textContent = u;
      }
    }
    return;
  }
  const order = e.target.closest("[data-order]");
  if(order){ openVendorOrder(findRow(order.dataset.order || "")); return; }
  const add = e.target.closest("[data-add-product]");
  if(add){ openCatalog(); return; }
  const neu = e.target.closest("[data-new-ap]");
  if(neu){ toggleNewAp(neu.dataset.newAp || ""); return; }
  const apUse = e.target.closest("[data-ap-use]");
  if(apUse){
    applyNewVendor(apRowFromKey(apUse.dataset.apUse || ""), apUse.dataset.acct || "", apUse.dataset.name || "");
    return;
  }
  const back = e.target.closest("[data-vendor-back]");
  if(back){ state.vendorKey = null; state.vendorName = ""; state.historyOnly = false; renderList(); return; }
  const past = e.target.closest("[data-load-history]");
  if(past){ loadVendorHistory(past.getAttribute("data-load-history") || ""); return; }
  const history = e.target.closest("[data-vendor-history]");
  if(history){
    state.q = "";
    const q = document.getElementById("q");
    if(q) q.value = "";
    showVendor(history.getAttribute("data-vendor-history") || "", history.getAttribute("data-vendor-name") || "", true);
    return;
  }
  const open = e.target.closest("[data-open-vendor]");
  if(open){
    const acct = open.getAttribute("data-open-vendor") || "";
    const named = state.items.find(row => (row.vendor || "") === acct);
    showVendor(acct, named ? (named.vendor_name || "") : "", false);
    return;
  }
  const vendors = e.target.closest("[data-vendors]");
  if(vendors){ loadSuppliers(findRow(vendors.dataset.vendors || "")); return; }
  const peers = e.target.closest("[data-peers]");
  if(peers){ loadPeers(findRow(peers.dataset.peers || "")); return; }
  const use = e.target.closest("[data-use]");
  if(use){ usePeer(findRow(use.dataset.use || ""), use.dataset.peer || ""); return; }
  const fill = e.target.closest("[data-fill]");
  if(fill){
    const row = findRow(fill.dataset.fill || "");
    const q = Number(fill.dataset.fillq);
    if(row && q > 0){
      row.order_qty = q;
      const input = document.querySelector(`input[data-qty="${CSS.escape(fill.dataset.fill || "")}"]`);
      if(input) input.value = qtyText(q);
    }
    return;
  }
};
document.getElementById("list").oninput = (e) => {
  const ap = e.target.closest("input[data-apq]");
  if(ap){
    const row = apRowFromKey(ap.dataset.apq || "");
    if(!row) return;
    row.apQ = ap.value;
    scheduleAp(row, ap.dataset.apq || "");
    return;
  }
  const input = e.target.closest("input[data-qty]");
  if(!input) return;
  const row = findRow(input.dataset.qty || "");
  if(row) row.order_qty = input.value;
};
document.getElementById("list").onchange = (e) => {
  const all = e.target.closest("input[data-select-all]");
  if(all){
    const card = all.closest(".card");
    const on = all.checked;
    if(card){
      card.querySelectorAll("input[type=checkbox][data-key]:not(:disabled)").forEach(box => applyPicked(box, on));
    }
    all.indeterminate = false;
    syncDock();
    return;
  }
  const box = e.target.closest("input[type=checkbox][data-key]");
  if(box){
    applyPicked(box, box.checked);
    syncSelectAll();
    syncDock();
    return;
  }
  const pick = e.target.closest("select[data-pick]");
  if(!pick){ syncDock(); return; }
  const row = findRow(pick.dataset.pick || "");
  const hit = row && (row.suppliers || []).find(s => s.acctno === pick.value);
  if(hit && row){
    row.vendor = hit.acctno;
    row.vendor_name = hit.name || "";
    row._hay = "";
    haystack(row);
    const line = document.getElementById("line-" + rowKey(row));
    const shown = line && line.querySelector("[data-vendor-label]");
    if(shown) shown.textContent = vendorTitle(row) + (vendorFresh(row) ? " · เจ้าหนี้ใหม่" : "");
    const orderBtn = line && line.querySelector(".order-btn");
    if(orderBtn && row.vendor){
      orderBtn.textContent = "สั่งกับเจ้าหนี้นี้";
      orderBtn.removeAttribute("data-vendors");
      orderBtn.setAttribute("data-order", rowKey(row));
    }
  }
};
document.getElementById("dockConfirm").onclick = () => openSheet(checkedRows());
document.getElementById("sheetClose").onclick = () => closeSheet();
document.getElementById("varSimple").onclick = () => { if(state.forms) showVariant("simple"); };
document.getElementById("varFull").onclick = () => { if(state.forms) showVariant("full"); };
document.getElementById("sheetPrint").onclick = () => {
  const html = (state.forms && state.forms[state.variant + "_html"]) || "";
  if(!html){ alert("กำลังจัดใบสั่งซื้อ"); return; }
  document.getElementById("printSheet").innerHTML = html;
  document.body.setAttribute("data-print", "po");
  window.print();
};
window.addEventListener("afterprint", () => document.body.removeAttribute("data-print"));
document.getElementById("sheetCopy").onclick = async () => {
  const text = currentSheetText();
  if(!text){ alert("กำลังจัดใบสั่งซื้อ"); return; }
  try {
    await navigator.clipboard.writeText(text);
    alert("คัดลอกแล้ว วางส่งฝ่ายขายได้");
  } catch (err) {
    alert(text);
  }
};
document.getElementById("sheetCommit").onclick = () => confirmRows(state.sheet || []);
function openSavedSheet(id){
  const order = (state.orders || []).find(row => row.order_id === id);
  if(!order) return;
  const rows = (order.lines || []).filter(line => !line.canceled_at).map(line => ({
    confirmable: true,
    vendor: order.vendor_acctno || "",
    vendor_name: order.vendor_name || "",
    docno: order.docno || "",
    docdate: order.ordered_at || "",
    bcode: line.bcode || "",
    descr: line.descr || "",
    qty: line.qty,
    order_qty: line.qty,
    ui: line.ui || "",
  }));
  openSheet(rows, {saved:true});
}
document.getElementById("orders").onclick = (e) => {
  const sheet = e.target.closest("[data-sheet]");
  if(sheet){ openSavedSheet(sheet.getAttribute("data-sheet")); return; }
  const lineBtn = e.target.closest("[data-cancel-line]");
  if(lineBtn){
    cancelLine(lineBtn.getAttribute("data-cancel-line"), lineBtn.getAttribute("data-line"), lineBtn.getAttribute("data-bcode") || "");
    return;
  }
  const btn = e.target.closest("[data-cancel]");
  if(btn) cancelOrder(btn.getAttribute("data-cancel"));
};
document.getElementById("viewVendor").classList.toggle("on", state.view==="vendor");
document.getElementById("viewProduct").classList.toggle("on", state.view==="product");
loadSuggest();
</script>
</body>
</html>
"""

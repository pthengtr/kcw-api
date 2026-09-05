from __future__ import annotations

import html as html_lib
import json
import re

APP = "kcw-transfer"
SESSION_COOKIE = "kcw_transfer"
_BRANCH_LABELS = {"HQ": "สำนักงานใหญ่", "SYP": "สาขา"}


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


def page(
    *,
    user_name: str = "",
    site: str = "HQ",
    hq_ship_enabled: bool = False,
    syp_ship_enabled: bool = False,
    hq_receive_enabled: bool = False,
    syp_receive_enabled: bool = False,
    sticker_printer_model: str = "te310",
    sticker_printer_host: str = "",
) -> str:
    who = (user_name or "operator").strip()
    site_u = (site or "HQ").upper()
    ship_on = syp_ship_enabled if site_u == "SYP" else hq_ship_enabled
    recv_on = syp_receive_enabled if site_u == "SYP" else hq_receive_enabled
    other = "HQ" if site_u == "SYP" else "SYP"
    site_label = _BRANCH_LABELS.get(site_u, site_u)
    other_label = _BRANCH_LABELS.get(other, other)
    # HQ = blue, SYP = teal — distinct at a glance on phone / shared screens
    theme_color = "#e8eef8" if site_u == "HQ" else "#e6f5f2"
    model = (sticker_printer_model or "te310").strip() or "te310"
    host = (sticker_printer_host or "").strip()
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace("__OTHER__", other)
        .replace("__SITE_LABEL__", site_label)
        .replace("__OTHER_LABEL__", other_label)
        .replace("__THEME_COLOR__", theme_color)
        .replace('__SHIP_WRITE__ === "true"', "true" if ship_on else "false")
        .replace('__RECV_WRITE__ === "true"', "true" if recv_on else "false")
        .replace("__INITIALS__", html_lib.escape(initials(who)))
        .replace("__STICKER_MODEL_JSON__", json.dumps(model, ensure_ascii=False))
        .replace("__STICKER_HOST_JSON__", json.dumps(host, ensure_ascii=False))
    )


_HTML = r"""<!doctype html>
<html lang="th" data-theme="light" data-site="__SITE__">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light"/>
<meta name="theme-color" content="__THEME_COLOR__" id="themeColor"/>
<title>โอนสินค้า · __SITE_LABEL__</title>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root{
  --ok:#15803d;--warn:#c2410c;--down:#dc2626;--card:#fff;--line:#e5e9f2;--text:#111827;--muted:#6b7280;
  --shadow:0 1px 2px rgba(16,24,40,.06),0 4px 12px rgba(16,24,40,.04);
  /* defaults = HQ blue */
  --acc:#2563eb;--acc-soft:#dbeafe;--acc-mid:#93c5fd;--acc-pick:#eff6ff;--acc-pick-card:#eff6ff;
  --page-bg:#e8eef8;--hdr-bar:#2563eb;--site-badge-bg:#1e40af;
}
html[data-site="HQ"]{
  --acc:#2563eb;--acc-soft:#dbeafe;--acc-mid:#93c5fd;--acc-pick:#eff6ff;--acc-pick-card:#eff6ff;
  --page-bg:#e8eef8;--hdr-bar:#2563eb;--site-badge-bg:#1e40af;
}
html[data-site="SYP"]{
  --acc:#0f766e;--acc-soft:#ccfbf1;--acc-mid:#5eead4;--acc-pick:#f0fdfa;--acc-pick-card:#f0fdfa;
  --page-bg:#e6f5f2;--hdr-bar:#0f766e;--site-badge-bg:#115e59;
}
*{box-sizing:border-box}body{margin:0;font-family:Prompt,sans-serif;background:var(--page-bg);color:var(--text)}
button{font:inherit;color:var(--text);-webkit-appearance:none;appearance:none}
.hdr{position:sticky;top:0;z-index:20;background:#fff;border-bottom:1px solid var(--line);border-top:3px solid var(--hdr-bar);padding:.75rem 1rem;box-shadow:var(--shadow);display:flex;align-items:center;gap:.65rem}
.hdr-main{flex:1;min-width:0}
.hdr h1{margin:0;font-size:1.05rem;color:var(--text)}.hdr .sub{font-size:.78rem;color:var(--muted)}
.site-badge{flex:0 0 auto;display:inline-flex;align-items:center;gap:.25rem;padding:.28rem .55rem;border-radius:999px;background:var(--site-badge-bg);color:#fff;font-size:.72rem;font-weight:700;letter-spacing:.02em;line-height:1.2;white-space:nowrap}
.site-badge .code{opacity:.9;font-weight:600}
.back-btn{border:1px solid var(--line);background:#fff;color:var(--text);border-radius:10px;padding:.4rem .7rem;font:inherit;cursor:pointer;white-space:nowrap}
main{padding:1rem;max-width:1200px;margin:0 auto;width:100%}
.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:1rem;box-shadow:var(--shadow);margin-bottom:.85rem}
.card:has(.view-table){overflow:visible}
.card-table{padding-bottom:0}
.card-table > .view-table > .table-wrap{margin-top:.5rem}
.card-table > .view-table > .table-wrap:last-child{margin-bottom:0;border-radius:0 0 12px 12px}
.card-table > .view-cards{padding-top:.5rem}
.card-table > .row-actions{margin:1rem}
.table-wrap{
  overflow:auto;
  -webkit-overflow-scrolling:touch;
  max-height:min(58vh,26rem);
  border:1px solid var(--line);
  border-radius:12px;
  background:var(--card);
}
.table-wrap--tall{max-height:min(72vh,34rem)}
.modal .table-wrap{max-height:min(50vh,22rem)}
table{width:100%;border-collapse:separate;border-spacing:0;font-size:.88rem}
thead th{
  position:sticky;
  top:0;
  z-index:2;
  background:#f8fafc;
  box-shadow:0 1px 0 var(--line);
  font-weight:600;
  white-space:nowrap;
}
th,td{padding:.55rem .65rem;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th.num,td.num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tbody tr:hover td{background:#f8fafc}
tbody tr:last-child td{border-bottom:0}
.badge{display:inline-block;padding:.15rem .5rem;border-radius:999px;font-size:.72rem;font-weight:600}
.b-requested{background:var(--acc-soft);color:var(--acc)}.b-await{background:#ffedd5;color:#c2410c}.b-done{background:#dcfce7;color:#15803d}.b-alert{background:#fee2e2;color:#b91c1c}
.flag-mismatch{color:#b91c1c;font-weight:700}
.qty-mismatch{color:#b91c1c;font-weight:600}
.alert-banner{background:#fef2f2;border:1px solid #fecaca;color:#991b1b;border-radius:8px;padding:.5rem .75rem;margin:.5rem 0;font-size:.85rem}
tr.row-mismatch td{background:#fff7f7}
.item-card.row-mismatch{border-color:#fecaca;background:#fff7f7}
.btn{border:0;border-radius:10px;padding:.55rem 1rem;font-family:inherit;font-weight:600;cursor:pointer;color:var(--text)}
.btn-primary{background:var(--acc);color:#fff}.btn-ghost{background:#fff;border:1px solid var(--line);color:var(--text)}
.btn:disabled{opacity:.45;cursor:not-allowed}
.btn-block{width:100%;text-align:left}
.row-actions{display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.75rem}
.empty{color:var(--muted);text-align:center;padding:2rem 1rem}
#busy{position:fixed;inset:0;background:rgba(255,255,255,.75);display:none;align-items:center;justify-content:center;z-index:50;font-weight:600}
body.busy #busy{display:flex}
.dir{font-size:.75rem;color:var(--muted)}
.qty-input{width:5rem;padding:.35rem .5rem;border:1px solid var(--line);border-radius:8px;font-family:inherit;color:var(--text);background:#fff;color-scheme:light}
.text-input{flex:1;min-width:0;padding:.5rem;border:1px solid var(--line);border-radius:8px;font-family:inherit;color:var(--text);background:#fff;color-scheme:light}
.search-bar{display:flex;gap:.5rem;align-items:center;margin-bottom:.75rem}
.search-bar .text-input{flex:1}
.tool-section{border:1px solid var(--line);border-radius:12px;padding:.75rem;background:#f8fafc;margin-bottom:.75rem}
.tool-section .tool-title{font-size:.82rem;font-weight:600;margin:0 0 .5rem;color:var(--text)}
.tool-row{display:flex;gap:.5rem;align-items:flex-end;flex-wrap:wrap}
.field{flex:1;min-width:7rem}
.field label{display:block;font-size:.72rem;color:var(--muted);margin-bottom:.25rem}
.field .qty-input,.field .text-input{width:100%}
.unit-select{padding:.35rem .5rem;border:1px solid var(--line);border-radius:8px;font-family:inherit;font-size:.82rem;color:var(--text);background:#fff;color-scheme:light}
.meta{font-size:.72rem;color:var(--muted);line-height:1.35}
.toast{position:fixed;bottom:1rem;left:50%;transform:translateX(-50%);background:#111827;color:#fff;padding:.55rem 1rem;border-radius:10px;font-size:.85rem;z-index:70;display:none;max-width:90vw;text-align:center}
.toast.on{display:block}
.modal-backdrop{position:fixed;inset:0;background:rgba(0,0,0,.35);display:none;align-items:center;justify-content:center;z-index:60;padding:1rem}
.modal-backdrop.on{display:flex}
.modal{background:#fff;border-radius:14px;max-width:640px;width:100%;max-height:90vh;overflow:auto;padding:1rem;box-shadow:var(--shadow)}
.modal h2{margin:0 0 .75rem;font-size:1rem}
#printSheet{
  position:absolute; left:-10000px; top:0; width:5cm;
  overflow:hidden; pointer-events:none; opacity:0;
}
@media print{
  body > *:not(#printSheet){display:none !important}
  #printSheet{
    display:block !important; position:static !important; inset:auto !important; left:auto !important;
    width:auto !important; max-width:none !important; margin:0 !important; padding:16px !important;
    background:#fff !important; color:#000 !important; font-family:Prompt,sans-serif;
    opacity:1 !important; pointer-events:auto !important; overflow:visible !important;
    -webkit-print-color-adjust:exact; print-color-adjust:exact;
  }
  #printSheet table{width:100%; border-collapse:collapse; font-size:11pt}
  #printSheet th,#printSheet td{border:1px solid #ccc; padding:6px 8px; text-align:left}
  #printSheet th.num,#printSheet td.num{text-align:right}
  #printSheet .sig{margin-top:2rem; display:grid; grid-template-columns:1fr 1fr; gap:2rem}
  #printSheet .sig-box{border-top:1px solid #999; padding-top:.5rem; font-size:10pt}
}
.action-grid{display:grid;gap:.85rem}
.action-group{display:grid;gap:.55rem}
.action-group-label{margin:0;font-size:.72rem;font-weight:700;letter-spacing:.04em;text-transform:uppercase;color:var(--muted)}
.action-card{border:1px solid var(--line);border-radius:14px;padding:1rem;background:#fff;color:var(--text);cursor:pointer;text-align:left;transition:border-color .15s,box-shadow .15s;width:100%}
.action-card:hover,.action-card:focus{border-color:var(--acc);box-shadow:var(--shadow);outline:none}
.action-card .title{font-size:1rem;font-weight:700;margin:0 0 .25rem;color:var(--text)}
.action-card .desc{font-size:.82rem;color:var(--muted);margin:0;line-height:1.45}
.action-card .count{display:inline-block;margin-top:.55rem;font-size:.75rem;font-weight:600;color:var(--acc);background:var(--acc-soft);padding:.2rem .55rem;border-radius:999px}
.no-stock{color:var(--muted);font-weight:600;font-size:.85rem}
.stock-legend{font-size:.72rem;color:var(--muted);margin:.65rem 0 0;line-height:1.45}
.flow-hint{font-size:.82rem;color:var(--muted);background:#f8fafc;border:1px dashed var(--line);border-radius:12px;padding:.75rem .85rem;margin-bottom:.85rem;line-height:1.5}
.info-toggle{margin:.75rem 0;border:1px solid #fde68a;border-radius:12px;background:#fffbeb;overflow:hidden}
.info-toggle summary{cursor:pointer;padding:.6rem .85rem;font-size:.82rem;font-weight:600;color:#92400e;list-style:none;display:flex;align-items:center;gap:.35rem;user-select:none}
.info-toggle summary::-webkit-details-marker{display:none}
.info-toggle summary::before{content:"▸";font-size:.7rem;transition:transform .15s;flex-shrink:0}
.info-toggle[open] summary::before{transform:rotate(90deg)}
.info-toggle .info-body{padding:.65rem .85rem .75rem;border-top:1px solid #fde68a;font-size:.82rem;color:var(--text);line-height:1.55}
.info-toggle .info-body strong{color:#92400e}
.stk-prn-helper{
  display:flex;align-items:center;justify-content:space-between;gap:.5rem .75rem;flex-wrap:wrap;
  margin:.55rem 0 0;padding:.4rem .65rem;
  border:1px solid var(--line);border-radius:10px;background:#f8fafc;
}
.stk-prn-helper .stk-prn-helper-text{font-size:.72rem;color:var(--muted);line-height:1.35;min-width:0}
.stk-prn-helper a{
  flex:0 0 auto;font-size:.78rem;font-weight:600;color:var(--acc);text-decoration:none;
  padding:.25rem .55rem;border:1px solid #c5d4ce;
  border-radius:999px;background:#fff;white-space:nowrap;
}
.stk-prn-helper a:hover{background:#eef7f3}
.bill-explain{font-size:.82rem;color:var(--text);background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:.75rem .85rem;margin:.75rem 0;line-height:1.55}
.bill-explain strong{color:#92400e}
.bill-steps{margin:.45rem 0 0;padding-left:1.15rem}
.bill-steps li{margin:.35rem 0}
.bill-when{font-weight:600}
.bill-none{color:var(--warn);font-weight:500}
.steps{display:flex;gap:.35rem;margin-bottom:1rem;flex-wrap:wrap}
.step{flex:1;min-width:5.5rem;text-align:center;padding:.45rem .35rem;border-radius:10px;font-size:.72rem;background:#fff;border:1px solid var(--line);color:var(--muted)}
.step.on{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:600}
.step.done{background:#dcfce7;color:var(--ok);border-color:#bbf7d0}
.step-label{display:block;font-size:.68rem;opacity:.9;margin-top:.15rem}
.row-clickable{cursor:pointer}
.row-clickable:hover td{background:#f8fafc}
.status-tabs{display:flex;gap:.35rem;margin-bottom:.75rem;flex-wrap:wrap}
.status-tab{border:1px solid var(--line);background:#fff;color:var(--text);border-radius:999px;padding:.4rem .75rem;font-size:.8rem;cursor:pointer;font-family:inherit}
.status-tab.on{background:var(--acc);color:#fff;border-color:var(--acc)}
.pipeline{display:flex;gap:.25rem;align-items:center;font-size:.68rem;color:var(--muted);margin-top:.35rem}
.pipe-dot{width:.45rem;height:.45rem;border-radius:50%;background:#d1d5db;flex-shrink:0}
.pipe-dot.on{background:var(--acc)}.pipe-dot.done{background:var(--ok)}
.view-cards{display:none}
.item-cards{display:flex;flex-direction:column;gap:.55rem}
.item-card{border:1px solid var(--line);border-radius:12px;padding:.75rem .85rem;background:#fff}
.item-card.row-clickable{cursor:pointer;transition:border-color .15s,box-shadow .15s}
.item-card.row-clickable:hover,.item-card.row-clickable:focus-within{border-color:var(--acc);box-shadow:var(--shadow)}
.item-card-head{display:flex;align-items:baseline;justify-content:space-between;gap:.5rem;flex-wrap:wrap;margin-bottom:.35rem}
.item-card-head code{font-size:.92rem}
.item-card-desc{font-size:.85rem;margin-bottom:.5rem;line-height:1.4;color:var(--text)}
.model{font-size:.78rem;color:var(--muted);margin-top:.15rem;line-height:1.35}
.item-card-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.4rem .75rem;margin-bottom:.45rem}
.item-field .lbl{display:block;font-size:.68rem;color:var(--muted);margin-bottom:.12rem}
.item-field .val{font-size:.85rem;line-height:1.35}
.item-field.num .val{text-align:right;font-variant-numeric:tabular-nums}
.item-card-actions{display:flex;gap:.5rem;flex-wrap:wrap;align-items:center;margin-top:.35rem}
.item-card-actions .btn{margin-left:auto}
.item-card-actions .qty-input,.item-card-actions .unit-select{flex:0 0 auto}
.pick-check{width:1.1rem;height:1.1rem;accent-color:var(--acc);cursor:pointer}
tr.row-picked td{background:var(--acc-pick)}
.item-card.row-picked{border-color:var(--acc-mid);background:var(--acc-pick-card)}
.commit-bar{
  position:sticky; bottom:0; z-index:15;
  display:flex; gap:.5rem; flex-wrap:wrap; align-items:center;
  margin:0 -1rem -1rem; padding:.75rem 1rem calc(.75rem + env(safe-area-inset-bottom,0px));
  background:#fff; border-top:1px solid var(--line);
  box-shadow:0 -4px 12px rgba(16,24,40,.06);
}
.commit-bar .commit-meta{flex:1; min-width:8rem; font-size:.82rem; color:var(--muted)}
.commit-bar .commit-meta strong{color:var(--text)}
@media (min-width:900px){
  main{padding:1.25rem 1.5rem}
  .table-wrap table{table-layout:auto}
}
@media (max-width:640px){
  main{padding:.75rem .65rem calc(.85rem + env(safe-area-inset-bottom,0px));padding-left:max(.65rem,env(safe-area-inset-left,0px));padding-right:max(.65rem,env(safe-area-inset-right,0px));min-width:0}
  .hdr{padding:.65rem max(.65rem,env(safe-area-inset-left,0px)) .65rem max(.65rem,env(safe-area-inset-right,0px))}
  .hdr h1{font-size:.98rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .hdr .sub{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .site-badge{font-size:.65rem;padding:.22rem .45rem;max-width:42vw;overflow:hidden;text-overflow:ellipsis}
  .card{padding:.85rem .8rem;border-radius:12px;margin-bottom:.65rem;min-width:0}
  .card:not(:has(.view-table)):not(:has(.view-cards)){overflow:hidden}
  .card:has(.view-table){overflow:visible}
  .view-table{display:none !important}
  .view-cards{display:block}
  .item-card{padding:.7rem .75rem;border-radius:10px}
  .item-card-grid{grid-template-columns:1fr 1fr}
  .item-card-actions .btn{width:100%;margin-left:0;text-align:center}
  .item-card-actions:has(.qty-input){justify-content:space-between}
  .item-card-actions .qty-input{flex:1;min-width:0;max-width:5.5rem}
  .item-card-actions .unit-select{flex:1;min-width:0;max-width:6.5rem}
  .table-wrap{-webkit-overflow-scrolling:touch;max-width:100%;max-height:min(52vh,22rem)}
  .table-wrap--tall{max-height:min(65vh,30rem)}
  .modal .table-wrap{max-height:min(42vh,18rem)}
  table{font-size:.8rem}
  th,td{padding:.45rem .5rem;vertical-align:top}
  th{white-space:nowrap}
  td code{word-break:break-all}
  .steps{display:flex;flex-wrap:nowrap;gap:.3rem;overflow-x:auto;-webkit-overflow-scrolling:touch;scrollbar-width:none;margin-bottom:.85rem;padding-bottom:.1rem}
  .steps::-webkit-scrollbar{display:none}
  .step{flex:0 0 auto;min-width:6.25rem;padding:.4rem .35rem;font-size:.68rem}
  .step-label{font-size:.6rem}
  .flow-hint,.info-toggle{font-size:.78rem;padding:.65rem .75rem;margin-bottom:.65rem}
  .info-toggle summary{padding:.55rem .75rem;font-size:.78rem}
  .info-toggle .info-body{padding:.55rem .75rem .65rem}
  .action-card{padding:.9rem .85rem}
  .action-card .title{font-size:.95rem}
  .row-actions{gap:.4rem}
  .row-actions .btn{flex:1 1 auto;min-width:0;text-align:center;padding:.55rem .7rem;font-size:.85rem}
  td.row-actions{display:flex;flex-direction:column;gap:.35rem;align-items:stretch;white-space:normal;min-width:4.75rem}
  td.row-actions .btn{width:100%;padding:.42rem .5rem;font-size:.76rem}
  td .btn{padding:.42rem .55rem;font-size:.76rem}
  .pipeline{flex-wrap:wrap;row-gap:.15rem;max-width:9.5rem}
  .tool-row{flex-direction:column;align-items:stretch}
  .tool-row .field{min-width:0;max-width:none!important;width:100%}
  .tool-row .btn{width:100%;margin:0}
  .search-bar{margin-bottom:.65rem}
  .status-tabs{display:flex;gap:.35rem}
  .status-tab{flex:1;text-align:center;padding:.45rem .5rem;font-size:.76rem}
  .qty-input{width:4.25rem;max-width:100%}
  .unit-select{max-width:5.5rem}
  .modal-backdrop{padding:0;align-items:flex-end}
  .modal{border-radius:16px 16px 0 0;max-height:88vh;padding:.9rem .85rem calc(.9rem + env(safe-area-inset-bottom,0px))}
  .toast{bottom:calc(1rem + env(safe-area-inset-bottom,0px));font-size:.8rem}
  .empty{padding:1.5rem .75rem}
  .bill-steps{padding-left:1rem}
  .sticker-preview{width:min(100%,10rem);height:auto}
}
.success-card{text-align:center;padding:1.25rem 1rem}
.success-card .ok-mark{width:3rem;height:3rem;border-radius:50%;background:#dcfce7;color:var(--ok);display:inline-flex;align-items:center;justify-content:center;font-size:1.6rem;font-weight:700;margin-bottom:.65rem}
.success-card h2{margin:.15rem 0 .35rem;font-size:1.15rem}
.seg{display:flex;gap:.35rem;flex-wrap:wrap}
.seg button{border:1px solid var(--line);background:#fff;border-radius:999px;padding:.4rem .75rem;font:inherit;cursor:pointer}
.seg button.on{background:var(--acc);color:#fff;border-color:var(--acc);font-weight:600}
.sticker-preview-wrap{display:flex;justify-content:center;padding:.75rem;background:#f8fafc;border:1px dashed var(--line);border-radius:12px;margin:.65rem 0}
.sticker-preview{width:5cm;height:3.5cm;object-fit:contain;background:#fff;border:1px solid #d1d5db;box-shadow:var(--shadow);image-rendering:pixelated}
.sticker-line{display:flex;align-items:center;gap:.55rem;padding:.45rem 0;border-bottom:1px solid var(--line)}
.sticker-line:last-child{border-bottom:0}
.sticker-line .grow{flex:1;min-width:0}
.qty-step{display:inline-flex;align-items:center;gap:.2rem}
.qty-step button{width:1.85rem;height:1.85rem;border:1px solid var(--line);background:#fff;border-radius:8px;font:inherit;cursor:pointer;padding:0}
.qty-step .qty-input{width:3.6rem;text-align:center}
</style>
</head>
<body>
<div id="busy">กำลังดำเนินการ…</div>
<div id="toast" class="toast"></div>
<div id="modalBackdrop" class="modal-backdrop"><div class="modal" id="modalBox"></div></div>
<div id="printSheet" aria-hidden="true"></div>
<header class="hdr">
  <button id="btnBack" class="back-btn" style="display:none">← กลับ</button>
  <div class="hdr-main">
    <h1 id="hdrTitle">โอนสินค้า · __SITE_LABEL__</h1>
    <div class="sub" id="hdrSub">__USER__</div>
  </div>
  <span class="site-badge" title="สาขาที่เปิดอยู่ตอนนี้"><span class="code">__SITE__</span> · __SITE_LABEL__</span>
</header>
<main><div id="content" class="empty">กำลังโหลด…</div></main>
<script>
const SITE = "__SITE__";
const OTHER = "__OTHER__";
const SITE_LABEL = "__SITE_LABEL__";
const OTHER_LABEL = "__OTHER_LABEL__";
const BRANCH_LABEL = {HQ:"สำนักงานใหญ่",SYP:"สาขา"};
const SHIP_BILL = "ใบจัดสินค้า";
const RECV_BILL = "ใบรับสินค้า";
const SHIP_WRITE = __SHIP_WRITE__ === "true";
const RECV_WRITE = __RECV_WRITE__ === "true";
const USER = __USER_JSON__;
const STICKER_DEFAULT_MODEL = __STICKER_MODEL_JSON__;
const STICKER_DEFAULT_HOST = __STICKER_HOST_JSON__;
const STICKER_PRINTERS = [
  {id:"te310", label:"TSC TE310 · 300 dpi · 2 คอลัมน์"},
  {id:"ttp244pro", label:"TSC 244 Pro · 203 dpi · 2 คอลัมน์"},
];

let view = "home";
let requestStep = 1;
let orderDirection = SITE === "SYP" ? "to_syp" : "to_hq";
let statusFilter = "active";
let editingDraftId = null;
let receiveStep = 1;
let receiveShipment = null;
let prepareStep = 1;
let prepareRequest = null;
let suggestItems = [];
let suggestFilter = "";
/** Local picks on suggest list: bcode → {checked, unit, qty} — survives soft re-renders. */
let suggestPick = {};
let receiveFilter = "";
/** After a successful receive / history reprint: {bill, shortId, lines:[{bcode,descr,qty,selected}]} */
let receivePrintJob = null;
let stickerReturnView = "home";
let toastTimer = null;

const VIEWS = {
  home: {title: "โอนสินค้า · " + SITE_LABEL, sub: "เลือกสิ่งที่ต้องการทำ"},
  request: {title: "ขอสินค้าจาก " + OTHER_LABEL, sub: "ขั้นตอนที่ " + requestStep + " จาก 3"},
  prepare: {title: "ส่งสินค้า", sub: "รายการที่รอจัดออกจาก " + SITE_LABEL},
  receive: {title: "รับสินค้า", sub: "รายการที่รอรับเข้า " + SITE_LABEL},
  status: {title: "ตรวจสอบสถานะ", sub: "ติดตามคำขอโอนทั้งหมด"},
};

function $(id){return document.getElementById(id)}
function fmtQty(n){
  const x = Number(n);
  if(n === null || n === undefined || n === "" || Number.isNaN(x)) return "—";
  if(Math.abs(x - Math.round(x)) < 1e-9) return String(Math.round(x));
  return x.toLocaleString("th-TH",{maximumFractionDigits:2});
}
function fmtQtyUi(qty, ui){
  const q = fmtQty(qty);
  const u = (ui || "").trim();
  if(q === "—") return q;
  return u ? (q + " " + u) : q;
}
function unitChoices(row){
  const mtp2 = Number(row.mtp2) || 1;
  const ui1 = (row.ui1 || "ชิ้น").trim() || "ชิ้น";
  const ui2 = (row.ui2 || "").trim();
  const out = [{id:"small", label:ui1, factor:1}];
  if(mtp2 > 1 && ui2) out.push({id:"large", label:ui2, factor:mtp2});
  return out;
}
function fmtStockDual(smallQty, row){
  const mtp2 = Number(row.mtp2) || 1;
  const ui1 = (row.ui1 || "").trim();
  const ui2 = (row.ui2 || "").trim();
  const main = fmtQtyUi(smallQty, ui1);
  if(mtp2 > 1 && ui2) return main + `<div class="meta">${fmtQty(smallQty / mtp2)} ${ui2}</div>`;
  return main;
}
/** HQ QTYMIN < 0 (L-1) = สนญ.ไม่เก็บสต็อก */
function isHqNoStock(row){
  if(!row) return false;
  if(row.hq_no_stock === true || row.hq_no_stock === 1 || row.hq_no_stock === "1") return true;
  const q = Number(row.hq_qtymin);
  return !Number.isNaN(q) && q < 0;
}
function fmtHqStock(row){
  const qtyHtml = fmtStockDual(row && row.hq_qtyoh2, row || {});
  if(isHqNoStock(row)){
    return `<span class="no-stock" title="L-1 · สนญ.ไม่เก็บสต็อก">ไม่สต็อก</span><br>${qtyHtml}`;
  }
  return qtyHtml;
}
function fmtBranchStock(row, branch){
  const qtyHtml = fmtStockDual(branchQtyoh2(row, branch), row || {});
  if((branch||"").toUpperCase() === "HQ" && isHqNoStock(row)){
    return `<span class="no-stock" title="L-1 · สนญ.ไม่เก็บสต็อก">ไม่สต็อก</span><br>${qtyHtml}`;
  }
  return qtyHtml;
}
function hqNoStockNoteHtml(){
  return `<p class="stock-legend">ไม่สต็อก = L -1 (สนญ.ไม่เก็บสต็อก) — ยังแสดงยอดคงเหลือจริง</p>`;
}
function fmtHqStockPlain(row){
  const qty = fmtQty(row && row.hq_qtyoh2);
  if(isHqNoStock(row)) return "ไม่สต็อก · " + qty;
  return qty;
}
function fmtModel(row){
  const m = (row && row.model || "").trim();
  return m ? `<div class="model">รุ่น ${m}</div>` : "";
}
function fmtLocation(row){
  const hq = (row && row.location_hq || "").trim();
  const syp = (row && row.location_syp || "").trim();
  if(hq || syp){
    const bits = [];
    if(hq) bits.push("สนญ "+hq);
    if(syp) bits.push("สาขา "+syp);
    return `<div class="meta">ที่เก็บ ${bits.join(" · ")}</div>`;
  }
  const cur = (row && row.location || "").trim();
  return cur ? `<div class="meta">ที่เก็บ ${cur}</div>` : "";
}
function fmtDescr(row){
  return `${(row && row.descr) || ""}${fmtModel(row)}${fmtLocation(row)}`;
}
function qtyToSmall(qty, unitId, row){
  const choices = unitChoices(row);
  const picked = choices.find(c=>c.id===unitId) || choices[0];
  return Number(qty||0) * picked.factor;
}
function defaultEntryQty(row){
  const choices = unitChoices(row);
  const small = Number(row.suggest_qty||0);
  if(choices.length > 1 && small >= (Number(row.mtp2)||1)) return {unit:"large", qty: small / (Number(row.mtp2)||1)};
  return {unit:"small", qty: small || 1};
}
function showToast(msg){
  const el = $("toast");
  el.textContent = msg;
  el.classList.add("on");
  if(toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(()=>el.classList.remove("on"), 2600);
}
function uuid(){return crypto.randomUUID ? crypto.randomUUID() : String(Date.now())+"-"+Math.random().toString(16).slice(2)}
function branchLabel(b){
  const u = (b||"").toUpperCase();
  return BRANCH_LABEL[u] || b || "?";
}
function dirLabel(fromB, toB){return branchLabel(fromB)+" → "+branchLabel(toB);}
function shipBillPrefix(fromBranch){
  return (fromBranch||"").toUpperCase()==="SYP" ? "3TF" : "TF";
}
function branchQtyoh2(row, branch){
  const b = (branch||"").toUpperCase();
  if(b === "HQ") return row.hq_qtyoh2;
  if(b === "SYP") return row.syp_qtyoh2;
  return row.from_qtyoh2 ?? row.to_qtyoh2;
}
function receiveBillPrefix(fromBranch, toBranch){
  if((fromBranch||"").toUpperCase()==="SYP" && (toBranch||"").toUpperCase()==="HQ") return "3TF";
  return "TF";
}
function parts9Host(branch){
  const u = (branch||"").toUpperCase();
  return u === "SYP" ? "kss-pc (สาขา)" : "KSS (สำนักงานใหญ่)";
}
function iclowStampApplies(fromB, toB){
  const fb = (fromB||"").toUpperCase();
  const tb = (toB||"").toUpperCase();
  return fb === "HQ" && tb === "SYP";
}
function infoToggleHtml(title, bodyHtml){
  return `<details class="info-toggle"><summary>${title}</summary><div class="info-body">${bodyHtml}</div></details>`;
}
function billTimelineHtml(fromB, toB){
  const fb = (fromB||"HQ").toUpperCase();
  const tb = (toB||"SYP").toUpperCase();
  const shipP = shipBillPrefix(fb);
  const recvP = receiveBillPrefix(fb, tb);
  const submitStep = iclowStampApplies(fb, tb)
    ? `<li><span class="bill-when">ส่งคำขอ</span> — บันทึกคำขอ <code>TRF-…</code> + แสตมป์ ICLOW รอสั่งที่สาขา (<strong>ยังไม่ออกใบ TF</strong> ใน PARTS9)</li>`
    : `<li><span class="bill-when">ส่งคำขอ</span> — บันทึกคำขอ <code>TRF-…</code> เท่านั้น (<strong>ไม่แตะ ICLOW</strong> รอสั่ง — เก็บไว้สั่งซื้อจากเจ้าหนี้)</li>`;
  return infoToggleHtml("ใบ TF ถูกสร้างเมื่อไหร่?", `<ol class="bill-steps">
      ${submitStep}
      <li><span class="bill-when">${branchLabel(fb)} จัดส่ง</span> — สร้าง<strong>${shipP} ${SHIP_BILL}</strong> บน ${parts9Host(fb)} (ตัดสต๊อกออก)</li>
      <li><span class="bill-when">${branchLabel(tb)} รับเข้า</span> — สร้าง<strong>${recvP} ${RECV_BILL}</strong> บน ${parts9Host(tb)} (เพิ่มสต๊อกเข้า)</li>
    </ol>`);
}
function submitBillNoteHtml(fromB, toB){
  const fb = (fromB||OTHER).toUpperCase();
  const tb = (toB||SITE).toUpperCase();
  const shipP = shipBillPrefix(fb);
  const recvP = receiveBillPrefix(fb, tb);
  const iclowLi = iclowStampApplies(fb, tb)
    ? `<li>แสตมป์ ICLOW รอสั่งที่สาขา ว่าสั่งแล้ว (กันสั่งซ้ำในรายการรอสั่ง)</li>`
    : `<li><strong>ไม่แตะ ICLOW</strong> รอสั่ง — เก็บรายการไว้สำหรับสั่งซื้อจากเจ้าหนี้</li>`;
  return infoToggleHtml("ตอนกดยืนยันส่งคำขอ จะเกิดอะไรขึ้น?", `<ul class="bill-steps">
      <li>สร้างคำขอโอน <code>TRF-…</code> (อ้างอิงในระบบ — <strong>ไม่ใช่เลขบิล PARTS9</strong>)</li>
      ${iclowLi}
      <li class="bill-none">ยังไม่ออกใบ TF — ${SHIP_BILL} ${shipP} สร้างตอน ${branchLabel(fb)} จัดส่ง · ${RECV_BILL} ${recvP} สร้างตอน ${branchLabel(tb)} รับเข้า</li>
    </ul>`);
}
function prepareBillNoteHtml(fromB, toB){
  const fb = (fromB||SITE).toUpperCase();
  const tb = (toB||OTHER).toUpperCase();
  const shipP = shipBillPrefix(fb);
  const recvP = receiveBillPrefix(fb, tb);
  return infoToggleHtml("เมื่อยืนยันจัดส่ง ระบบจะ:", `<ul class="bill-steps">
      <li>สร้าง<strong>${shipP} ${SHIP_BILL}</strong> บน ${parts9Host(fb)} ทันที (ตัดสต๊อก ${branchLabel(fb)})</li>
      <li>ยังไม่มีใบรับ — ${branchLabel(tb)} จะออก<strong>${recvP} ${RECV_BILL}</strong> ตอนกดรับเข้า</li>
    </ul>`);
}
function receiveBillNoteHtml(fromB, toB, shipBillno){
  const fb = (fromB||OTHER).toUpperCase();
  const tb = (toB||SITE).toUpperCase();
  const recvP = receiveBillPrefix(fb, tb);
  const shipP = shipBillPrefix(fb);
  const shipRef = shipBillno ? `<code>${shipBillno}</code>` : `${SHIP_BILL} ${shipP} ที่ ${branchLabel(fb)} จัดไป`;
  const iclowLi = iclowStampApplies(fb, tb)
    ? `<li>อัปเดต ICLOW รอสั่งที่สาขา ว่ารับแล้ว</li>`
    : "";
  return infoToggleHtml("เมื่อยืนยันรับเข้า ระบบจะ:", `<ul class="bill-steps">
      <li>สร้าง<strong>${recvP} ${RECV_BILL}</strong> บน ${parts9Host(tb)} (เพิ่มสต๊อก ${branchLabel(tb)})</li>
      <li>อ้างอิงใบจัด ${shipRef}</li>
      ${iclowLi}
    </ul>`);
}
function orderFlowText(){
  return OTHER_LABEL + " จัดส่ง → " + SITE_LABEL + " รับเข้า";
}
function badge(status, fromB, toB, hasMismatch){
  const m={draft:"b-requested",requested:"b-requested",partial_prepared:"b-await",awaiting_receive:"b-await",partial_received:"b-await",complete:"b-done",cancelled:"b-requested"};
  const fb = branchLabel(fromB||"HQ");
  const t={draft:"ร่าง",requested:"รอ "+fb+" จัด",partial_prepared:"จัดไม่ครบตามขอ",awaiting_receive:"รอรับ",partial_received:"รับไม่ครบตามขอ",complete:"เสร็จสิ้น",cancelled:"ยกเลิก"};
  const cls = hasMismatch ? "b-alert" : (m[status]||"b-requested");
  const label = hasMismatch ? "จัด≠รับ" : (t[status]||status||"-");
  return `<span class="badge ${cls}" title="${hasMismatch ? "จำนวนจัดกับรับไม่ตรงกัน" : ""}">${label}</span>`;
}
function pipeline(status, hasMismatch){
  const idx = status==="complete" ? 3 : status==="awaiting_receive"||status==="partial_received" ? 2 : status==="partial_prepared" ? 1 : 0;
  const labels = ["ขอแล้ว","จัดแล้ว","รับแล้ว","เสร็จ"];
  const warn = hasMismatch ? `<span class="flag-mismatch" title="จัด≠รับ"> ⚠</span>` : "";
  return `<div class="pipeline">${labels.map((l,i)=>`<span class="pipe-dot ${i<idx?"done":i===idx?"on":""}"></span><span>${l}</span>`).join("")}${warn}</div>`;
}
function lineStatusLabel(ln){
  const status = ln.line_status || ln.status || "";
  const t={open:"รอจัด",partial_prepared:"จัดไม่ครบตามขอ",prepared:"จัดครบ รอรับ",partial_received:"รับไม่ครบตามขอ",complete:"เสร็จ",cancelled:"ยกเลิก"};
  const base = t[status]||status||"-";
  if(ln.prep_recv_mismatch) return `<span class="flag-mismatch" title="จัด ${fmtQty(ln.qty_prepared)} ≠ รับ ${fmtQty(ln.qty_received)}">⚠ ${base}</span>`;
  return base;
}
function mismatchBanner(progress){
  if(!progress || !progress.prep_recv_mismatch) return "";
  const n = progress.prep_recv_mismatch_count || 0;
  return `<div class="alert-banner"><strong>⚠ จัดกับรับไม่ตรงกัน</strong> — ${n} รายการ (จัดแล้วแต่ยังรับไม่ครบ หรือรับไม่เท่าที่จัด)</div>`;
}
function qtyCell(qty, mismatch){
  const q = fmtQty(qty);
  return mismatch ? `<span class="qty-mismatch">${q}</span>` : q;
}
function fmtDateTime(iso){
  return iso ? String(iso).slice(0,16).replace("T"," ") : "—";
}
function dualView(tableHtml, cardsHtml){
  return `<div class="view-table">${tableHtml}</div><div class="view-cards">${cardsHtml}</div>`;
}
function itemCards(html){ return `<div class="item-cards">${html}</div>`; }
/** dualView keeps both panes in the DOM; only one is visible — read/sync that one. */
function visibleDualPane(root){
  const panes = [...root.querySelectorAll(".view-table, .view-cards")];
  const shown = panes.find(p => getComputedStyle(p).display !== "none");
  return shown || root;
}
function qtyKeyAttr(inp){
  return inp.dataset.shipmentLine || inp.dataset.line || "";
}
function bindSyncedQtyInputs(root, selector){
  root.querySelectorAll(selector).forEach(inp=>{
    inp.oninput = ()=>{
      const key = qtyKeyAttr(inp);
      if(!key) return;
      root.querySelectorAll(selector).forEach(other=>{
        if(other !== inp && qtyKeyAttr(other) === key) other.value = inp.value;
      });
    };
  });
}
/** Collect qty>0 from the visible dualView pane only (hidden twin inputs stay at defaults). */
function collectPositiveQtyMap(root, selector, dataProp){
  const qtyMap = {};
  let any = false;
  visibleDualPane(root).querySelectorAll(selector).forEach(inp=>{
    const key = inp.dataset[dataProp];
    if(!key) return;
    const q = Number(inp.value);
    if(!Number.isFinite(q) || q <= 0) return;
    qtyMap[key] = q;
    any = true;
  });
  return {qtyMap, any};
}
function bindDetailRows(container){
  container.querySelectorAll(".row-clickable[data-detail]").forEach(row=>{
    row.onclick = e=>{
      if(e.target.closest("button")) return;
      openRequestDetail(row.dataset.detail);
    };
  });
}
let busyDepth = 0;
function setBusy(on){
  if(on){
    busyDepth++;
    document.body.classList.add("busy");
  }else{
    busyDepth = Math.max(0, busyDepth-1);
    if(!busyDepth) document.body.classList.remove("busy");
  }
}
function showModal(html){
  const box = $("modalBox");
  box.innerHTML = html;
  $("modalBackdrop").classList.add("on");
  const close = ()=>{$("modalBackdrop").classList.remove("on"); box.innerHTML="";};
  $("modalBackdrop").onclick = e=>{if(e.target===$("modalBackdrop")) close();};
  box.querySelectorAll("[data-close]").forEach(b=>b.onclick=close);
  return {close, box};
}
async function api(path, opts){
  const o = Object.assign({}, opts||{});
  const quiet = !!o.quiet;
  delete o.quiet;
  if(!quiet) setBusy(true);
  try{
    const headers = Object.assign({"Content-Type":"application/json"}, o.headers||{});
    const r = await fetch(path, Object.assign({credentials:"same-origin"}, o, {headers}));
    const j = await r.json().catch(()=>({}));
    if(!r.ok) throw new Error(j.error||j.detail||("HTTP "+r.status));
    return j;
  } finally { if(!quiet) setBusy(false); }
}
async function submitTransferLines(lines, direction){
  let transferId = editingDraftId;
  if(!transferId){
    const d = await api("/transfer/api/requests/draft",{method:"POST",body:JSON.stringify({direction})});
    transferId = d.transfer_id;
  }
  await api("/transfer/api/requests/"+transferId+"/lines",{
    method:"PUT",
    body:JSON.stringify({lines:lines.map(l=>({bcode:l.bcode,qty:l.qty,descr:l.descr||""}))}),
  });
  const submitted = await api("/transfer/api/requests/"+transferId+"/submit",{method:"POST",body:"{}"});
  editingDraftId = null;
  return submitted;
}
async function saveDraftLines(lines){
  let transferId = editingDraftId;
  if(!transferId){
    const d = await api("/transfer/api/requests/draft",{method:"POST",body:JSON.stringify({direction:orderDirection})});
    transferId = d.transfer_id;
    editingDraftId = transferId;
  }
  await api("/transfer/api/requests/"+transferId+"/lines",{
    method:"PUT",
    body:JSON.stringify({lines:lines.map(l=>({bcode:l.bcode,qty:l.qty,descr:l.descr||""}))}),
  });
  return transferId;
}
async function deleteDraft(transferId){
  if(!confirm("ลบร่างนี้?")) return;
  await api("/transfer/api/requests/"+transferId,{method:"DELETE"});
  if(editingDraftId === transferId) editingDraftId = null;
  showToast("ลบร่างแล้ว");
  render();
}
async function cancelRequest(transferId){
  if(!confirm("ยกเลิกคำขอนี้? รายการจะกลับมาขอใหม่ได้ และจะคืนสถานะ ICLOW (ถ้ามี)")) return;
  try{
    await api("/transfer/api/requests/"+transferId+"/cancel",{method:"POST",body:"{}"});
    showToast("ยกเลิกคำขอแล้ว");
    render();
  }catch(e){
    alert(e.message || "ยกเลิกไม่สำเร็จ");
  }
}
function canCancelRequest(status, toBranch, hasShipments){
  // Requester only; match API — allowed until any ship bill exists.
  if((toBranch||"").toUpperCase() !== SITE) return false;
  if(hasShipments) return false;
  const st = status || "";
  if(["draft","complete","cancelled"].includes(st)) return false;
  return true;
}
function apCounterpartyLabel(writingBranch, counterpartyBranch){
  const w = (writingBranch||"").toUpperCase();
  const c = (counterpartyBranch||"").toUpperCase();
  if(w === "HQ" && c === "SYP") return "ACCTNO KCW1 · สาขา (AP)";
  if(w === "SYP" && c === "HQ") return "ACCTNO KCW · สำนักงานใหญ่ (AP)";
  return "";
}
function stickerPrinterModel(){
  try{ return localStorage.getItem("kcw_sticker_model") || STICKER_DEFAULT_MODEL || "te310"; }
  catch(_e){ return STICKER_DEFAULT_MODEL || "te310"; }
}
function stickerPrinterHost(){
  try{ return localStorage.getItem("kcw_sticker_host") || STICKER_DEFAULT_HOST || ""; }
  catch(_e){ return STICKER_DEFAULT_HOST || ""; }
}
function setStickerPrinterModel(id){
  try{ localStorage.setItem("kcw_sticker_model", id); }catch(_e){}
}
function setStickerPrinterHost(host){
  try{ localStorage.setItem("kcw_sticker_host", host || ""); }catch(_e){}
}
function stickerLinesFromDetail(detail, {selected}={}){
  const lines = detail.items || detail.lines || [];
  const recvBill = (detail.shipments||[]).map(s=>s.receive_billno).filter(Boolean)[0] || "";
  return {
    bill: recvBill,
    shortId: detail.short_id || detail.transfer_id || "",
    lines: lines.filter(ln=>Number(ln.qty_received||0)>0).map(ln=>({
      bcode: ln.bcode,
      descr: ln.descr || "",
      qty: Number(ln.qty_received||0),
      selected: selected === true ? true : selected === false ? false : !!ln.selected,
    })),
  };
}
function openStickerPrint(job){
  stickerReturnView = job.returnView || view || "home";
  const pick = job.selectAll === false;
  receivePrintJob = {
    bill: job.bill || "",
    shortId: job.shortId || "",
    lines: (job.lines || []).map(ln=>({
      bcode: ln.bcode,
      descr: ln.descr || "",
      qty: Math.max(1, Math.round(Number(ln.qty || ln.qty_receive || ln.qty_received || 0))),
      selected: pick ? ln.selected === true : ln.selected !== false,
    })).filter(ln=>ln.bcode && ln.qty>0),
  };
  view = "stickers";
  render();
}
function leaveStickerPrint(){
  receivePrintJob = null;
  const back = stickerReturnView || "home";
  stickerReturnView = "home";
  if(back === "receive"){
    view = "receive";
    receiveStep = 1;
    receiveShipment = null;
  }else{
    view = back;
  }
  render();
}
async function openStickerPrintFromTransfer(transferId, {selectAll}={}){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  const job = stickerLinesFromDetail(detail, {selected: selectAll === true});
  if(!job.lines.length) throw new Error("ยังไม่มีสินค้าที่รับเข้าสำหรับพิมพ์บาร์โค้ด");
  openStickerPrint({...job, selectAll: selectAll === true, returnView: "status"});
}
function stickerCopies(job){
  return (job.lines||[]).filter(l=>l.selected).reduce((n,l)=>n+Number(l.qty||0),0);
}
async function fetchStickerPreview(job, model){
  const lines = (job.lines||[]).filter(l=>l.selected && Number(l.qty)>0).map(l=>({bcode:l.bcode, qty:Number(l.qty), descr:l.descr||""}));
  if(!lines.length) return null;
  return api("/transfer/api/stickers/preview",{
    method:"POST",
    quiet:true,
    body:JSON.stringify({lines, printer_model:model}),
  });
}
async function downloadStickerPrn(job, model){
  const lines = (job.lines||[]).filter(l=>l.selected && Number(l.qty)>0).map(l=>({bcode:l.bcode, qty:Number(l.qty), descr:l.descr||""}));
  if(!lines.length) throw new Error("เลือกอย่างน้อย 1 รายการ");
  setBusy(true);
  try{
    const r = await fetch("/transfer/api/stickers/print",{
      method:"POST",
      credentials:"same-origin",
      headers:{"Content-Type":"application/json"},
      body:JSON.stringify({lines, printer_model:model, action:"download"}),
    });
    if(!r.ok){
      const j = await r.json().catch(()=>({}));
      throw new Error(j.error||("HTTP "+r.status));
    }
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "kcw-stickers-"+(job.bill||job.shortId||"batch")+".prn";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } finally { setBusy(false); }
}
async function sendStickerPrint(job, model, host){
  const lines = (job.lines||[]).filter(l=>l.selected && Number(l.qty)>0).map(l=>({bcode:l.bcode, qty:Number(l.qty), descr:l.descr||""}));
  if(!lines.length) throw new Error("เลือกอย่างน้อย 1 รายการ");
  return api("/transfer/api/stickers/print",{
    method:"POST",
    body:JSON.stringify({lines, printer_model:model, printer_host:host, action:"print"}),
  });
}
function renderStickerComposer(el, job){
  const model = stickerPrinterModel();
  const host = stickerPrinterHost();
  const copies = stickerCopies(job);
  const rows = (job.lines||[]).map((ln,i)=>`
    <tr class="sticker-row">
      <td><input type="checkbox" class="pick-check stk-sel" data-i="${i}" ${ln.selected?"checked":""}/></td>
      <td><code>${ln.bcode}</code></td>
      <td>${(ln.descr||"").replace(/</g,"&lt;")}</td>
      <td class="num"><span class="qty-step">
        <button type="button" data-stk-delta="${i}" data-d="-1">−</button>
        <input class="qty-input stk-qty" type="number" min="1" max="200" step="1" value="${ln.qty}" data-i="${i}"/>
        <button type="button" data-stk-delta="${i}" data-d="1">+</button>
      </span></td>
    </tr>`).join("");
  const cards = (job.lines||[]).map((ln,i)=>`<div class="item-card">
    <div class="item-card-head">
      <label style="display:flex;align-items:center;gap:.4rem"><input type="checkbox" class="pick-check stk-sel" data-i="${i}" ${ln.selected?"checked":""}/><code>${ln.bcode}</code></label>
    </div>
    <div class="item-card-desc">${(ln.descr||"").replace(/</g,"&lt;")}</div>
    <div class="item-card-actions">
      <span class="meta" style="margin-right:auto">จำนวนดวง</span>
      <span class="qty-step">
        <button type="button" data-stk-delta="${i}" data-d="-1">−</button>
        <input class="qty-input stk-qty" type="number" min="1" max="200" step="1" value="${ln.qty}" data-i="${i}"/>
        <button type="button" data-stk-delta="${i}" data-d="1">+</button>
      </span>
    </div>
  </div>`).join("");
  el.innerHTML = `<div class="card">
      <p><strong>พิมพ์สติ๊กเกอร์บาร์โค้ด</strong>${job.bill?` · ใบรับ <code>${job.bill}</code>`:""}${job.shortId?` · <code>${job.shortId}</code>`:""}</p>
      <p class="meta">ติ๊กสินค้า · 1 ชิ้น = 1 ดวง · 5×3.5 ซม. · ดาวน์โหลด .prn แล้วดับเบิลคลิกเพื่อพิมพ์</p>
      <div class="sticker-preview-wrap"><img id="stkPreview" class="sticker-preview" alt="ตัวอย่างสติ๊กเกอร์" hidden/>
        <p id="stkPreviewMeta" class="meta">กำลังโหลดตัวอย่าง…</p>
      </div>
      <div class="row-actions" style="margin:.35rem 0 .15rem">
        <button class="btn btn-ghost" id="btnStkAll" type="button">เลือกทั้งหมด</button>
        <button class="btn btn-ghost" id="btnStkNone" type="button">ล้าง</button>
      </div>
      ${dualView(
        `<div class="table-wrap table-wrap--tall"><table><thead><tr><th></th><th>รหัส</th><th>รายละเอียด</th><th class="num">ดวง</th></tr></thead><tbody>${rows}</tbody></table></div>`,
        itemCards(cards)
      )}
      <div class="field" style="margin:.75rem 0 .35rem">
        <label>รุ่นเครื่องพิมพ์ (ความละเอียดไฟล์ .prn)</label>
        <div class="seg" id="stkModelSeg">
          ${STICKER_PRINTERS.map(p=>`<button type="button" data-model="${p.id}" class="${p.id===model?"on":""}">${p.label}</button>`).join("")}
        </div>
      </div>
      <details class="info-toggle" id="stkAdvanced">
        <summary>พิมพ์ผ่าน LAN (ทางเลือก)</summary>
        <div class="info-body">
          <p class="meta" style="margin:0 0 .5rem">ส่ง TSPL ตรงเข้าเครื่องบนพอร์ต 9100 — ต้องอยู่ในวง LAN / Tailscale เดียวกับเซิร์ฟเวอร์</p>
          <div class="field" style="margin:.35rem 0">
            <label>IP เครื่องพิมพ์</label>
            <input id="stkHost" class="text-input" type="text" placeholder="เช่น 192.168.1.50" value="${escapeAttr(host)}"/>
          </div>
          <div class="row-actions" style="margin:.5rem 0 0">
            <button class="btn btn-ghost" id="btnStkLan" type="button" ${copies && host?"":"disabled"}>พิมพ์ผ่าน LAN</button>
          </div>
        </div>
      </details>
      <div class="stk-prn-helper" id="stkPrnHelper">
        <span class="stk-prn-helper-text">ครั้งแรกบนเครื่องนี้? ติดตั้งตัวช่วย แล้วดับเบิลคลิกไฟล์ .prn <span id="stkPrnHelperVer"></span></span>
        <a id="btnStkPrnHelperDownload" href="/tools/prn-printer/install.cmd">ดาวน์โหลดตัวติดตั้ง</a>
      </div>
      <div class="commit-bar">
        <div class="commit-meta">จะพิมพ์ <strong id="stkCopyCount">${copies}</strong> ดวง · เลือกแล้ว <strong id="stkSelectedCount">${(job.lines||[]).filter(l=>l.selected).length}</strong> รายการ</div>
        <button class="btn btn-ghost" id="btnStkSkip">ข้าม</button>
        <button class="btn btn-primary" id="btnStkDownload" type="button" ${copies?"":"disabled"}>ดาวน์โหลดไฟล์ .prn</button>
      </div>
    </div>`;
  const syncQty = ()=>{
    const pane = visibleDualPane(el);
    pane.querySelectorAll(".stk-qty").forEach(inp=>{
      const i = Number(inp.dataset.i);
      if(!Number.isFinite(i) || !job.lines[i]) return;
      const q = Math.max(1, Math.min(200, Math.round(Number(inp.value||1))));
      job.lines[i].qty = q;
      el.querySelectorAll(`.stk-qty[data-i="${i}"]`).forEach(other=>{ other.value = q; });
    });
    pane.querySelectorAll(".stk-sel").forEach(inp=>{
      const i = Number(inp.dataset.i);
      if(!Number.isFinite(i) || !job.lines[i]) return;
      job.lines[i].selected = !!inp.checked;
      el.querySelectorAll(`.stk-sel[data-i="${i}"]`).forEach(other=>{ other.checked = inp.checked; });
    });
    const n = stickerCopies(job);
    const selectedN = (job.lines||[]).filter(l=>l.selected).length;
    const meta = el.querySelector("#stkCopyCount");
    if(meta) meta.textContent = n;
    const selMeta = el.querySelector("#stkSelectedCount");
    if(selMeta) selMeta.textContent = selectedN;
    const hostVal = ((el.querySelector("#stkHost")||{}).value || stickerPrinterHost() || "").trim();
    const downloadBtn = el.querySelector("#btnStkDownload");
    if(downloadBtn) downloadBtn.disabled = n<=0;
    const lanBtn = el.querySelector("#btnStkLan");
    if(lanBtn) lanBtn.disabled = n<=0 || !hostVal;
  };
  let previewTimer = null;
  let lastPreviewKey = "";
  const refreshPreview = (force)=>{
    clearTimeout(previewTimer);
    previewTimer = setTimeout(async()=>{
      try{
        const selected = (job.lines||[]).filter(l=>l.selected && Number(l.qty)>0);
        const first = selected[0];
        const key = first ? (stickerPrinterModel()+"|"+first.bcode) : "";
        if(!force && key && key === lastPreviewKey){
          const note = el.querySelector("#stkPreviewMeta");
          if(note) note.hidden = true;
          return;
        }
        if(!key){
          lastPreviewKey = "";
          const img = el.querySelector("#stkPreview");
          const note = el.querySelector("#stkPreviewMeta");
          if(img){ img.hidden = true; img.removeAttribute("src"); }
          if(note){ note.textContent = "เลือกอย่างน้อย 1 รายการเพื่อดูตัวอย่าง"; note.hidden = false; }
          return;
        }
        const data = await fetchStickerPreview(job, stickerPrinterModel());
        lastPreviewKey = key;
        const img = el.querySelector("#stkPreview");
        const note = el.querySelector("#stkPreviewMeta");
        if(data && data.preview_png_b64 && img){
          img.src = "data:image/png;base64,"+data.preview_png_b64;
          img.hidden = false;
          if(note) note.hidden = true;
        }else if(note){
          note.textContent = "เลือกอย่างน้อย 1 รายการเพื่อดูตัวอย่าง";
          note.hidden = false;
        }
      }catch(e){
        const note = el.querySelector("#stkPreviewMeta");
        if(note){ note.textContent = e.message||"โหลดตัวอย่างไม่สำเร็จ"; note.hidden=false; }
      }
    }, 250);
  };
  el.querySelectorAll(".stk-qty, .stk-sel").forEach(inp=>inp.addEventListener("change", ()=>{ syncQty(); refreshPreview(); }));
  el.querySelectorAll("[data-stk-delta]").forEach(btn=>btn.onclick=()=>{
    const i = Number(btn.dataset.stkDelta);
    const d = Number(btn.dataset.d);
    job.lines[i].qty = Math.max(1, Math.min(200, Number(job.lines[i].qty||1)+d));
    el.querySelectorAll(`.stk-qty[data-i="${i}"]`).forEach(inp=>inp.value=job.lines[i].qty);
    syncQty();
    refreshPreview();
  });
  el.querySelector("#stkModelSeg").onclick = e=>{
    const b = e.target.closest("[data-model]");
    if(!b) return;
    setStickerPrinterModel(b.dataset.model);
    el.querySelectorAll("#stkModelSeg button").forEach(x=>x.classList.toggle("on", x===b));
    refreshPreview(true);
  };
  el.querySelector("#btnStkAll").onclick = ()=>{
    job.lines.forEach(l=>l.selected=true);
    el.querySelectorAll(".stk-sel").forEach(inp=>inp.checked=true);
    syncQty();
    refreshPreview();
  };
  el.querySelector("#btnStkNone").onclick = ()=>{
    job.lines.forEach(l=>l.selected=false);
    el.querySelectorAll(".stk-sel").forEach(inp=>inp.checked=false);
    syncQty();
    refreshPreview();
  };
  const hostInput = el.querySelector("#stkHost");
  if(hostInput) hostInput.oninput = hostInput.onchange = e=>{
    setStickerPrinterHost(e.target.value.trim());
    syncQty();
  };
  el.querySelector("#btnStkSkip").onclick = ()=> leaveStickerPrint();
  const downloadBtn = el.querySelector("#btnStkDownload");
  if(downloadBtn) downloadBtn.onclick = async()=>{
    syncQty();
    try{
      await downloadStickerPrn(job, stickerPrinterModel());
      showToast("ดาวน์โหลด .prn แล้ว — ดับเบิลคลิกเพื่อพิมพ์ (ถ้าติดตั้งตัวช่วยแล้ว)");
    }catch(e){ alert(e.message); }
  };
  // PRN helper: one-click download + double-click install
  (function setupPrnHelper(){
    const base = window.location.origin;
    const dl = el.querySelector("#btnStkPrnHelperDownload");
    if(dl) dl.href = base + "/tools/prn-printer/install.cmd";
    const verEl = el.querySelector("#stkPrnHelperVer");
    if(verEl){
      fetch(base + "/tools/prn-printer/version", {credentials:"same-origin"})
        .then(r=>r.ok?r.json():null)
        .then(v=>{
          if(!v || !v.version){ return; }
          verEl.textContent = "· v"+v.version;
        })
        .catch(()=>{});
    }
  })();
  const lanBtn = el.querySelector("#btnStkLan");
  if(lanBtn) lanBtn.onclick = async()=>{
    syncQty();
    const h = hostInput ? hostInput.value.trim() : stickerPrinterHost();
    setStickerPrinterHost(h);
    if(!h){ alert("ยังไม่ได้ตั้งค่าเครื่องบน LAN"); return; }
    try{
      const result = await sendStickerPrint(job, stickerPrinterModel(), h);
      showToast("พิมพ์แล้ว "+(result.copies||copies)+" ดวง");
      leaveStickerPrint();
    }catch(e){ alert(e.message); }
  };
  refreshPreview();
}
function printRequestBill(detail){
  const lines = detail.items || detail.lines || [];
  const fromB = detail.from_branch;
  const toB = detail.to_branch;
  const shortId = detail.short_id || detail.transfer_id || "";
  const shipAp = apCounterpartyLabel(fromB, toB);
  const recvAp = apCounterpartyLabel(toB, fromB);
  const rows = lines.map((ln,i)=>`<tr>
    <td class="num">${i+1}</td>
    <td><code>${ln.bcode||""}</code></td>
    <td>${(ln.descr||"").replace(/</g,"&lt;")}${ln.model?`<div class="meta">รุ่น ${String(ln.model).replace(/</g,"&lt;")}</div>`:""}${ln.location?`<div class="meta">ที่เก็บ ${String(ln.location).replace(/</g,"&lt;")}</div>`:(ln.location_hq||ln.location_syp)?`<div class="meta">ที่เก็บ สนญ ${String(ln.location_hq||"—").replace(/</g,"&lt;")} · สาขา ${String(ln.location_syp||"—").replace(/</g,"&lt;")}</div>`:""}</td>
    <td class="num">${fmtQty(ln.qty_requested)}</td>
    <td class="num">${fmtQty(ln.qty_prepared)}</td>
    <td class="num">${fmtQty(ln.qty_received)}</td>
  </tr>`).join("");
  $("printSheet").className = "";
  $("printSheet").innerHTML = `
    <h1 style="margin:0 0 .35rem;font-size:18pt">ใบคำขอโอนสินค้า</h1>
    <p style="margin:0 0 .75rem;font-size:12pt"><strong>TRF-${String(shortId).replace(/^TRF-/,"")}</strong>
      · ${dirLabel(fromB,toB)}
      · สถานะ ${badge(detail.status||"", fromB, toB, detail.prep_recv_mismatch)}</p>
    <p class="meta" style="margin:0 0 .75rem">สร้าง ${fmtDateTime(detail.created_at)} · ส่งคำขอ ${fmtDateTime(detail.requested_at)} · พิมพ์โดย ${USER}</p>
    <p class="meta" style="margin:0 0 .75rem">AP จัดออก (${branchLabel(fromB)}): ${shipAp||"—"} · AP รับเข้า (${branchLabel(toB)}): ${recvAp||"—"}</p>
    <table><thead><tr><th class="num">#</th><th>รหัส</th><th>รายละเอียด</th><th class="num">ขอ</th><th class="num">จัด</th><th class="num">รับ</th></tr></thead>
      <tbody>${rows || '<tr><td colspan="6">ไม่มีรายการ</td></tr>'}</tbody></table>
    <div class="sig">
      <div class="sig-box">ผู้ขอ · ${branchLabel(toB)}<br/>ลายเซ็น / วันที่</div>
      <div class="sig-box">ผู้จัด · ${branchLabel(fromB)}<br/>ลายเซ็น / วันที่</div>
    </div>`;
  window.print();
}
async function openRequestDetail(transferId){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  const lines = detail.items || detail.lines || [];
  const shipments = detail.shipments || [];
  const status = detail.status || (detail.header && detail.header.status) || "";
  const fromB = detail.from_branch;
  const toB = detail.to_branch;
  const progress = {prep_recv_mismatch: detail.prep_recv_mismatch, prep_recv_mismatch_count: detail.prep_recv_mismatch_count};
  const stickerLines = lines.filter(ln=>Number(ln.qty_received||0)>0).map(ln=>({
    bcode: ln.bcode,
    descr: ln.descr || "",
    qty: Number(ln.qty_received||0),
  }));
  const stickerIndex = Object.fromEntries(stickerLines.map((ln,i)=>[ln.bcode, i]));
  const lineRows = lines.map(ln=>{
    const si = stickerIndex[ln.bcode];
    const pick = si!=null ? `<input type="checkbox" class="pick-check stk-pick" data-i="${si}" title="พิมพ์บาร์โค้ด"/>` : "";
    return `<tr class="${ln.prep_recv_mismatch?"row-mismatch":""}">
    <td>${pick}</td>
    <td><code>${ln.bcode}</code></td>
    <td>${fmtDescr(ln)}</td>
    <td class="num">${fmtQty(ln.qty_requested)}</td>
    <td class="num">${qtyCell(ln.qty_prepared, ln.prep_recv_mismatch)}</td>
    <td class="num">${qtyCell(ln.qty_received, ln.prep_recv_mismatch)}</td>
    <td>${lineStatusLabel(ln)}</td>
  </tr>`;
  }).join("");
  let shipHtml = "";
  if(shipments.length){
    shipHtml = shipments.map((ship,i)=>{
      const shipBill = ship.ship_billno || ship.tf_billno || "—";
      const recvBill = ship.receive_billno || "";
      const slines = (ship.lines||[]).map(sl=>{
        const open = Math.max(Number(sl.qty_shipped||0)-Number(sl.qty_received||0),0);
        const mm = open > 0 && Number(sl.qty_received||0) > 0;
        return `<tr><td><code>${sl.bcode||""}</code></td><td class="num">${fmtQty(sl.qty_shipped)}</td><td class="num">${qtyCell(sl.qty_received, mm)}</td><td class="num">${mm ? `<span class="flag-mismatch">${fmtQty(open)}</span>` : fmtQty(open)}</td></tr>`;
      }).join("");
      return `<div style="margin-top:.65rem">
        <p class="meta" style="margin:0"><strong>ใบจัด ${i+1}</strong> · <code>${shipBill}</code>${recvBill ? ` · ใบรับ <code>${recvBill}</code>` : ""}</p>
        ${slines ? `<div class="table-wrap" style="margin-top:.35rem"><table><thead><tr><th>รหัส</th><th class="num">จัด</th><th class="num">รับแล้ว</th><th class="num">ค้างรับ</th></tr></thead><tbody>${slines}</tbody></table></div>` : ""}
      </div>`;
    }).join("");
    shipHtml = `<div class="tool-section" style="margin-top:.75rem"><p class="tool-title">ใบ TF / การจัดส่ง</p>${shipHtml}</div>`;
  }
  const canCancel = canCancelRequest(status, toB, shipments.length > 0);
  const isDraft = status==="draft";
  const shipAp = apCounterpartyLabel(fromB, toB);
  const recvAp = apCounterpartyLabel(toB, fromB);
  const lineCards = lines.map(ln=>{
    const si = stickerIndex[ln.bcode];
    const pick = si!=null ? `<label style="display:flex;align-items:center;gap:.35rem"><input type="checkbox" class="pick-check stk-pick" data-i="${si}"/><code>${ln.bcode}</code></label>` : `<code>${ln.bcode}</code>`;
    return `<div class="item-card ${ln.prep_recv_mismatch?"row-mismatch":""}">
    <div class="item-card-head">${pick}${lineStatusLabel(ln)}</div>
    <div class="item-card-desc">${fmtDescr(ln)}</div>
    <div class="item-card-grid">
      <div class="item-field num"><span class="lbl">ขอ</span><span class="val">${fmtQty(ln.qty_requested)}</span></div>
      <div class="item-field num"><span class="lbl">จัด</span><span class="val">${qtyCell(ln.qty_prepared, ln.prep_recv_mismatch)}</span></div>
      <div class="item-field num"><span class="lbl">รับ</span><span class="val">${qtyCell(ln.qty_received, ln.prep_recv_mismatch)}</span></div>
    </div>
  </div>`;
  }).join("");
  const modal = showModal(`<h2>รายละเอียด · <code>${detail.short_id||transferId}</code></h2>
    <p class="dir">${dirLabel(fromB, toB)}</p>
    <p style="margin:.35rem 0">${badge(status, fromB, toB, detail.prep_recv_mismatch)} ${pipeline(status, detail.prep_recv_mismatch)}</p>
    ${mismatchBanner(detail)}
    <p class="meta">สร้าง ${fmtDateTime(detail.created_at)} · ส่งคำขอ ${fmtDateTime(detail.requested_at)}</p>
    <p class="meta">AP จัดออก: ${shipAp||"—"} · AP รับเข้า: ${recvAp||"—"}</p>
    ${stickerLines.length ? `<p class="meta" style="margin:.65rem 0 0">ติ๊กสินค้าที่ต้องการพิมพ์บาร์โค้ด — จำนวนดวง = จำนวนที่รับ</p>` : ""}
    ${dualView(
      `<div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th></th><th>รหัส</th><th>รายละเอียด</th><th class="num">ขอ</th><th class="num">จัด</th><th class="num">รับ</th><th>สถานะ</th></tr></thead><tbody>
        ${lineRows || '<tr><td colspan="7" class="empty">ไม่มีรายการ</td></tr>'}
      </tbody></table></div>`,
      itemCards(lineCards || '<div class="empty">ไม่มีรายการ</div>')
    )}
    ${shipHtml}
    <div class="row-actions">
      <button class="btn btn-ghost" data-close>ปิด</button>
      <button class="btn btn-ghost" id="btnDetailPrint">พิมพ์ใบคำขอ</button>
      ${stickerLines.length ? `<button class="btn btn-ghost" id="btnDetailStkAll">เลือกสินค้าทั้งหมด</button>
      <button class="btn btn-primary" id="btnDetailStickers">พิมพ์บาร์โค้ดที่เลือก</button>` : ""}
      ${canCancel ? `<button class="btn btn-ghost" id="btnDetailCancel">ยกเลิกคำขอ</button>` : ""}
      ${isDraft ? `<button class="btn btn-primary" id="btnDetailEdit">แก้ไขร่าง</button>` : ""}
    </div>`);
  const printBtn = modal.box.querySelector("#btnDetailPrint");
  if(printBtn) printBtn.onclick = ()=>printRequestBill(detail);
  const pickAllBtn = modal.box.querySelector("#btnDetailStkAll");
  if(pickAllBtn) pickAllBtn.onclick = ()=>{
    modal.box.querySelectorAll(".stk-pick").forEach(inp=>inp.checked=true);
  };
  const stickerBtn = modal.box.querySelector("#btnDetailStickers");
  if(stickerBtn) stickerBtn.onclick = ()=>{
    const picked = [...modal.box.querySelectorAll(".stk-pick:checked")].map(inp=>{
      const ln = stickerLines[Number(inp.dataset.i)];
      return ln ? {...ln, selected:true} : null;
    }).filter(Boolean);
    if(!picked.length){ alert("ติ๊กสินค้าที่ต้องการพิมพ์บาร์โค้ด"); return; }
    modal.close();
    const job = stickerLinesFromDetail(detail, {selected:false});
    openStickerPrint({
      ...job,
      lines: picked,
      selectAll: false,
      returnView: "status",
    });
  };
  const cancelBtn = modal.box.querySelector("#btnDetailCancel");
  if(cancelBtn) cancelBtn.onclick = async()=>{ modal.close(); await cancelRequest(transferId); };
  const editBtn = modal.box.querySelector("#btnDetailEdit");
  if(editBtn) editBtn.onclick = ()=>{ modal.close(); editDraft(transferId); };
}
async function editDraft(transferId){
  const detail = await api("/transfer/api/requests/"+transferId+"/lines");
  editingDraftId = transferId;
  orderDirection = (detail.to_branch||"SYP").toUpperCase() === SITE ? "to_syp" : "to_hq";
  const lines = detail.items || detail.lines || [];
  await api("/transfer/api/need-list",{
    method:"PUT",
    body:JSON.stringify({
      lines: lines.map(ln=>({
        bcode:ln.bcode, qty:ln.qty_requested, descr:ln.descr||"", suggest_qty:ln.qty_requested,
      })),
    }),
  });
  view = "request";
  requestStep = 2;
  render();
}
function goHome(){ view="home"; requestStep=1; receiveStep=1; receiveShipment=null; receivePrintJob=null; stickerReturnView="home"; prepareStep=1; prepareRequest=null; editingDraftId=null; suggestPick={}; suggestFilter=""; receiveFilter=""; render(); }
function goView(v){
  view=v;
  if(v==="request" && !editingDraftId){ requestStep=1; suggestPick={}; }
  if(v==="receive"){ receiveStep=1; receiveShipment=null; receiveFilter=""; }
  if(v!=="stickers" && v!=="receive") receivePrintJob=null;
  if(v==="prepare"){ prepareStep=1; prepareRequest=null; }
  render();
}
function setReceiveStep(n){ receiveStep=n; render(); }
function setPrepareStep(n){ prepareStep=n; render(); }
function setRequestStep(n){ requestStep=n; render(); }
function withScrollPreserved(fn){
  const y = window.scrollY || document.documentElement.scrollTop || 0;
  return Promise.resolve(fn()).then((v)=>{
    requestAnimationFrame(()=>{ window.scrollTo(0, y); });
    return v;
  });
}
function readSuggestPick(row){
  const b = row.bcode;
  const entry = defaultEntryQty(row);
  const cur = suggestPick[b] || {};
  return {
    checked: !!cur.checked,
    unit: cur.unit || entry.unit,
    qty: cur.qty != null ? cur.qty : entry.qty,
  };
}
function writeSuggestPick(bcode, patch, row){
  const entry = row ? defaultEntryQty(row) : {unit:"small", qty:1};
  const cur = suggestPick[bcode] || {checked:false, unit:entry.unit, qty:entry.qty};
  suggestPick[bcode] = {...cur, ...patch};
}
function pickedCount(){
  return Object.values(suggestPick).filter(p=>p && p.checked).length;
}

function updateHeader(){
  const titles = {
    home: ["โอนสินค้า · " + SITE_LABEL, USER + " · เลือกสิ่งที่ต้องการทำ"],
    request: ["ขอสินค้าจาก " + OTHER_LABEL, "ขั้นตอนที่ " + requestStep + " จาก 3 · " + orderFlowText()],
    prepare: ["ส่งสินค้าไป " + OTHER_LABEL, prepareStep===1 ? "เลือกคำขอที่ต้องจัด" : prepareStep===2 ? "ขั้นตอนที่ 2 จาก 3 · ระบุจำนวนจัด" : "ขั้นตอนที่ 3 จาก 3 · ยืนยันส่งสินค้า"],
    receive: ["รับสินค้าจาก " + OTHER_LABEL, receiveStep===1 ? "เลือกคำขอที่จัดส่งมาแล้ว" : receiveStep===2 ? "ขั้นตอนที่ 2 จาก 3 · ระบุจำนวนรับ" : "ขั้นตอนที่ 3 จาก 3 · ยืนยันรับเข้า"],
    status: ["ตรวจสอบสถานะ", "ติดตามคำขอโอนทั้งหมด"],
    stickers: ["พิมพ์สติ๊กเกอร์บาร์โค้ด", "เลือกสินค้าที่ต้องการพิมพ์"],
  };
  const t = titles[view] || titles.home;
  $("hdrTitle").textContent = t[0];
  $("hdrSub").textContent = t[1];
  $("btnBack").style.display = view === "home" ? "none" : "";
}

function stepBar(current){
  const labels = ["1. เลือกทิศทาง","2. เลือกสินค้า","3. ยืนยันส่ง"];
  return `<div class="steps">${labels.map((l,i)=>{
    const n = i+1;
    const cls = n===current ? "on" : n<current ? "done" : "";
    return `<div class="step ${cls}">${l}<span class="step-label">${n===1?"ขอจากสาขาไหน":n===2?"เพิ่มรายการ": "ตรวจสอบ"}</span></div>`;
  }).join("")}</div>`;
}
function receiveStepBar(current){
  const labels = ["1. เลือกคำขอ","2. ระบุจำนวน","3. ยืนยันรับ"];
  return `<div class="steps">${labels.map((l,i)=>{
    const n = i+1;
    const cls = n===current ? "on" : n<current ? "done" : "";
    return `<div class="step ${cls}">${l}<span class="step-label">${n===1?"เปิดคำขอ":n===2?"กรอกจำนวน":"ออกใบ TF"}</span></div>`;
  }).join("")}</div>`;
}
function prepareStepBar(current){
  const labels = ["1. เลือกคำขอ","2. ระบุจำนวน","3. ยืนยันจัด"];
  return `<div class="steps">${labels.map((l,i)=>{
    const n = i+1;
    const cls = n===current ? "on" : n<current ? "done" : "";
    return `<div class="step ${cls}">${l}<span class="step-label">${n===1?"เปิดคำขอ":n===2?"กรอกจำนวน":"ออกใบ TF"}</span></div>`;
  }).join("")}</div>`;
}
function groupReceiveQueue(items){
  const map = new Map();
  for(const row of items){
    const key = row.shipment_id;
    if(!map.has(key)){
      map.set(key, {
        transfer_id: row.transfer_id,
        shipment_id: row.shipment_id,
        short_id: row.short_id,
        from_branch: row.from_branch,
        to_branch: row.to_branch,
        ship_billno: row.ship_billno,
        lines: [],
      });
    }
    map.get(key).lines.push(row);
  }
  return [...map.values()];
}
function lineFilterText(ln){
  return [ln.bcode, ln.descr, ln.model, ln.location, ln.location_hq, ln.location_syp]
    .map(v=>(v==null?"":String(v))).join(" ").trim();
}
function escapeAttr(s){
  return String(s||"").replace(/&/g,"&amp;").replace(/"/g,"&quot;").replace(/</g,"&lt;");
}
/** Client-side hide/show of line rows — keeps qty inputs in DOM. */
function bindLineSearch(root, {inputId, rowSelector, metaId, total}){
  const input = root.querySelector(inputId);
  if(!input) return;
  const apply = ()=>{
    const q = (input.value||"").trim().toLowerCase();
    receiveFilter = input.value;
    let shown = 0;
    root.querySelectorAll(rowSelector).forEach(row=>{
      const hay = (row.dataset.filterText||"").toLowerCase();
      const ok = !q || hay.includes(q);
      row.hidden = !ok;
      if(ok) shown++;
    });
    const meta = metaId ? root.querySelector(metaId) : null;
    if(meta){
      if(q){
        meta.hidden = false;
        meta.textContent = shown
          ? `แสดง ${shown} จาก ${total} รายการ`
          : `ไม่พบ "${input.value.trim()}" ในรายการ`;
      } else {
        meta.hidden = true;
        meta.textContent = "";
      }
    }
  };
  input.oninput = apply;
  input.onkeydown = e=>{
    if(e.key==="Escape"){
      e.preventDefault();
      input.value = "";
      apply();
    }
  };
  if((input.value||"").trim()) apply();
}

async function fetchCounts(){
  try{
    const [prep, recv] = await Promise.all([
      api("/transfer/api/requests?role=prepare",{quiet:true}),
      api("/transfer/api/receive-lines",{quiet:true}),
    ]);
    return {prepare:(prep.items||[]).length, receive:(recv.items||[]).length};
  }catch(e){ return {prepare:0, receive:0}; }
}

async function renderHome(el){
  const counts = await fetchCounts();
  el.innerHTML = `
    ${billTimelineHtml(OTHER, SITE)}
    <div class="action-grid">
      <div class="action-group">
        <p class="action-group-label">ของเข้า</p>
        <button class="action-card" data-go="request">
          <p class="title">📥 ขอสินค้าจาก ${OTHER_LABEL}</p>
          <p class="desc">ฉันอยู่ที่ ${SITE_LABEL} และต้องการให้ ${OTHER_LABEL} ส่งสินค้ามา</p>
        </button>
        <button class="action-card" data-go="receive">
          <p class="title">📦 รับสินค้าจาก ${OTHER_LABEL}</p>
          <p class="desc">สินค้าถูกจัดส่งมาแล้ว — เปิดคำขอ กรอกจำนวน แล้วยืนยันรับ${counts.receive ? `<span class="count">${counts.receive} รายการรอรับ</span>` : ""}</p>
        </button>
      </div>
      <div class="action-group">
        <p class="action-group-label">ของออก</p>
        <button class="action-card" data-go="prepare">
          <p class="title">📤 ส่งสินค้าไป ${OTHER_LABEL}</p>
          <p class="desc">มีคำขอรอจัด — ${SITE_LABEL} ต้องจัดสินค้าออก${counts.prepare ? `<span class="count">${counts.prepare} รายการรอจัด</span>` : ""}</p>
        </button>
      </div>
      <div class="action-group">
        <p class="action-group-label">ติดตาม</p>
        <button class="action-card" data-go="status">
          <p class="title">📋 ตรวจสอบสถานะ</p>
          <p class="desc">ดูคำขอที่ส่งแล้ว กำลังจัด รอรับ หรือเสร็จสิ้น</p>
        </button>
      </div>
    </div>`;
  el.querySelectorAll("[data-go]").forEach(b=>b.onclick=()=>goView(b.dataset.go));
}

async function renderRequest(el, opts){
  const reuseSuggest = !!(opts && opts.reuseSuggest);
  if(requestStep === 1){
    if(SITE === "SYP") orderDirection = "to_syp";
    else orderDirection = "to_hq";
    el.innerHTML = `${stepBar(1)}
      <div class="card">
        <p style="margin:0 0 .5rem"><strong>คุณอยู่ที่ ${SITE_LABEL}</strong></p>
        <p style="margin:0 0 .75rem">ต้องการขอสินค้าจาก <strong>${OTHER_LABEL}</strong> ให้ส่งมาที่ ${SITE_LABEL}</p>
        <div class="flow-hint" style="margin-bottom:0">
          <strong>ขั้นตอนถัดไป:</strong><br>
          1. เลือกรายการสินค้า → 2. ส่งคำขอ → 3. รอ ${OTHER_LABEL} จัดส่ง → 4. กลับมากดรับสินค้าที่นี่
        </div>
        <div class="row-actions" style="margin-top:1rem">
          <button class="btn btn-ghost" onclick="goHome()">ยกเลิก</button>
          <button class="btn btn-primary" id="btnReqNext1">ถัดไป → เลือกสินค้า</button>
        </div>
      </div>`;
    el.querySelector("#btnReqNext1").onclick = ()=>setRequestStep(2);
    return;
  }

  if(requestStep === 2){
    let cart;
    if(reuseSuggest && Array.isArray(suggestItems) && suggestItems.length){
      cart = await api("/transfer/api/need-list",{quiet:true});
    }else{
      const [rows, cartResp] = await Promise.all([
        api("/transfer/api/suggest"),
        api("/transfer/api/need-list",{quiet:true}),
      ]);
      suggestItems = rows.items || [];
      cart = cartResp;
    }
    const cartItems = cart.items || [];
    const cartBcodes = new Set(cartItems.map(n=>(n.bcode||"").trim()).filter(Boolean));
    const q = (suggestFilter || "").trim().toLowerCase();
    const filtered = q ? suggestItems.filter(r=>{
      const b = (r.bcode||"").toLowerCase();
      const d = (r.descr||"").toLowerCase();
      const m = (r.model||"").toLowerCase();
      return b.includes(q) || d.includes(q) || m.includes(q);
    }) : suggestItems;
    const nPicked = pickedCount();

    let html = stepBar(2) + `<div class="card">
      <p style="margin:0 0 .75rem"><strong>ทิศทาง:</strong> ${OTHER_LABEL} → ${SITE_LABEL}</p>
      <p class="meta" style="margin:0 0 .75rem">ติ๊กเลือกรายการ ปรับจำนวน แล้วกด <strong>เพิ่มที่เลือก</strong> — หน้าจอจะไม่กระโดดกลับด้านบน</p>

      <div class="search-bar">
        <input id="suggestSearch" class="text-input" placeholder="ค้นหาในรายการ (รหัส / รายละเอียด / รุ่น)" value="${suggestFilter.replace(/"/g,"&quot;")}"/>
      </div>

      <div class="tool-section">
        <p class="tool-title">เพิ่มรหัสเอง (ไม่อยู่ในรายการแนะนำ)</p>
        <div class="tool-row">
          <div class="field" style="flex:2">
            <label for="manualBcode">รหัสสินค้า (BCODE)</label>
            <input id="manualBcode" class="text-input" placeholder="เช่น 15010490"/>
          </div>
          <div class="field" style="max-width:6rem">
            <label for="manualQty">จำนวน</label>
            <input id="manualQty" type="number" min="1" value="1" class="qty-input"/>
          </div>
          <button class="btn btn-primary" id="btnManualAdd" style="margin-bottom:1px">เพิ่ม</button>
        </div>
        <p id="manualPreview" class="meta" style="margin:.5rem 0 0;display:none"></p>
      </div>
    </div>

    <div class="card card-table">
      <p class="meta" style="margin:0">${SITE === "HQ"
        ? "รายการ <strong>สต๊อกต่ำ (ICMAS)</strong> ที่สนญ. — ไม่ดึง ICLOW รอสั่งซื้อ (เก็บไว้สั่งจากเจ้าหนี้) · เพิ่มรหัสเองได้ด้านบน"
        : "รายการ <strong>รอสั่ง (ICLOW)</strong> ตรงกับแท็บรอสั่งซื้อใน /po — จำนวนแนะนำรวมทุกแถว ICLOW ต่อรหัส · ด้านล่าง (ถ้ามี) คือสต๊อกต่ำ ICMAS หลังโอนครั้งก่อน"}</p>`;

    if(!suggestItems.length){
      html += `<div class="empty">ไม่พบรายการแนะนำ — ใช้เพิ่มรหัสเองด้านบน</div>`;
    } else if(!filtered.length){
      html += `<div class="empty">ไม่พบ "${suggestFilter}" ในรายการ — ลองเพิ่มรหัสเองด้านบน</div>`;
      if(/^[0-9A-Za-z-]+$/.test(q)){
        html += `<div class="row-actions"><button class="btn btn-ghost" id="btnSearchAdd">เพิ่ม <code>${q}</code> เข้าคำขอ</button></div>`;
      }
    } else {
      const suggestTableRows = filtered.map((r)=>{
        const idx = suggestItems.indexOf(r);
        const pick = readSuggestPick(r);
        const inCart = cartBcodes.has((r.bcode||"").trim());
        const unitOpts = unitChoices(r).map(c=>`<option value="${c.id}" ${c.id===pick.unit?"selected":""}>${c.label}</option>`).join("");
        const src = (r.source||"iclow")==="icmas" ? "สต๊อกต่ำ" : "รอสั่ง";
        const srcTitle = src==="รอสั่ง" && Number(r.iclow_line_count||0)>1 ? ` title="รวม ${r.iclow_line_count} แถว ICLOW"` : "";
        return `<tr class="${pick.checked?"row-picked":""}"><td><input type="checkbox" class="pick-check" data-pick="${idx}" ${pick.checked?"checked":""} ${inCart?"title=\"มีในคำขอแล้ว — ติ๊กแล้วเพิ่มซ้ำได้\"":""}/></td>
          <td><code>${r.bcode}</code>${inCart?` <span class="meta">ในคำขอ</span>`:""}</td><td class="meta"${srcTitle}>${src}</td><td>${fmtDescr(r)}</td>
          <td class="num">${fmtHqStock(r)}</td><td class="num">${fmtStockDual(r.syp_qtyoh2,r)}</td>
          <td class="num">${fmtStockDual(r.suggest_qty,r)}</td>
          <td><select class="unit-select" data-unit="${idx}">${unitOpts}</select></td>
          <td class="num"><input class="qty-input" type="number" min="0.01" step="any" value="${pick.qty}" data-qty="${idx}"/></td></tr>`;
      }).join("");
      const suggestCardRows = filtered.map((r)=>{
        const idx = suggestItems.indexOf(r);
        const pick = readSuggestPick(r);
        const inCart = cartBcodes.has((r.bcode||"").trim());
        const unitOpts = unitChoices(r).map(c=>`<option value="${c.id}" ${c.id===pick.unit?"selected":""}>${c.label}</option>`).join("");
        const src = (r.source||"iclow")==="icmas" ? "สต๊อกต่ำ" : "รอสั่ง";
        return `<div class="item-card ${pick.checked?"row-picked":""}">
          <div class="item-card-head">
            <label style="display:flex;align-items:center;gap:.45rem;cursor:pointer">
              <input type="checkbox" class="pick-check" data-pick="${idx}" ${pick.checked?"checked":""}/>
              <code>${r.bcode}</code>
            </label>
            <span class="meta">${src}${inCart?" · ในคำขอ":""}</span>
          </div>
          <div class="item-card-desc">${fmtDescr(r)}</div>
          <div class="item-card-grid">
            <div class="item-field num"><span class="lbl">คงเหลือ สำนักงานใหญ่</span><span class="val">${fmtHqStock(r)}</span></div>
            <div class="item-field num"><span class="lbl">คงเหลือ สาขา</span><span class="val">${fmtStockDual(r.syp_qtyoh2,r)}</span></div>
            <div class="item-field num"><span class="lbl">แนะนำ</span><span class="val">${fmtStockDual(r.suggest_qty,r)}</span></div>
          </div>
          <div class="item-card-actions">
            <select class="unit-select" data-unit="${idx}">${unitOpts}</select>
            <input class="qty-input" type="number" min="0.01" step="any" value="${pick.qty}" data-qty="${idx}"/>
          </div>
        </div>`;
      }).join("");
      html += dualView(
        `<div class="table-wrap table-wrap--tall"><table><thead><tr>
          <th style="width:2.2rem"></th><th>รหัส</th><th>แหล่ง</th><th>รายละเอียด</th><th class="num">คงเหลือ สำนักงานใหญ่</th><th class="num">คงเหลือ สาขา</th><th class="num">แนะนำ</th><th>หน่วย</th><th class="num">จำนวน</th>
        </tr></thead><tbody>${suggestTableRows}</tbody></table></div>`,
        itemCards(suggestCardRows)
      );
      html += hqNoStockNoteHtml();
      if(q) html += `<p class="meta" style="margin:.5rem 1rem 0">แสดง ${filtered.length} จาก ${suggestItems.length} รายการ</p>`;
    }
    html += `
      <div class="commit-bar">
        <div class="commit-meta">เลือกแล้ว <strong id="pickCountLabel">${nPicked}</strong> · ในคำขอ <strong>${cartItems.length}</strong></div>
        <button class="btn btn-ghost" id="btnClearPick" ${nPicked?"":"disabled"}>ล้างที่เลือก</button>
        <button class="btn btn-primary" id="btnCommitPick" ${nPicked?"":"disabled"}>เพิ่มที่เลือก (${nPicked})</button>
      </div>
    </div>`;

    html += `<div class="card card-table"><strong>รายการในคำขอ (${cartItems.length})</strong>`;
    if(!cartItems.length) html += `<div class="empty">ยังไม่มีรายการ — ติ๊กจากรายการแนะนำแล้วกดเพิ่มที่เลือก</div>`;
    else {
      const cartTableRows = cartItems.map(n=>`<tr><td><code>${n.bcode}</code></td><td>${fmtDescr(n)}</td><td class="num">${fmtQty(n.qty)}</td>
        <td><button class="btn btn-ghost" data-del="${n.need_id}">ลบ</button></td></tr>`).join("");
      const cartCardRows = cartItems.map(n=>`<div class="item-card">
        <div class="item-card-head"><code>${n.bcode}</code><span class="num">${fmtQty(n.qty)}</span></div>
        <div class="item-card-desc">${fmtDescr(n)}</div>
        <div class="item-card-actions"><button class="btn btn-ghost" data-del="${n.need_id}">ลบ</button></div>
      </div>`).join("");
      html += dualView(
        `<div class="table-wrap"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th class="num">จำนวน</th><th></th></tr></thead><tbody>${cartTableRows}</tbody></table></div>`,
        itemCards(cartCardRows)
      );
    }
    html += `<div class="row-actions">
      <button class="btn btn-ghost" onclick="setRequestStep(1)">← ย้อนกลับ</button>
      <button class="btn btn-primary" id="btnReqNext2" ${cartItems.length?"":"disabled"}>ถัดไป → ตรวจสอบ</button>
    </div></div>`;
    el.innerHTML = html;

    function syncPickChrome(){
      const n = pickedCount();
      const lbl = el.querySelector("#pickCountLabel");
      if(lbl) lbl.textContent = String(n);
      const commit = el.querySelector("#btnCommitPick");
      if(commit){ commit.disabled = n===0; commit.textContent = `เพิ่มที่เลือก (${n})`; }
      const clear = el.querySelector("#btnClearPick");
      if(clear) clear.disabled = n===0;
    }
    function livePickFromDom(idx, row){
      const fallback = readSuggestPick(row);
      const qtyEl = el.querySelector(`[data-qty="${idx}"]`);
      const unitEl = el.querySelector(`[data-unit="${idx}"]`);
      const qty = qtyEl != null ? Number(qtyEl.value||0) : fallback.qty;
      const unit = unitEl != null ? unitEl.value : fallback.unit;
      return {qty, unit};
    }
    function bindPickRow(idx){
      const row = suggestItems[idx];
      if(!row) return;
      const checks = el.querySelectorAll(`[data-pick="${idx}"]`);
      const unitEls = el.querySelectorAll(`[data-unit="${idx}"]`);
      const qtyEls = el.querySelectorAll(`[data-qty="${idx}"]`);
      checks.forEach(chk=>{
        chk.onchange = ()=>{
          const live = livePickFromDom(idx, row);
          writeSuggestPick(row.bcode, {checked: chk.checked, qty: live.qty, unit: live.unit}, row);
          checks.forEach(c=>{ c.checked = chk.checked; });
          const tr = chk.closest("tr");
          const card = chk.closest(".item-card");
          if(tr) tr.classList.toggle("row-picked", chk.checked);
          if(card) card.classList.toggle("row-picked", chk.checked);
          syncPickChrome();
        };
      });
      unitEls.forEach(sel=>{
        sel.onchange = ()=>{
          const live = livePickFromDom(idx, row);
          writeSuggestPick(row.bcode, {unit: sel.value, qty: live.qty, checked: true}, row);
          unitEls.forEach(s=>{ s.value = sel.value; });
          checks.forEach(c=>{ c.checked = true; });
          const tr = sel.closest("tr");
          const card = sel.closest(".item-card");
          if(tr) tr.classList.add("row-picked");
          if(card) card.classList.add("row-picked");
          syncPickChrome();
        };
      });
      qtyEls.forEach(inp=>{
        inp.oninput = ()=>{
          const live = livePickFromDom(idx, row);
          writeSuggestPick(row.bcode, {qty: Number(inp.value||0), unit: live.unit, checked: true}, row);
          qtyEls.forEach(i=>{ if(i!==inp) i.value = inp.value; });
          checks.forEach(c=>{ c.checked = true; });
          const tr = inp.closest("tr");
          const card = inp.closest(".item-card");
          if(tr) tr.classList.add("row-picked");
          if(card) card.classList.add("row-picked");
          syncPickChrome();
        };
      });
    }
    filtered.forEach(r=>bindPickRow(suggestItems.indexOf(r)));

    const searchEl = el.querySelector("#suggestSearch");
    if(searchEl){
      let searchTimer = null;
      searchEl.oninput = ()=>{
        suggestFilter = searchEl.value;
        if(searchTimer) clearTimeout(searchTimer);
        searchTimer = setTimeout(()=>withScrollPreserved(()=>renderRequest(el,{reuseSuggest:true})), 280);
      };
      searchEl.onkeydown = e=>{
        if(e.key==="Enter"){
          e.preventDefault();
          if(searchTimer) clearTimeout(searchTimer);
          suggestFilter = searchEl.value;
          withScrollPreserved(()=>renderRequest(el,{reuseSuggest:true}));
        }
      };
    }

    el.querySelector("#btnClearPick").onclick = ()=>{
      suggestPick = {};
      withScrollPreserved(()=>renderRequest(el,{reuseSuggest:true}));
    };
    el.querySelector("#btnCommitPick").onclick = async()=>{
      const picks = [];
      for(const row of suggestItems){
        const pick = suggestPick[row.bcode];
        if(!pick || !pick.checked) continue;
        const idx = suggestItems.indexOf(row);
        const live = livePickFromDom(idx, row);
        writeSuggestPick(row.bcode, {qty: live.qty, unit: live.unit, checked: true}, row);
        const qtySmall = qtyToSmall(live.qty, live.unit, row);
        if(qtySmall <= 0){ alert("จำนวนของ "+row.bcode+" ไม่ถูกต้อง"); return; }
        picks.push({row, qtySmall});
      }
      if(!picks.length){ alert("ยังไม่ได้เลือกรายการ"); return; }
      try{
        await Promise.all(picks.map(p=>api("/transfer/api/need-list",{
          method:"POST",
          quiet:true,
          body:JSON.stringify({
            bcode:p.row.bcode, qty:p.qtySmall, suggest_qty:p.row.suggest_qty,
            descr:p.row.descr||"", hq_qtyoh2:p.row.hq_qtyoh2,
          }),
        })));
        picks.forEach(p=>writeSuggestPick(p.row.bcode, {checked:false}));
        showToast("เพิ่ม "+picks.length+" รายการแล้ว");
        await withScrollPreserved(()=>renderRequest(el,{reuseSuggest:true}));
      }catch(e){ alert(e.message||"เพิ่มไม่สำเร็จ"); }
    };

    el.querySelector("#btnManualAdd").onclick = async()=>{
      const b = el.querySelector("#manualBcode").value.trim();
      const qv = Number(el.querySelector("#manualQty").value||0);
      if(!b||qv<=0){alert("ระบุรหัสและจำนวน");return;}
      try{
        await api("/transfer/api/need-list",{method:"POST",body:JSON.stringify({bcode:b, qty:qv, descr:""})});
        showToast("เพิ่มแล้ว");
        el.querySelector("#manualBcode").value = "";
        const prev = el.querySelector("#manualPreview");
        if(prev){ prev.style.display="none"; prev.textContent=""; }
        await withScrollPreserved(()=>renderRequest(el,{reuseSuggest:true}));
      }catch(e){ alert(e.message||"เพิ่มไม่สำเร็จ"); }
    };
    const btnSearchAdd = el.querySelector("#btnSearchAdd");
    if(btnSearchAdd){
      btnSearchAdd.onclick = async()=>{
        const b = (suggestFilter||"").trim();
        if(!b) return;
        try{
          await api("/transfer/api/need-list",{method:"POST",body:JSON.stringify({bcode:b, qty:1, descr:""})});
          showToast("เพิ่มแล้ว");
          suggestFilter = "";
          await withScrollPreserved(()=>renderRequest(el,{reuseSuggest:true}));
        }catch(e){ alert(e.message||"เพิ่มไม่สำเร็จ"); }
      };
    }
    const manualBcodeEl = el.querySelector("#manualBcode");
    const manualPreviewEl = el.querySelector("#manualPreview");
    let manualLookupTimer = null;
    async function refreshManualPreview(){
      const b = (manualBcodeEl?.value||"").trim();
      if(!manualPreviewEl) return;
      if(!b){ manualPreviewEl.style.display="none"; manualPreviewEl.textContent=""; return; }
      try{
        const p = await api("/transfer/api/product?bcode="+encodeURIComponent(b),{quiet:true});
        manualPreviewEl.style.display = "block";
        manualPreviewEl.innerHTML = `<strong>${p.descr||"—"}</strong>${fmtModel(p)}${fmtLocation(p)} · สำนักงานใหญ่ ${fmtHqStockPlain(p)} · สาขา ${fmtQty(p.syp_qtyoh2)}`;
      }catch(e){
        manualPreviewEl.style.display = "block";
        manualPreviewEl.textContent = e.message||"ไม่พบรหัสใน ICMAS";
      }
    }
    if(manualBcodeEl){
      manualBcodeEl.oninput = ()=>{
        if(manualLookupTimer) clearTimeout(manualLookupTimer);
        manualLookupTimer = setTimeout(refreshManualPreview, 350);
      };
      manualBcodeEl.onblur = refreshManualPreview;
    }
    el.querySelectorAll("[data-del]").forEach(btn=>btn.onclick=async()=>{
      await api("/transfer/api/need-list/"+btn.dataset.del,{method:"DELETE"});
      await withScrollPreserved(()=>renderRequest(el));
    });
    el.querySelector("#btnReqNext2").onclick = ()=>setRequestStep(3);
    return;
  }

  if(requestStep === 3){
    const cart = await api("/transfer/api/need-list");
    const cartItems = cart.items || [];
    el.innerHTML = `${stepBar(3)}
      <div class="card">
        <p><strong>ทิศทาง:</strong> ${OTHER_LABEL} จัดส่ง → ${SITE_LABEL} รับเข้า</p>
        <p class="meta">ตรวจสอบรายการก่อนส่งคำขอ — ${OTHER_LABEL} จะเห็นในรายการรอจัด</p>
        ${submitBillNoteHtml(OTHER, SITE)}
        ${dualView(
          `<div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th class="num">จำนวน (หน่วยเล็ก)</th></tr></thead><tbody>
            ${cartItems.map(n=>`<tr><td><code>${n.bcode}</code></td><td>${fmtDescr(n)}</td><td class="num">${fmtQty(n.qty)}</td></tr>`).join("")}
          </tbody></table></div>`,
          itemCards(cartItems.map(n=>`<div class="item-card">
            <div class="item-card-head"><code>${n.bcode}</code><span class="num">${fmtQty(n.qty)}</span></div>
            <div class="item-card-desc">${fmtDescr(n)}</div>
          </div>`).join(""))
        )}
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setRequestStep(2)">← แก้ไขรายการ</button>
          ${editingDraftId ? `<button class="btn btn-ghost" id="btnSaveDraft">บันทึกร่าง</button>` : ""}
          <button class="btn btn-primary" id="btnConfirmSubmit">ยืนยันส่งคำขอ</button>
        </div>
      </div>`;
    el.querySelector("#btnConfirmSubmit").onclick = async()=>{
      if(!cartItems.length) return;
      try{
        const submitted = await submitTransferLines(
          cartItems.map(n=>({bcode:n.bcode, qty:n.qty, descr:n.descr||""})),
          orderDirection,
        );
        await api("/transfer/api/need-list",{method:"DELETE"});
        showToast("ส่งคำขอแล้ว: "+(submitted.short_id||submitted.transfer_id));
        goView("status");
        statusFilter = "active";
      }catch(e){alert(e.message);}
    };
    const saveBtn = el.querySelector("#btnSaveDraft");
    if(saveBtn){
      saveBtn.onclick = async()=>{
        if(!cartItems.length) return;
        try{
          const id = await saveDraftLines(cartItems.map(n=>({bcode:n.bcode, qty:n.qty, descr:n.descr||""})));
          showToast("บันทึกร่างแล้ว: "+id.slice(0,8));
          goView("status");
          statusFilter = "active";
        }catch(e){alert(e.message);}
      };
    }
  }
}

async function submitPrepare(request, qtyByLineId){
  const shipLines = (request.lines||[]).map(ln=>{
    const q = Number(qtyByLineId[ln.line_id]||0);
    return {line_id: ln.line_id, bcode: ln.bcode, qty_ship: q};
  }).filter(l=>l.qty_ship>0);
  if(!shipLines.length) throw new Error("ระบุจำนวนที่จัด");
  if(!SHIP_WRITE && !confirm("โหมดทดสอบ: writer ปิดอยู่")) throw new Error("ยกเลิก");
  return api("/transfer/api/requests/"+request.transfer_id+"/prepare",{
    method:"POST",
    body:JSON.stringify({client_token:uuid(), lines:shipLines}),
  });
}

async function submitReceive(shipment, qtyByLineId){
  const recvLines = shipment.lines.map(ln=>{
    const q = Number(qtyByLineId[ln.shipment_line_id]||0);
    return {
      shipment_line_id: ln.shipment_line_id,
      line_id: ln.line_id,
      bcode: ln.bcode,
      qty_receive: q,
      iclow_id: ln.iclow_id||undefined,
    };
  }).filter(l=>l.qty_receive>0);
  if(!recvLines.length) throw new Error("ระบุจำนวนที่รับ");
  if(!RECV_WRITE && !confirm("โหมดทดสอบ: writer ปิดอยู่")) throw new Error("ยกเลิก");
  return api("/transfer/api/shipments/"+shipment.shipment_id+"/receive",{
    method:"POST",
    body:JSON.stringify({client_token:uuid(), lines:recvLines}),
  });
}

async function renderReceive(el){
  if(receiveStep === 4 && receivePrintJob && (receivePrintJob.lines||[]).length){
    renderStickerComposer(el, receivePrintJob);
    return;
  }
  const data = await api("/transfer/api/receive-lines");
  const queue = groupReceiveQueue(data.items||[]);
  if(!queue.length){
    el.innerHTML = `<div class="card"><div class="empty">ไม่มีรายการรอรับ<br><span class="meta">จะแสดงเมื่อ ${OTHER_LABEL} จัดส่งและออกใบ TF แล้วเท่านั้น</span></div>
      <div class="row-actions"><button class="btn btn-ghost" onclick="goHome()">กลับหน้าหลัก</button></div></div>`;
    return;
  }

  if(receiveStep === 1){
    el.innerHTML = `${receiveStepBar(1)}
      <div class="flow-hint">เลือกคำขอที่ ${OTHER_LABEL} จัดส่งแล้ว (มี${SHIP_BILL} TF) → กรอกจำนวนรับ → ยืนยันเพื่อออก${RECV_BILL} TF</div>
      ${billTimelineHtml(OTHER, SITE)}
      <div class="card">${dualView(
        `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>ใบจัด</th><th class="num">รายการค้างรับ</th><th>วันที่</th><th></th></tr></thead><tbody>
          ${queue.map((g,i)=>`<tr class="row-clickable" data-recv-idx="${i}">
            <td><code>${g.short_id}</code></td>
            <td class="dir">${dirLabel(g.from_branch,g.to_branch)}</td>
            <td><code>${g.ship_billno||"-"}</code></td>
            <td class="num">${g.lines.length}</td>
            <td>—</td>
            <td><button class="btn btn-primary" data-recv-open="${i}">เปิดรับสินค้า</button></td>
          </tr>`).join("")}
        </tbody></table></div>`,
        itemCards(queue.map((g,i)=>`<div class="item-card row-clickable" data-recv-idx="${i}">
          <div class="item-card-head"><code>${g.short_id}</code><span class="dir">${dirLabel(g.from_branch,g.to_branch)}</span></div>
          <div class="item-card-grid">
            <div class="item-field"><span class="lbl">ใบจัด</span><span class="val"><code>${g.ship_billno||"-"}</code></span></div>
            <div class="item-field num"><span class="lbl">ค้างรับ</span><span class="val">${g.lines.length} รายการ</span></div>
          </div>
          <div class="item-card-actions"><button class="btn btn-primary" data-recv-open="${i}">เปิดรับสินค้า</button></div>
        </div>`).join(""))
      )}
      <div class="row-actions"><button class="btn btn-ghost" onclick="goHome()">กลับหน้าหลัก</button></div></div>`;
    window._receiveGroups = queue;
    el.querySelectorAll("[data-recv-open]").forEach(b=>b.onclick=e=>{
      e.stopPropagation();
      receiveShipment = window._receiveGroups[Number(b.dataset.recvOpen)];
      receiveFilter = "";
      setReceiveStep(2);
    });
    el.querySelectorAll(".row-clickable[data-recv-idx]").forEach(row=>{
      row.onclick = e=>{
        if(e.target.closest("button")) return;
        receiveShipment = window._receiveGroups[Number(row.dataset.recvIdx)];
        receiveFilter = "";
        setReceiveStep(2);
      };
    });
    return;
  }

  if(receiveStep === 4){
    if(!receivePrintJob || !(receivePrintJob.lines||[]).length){
      receivePrintJob = null;
      receiveStep = 1;
      return renderReceive(el);
    }
    renderStickerComposer(el, receivePrintJob);
    return;
  }

  if(!receiveShipment){
    receiveStep = 1;
    return renderReceive(el);
  }

  const ship = receiveShipment;
  const openLines = (ship.lines||[]).filter(l=>Number(l.qty_open||0)>0);
  if(!openLines.length){
    receiveShipment = null;
    receiveStep = 1;
    return renderReceive(el);
  }

  if(receiveStep === 2){
    const rows = openLines.map(ln=>{
      const remain = Number(ln.qty_open||0);
      const ft = escapeAttr(lineFilterText(ln));
      return `<tr class="recv-line" data-filter-text="${ft}"><td><code>${ln.bcode}</code></td><td>${fmtDescr(ln)}</td><td class="num">${fmtQty(ln.qty_shipped)}</td><td class="num">${fmtQty(ln.qty_received)}</td>
        <td class="num"><input class="qty-input recv-qty" type="number" min="0" max="${remain}" step="1" value="${remain}"
          data-shipment-line="${ln.shipment_line_id}"/></td></tr>`;
    }).join("");
    const cardRows = openLines.map(ln=>{
      const remain = Number(ln.qty_open||0);
      const ft = escapeAttr(lineFilterText(ln));
      return `<div class="item-card recv-line" data-filter-text="${ft}">
        <div class="item-card-head"><code>${ln.bcode}</code></div>
        <div class="item-card-desc">${fmtDescr(ln)}</div>
        <div class="item-card-grid">
          <div class="item-field num"><span class="lbl">จัด</span><span class="val">${fmtQty(ln.qty_shipped)}</span></div>
          <div class="item-field num"><span class="lbl">รับแล้ว</span><span class="val">${fmtQty(ln.qty_received)}</span></div>
        </div>
        <div class="item-card-actions">
          <label class="meta" style="margin-right:auto">รับครั้งนี้</label>
          <input class="qty-input recv-qty" type="number" min="0" max="${remain}" step="1" value="${remain}" data-shipment-line="${ln.shipment_line_id}"/>
        </div>
      </div>`;
    }).join("");
    const filterVal = escapeAttr(receiveFilter);
    el.innerHTML = `${receiveStepBar(2)}
      <div class="card">
        <p><strong>${ship.short_id}</strong> · ${dirLabel(ship.from_branch, ship.to_branch)}</p>
        <p class="meta">ใบจัด <code>${ship.ship_billno||"-"}</code> — ค้นหารหัสที่แกะกล่องแล้วกรอกจำนวนรับ (รายการที่ซ่อนยังคงจำนวนเดิม)</p>
        ${receiveBillNoteHtml(ship.from_branch, ship.to_branch, ship.ship_billno)}
        <div class="search-bar" style="margin-top:.75rem">
          <input id="recvSearch" class="text-input" type="search" autocomplete="off"
            placeholder="ค้นหาในรายการ (รหัส / รายละเอียด / รุ่น / ที่เก็บ)" value="${filterVal}"/>
        </div>
        <p id="recvFilterMeta" class="meta" style="margin:.35rem 0 0" hidden></p>
        ${dualView(
          `<div class="table-wrap table-wrap--tall" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th class="num">จัด</th><th class="num">รับแล้ว</th><th class="num">รับครั้งนี้</th></tr></thead><tbody>${rows}</tbody></table></div>`,
          itemCards(cardRows)
        )}
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setReceiveStep(1)">← เลือกคำขออื่น</button>
          <button class="btn btn-primary" id="btnRecvNext2">ถัดไป → ตรวจสอบ</button>
        </div>
      </div>`;
    bindSyncedQtyInputs(el, ".recv-qty");
    bindLineSearch(el, {
      inputId: "#recvSearch",
      rowSelector: ".recv-line",
      metaId: "#recvFilterMeta",
      total: openLines.length,
    });
    const searchEl = el.querySelector("#recvSearch");
    if(searchEl && receiveFilter){
      searchEl.focus();
      const len = searchEl.value.length;
      try{ searchEl.setSelectionRange(len, len); }catch(_e){}
    }
    el.querySelector("#btnRecvNext2").onclick = ()=>{
      const {qtyMap, any} = collectPositiveQtyMap(el, ".recv-qty", "shipmentLine");
      if(!any){alert("ระบุจำนวนที่รับ");return;}
      ship._qtyDraft = qtyMap;
      receiveFilter = "";
      setReceiveStep(3);
    };
    return;
  }

  if(receiveStep === 3){
    const qtyMap = ship._qtyDraft||{};
    const confirmRows = openLines.filter(ln=>Number(qtyMap[ln.shipment_line_id]||0)>0).map(ln=>`
      <tr><td><code>${ln.bcode}</code></td><td>${fmtDescr(ln)}</td><td class="num">${fmtQty(ln.qty_shipped)}</td><td class="num">${fmtQty(ln.qty_received)}</td><td class="num"><strong>${fmtQty(qtyMap[ln.shipment_line_id])}</strong></td></tr>
    `).join("");
    const confirmCards = openLines.filter(ln=>Number(qtyMap[ln.shipment_line_id]||0)>0).map(ln=>`<div class="item-card">
      <div class="item-card-head"><code>${ln.bcode}</code><strong class="num">${fmtQty(qtyMap[ln.shipment_line_id])}</strong></div>
      <div class="item-card-desc">${fmtDescr(ln)}</div>
      <div class="item-card-grid">
        <div class="item-field num"><span class="lbl">จัด</span><span class="val">${fmtQty(ln.qty_shipped)}</span></div>
        <div class="item-field num"><span class="lbl">รับแล้ว</span><span class="val">${fmtQty(ln.qty_received)}</span></div>
        <div class="item-field num"><span class="lbl">รับครั้งนี้</span><span class="val"><strong>${fmtQty(qtyMap[ln.shipment_line_id])}</strong></span></div>
      </div>
    </div>`).join("");
    el.innerHTML = `${receiveStepBar(3)}
      <div class="card">
        <p><strong>${ship.short_id}</strong> · ${dirLabel(ship.from_branch, ship.to_branch)}</p>
        <p class="meta">ใบจัด <code>${ship.ship_billno||"-"}</code></p>
        ${receiveBillNoteHtml(ship.from_branch, ship.to_branch, ship.ship_billno)}
        ${dualView(
          `<div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th class="num">จัด</th><th class="num">รับแล้ว</th><th class="num">รับครั้งนี้</th></tr></thead><tbody>${confirmRows}</tbody></table></div>`,
          itemCards(confirmCards)
        )}
        <label class="meta" style="display:flex;align-items:center;gap:.45rem;margin:.85rem 0 .25rem">
          <input id="chkPrintStickers" type="checkbox" class="pick-check" checked/>
          พิมพ์สติ๊กเกอร์บาร์โค้ดตามจำนวนที่รับ (1 ชิ้น = 1 ดวง)
        </label>
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setReceiveStep(2)">← แก้ไขจำนวน</button>
          <button class="btn btn-primary" id="btnConfirmReceive">ยืนยันรับเข้า (ออกใบ TF)</button>
        </div>
      </div>`;
    el.querySelector("#btnConfirmReceive").onclick = async()=>{
      try{
        const wantPrint = !!(el.querySelector("#chkPrintStickers")||{}).checked;
        const result = await submitReceive(ship, qtyMap);
        const bill = result.receive_billno || "";
        const printLines = (result.lines && result.lines.length ? result.lines : openLines
          .filter(ln=>Number(qtyMap[ln.shipment_line_id]||0)>0)
          .map(ln=>({bcode:ln.bcode, descr:ln.descr||"", qty:Number(qtyMap[ln.shipment_line_id]||0)}))
        ).filter(ln=>ln.bcode && Number(ln.qty||ln.qty_receive||0)>0)
         .map(ln=>({bcode:ln.bcode, descr:ln.descr||"", qty:Number(ln.qty||ln.qty_receive||0)}));
        showToast(bill ? ("รับสินค้าแล้ว — ออกใบ "+bill) : "รับสินค้าแล้ว");
        receiveShipment = null;
        if(wantPrint && printLines.length){
          openStickerPrint({bill, shortId: ship.short_id, lines: printLines, returnView:"receive"});
          return;
        }
        receiveStep = 1;
        render();
      }catch(e){ if(e.message!=="ยกเลิก") alert(e.message); }
    };
  }
}

async function renderPrepare(el){
  const data = await api("/transfer/api/requests?role=prepare");
  const items = data.items||[];
  if(!items.length){
    el.innerHTML = `<div class="card"><div class="empty">ไม่มีรายการรอจัด<br><span class="meta">เมื่อสาขาอื่นส่งคำขอมา จะแสดงที่นี่</span></div>
      <div class="row-actions"><button class="btn btn-ghost" onclick="goHome()">กลับหน้าหลัก</button></div></div>`;
    return;
  }

  if(prepareStep === 1){
    el.innerHTML = `${prepareStepBar(1)}
      <div class="flow-hint">เลือกคำขอ → กรอกจำนวนที่จัด → ยืนยันเพื่อออก${SHIP_BILL} TF</div>
      ${billTimelineHtml(SITE, OTHER)}
      <div class="card">${dualView(
        `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>สถานะ</th><th>วันที่</th><th class="num">รายการ</th><th></th></tr></thead><tbody>
          ${items.map((r,i)=>`<tr class="row-clickable" data-prep-idx="${i}">
            <td><code>${r.short_id}</code></td>
            <td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td>
            <td>${badge(r.status,r.from_branch,r.to_branch,!!r.prep_recv_mismatch)}</td>
            <td>${(r.requested_at||r.created_at||"").slice(0,10)}</td>
            <td class="num">${r.line_count||0}</td>
            <td><button class="btn btn-primary" data-prep-open="${i}">เปิดจัดสินค้า</button></td>
          </tr>`).join("")}
        </tbody></table></div>`,
        itemCards(items.map((r,i)=>`<div class="item-card row-clickable" data-prep-idx="${i}">
          <div class="item-card-head"><code>${r.short_id}</code>${badge(r.status,r.from_branch,r.to_branch,!!r.prep_recv_mismatch)}</div>
          <div class="item-card-grid">
            <div class="item-field"><span class="lbl">ทิศทาง</span><span class="val dir">${dirLabel(r.from_branch,r.to_branch)}</span></div>
            <div class="item-field"><span class="lbl">วันที่</span><span class="val">${(r.requested_at||r.created_at||"").slice(0,10)}</span></div>
            <div class="item-field num"><span class="lbl">รายการ</span><span class="val">${r.line_count||0}</span></div>
          </div>
          <div class="item-card-actions"><button class="btn btn-primary" data-prep-open="${i}">เปิดจัดสินค้า</button></div>
        </div>`).join(""))
      )}
      <div class="row-actions"><button class="btn btn-ghost" onclick="goHome()">กลับหน้าหลัก</button></div></div>`;
    window._prepareList = items;
    el.querySelectorAll("[data-prep-open]").forEach(b=>b.onclick=e=>{
      e.stopPropagation();
      openPrepareRequest(window._prepareList[Number(b.dataset.prepOpen)]);
    });
    el.querySelectorAll(".row-clickable[data-prep-idx]").forEach(row=>{
      row.onclick = e=>{
        if(e.target.closest("button")) return;
        openPrepareRequest(window._prepareList[Number(row.dataset.prepIdx)]);
      };
    });
    return;
  }

  if(!prepareRequest){
    prepareStep = 1;
    return renderPrepare(el);
  }

  const req = prepareRequest;
  const openLines = (req.lines||[]).filter(l=>Number(l.qty_requested||0)>Number(l.qty_prepared||0));
  if(!openLines.length){
    prepareRequest = null;
    prepareStep = 1;
    return renderPrepare(el);
  }

  if(prepareStep === 2){
    const shipBranch = (req.from_branch||SITE).toUpperCase();
    const shipBranchLabel = branchLabel(shipBranch);
    const rows = openLines.map(ln=>{
      const remain = Number(ln.qty_requested||0)-Number(ln.qty_prepared||0);
      return `<tr><td><code>${ln.bcode}</code></td><td>${fmtDescr(ln)}</td><td class="num">${fmtBranchStock(ln, shipBranch)}</td><td class="num">${fmtQty(ln.qty_requested)}</td><td class="num">${fmtQty(ln.qty_prepared)}</td>
        <td class="num"><input class="qty-input prep-qty" type="number" min="0" max="${remain}" step="1" value="${remain}"
          data-line="${ln.line_id}"/></td></tr>`;
    }).join("");
    const cardRows = openLines.map(ln=>{
      const remain = Number(ln.qty_requested||0)-Number(ln.qty_prepared||0);
      return `<div class="item-card">
        <div class="item-card-head"><code>${ln.bcode}</code></div>
        <div class="item-card-desc">${fmtDescr(ln)}</div>
        <div class="item-card-grid">
          <div class="item-field num"><span class="lbl">คงเหลือ ${shipBranchLabel}</span><span class="val">${fmtBranchStock(ln, shipBranch)}</span></div>
          <div class="item-field num"><span class="lbl">ขอ</span><span class="val">${fmtQty(ln.qty_requested)}</span></div>
          <div class="item-field num"><span class="lbl">จัดแล้ว</span><span class="val">${fmtQty(ln.qty_prepared)}</span></div>
        </div>
        <div class="item-card-actions">
          <label class="meta" style="margin-right:auto">จัดครั้งนี้</label>
          <input class="qty-input prep-qty" type="number" min="0" max="${remain}" step="1" value="${remain}" data-line="${ln.line_id}"/>
        </div>
      </div>`;
    }).join("");
    el.innerHTML = `${prepareStepBar(2)}
      <div class="card">
        <p><strong>${req.short_id}</strong> · ${dirLabel(req.from_branch, req.to_branch)}</p>
        <p class="meta">ระบุจำนวนที่จัดแต่ละรายการในครั้งนี้ · คงเหลือ ${shipBranchLabel} อ่านจาก PARTS9 สด</p>
        ${prepareBillNoteHtml(req.from_branch, req.to_branch)}
        ${dualView(
          `<div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th class="num">คงเหลือ ${shipBranchLabel}</th><th class="num">ขอ</th><th class="num">จัดแล้ว</th><th class="num">จัดครั้งนี้</th></tr></thead><tbody>${rows}</tbody></table></div>`,
          itemCards(cardRows)
        )}
        ${shipBranch === "HQ" ? hqNoStockNoteHtml() : ""}
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setPrepareStep(1)">← เลือกคำขออื่น</button>
          <button class="btn btn-primary" id="btnPrepNext2">ถัดไป → ตรวจสอบ</button>
        </div>
      </div>`;
    bindSyncedQtyInputs(el, ".prep-qty");
    el.querySelector("#btnPrepNext2").onclick = ()=>{
      const {qtyMap, any} = collectPositiveQtyMap(el, ".prep-qty", "line");
      if(!any){alert("ระบุจำนวนที่จัด");return;}
      req._qtyDraft = qtyMap;
      setPrepareStep(3);
    };
    return;
  }

  if(prepareStep === 3){
    const qtyMap = req._qtyDraft||{};
    const shipBranch = (req.from_branch||SITE).toUpperCase();
    const shipBranchLabel = branchLabel(shipBranch);
    const confirmRows = openLines.filter(ln=>Number(qtyMap[ln.line_id]||0)>0).map(ln=>`
      <tr><td><code>${ln.bcode}</code></td><td>${fmtDescr(ln)}</td><td class="num">${fmtBranchStock(ln, shipBranch)}</td><td class="num">${fmtQty(ln.qty_requested)}</td><td class="num">${fmtQty(ln.qty_prepared)}</td><td class="num"><strong>${fmtQty(qtyMap[ln.line_id])}</strong></td></tr>
    `).join("");
    const confirmCards = openLines.filter(ln=>Number(qtyMap[ln.line_id]||0)>0).map(ln=>`<div class="item-card">
      <div class="item-card-head"><code>${ln.bcode}</code><strong class="num">${fmtQty(qtyMap[ln.line_id])}</strong></div>
      <div class="item-card-desc">${fmtDescr(ln)}</div>
      <div class="item-card-grid">
        <div class="item-field num"><span class="lbl">คงเหลือ ${shipBranchLabel}</span><span class="val">${fmtBranchStock(ln, shipBranch)}</span></div>
        <div class="item-field num"><span class="lbl">ขอ</span><span class="val">${fmtQty(ln.qty_requested)}</span></div>
        <div class="item-field num"><span class="lbl">จัดแล้ว</span><span class="val">${fmtQty(ln.qty_prepared)}</span></div>
        <div class="item-field num"><span class="lbl">จัดครั้งนี้</span><span class="val"><strong>${fmtQty(qtyMap[ln.line_id])}</strong></span></div>
      </div>
    </div>`).join("");
    el.innerHTML = `${prepareStepBar(3)}
      <div class="card">
        <p><strong>${req.short_id}</strong> · ${dirLabel(req.from_branch, req.to_branch)}</p>
        <p class="meta">ตรวจสอบจำนวนก่อนยืนยัน — ระบบจะออก${SHIP_BILL} TF ทันที</p>
        ${prepareBillNoteHtml(req.from_branch, req.to_branch)}
        ${dualView(
          `<div class="table-wrap" style="margin-top:.75rem"><table><thead><tr><th>รหัส</th><th>รายละเอียด</th><th class="num">คงเหลือ ${shipBranchLabel}</th><th class="num">ขอ</th><th class="num">จัดแล้ว</th><th class="num">จัดครั้งนี้</th></tr></thead><tbody>${confirmRows}</tbody></table></div>`,
          itemCards(confirmCards)
        )}
        ${shipBranch === "HQ" ? hqNoStockNoteHtml() : ""}
        <div class="row-actions">
          <button class="btn btn-ghost" onclick="setPrepareStep(2)">← แก้ไขจำนวน</button>
          <button class="btn btn-primary" id="btnConfirmPrepare">ยืนยันส่งสินค้า (ออกใบ TF)</button>
        </div>
      </div>`;
    el.querySelector("#btnConfirmPrepare").onclick = async()=>{
      try{
        const result = await submitPrepare(req, qtyMap);
        const bill = result.ship_billno || result.tf_billno || "";
        showToast(bill ? ("จัดสินค้าแล้ว — ออกใบ "+bill) : "จัดสินค้าแล้ว");
        prepareRequest = null;
        prepareStep = 1;
        render();
      }catch(e){ if(e.message!=="ยกเลิก") alert(e.message); }
    };
  }
}

async function openPrepareRequest(summary){
  const detail = await api("/transfer/api/requests/"+summary.transfer_id+"/lines");
  const lines = (detail.items || detail.lines || []).filter(l=>Number(l.qty_requested||0)>Number(l.qty_prepared||0));
  if(!lines.length){alert("ไม่มีรายการที่ต้องจัด");return;}
  prepareRequest = {
    transfer_id: summary.transfer_id,
    short_id: detail.short_id || summary.short_id,
    from_branch: detail.from_branch || summary.from_branch,
    to_branch: detail.to_branch || summary.to_branch,
    lines,
  };
  setPrepareStep(2);
}

async function renderStatus(el){
  const isDone = statusFilter === "done";
  const data = await api("/transfer/api/requests" + (isDone ? "?status=complete" : ""));
  let items = data.items||[];
  if(!isDone) items = items.filter(r=>r.status!=="complete"&&r.status!=="cancelled");
  const drafts = isDone ? [] : items.filter(r=>r.status==="draft");
  const active = isDone ? items : items.filter(r=>r.status!=="draft");
  el.innerHTML = `
    <div class="status-tabs">
      <button class="status-tab ${statusFilter==="active"?"on":""}" data-sf="active">กำลังดำเนินการ</button>
      <button class="status-tab ${statusFilter==="done"?"on":""}" data-sf="done">เสร็จสิ้น</button>
    </div>`;
  if(drafts.length){
    const draftTableRows = drafts.map(r=>`<tr class="row-clickable" data-detail="${r.transfer_id}">
      <td><code>${r.short_id}</code></td>
      <td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td>
      <td class="num">${r.line_count||0}</td>
      <td>${(r.created_at||"").slice(0,10)}</td>
      <td class="row-actions" style="margin:0">
        <button class="btn btn-ghost" data-detail-btn="${r.transfer_id}">ดู</button>
        <button class="btn btn-ghost" data-edit="${r.transfer_id}">แก้ไข</button>
        <button class="btn btn-ghost" data-del-draft="${r.transfer_id}">ลบ</button>
      </td>
    </tr>`).join("");
    const draftCardRows = drafts.map(r=>`<div class="item-card row-clickable" data-detail="${r.transfer_id}">
      <div class="item-card-head"><code>${r.short_id}</code><span class="dir">${dirLabel(r.from_branch,r.to_branch)}</span></div>
      <div class="item-card-grid">
        <div class="item-field num"><span class="lbl">รายการ</span><span class="val">${r.line_count||0}</span></div>
        <div class="item-field"><span class="lbl">วันที่</span><span class="val">${(r.created_at||"").slice(0,10)}</span></div>
      </div>
      <div class="item-card-actions">
        <button class="btn btn-ghost" data-detail-btn="${r.transfer_id}">ดู</button>
        <button class="btn btn-ghost" data-edit="${r.transfer_id}">แก้ไข</button>
        <button class="btn btn-ghost" data-del-draft="${r.transfer_id}">ลบ</button>
      </div>
    </div>`).join("");
    el.innerHTML += `<div class="card"><strong>ร่าง (${drafts.length})</strong>
      <p class="meta">ยังไม่ส่งคำขอ — แก้ไขหรือลบได้</p>
      ${dualView(
        `<div class="table-wrap" style="margin-top:.5rem"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th class="num">รายการ</th><th>วันที่</th><th></th></tr></thead><tbody>${draftTableRows}</tbody></table></div>`,
        itemCards(draftCardRows)
      )}</div>`;
  }
  if(!active.length && !drafts.length){
    el.innerHTML += `<div class="card"><div class="empty">ไม่มีรายการ</div></div>`;
  } else if(active.length){
    const activeTableRows = active.map(r=>{
      const canCancel = canCancelRequest(r.status, r.to_branch, !!r.has_shipments);
      const mm = !!r.prep_recv_mismatch;
      return `<tr class="row-clickable ${mm?"row-mismatch":""}" data-detail="${r.transfer_id}">
        <td><code>${r.short_id}</code></td><td class="dir">${dirLabel(r.from_branch,r.to_branch)}</td>
        <td>${badge(r.status,r.from_branch,r.to_branch,mm)}</td>
        <td>${pipeline(r.status,mm)}</td>
        <td>${(r.requested_at||r.created_at||"").slice(0,10)}</td>
        <td class="row-actions" style="margin:0">
          <button class="btn btn-ghost" data-detail-btn="${r.transfer_id}">ดู</button>
          <button class="btn btn-ghost" data-print="${r.transfer_id}">พิมพ์</button>
          ${r.has_received || isDone ? `<button class="btn btn-ghost" data-stickers="${r.transfer_id}">บาร์โค้ด</button>` : ""}
          ${canCancel ? `<button class="btn btn-ghost" data-cancel="${r.transfer_id}">ยกเลิก</button>` : ""}
        </td>
      </tr>`;
    }).join("");
    const activeCardRows = active.map(r=>{
      const canCancel = canCancelRequest(r.status, r.to_branch, !!r.has_shipments);
      const mm = !!r.prep_recv_mismatch;
      return `<div class="item-card row-clickable ${mm?"row-mismatch":""}" data-detail="${r.transfer_id}">
        <div class="item-card-head"><code>${r.short_id}</code>${badge(r.status,r.from_branch,r.to_branch,mm)}</div>
        <div class="item-card-grid">
          <div class="item-field"><span class="lbl">ทิศทาง</span><span class="val dir">${dirLabel(r.from_branch,r.to_branch)}</span></div>
          <div class="item-field"><span class="lbl">วันที่</span><span class="val">${(r.requested_at||r.created_at||"").slice(0,10)}</span></div>
        </div>
        ${pipeline(r.status,mm)}
        <div class="item-card-actions">
          <button class="btn btn-ghost" data-detail-btn="${r.transfer_id}">ดู</button>
          <button class="btn btn-ghost" data-print="${r.transfer_id}">พิมพ์</button>
          ${r.has_received || isDone ? `<button class="btn btn-ghost" data-stickers="${r.transfer_id}">บาร์โค้ด</button>` : ""}
          ${canCancel ? `<button class="btn btn-ghost" data-cancel="${r.transfer_id}">ยกเลิก</button>` : ""}
        </div>
      </div>`;
    }).join("");
    el.innerHTML += `<div class="card">${dualView(
      `<div class="table-wrap"><table><thead><tr><th>เลขที่</th><th>ทิศทาง</th><th>สถานะ</th><th>ความคืบหน้า</th><th>วันที่</th><th></th></tr></thead><tbody>${activeTableRows}</tbody></table></div>`,
      itemCards(activeCardRows)
    )}</div>`;
  }
  el.querySelectorAll("[data-sf]").forEach(b=>b.onclick=()=>{statusFilter=b.dataset.sf; renderStatus(el);});
  el.querySelectorAll("[data-detail-btn]").forEach(b=>b.onclick=e=>{e.stopPropagation(); openRequestDetail(b.dataset.detailBtn);});
  bindDetailRows(el);
  el.querySelectorAll("[data-edit]").forEach(b=>b.onclick=()=>editDraft(b.dataset.edit));
  el.querySelectorAll("[data-del-draft]").forEach(b=>b.onclick=()=>deleteDraft(b.dataset.delDraft));
  el.querySelectorAll("[data-cancel]").forEach(b=>b.onclick=e=>{e.stopPropagation(); cancelRequest(b.dataset.cancel);});
  el.querySelectorAll("[data-print]").forEach(b=>b.onclick=async e=>{
    e.stopPropagation();
    try{
      const detail = await api("/transfer/api/requests/"+b.dataset.print+"/lines");
      printRequestBill(detail);
    }catch(err){ alert(err.message||"พิมพ์ไม่สำเร็จ"); }
  });
  el.querySelectorAll("[data-stickers]").forEach(b=>b.onclick=async e=>{
    e.stopPropagation();
    try{ await openStickerPrintFromTransfer(b.dataset.stickers, {selectAll:false}); }
    catch(err){ alert(err.message||"เปิดพิมพ์บาร์โค้ดไม่สำเร็จ"); }
  });
}

async function render(){
  updateHeader();
  const el = $("content");
  try{
    if(view==="home") await renderHome(el);
    else if(view==="request") await renderRequest(el);
    else if(view==="prepare") await renderPrepare(el);
    else if(view==="receive") await renderReceive(el);
    else if(view==="status") await renderStatus(el);
    else if(view==="stickers"){
      if(!receivePrintJob || !(receivePrintJob.lines||[]).length){
        view = stickerReturnView || "status";
        receivePrintJob = null;
        return render();
      }
      renderStickerComposer(el, receivePrintJob);
    }
  }catch(e){el.innerHTML='<div class="card empty">'+String(e.message||e)+'</div>';}
}

$("btnBack").onclick = ()=> view==="stickers" ? leaveStickerPrint() : goHome();
render();
</script>
</body>
</html>"""

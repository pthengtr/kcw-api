from __future__ import annotations

import html as html_lib
import json
import re

from src.receive_notes.company_banks import (
    DEFAULT_RECEIVE_BANK_KEY,
    list_company_receive_accounts,
)
from src.receive_notes.writer import RVI_ACCTNOS

APP = "receive-notes"
SESSION_COOKIE = "kcw_receive_notes"


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
    write_enabled: bool = False,
    ai_enabled: bool = False,
) -> str:
    who = (user_name or "operator").strip()
    site_u = (site or "HQ").upper()
    write_flag = "true" if write_enabled else "false"
    ai_flag = "false"  # AR receive-notes: no AI scan
    company_recv = list_company_receive_accounts()
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace("__WRITE__", write_flag)
        .replace("__AI__", ai_flag)
        .replace("__INITIALS__", html_lib.escape(initials(who)))
        .replace("__COMPANY_PAY_JSON__", json.dumps(company_recv, ensure_ascii=False))
        .replace("__DEFAULT_PAY_BANK__", json.dumps(DEFAULT_RECEIVE_BANK_KEY))
        .replace("__RVI_ACCTNOS_JSON__", json.dumps(sorted(RVI_ACCTNOS)))
    )


_HTML = r"""<!doctype html>
<html lang="th" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light dark"/>
<meta name="theme-color" content="#f3f5f9" id="themeColor"/>
<title>รับชำระลูกหนี้</title>
<script>
(function () {
  try {
    var t = localStorage.getItem("kcw.receive_notes.theme");
    if (t !== "light" && t !== "dark") t = "light";
    document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
</script>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root {
  /* AR (รับชำระลูกหนี้) brand accent — Header / Active Tab / primary buttons */
  --acc:#247B74; --acc-soft:#e5f2f1; --on-acc:#fff;
  --ok:#15803d; --ok-bg:#dcfce7;
  --warn:#c2410c; --warn-bg:#ffedd5;
  --down:#dc2626; --down-bg:#fee2e2;
  --soon:#15803d; --soon-bg:#dcfce7;
  --proof:#a16207; --proof-bg:#fef3c7;
  --shadow:0 1px 2px rgba(16,24,40,.06), 0 4px 12px rgba(16,24,40,.04);
  --space-page-x:1.15rem;
  --space-page-b:2.5rem;
  --space-card:1rem;
  --space-stack:.85rem;
}
html[data-theme="dark"] {
  color-scheme: dark;
  --bg:#0c1014; --card:#161d26; --line:#2a3542; --text:#e8eef4; --muted:#8b9aab;
  --chip:#243040; --inset:#0a0e12; --acc-soft:#1a3331;
  --ok-bg:#163024; --warn-bg:#3a2718; --down-bg:#3a1c1c; --soon-bg:#163024; --proof-bg:#3a3018;
  --shadow:none; --head:#0c1014;
}
html[data-theme="light"] {
  color-scheme: light;
  --bg:#f3f5f9; --card:#ffffff; --line:#e6eaf0; --text:#1b2430; --muted:#6b7c8f;
  --chip:#f3f5f8; --inset:#f7f9fc; --head:#ffffff;
}
* { box-sizing:border-box; }
body { margin:0; font-family:Prompt,sans-serif; background:var(--bg); color:var(--text); }
button, input, select, textarea { font:inherit; }
button { cursor:pointer; }
a { color:var(--acc); }
.hidden { display:none !important; }
header {
  position:sticky; top:0; z-index:5; background:var(--head);
  border-bottom:2px solid var(--acc); padding:.85rem var(--space-page-x) 0;
}
.topbar { display:flex; align-items:center; justify-content:space-between; gap:.75rem; }
h1 { margin:0; font-size:1.2rem; font-weight:700; letter-spacing:-.01em; color:var(--acc); }
.crumb { font-size:.78rem; color:var(--muted); margin-top:.15rem; }
.avatar {
  width:2.15rem; height:2.15rem; border-radius:50%; border:0;
  background:var(--acc-soft); color:var(--acc); font-weight:700; font-size:.78rem;
  flex:0 0 auto;
}
html[data-theme="dark"] .avatar { background:var(--acc-soft); color:#7dbdb6; }
.tabs {
  display:flex; gap:.5rem; margin-top:.7rem; width:100%;
  overflow-x:visible; scroll-snap-type:none;
}
.tabs::-webkit-scrollbar { display:none; }
.tabs button {
  appearance:none; background:none; border:0; border-bottom:2px solid transparent;
  color:var(--muted); padding:.45rem .5rem .7rem; font-weight:500; font-size:.95rem;
  flex:1 1 0; min-width:0; text-align:center; white-space:normal; line-height:1.25;
  display:flex; align-items:center; justify-content:center;
}
.tabs .t-short { display:none; }
.tabs button.on { color:var(--acc); font-weight:600; border-bottom-color:var(--acc); }
main { max-width:1120px; margin:0 auto; padding:var(--space-page-y) var(--space-page-x) var(--space-page-b); }
.panel { display:none; }
.panel.on { display:block; }
.panel-intro { margin:0 0 var(--space-stack); font-size:.82rem; color:var(--muted); line-height:1.4; }
.card {
  background:var(--card); border:1px solid var(--line); border-radius:.85rem;
  box-shadow:var(--shadow); padding:var(--space-card);
}
.card + .card, .kpis + .card, .card + .kpis { margin-top:var(--space-stack); }
.card-table { padding:0; overflow:hidden; }
.card-table .table-wrap th:first-child,
.card-table .table-wrap td:first-child { padding-left:var(--space-card); }
.card-table .table-wrap th:last-child,
.card-table .table-wrap td:last-child { padding-right:var(--space-card); }
.card-table .empty { padding:1.25rem var(--space-card); }
.toolbar { display:flex; gap:.55rem; flex-wrap:wrap; align-items:center; }
.grow { flex:1 1 16rem; min-width:12rem; }
.field {
  position:relative; display:flex; align-items:center; gap:.35rem;
  background:var(--card); border:1px solid var(--line); border-radius:.65rem;
  padding:.15rem .7rem; min-height:2.55rem; color:var(--muted);
}
.field input, .field select {
  border:0; background:transparent; color:var(--text); width:100%;
  padding:.4rem .15rem; outline:none; min-width:0;
}
.field .ico { flex:0 0 auto; display:flex; opacity:.7; }
.btn {
  display:inline-flex; align-items:center; justify-content:center; gap:.4rem;
  border:1px solid var(--line); background:var(--card); color:var(--text);
  border-radius:.65rem; padding:.5rem .9rem; min-height:2.55rem; font-weight:500;
  width:auto; white-space:nowrap;
}
.btn.primary { background:var(--acc); border-color:var(--acc); color:var(--on-acc); font-weight:600; }
.btn.ghost { background:var(--chip); }
.btn.soft { background:var(--acc-soft); border-color:transparent; color:var(--acc); }
.btn.sm { min-height:2.05rem; padding:.3rem .7rem; font-size:.82rem; border-radius:.5rem; }
.btn.outline { color:var(--acc); border-color:#9bc4c0; background:var(--card); }
.btn.danger {
  color:var(--down); border-color:#fecaca; background:var(--card);
}
.btn.danger:hover { background:var(--down-bg); }
.btn.block { width:100%; }
/* Gray only for disabled / secondary — clear clickable vs not */
.btn:disabled, .btn[disabled],
.pager button:disabled, .pager button[disabled] {
  background:var(--chip) !important; border-color:var(--line) !important;
  color:var(--muted) !important; cursor:not-allowed; opacity:1;
}
.edit-actions {
  display:flex; gap:.55rem; flex-wrap:wrap; margin-top:.85rem;
}
.edit-actions .btn { flex:1 1 10rem; }
.create-actions { margin-top:.85rem; }
.kpis { display:grid; gap:.65rem; grid-template-columns:repeat(4, 1fr); margin:.85rem 0; }
.kpi {
  display:flex; gap:.7rem; align-items:flex-start; text-align:left;
  border:1px solid var(--line); border-radius:.85rem; padding:.85rem .9rem;
  background:var(--card); box-shadow:var(--shadow); width:100%;
}
.kpi.on { outline:2px solid var(--acc); }
.kpi .mark {
  width:2.1rem; height:2.1rem; border-radius:.65rem; display:flex; align-items:center; justify-content:center; flex:0 0 auto;
}
.kpi b { display:block; font-size:.9rem; font-weight:600; }
.kpi span { display:block; font-size:.75rem; color:var(--muted); margin-top:.15rem; }
.kpi-all { background:var(--acc-soft); border-color:transparent; }
.kpi-all .mark { background:var(--acc-soft); color:var(--acc); }
.kpi-overdue { background:var(--down-bg); border-color:transparent; }
.kpi-overdue .mark { background:#fecaca; color:var(--down); }
.kpi-today { background:var(--warn-bg); border-color:transparent; }
.kpi-today .mark { background:#fed7aa; color:var(--warn); }
.kpi-soon { background:var(--soon-bg); border-color:transparent; }
.kpi-soon .mark { background:#bbf7d0; color:var(--soon); }
.table-wrap { overflow:auto; -webkit-overflow-scrolling:touch; }
.mob-cards { --card-pad:.65rem; }
table { width:100%; border-collapse:collapse; min-width:40rem; }
th, td { padding:.85rem .75rem; text-align:left; border-bottom:1px solid var(--line); font-size:.9rem; }
th { font-size:.75rem; color:var(--muted); font-weight:600; letter-spacing:.02em; }
td.num, th.num { text-align:right; font-variant-numeric:tabular-nums; }
.linkish {
  background:none; border:0; color:var(--acc); font-weight:600; padding:0; width:auto;
}
.badge {
  display:inline-flex; align-items:center; justify-content:center;
  border-radius:999px; padding:.18rem .65rem; font-size:.75rem; font-weight:600; white-space:nowrap;
}
.b-pending { background:var(--warn-bg); color:var(--warn); }
.b-overdue { background:var(--down-bg); color:var(--down); }
.b-paid { background:var(--ok-bg); color:var(--ok); }
.b-today { background:var(--warn-bg); color:var(--warn); }
.b-soon { background:var(--soon-bg); color:var(--soon); }
.b-wait { background:var(--proof-bg); color:var(--proof); }
.b-done { background:var(--ok-bg); color:var(--ok); }
.b-cheque { background:var(--soon-bg); color:var(--soon); }
.b-transfer { background:var(--chip); color:var(--muted); }
.note-reuse-badge {
  display:inline-flex; align-items:center; margin-left:.35rem;
  border-radius:999px; padding:.12rem .5rem; font-size:.68rem; font-weight:700;
  background:#fff3e0; color:#b45309; border:1px solid #f5c78a; vertical-align:middle;
}
.note-reuse-hint {
  margin:.65rem 0 0; padding:.55rem .7rem; border-radius:.55rem;
  background:#fff8eb; border:1px solid #f0d88a; color:#8a5a00; font-size:.84rem; line-height:1.45;
}
.note-kss-id { font-size:.78rem; color:var(--muted); margin-top:.2rem; }
.table-foot {
  display:flex; justify-content:space-between; align-items:center; gap:.75rem 1rem; flex-wrap:wrap;
  padding:.7rem var(--space-card) .8rem; font-size:.8rem; color:var(--muted);
  border-top:1px solid var(--line); min-height:2.75rem;
}
.table-foot-meta {
  flex:1 1 12rem; min-width:0; display:flex; align-items:center; gap:.65rem;
  flex-wrap:wrap; line-height:1.35;
}
.table-foot-nav {
  flex:0 0 auto; display:flex; align-items:center; gap:.55rem;
  flex-wrap:wrap; margin-left:auto;
}
.page-size {
  display:inline-flex; align-items:center; gap:.35rem;
  font-size:inherit; color:var(--muted); white-space:nowrap; margin:0;
}
.page-size-select { width:auto; padding:.25rem .4rem; min-height:2rem; }
.pager { display:flex; gap:.3rem; align-items:center; }
.pager button {
  min-width:2rem; height:2rem; padding:0 .45rem; border-radius:.45rem;
  border:1px solid var(--line); background:var(--card); color:var(--text);
}
.pager button.on { border-color:var(--acc); color:var(--acc); font-weight:700; }
.hint {
  display:flex; align-items:center; gap:.4rem; font-size:.8rem; color:var(--muted);
  margin:0; line-height:1.35;
}
.empty { text-align:center; color:var(--muted); padding:1.6rem .8rem; }
.err { color:var(--down); font-size:.85rem; margin:.35rem 0; }
.ok { color:var(--ok); font-size:.85rem; }
.tiger-voucher-box {
  margin:.65rem 0 .35rem; padding:.75rem; border:1px solid var(--line);
  border-radius:10px; background:var(--inset); text-align:center;
}
.tiger-voucher-box img {
  width:min(220px, 70vw); height:auto; display:block; margin:.45rem auto 0;
  background:#fff; border-radius:8px;
}
.tiger-voucher-code {
  font-weight:700; letter-spacing:.04em; font-size:1.05rem; margin:.25rem 0 0;
}
.row-actions { display:flex; gap:.4rem; justify-content:flex-end; flex-wrap:wrap; }
.step { display:flex; gap:.85rem; margin:0 0 1.15rem; }
.step-num {
  width:1.7rem; height:1.7rem; border-radius:50%; background:var(--acc); color:#fff;
  display:flex; align-items:center; justify-content:center; font-weight:700; font-size:.85rem; flex:0 0 auto; margin-top:.1rem;
}
.step-body { flex:1; min-width:0; }
.step h3 { margin:0 0 .55rem; font-size:.98rem; }
.step h3 .sub { font-weight:400; color:var(--muted); font-size:.82rem; }
.grid-3 { display:grid; grid-template-columns:repeat(3, 1fr); gap:.65rem; }
.bank-editor { margin-top:.45rem; }
.bank-actions { display:flex; flex-wrap:wrap; gap:.4rem; margin-top:.4rem; }
.bank-form { margin-top:.5rem; padding:.65rem; border:1px solid var(--line); border-radius:10px; background:var(--card); }
.bank-form h4 { margin:0 0 .45rem; font-size:.88rem; }
.grid-2 { display:grid; grid-template-columns:1fr 1fr; gap:.65rem; }
label.lbl { display:block; font-size:.78rem; color:var(--muted); margin:0 0 .25rem; }
.inp, .area {
  width:100%; border:1px solid var(--line); background:var(--inset); color:var(--text);
  border-radius:.55rem; padding:.5rem .65rem; outline:none;
}
.area { min-height:4rem; resize:vertical; }
.combo { position:relative; }
.combo-list {
  position:absolute; left:0; right:0; top:calc(100% + 4px); z-index:6;
  background:var(--card); border:1px solid var(--line); border-radius:.55rem;
  box-shadow:var(--shadow); max-height:16rem; overflow:auto;
}
.combo-list button {
  display:block; width:100%; text-align:left; border:0; background:none;
  padding:.55rem .75rem; color:var(--text);
}
.combo-list button:hover { background:var(--acc-soft); }
.picked {
  margin-top:.45rem; display:inline-flex; align-items:center; gap:.4rem;
  background:var(--acc-soft); color:var(--acc); border-radius:999px; padding:.2rem .7rem; font-size:.82rem; font-weight:600;
}
.bill-head, .bill-foot {
  display:flex; justify-content:space-between; align-items:center; gap:.5rem; flex-wrap:wrap;
  font-size:.82rem; color:var(--muted); margin-bottom:.4rem;
}
.bill-foot { margin:0; padding:.55rem .75rem; background:var(--chip); border-radius:0 0 .55rem .55rem; }
.seg { display:inline-flex; background:var(--chip); border-radius:.5rem; padding:.15rem; gap:.15rem; }
.seg button {
  border:0; background:transparent; color:var(--muted); border-radius:.4rem;
  padding:.35rem .7rem; width:auto; font-weight:500;
}
.seg button.on { background:var(--acc); color:#fff; font-weight:600; }
.disc-layout { display:grid; grid-template-columns:1.1fr .9fr; gap:1rem; align-items:start; }
.disc-sum {
  background:var(--inset); border-radius:.65rem; padding:.7rem .85rem;
}
.pay-line { display:flex; justify-content:space-between; gap:.5rem; margin:.2rem 0; font-size:.9rem; }
.pay-net { margin-top:.35rem; padding-top:.4rem; border-top:1px solid var(--line); font-weight:700; }
.drop {
  border:1.5px dashed var(--line); border-radius:.75rem; padding:1.4rem 1rem; text-align:center;
  background:var(--inset); color:var(--muted); cursor:pointer;
}
.drop.drag { border-color:var(--acc); background:var(--acc-soft); color:var(--acc); }
/* Full-size overlay input: mobile browsers ignore programmatic click() on display:none file inputs */
.drop-wrap { position:relative; }
.drop-file-input {
  position:absolute; inset:0; z-index:1; width:100%; height:100%; margin:0; padding:0;
  opacity:0; cursor:pointer; border:0; border-radius:inherit; font-size:0;
}
.thumbs { display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.5rem; }
.thumbs img { width:72px; height:72px; object-fit:cover; border-radius:.4rem; border:1px solid var(--line); }
.thumb-item { position:relative; display:inline-flex; }
.thumb-item .thumb-del {
  position:absolute; top:-.3rem; right:-.3rem; width:1.35rem; height:1.35rem; padding:0;
  border-radius:999px; border:1px solid var(--line); background:var(--card); color:var(--down, #b91c1c);
  font-size:.7rem; line-height:1; cursor:pointer; display:inline-flex; align-items:center; justify-content:center;
}
.thumb-item .thumb-del:disabled { opacity:.35; cursor:not-allowed; color:var(--muted); }
.file-chip {
  display:inline-flex; align-items:center; gap:.3rem; padding:.35rem .55rem;
  border:1px solid var(--line); border-radius:.45rem; font-size:.78rem; background:var(--card);
}
.create-head { display:flex; justify-content:space-between; align-items:flex-start; gap:.75rem; margin-bottom:1rem; }
.create-head h2 { margin:.1rem 0 0; font-size:1.15rem; }
.create-mode { display:inline-flex; background:var(--chip); border-radius:.55rem; padding:.15rem; gap:.15rem; margin-bottom:.75rem; }
.create-mode button {
  border:0; background:transparent; color:var(--muted); border-radius:.4rem;
  padding:.4rem .85rem; width:auto; font-weight:500; font-size:.82rem;
}
.create-mode button.on { background:var(--acc); color:#fff; font-weight:600; }
.wizard-nav {
  display:flex; justify-content:space-between; align-items:center; gap:.5rem;
  margin-bottom:1rem; padding:.55rem .75rem; background:var(--inset); border-radius:.55rem;
}
.wizard-nav .muted { font-size:.82rem; }
.wizard-hidden { display:none !important; }
.ai-panel {
  margin:.65rem 0; padding:.65rem .75rem; border-radius:.55rem; border:1px solid var(--line);
  background:var(--inset); font-size:.84rem;
}
.ai-ok { color:var(--ok, #0a7); border-color:rgba(0,160,100,.25); background:rgba(0,160,100,.06); }
.ai-warn { color:var(--warn, #b45309); border-color:rgba(180,83,9,.25); background:rgba(180,83,9,.06); }
.ai-warn label { display:flex; align-items:flex-start; gap:.45rem; cursor:pointer; font-size:.84rem; }
.ai-line-table { width:100%; border-collapse:collapse; font-size:.8rem; margin-top:.45rem; }
.ai-line-table th, .ai-line-table td { padding:.35rem .4rem; border-bottom:1px solid var(--line); text-align:left; }
.ai-line-table .num { text-align:right; }
.dlg {
  border:0; border-radius:.9rem; background:var(--card); color:var(--text);
  padding:0; max-width:40rem; width:calc(100% - 2rem);
  max-height:min(92dvh, 46rem); overflow:auto; box-shadow:0 16px 40px rgba(16,24,40,.18);
}
#dlgDetail[open] {
  max-width:min(58rem, calc(100% - 2rem));
  max-height:min(94dvh, 54rem);
  display:flex; flex-direction:column; overflow:hidden;
}
#dlgDetail .dlg-body { overflow:auto; flex:1 1 auto; min-height:0; }
#dlgDetail .dlg-head, #dlgDetail .dlg-foot { flex:0 0 auto; }
dialog.dlg:not([open]) { display:none !important; }
.det-bills { min-width:28rem; }
.det-bills .bill-row td { font-weight:600; }
.det-sum {
  background:var(--inset); border-radius:.65rem; padding:.7rem .85rem; margin-top:.55rem;
}
#printSheet { display:none; }
.dlg::backdrop { background:rgba(15,23,42,.45); }
.dlg-head {
  display:flex; justify-content:space-between; align-items:center;
  padding:1rem 1.1rem .4rem;
}
.dlg-head h2 { margin:0; font-size:1.05rem; }
.dlg-x { border:0; background:none; color:var(--muted); font-size:1.2rem; width:auto; padding:.2rem .4rem; }
.dlg-body { padding:.4rem 1.1rem 1.1rem; }
.dlg-foot {
  display:flex; justify-content:flex-end; gap:.45rem; padding:0 1.1rem 1.1rem;
}
.sum-box {
  display:grid; grid-template-columns:1fr 1fr; gap:.35rem 1.2rem;
  background:var(--acc-soft); border-radius:.7rem; padding:.85rem .95rem; margin:.4rem 0 1rem;
  font-size:.88rem;
}
.sum-box .k { color:var(--muted); font-size:.75rem; }
.sum-box .v { margin-top:.1rem; }
#payBankLine { white-space:pre-line; }
.sum-box .net .k, .sum-box .net .v { font-weight:700; }
.sum-box .net .v { color:var(--acc); }
.methods { display:grid; grid-template-columns:repeat(3, 1fr); gap:.45rem; margin:.25rem 0 .75rem; }
.methods-2 { grid-template-columns:repeat(2, 1fr); max-width:22rem; }
.grid-3 .methods-2 { max-width:none; }
.method {
  border:1px solid var(--line); background:var(--card); border-radius:.65rem;
  padding:.65rem .4rem; color:var(--muted); display:flex; flex-direction:column; align-items:center; gap:.25rem;
}
.method.on { border-color:var(--acc); color:var(--acc); background:var(--acc-soft); font-weight:600; }
.date-hint { font-size:.72rem; color:var(--muted); margin:.1rem 0 .35rem; }
.remark {
  margin:.4rem 0 0; padding:.45rem .55rem; border-radius:.45rem;
  border:1px dashed var(--line); background:var(--inset); font-size:.88rem; white-space:pre-wrap;
}
.remark-form .remark-ap {
  display:flex; align-items:center; min-height:2.4rem; padding:.45rem .65rem;
  background:var(--inset); border:1px solid var(--line); border-radius:.45rem; font-weight:600;
}
.remark-form .remark-extra-wrap { margin-top:.45rem; }
.remark-form .remark-extra-wrap.hidden { display:none; }
.remark-preview { margin-top:.35rem; font-style:italic; }
input[type="date"] { min-height:2.4rem; cursor:pointer; }
.sec-title { display:flex; justify-content:space-between; align-items:baseline; gap:.5rem; margin-bottom:.7rem; }
.sec-title h2 { margin:0; font-size:1.05rem; }
.muted { color:var(--muted); font-size:.82rem; }
.toggle { display:flex; align-items:center; gap:.35rem; font-size:.82rem; color:var(--muted); }
@media (max-width: 834px) {
  .tabs {
    display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:.35rem;
    margin-top:.6rem; overflow-x:visible; scroll-snap-type:none;
  }
  .tabs button {
    flex:unset; min-width:0; text-align:center; white-space:normal;
    font-size:.78rem; line-height:1.2; padding:.5rem .3rem;
    border-bottom:0; border-radius:.55rem; background:var(--chip);
    min-height:2.35rem; display:flex; align-items:center; justify-content:center;
  }
  .tabs button.on {
    background:var(--acc-soft); color:var(--acc); font-weight:600;
    box-shadow:inset 0 0 0 1px rgba(47,107,255,.25);
  }
  .tabs button#tabByAp {
    grid-column:1 / -1; margin-top:.1rem; min-height:2.1rem;
    font-size:.76rem;
  }
  .tabs .t-full { display:none; }
  .tabs .t-short { display:inline; }
}
@media (min-width: 835px) and (max-width: 1399px) {
  .tabs {
    display:flex; gap:.4rem; margin-top:.6rem;
    overflow-x:visible; scroll-snap-type:none;
  }
  .tabs button {
    flex:1 1 0; min-width:0; text-align:center; white-space:normal;
    font-size:.8rem; line-height:1.2; padding:.48rem .35rem;
    border-bottom:0; border-radius:.55rem; background:var(--chip);
    min-height:2.35rem; display:flex; align-items:center; justify-content:center;
  }
  .tabs button.on {
    background:var(--acc-soft); color:var(--acc); font-weight:600;
    box-shadow:inset 0 0 0 1px rgba(47,107,255,.25);
  }
  .tabs .t-full { display:none; }
  .tabs .t-short { display:inline; }
}
@media (min-width: 1000px) and (max-width: 1399px) {
  .tabs button { font-size:.84rem; padding:.5rem .45rem; }
  .tabs .t-full { display:inline; }
  .tabs .t-short { display:none; }
}
@media (max-width: 900px) {
  :root { --space-page-x:.85rem; --space-page-y:1rem; --space-page-b:2rem; --space-card:.9rem; --space-stack:.7rem; }
  .kpis, .grid-3, .disc-layout, .sum-box { grid-template-columns:1fr 1fr; }
  header { padding:.75rem var(--space-page-x) 0; }
}
@media (max-width: 640px) {
  :root { --space-page-x:.55rem; --space-page-y:.55rem; --space-page-b:calc(1.25rem + env(safe-area-inset-bottom)); --space-card:.6rem; --space-stack:.45rem; }
  body { padding: env(safe-area-inset-top) env(safe-area-inset-right) env(safe-area-inset-bottom) env(safe-area-inset-left); }
  header {
    padding:.5rem var(--space-page-x) 0;
    padding-top:max(.5rem, env(safe-area-inset-top));
  }
  h1 { font-size:1rem; line-height:1.2; }
  #pageCrumb {
    display:-webkit-box; -webkit-line-clamp:1; -webkit-box-orient:vertical;
    overflow:hidden; line-height:1.3; max-height:1.3em; font-size:.72rem;
  }
  .tabs { gap:.25rem; margin-top:.45rem; }
  .tabs button { font-size:.72rem; padding:.42rem .2rem; min-height:2.05rem; border-radius:.5rem; }
  .tabs button#tabByAp { min-height:1.95rem; font-size:.7rem; }
  .panel-intro { margin:0 0 .35rem; font-size:.74rem; line-height:1.35; }
  .card { padding:.55rem .6rem; border-radius:.65rem; }
  .card.card-table { padding:0; }
  .card + .picked { margin:.35rem 0 var(--space-stack); }
  .card + .card, .kpis + .card, .card + .kpis { margin-top:.45rem; }
  .card.toolbar { padding:.4rem .5rem; }
  .field {
    min-height:2rem; padding:0 .45rem; border-radius:.5rem; gap:.25rem;
  }
  .field input, .field select {
    padding:.2rem .1rem; font-size:.84rem; line-height:1.25;
  }
  .field .ico svg { width:14px; height:14px; }
  .inp, .area, select.inp {
    padding:.32rem .5rem; font-size:.84rem; line-height:1.25;
    min-height:2rem; border-radius:.5rem;
  }
  .area { min-height:2.6rem; }
  input[type="date"] { min-height:2rem; }
  label.lbl { font-size:.72rem; margin:0 0 .12rem; }
  .toolbar {
    flex-direction:row; flex-wrap:wrap; align-items:center; gap:.35rem;
  }
  .toolbar .field.grow, .toolbar .combo.grow {
    flex:1 1 100%; width:100%; min-width:0;
  }
  .toolbar .field:not(.grow) {
    flex:1 1 7.5rem; width:auto; min-width:0;
  }
  .toolbar .btn {
    flex:0 0 auto; width:auto; min-height:2rem;
    padding:.28rem .55rem; font-size:.76rem; justify-content:center;
  }
  .toolbar .field[style*="min-width"] {
    min-width:0 !important; width:auto; flex:1 1 7.5rem;
  }
  .toolbar .field:not(.grow) input[type="date"],
  .toolbar .field:not(.grow) select {
    flex:1 1 5.5rem; min-width:0;
  }
  .combo-list button { padding:.4rem .55rem; font-size:.84rem; }
  .step { gap:.4rem; margin:0 0 .65rem; }
  .step-num { width:1.45rem; height:1.45rem; font-size:.78rem; margin-top:.05rem; }
  .step h3 { margin:0 0 .3rem; font-size:.9rem; }
  .step h3 .sub { font-size:.76rem; }
  .create-head { margin-bottom:.45rem; gap:.45rem; }
  .create-head h2 { font-size:1rem; }
  .grid-3, .grid-2, .disc-layout, .sum-box, .methods { grid-template-columns:1fr; gap:.4rem; }
  .methods.methods-2 { grid-template-columns:1fr 1fr; max-width:none; }
  .kpis { grid-template-columns:1fr 1fr; gap:.35rem; margin:.4rem 0; }
  .kpi { padding:.4rem .5rem; gap:.4rem; border-radius:.6rem; }
  .kpi .mark { width:1.55rem; height:1.55rem; border-radius:.45rem; font-size:.72rem; }
  .kpi b { font-size:.78rem; }
  .kpi span { font-size:.66rem; margin-top:.08rem; }
  .btn { min-height:2.25rem; padding:.38rem .7rem; font-size:.84rem; }
  .btn.sm { min-height:2rem; padding:.28rem .55rem; font-size:.78rem; }
  .btn.block, .row-actions .btn, .dlg-foot .btn { min-height:2.45rem; }
  .row-actions { flex-direction:column; align-items:stretch; width:100%; }
  .row-actions .btn { width:100%; justify-content:center; }
  .create-head { flex-direction:column; }
  .create-head .btn { align-self:flex-start; }
  .seg { display:flex; width:100%; }
  .seg button { flex:1; padding:.35rem .3rem; font-size:.74rem; min-height:2rem; }
  .bill-head, .bill-foot { flex-direction:column; align-items:flex-start; gap:.25rem; margin-bottom:.3rem; }
  .bill-foot { padding:.4rem .55rem; }
  .date-hint { font-size:.68rem; margin:.05rem 0 .2rem; }
  .drop { padding:.75rem .55rem; border-radius:.6rem; }
  .drop > div:first-child { font-size:1.1rem !important; margin-bottom:.1rem !important; }
  .picked { margin-top:.3rem; padding:.15rem .55rem; font-size:.76rem; }
  .table-foot { flex-direction:column; align-items:stretch; gap:.5rem; padding:.5rem var(--space-card) .65rem; font-size:.74rem; min-height:0; }
  .table-foot-meta { flex:unset; justify-content:center; text-align:center; }
  .table-foot-nav { margin-left:0; justify-content:center; }
  .pager { justify-content:center; flex-wrap:wrap; }
  .pager button { min-width:2.1rem; height:2.1rem; }
  .dlg {
    width:100%; max-width:none; margin:0;
    max-height:100dvh; border-radius:1rem 1rem 0 0;
    align-self:flex-end;
  }
  .dlg-foot { flex-direction:column-reverse; }
  .dlg-foot .btn { width:100%; justify-content:center; }
  .sec-title { flex-direction:column; align-items:flex-start; gap:.2rem; margin-bottom:.45rem; }
  .sec-title h2 { font-size:.95rem; }
  .sec-title .toolbar { width:100%; }
  .mob-cards table { min-width:0; }
  .mob-cards thead { display:none; }
  .mob-cards tbody tr {
    display:block; border:1px solid var(--line); border-radius:.65rem;
    margin-bottom:.5rem; padding:var(--card-pad) .6rem; background:var(--inset);
    box-shadow:var(--shadow);
  }
  .mob-cards tbody tr:last-child { margin-bottom:0; }
  .mob-cards tbody td {
    display:flex; justify-content:space-between; align-items:flex-start;
    gap:.55rem; padding:.3rem 0; border:0; font-size:.84rem;
  }
  .mob-cards tbody td::before {
    content:attr(data-label); color:var(--muted); font-size:.7rem;
    font-weight:600; flex:0 0 38%; line-height:1.3;
  }
  .mob-cards tbody td[data-label=""]::before,
  .mob-cards tbody td.td-actions::before { display:none; }
  .mob-cards tbody td.td-actions {
    display:block; padding-top:.4rem; margin-top:.25rem;
    border-top:1px solid var(--line);
  }
  .mob-cards tbody td.num { text-align:right; }
  .mob-cards tbody td.num .linkish { margin-left:auto; }
  .mob-cards tbody td:has(input[type=checkbox]) {
    justify-content:flex-start; align-items:center; gap:.5rem;
  }
  .mob-cards tbody td:has(input[type=checkbox])::before {
    content:'เลือก'; display:block;
  }
  .mob-cards .empty, .mob-cards .err { display:block; padding:.75rem; }
  dialog.dlg { margin:auto 0 0; }
}
@media (max-width: 380px) {
  .kpis { grid-template-columns:1fr; }
  .tabs button { font-size:.68rem; }
}
@media print {
  /* margin:0 reduces browser print header/footer chrome; sheet pads itself */
  @page { size: A4 portrait; margin: 0; }
  html, body { background:#fff !important; margin:0 !important; }
  body > *:not(#printSheet) { display:none !important; }
  #printSheet {
    display:block !important; position:static; width:100%;
    color:#111; background:#fff; font-family: Prompt, "Noto Sans Thai", "TH Sarabun New", sans-serif;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
  .pv { max-width:none; margin:0; padding:12mm 12mm 10mm; box-sizing:border-box; }
}
.pv { font-family: Prompt, "Noto Sans Thai", sans-serif; font-size:11pt; color:#111; background:#fff;
  padding:18px 16px 22px; max-width:860px; margin:0 auto; position:relative; line-height:1.45; }
.pv-top { display:flex; justify-content:space-between; align-items:flex-start; gap:16px; }
.pv-brand { min-width:0; flex:1; }
.pv-logo {
  font-weight:800; font-size:34px; color:#9b1c2c; letter-spacing:-.03em; line-height:.9;
}
.pv-co-name { font-weight:700; font-size:15px; margin-top:2px; }
.pv-co-addr { font-size:12px; line-height:1.45; }
.pv-doc { text-align:right; flex:0 0 auto; }
.pv-title {
  margin:0; color:#9b1c2c; font-size:17px; line-height:1.25; font-weight:800; white-space:nowrap;
}
.pv-rule { height:3px; background:#9b1c2c; margin:8px 0 12px; }
.pv-boxes { display:grid; grid-template-columns:1.2fr .8fr; gap:10px 12px; align-items:start; margin-bottom:.55rem; }
.pv-box { border:1px solid #d0d5dd; border-radius:8px; padding:8px 10px; min-height:7rem; font-size:13px; }
.pv-fields { display:grid; grid-template-columns:max-content minmax(0,1fr); column-gap:12px; row-gap:4px; align-items:baseline; }
.pv-k { color:#344054; font-weight:650; white-space:nowrap; }
.pv-name { font-weight:800; }
.pv-pre { white-space:pre-line; }
.pv-docno { font-weight:800; }
.pv-table { width:100%; border-collapse:collapse; margin-top:.15rem; font-size:10pt; }
.pv-table th, .pv-table td { border-bottom:1px solid #eadfe3; padding:.28rem .4rem; vertical-align:top; }
.pv-table th { font-weight:700; text-align:left; background:#7a1f33; color:#fff; font-size:9.5pt; }
.pv-table .num { text-align:right; font-variant-numeric:tabular-nums; }
.pv-foot { display:flex; justify-content:space-between; gap:1rem; margin-top:.55rem; align-items:flex-start; }
.pv-words { flex:1; font-size:10.5pt; padding-top:.35rem; }
.pv-tot { min-width:16rem; font-size:11pt; }
.pv-tot .row { display:flex; justify-content:space-between; gap:1rem; padding:.12rem 0; }
.pv-tot .n { font-variant-numeric:tabular-nums; }
.pv-tot .pv-net { font-weight:800; background:#f2f4f7; margin-top:.12rem; padding:.28rem .35rem; }
.pv-tot .pv-net .n { color:#9b1c2c; }
.pv-pay { margin-top:.7rem; display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
.pv-checks { font-size:11pt; }
.pv-bank-hint { margin-top:.55rem; font-size:11pt; border:1px dashed #d0d5dd; border-radius:8px; padding:.45rem .6rem; }
.pv-amt-red { color:#9b1c2c; font-weight:800; font-size:13pt; font-variant-numeric:tabular-nums; }
.pv-paytbl { border-collapse:collapse; font-size:10pt; min-width:22rem; }
.pv-paytbl th, .pv-paytbl td { border:1px solid #d0d5dd; padding:.2rem .4rem; vertical-align:top; }
.pv-paytbl td.pv-bank { white-space:pre-line; }
.pv-sign { display:flex; justify-content:space-between; margin-top:1.6rem; font-size:10.5pt; }
.pv-sign .col { width:48%; }
.pv-sign .line { border-bottom:1px dotted #333; min-height:1.6rem; margin:.15rem 0 .35rem; }
.pv-void {
  position:absolute; inset:30% 8% auto; text-align:center; font-size:64px;
  color:rgba(180,35,24,.28); font-weight:800; transform:rotate(-12deg); pointer-events:none;
}
.badge.b-canceled { background:#fee2e2; color:#b91c1c; border:1px solid #fecaca; font-weight:700; }
</style>
</head>
<body>
<header>
  <div class="topbar">
    <div>
      <h1 id="pageTitle">รับชำระลูกหนี้ · __SITE__</h1>
      <div class="crumb" id="pageCrumb">__USER__ · HQ only</div>
    </div>
    <button type="button" class="avatar" id="themeBtn" title="สลับธีม" aria-label="สลับธีม">__INITIALS__</button>
  </div>
  <nav class="tabs" aria-label="ขั้นตอนงาน">
    <button type="button" id="tabCreate" class="on"><span class="t-full">1. สร้าง</span><span class="t-short">1. สร้าง</span></button>
    <button type="button" id="tabPending"><span class="t-full">2. รอรับชำระ</span><span class="t-short">2. รอรับ</span></button>
    <button type="button" id="tabAwaitProof"><span class="t-full">3. รอแนบหลักฐาน</span><span class="t-short">3. หลักฐาน</span></button>
    <button type="button" id="tabVoucher"><span class="t-full">4. ใบเสร็จรับเงิน</span><span class="t-short">4. ใบเสร็จ</span></button>
    <button type="button" id="tabByAp"><span class="t-full">ค้นหาตามลูกหนี้</span><span class="t-short">ค้นหาลูกหนี้</span></button>
  </nav>
</header>
<main>
  <section id="panelCreate" class="panel on">
    <div class="card">
      <div class="create-head">
        <div>
          <div class="crumb muted">ขั้นที่ 1 · สร้างใบวางบิล</div>
          <h2>สร้างใบวางบิล · __SITE__</h2>
        </div>
      </div>

        <div class="step" id="wizardStepVendor">
          <div class="step-num">1</div>
          <div class="step-body">
            <h3>เลือกลูกหนี้</h3>
            <div class="combo">
              <div class="field">
                <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
                <input id="vendorQ" placeholder="ค้นหา รหัส / ชื่อลูกหนี้" autocomplete="off"/>
              </div>
              <div id="vendorResults" class="combo-list hidden"></div>
            </div>
            <div id="pickedVendor" class="picked hidden"></div>
          </div>
        </div>

        <div class="step" id="wizardStepBills">
          <div class="step-num">2</div>
          <div class="step-body">
            <div class="bill-head">
              <h3 style="margin:0">เลือกบิล <span class="sub">(เลือกได้มากกว่า 1 บิล)</span></h3>
              <div class="toggle">
                <input type="checkbox" checked disabled/>
                แสดงบิลที่ยังไม่ถูกวางบิลเท่านั้น
                <button type="button" class="linkish" id="btnRefreshBills">รีเฟรช</button>
              </div>
            </div>
            <div class="table-wrap mob-cards" style="border:1px solid var(--line); border-radius:.55rem .55rem 0 0">
              <table>
                <thead>
                  <tr>
                    <th style="width:2.4rem"></th>
                    <th>เลขที่บิล</th>
                    <th>วันที่</th>
                    <th class="num">ยอดค้างชำระ (บาท)</th>
                  </tr>
                </thead>
                <tbody id="billList"></tbody>
              </table>
            </div>
            <div class="bill-foot">
              <span id="billSelectStatus">เลือก 0 บิล</span>
              <strong id="billSelectTotal">ยอดรวม 0.00 บาท</strong>
            </div>
          </div>
        </div>

        <div class="step" id="wizardStepDiscount">
          <div class="step-num">3</div>
          <div class="step-body">
            <h3>ส่วนลด (ถ้ามี)</h3>
            <div class="disc-layout">
              <div>
                <div class="seg" role="group" aria-label="ประเภทส่วนลด">
                  <button type="button" class="on" id="discModeAmount" data-mode="amount">จำนวนเงิน (บาท)</button>
                  <button type="button" id="discModePercent" data-mode="percent">% จากยอดรวม</button>
                </div>
                <label class="lbl" id="discInputLabel" for="discInput" style="margin-top:.65rem">ส่วนลด (บาท)</label>
                <input class="inp" id="discInput" type="number" inputmode="decimal" step="0.01" value="0.00"/>
              </div>
              <div class="disc-sum">
                <div class="pay-line"><span>ยอดรวมก่อนส่วนลด</span><strong id="discBillAmt">0.00</strong></div>
                <div class="pay-line"><span>ส่วนลด</span><strong id="discResolved">0.00</strong></div>
                <div class="pay-line pay-net"><span>ยอดสุทธิ</span><strong id="discNetAmt">0.00</strong></div>
              </div>
            </div>
            <div style="margin-top:.85rem">
              <label class="lbl" for="dueDate">วันครบกำหนดชำระ (optional)</label>
              <input class="inp date-ce" id="dueDate" type="date" lang="en" inputmode="none"/>
              <p class="date-hint">ว่างไว้ = ใช้วันนี้ · แตะวันที่เพื่อเปิดปฏิทิน · ปี ค.ศ.</p>
            </div>
            <div style="margin:.55rem 0 .15rem">
              <label class="lbl" for="noteReceiveBank">บัญชีสำหรับรับชำระ (optional)</label>
              <select class="inp" id="noteReceiveBank" aria-label="บัญชีสำหรับรับชำระ">
                <option value="">— ไม่ระบุ —</option>
              </select>
              <p class="date-hint">เลือกบัญชีธนาคารที่จะแจ้งลูกค้า · แสดงบนใบวางบิล · ไม่บังคับ</p>
            </div>
            <div class="remark-form" id="noteRemarkWrap" style="margin-top:.65rem">
              <label class="lbl">หมายเหตุ (optional)</label>
              <div class="grid-2" style="margin-bottom:.35rem">
                <div>
                  <label class="lbl muted">รหัสลูกหนี้</label>
                  <div class="remark-ap" id="noteRemarkAp">—</div>
                </div>
                <div>
                  <label class="lbl" for="noteBillMonth">บิลเดือน</label>
                  <input class="inp" id="noteBillMonth" type="month"/>
                </div>
              </div>
              <label class="toggle" style="margin:.15rem 0 .35rem">
                <input type="checkbox" id="noteRemarkExtraToggle"/>
                เพิ่มหมายเหตุเพิ่มเติม
              </label>
              <div class="remark-extra-wrap hidden" id="noteRemarkExtraWrap">
                <textarea class="area" id="noteRemarkExtra" maxlength="200" rows="2" placeholder="เช่น รอใบลดหนี้ / นัดโอนวันศุกร์"></textarea>
              </div>
              <p class="date-hint remark-preview" id="noteRemarkPreview">เก็บในระบบรับชำระลูกหนี้เท่านั้น · ไม่เขียนลง KSS</p>
            </div>
          </div>
        </div>

        <div class="edit-actions create-actions">
          <button type="button" class="btn outline" id="btnCreateNote">บันทึกใบวางบิล</button>
          <button type="button" class="btn primary" id="btnCreateAndPay">บันทึกและรับชำระ</button>
        </div>
        <div id="createMsg"></div>
    </div>
  </section>

  <section id="panelEdit" class="panel hidden">
    <div class="card">
      <div class="create-head">
        <div>
          <div class="crumb muted" id="editCrumb">แก้ไขใบวางบิล</div>
          <h2 id="editTitle">แก้ไขใบวางบิล</h2>
        </div>
        <button type="button" class="btn ghost" id="btnCancelEdit">ยกเลิก</button>
      </div>
      <div class="grid-3" style="margin-bottom:.85rem">
        <div><label class="lbl">ลูกหนี้</label><input class="inp" id="editVendor" readonly/></div>
        <div><label class="lbl">เลขที่ใบวางบิล</label><input class="inp" id="editNoteno" readonly/></div>
        <div id="editReuseWrap" class="note-reuse-hint hidden" style="margin-top:.35rem"></div>
        <div>
          <label class="lbl" for="editDueDate">วันครบกำหนดชำระ</label>
          <input class="inp date-ce" id="editDueDate" type="date" lang="en" inputmode="none"/>
        </div>
      </div>
      <div class="grid-2" style="margin-bottom:.85rem">
        <div>
          <label class="lbl" for="editReceiveBank">บัญชีสำหรับรับชำระ (optional)</label>
          <select class="inp" id="editReceiveBank" aria-label="บัญชีสำหรับรับชำระ">
            <option value="">— ไม่ระบุ —</option>
          </select>
        </div>
        <div class="remark-form" id="editRemarkWrap">
          <label class="lbl">หมายเหตุ</label>
          <div class="grid-2" style="margin-bottom:.35rem">
            <div>
              <label class="lbl muted">รหัสลูกหนี้</label>
              <div class="remark-ap" id="editRemarkAp">—</div>
            </div>
            <div>
              <label class="lbl" for="editBillMonth">บิลเดือน</label>
              <input class="inp" id="editBillMonth" type="month"/>
            </div>
          </div>
          <label class="toggle" style="margin:.15rem 0 .35rem">
            <input type="checkbox" id="editRemarkExtraToggle"/>
            เพิ่มหมายเหตุเพิ่มเติม
          </label>
          <div class="remark-extra-wrap hidden" id="editRemarkExtraWrap">
            <textarea class="area" id="editRemarkExtra" maxlength="200" rows="2" placeholder="เช่น รอใบลดหนี้ / นัดโอนวันศุกร์"></textarea>
          </div>
          <p class="date-hint remark-preview" id="editRemarkPreview"></p>
        </div>
      </div>
      <div class="bill-head">
        <h3 style="margin:0">เลือกบิล</h3>
        <button type="button" class="linkish" id="btnRefreshEditBills">รีเฟรช</button>
      </div>
      <div class="table-wrap mob-cards" style="border:1px solid var(--line); border-radius:.55rem .55rem 0 0;margin-bottom:0">
        <table>
          <thead><tr><th style="width:2.4rem"></th><th>เลขที่บิล</th><th>วันที่</th><th class="num">ยอด (บาท)</th></tr></thead>
          <tbody id="editBillList"></tbody>
        </table>
      </div>
      <div class="bill-foot" style="margin-bottom:.85rem">
        <span id="editBillSelectStatus">เลือก 0 บิล</span>
        <strong id="editBillSelectTotal">ยอดรวม 0.00 บาท</strong>
      </div>
      <div class="disc-layout" style="margin-bottom:.85rem">
        <div>
          <div class="seg" role="group">
            <button type="button" class="on" id="editDiscModeAmount">จำนวนเงิน (บาท)</button>
            <button type="button" id="editDiscModePercent">% จากยอดรวม</button>
          </div>
          <label class="lbl" id="editDiscInputLabel" for="editDiscInput" style="margin-top:.65rem">ส่วนลด (บาท)</label>
          <input class="inp" id="editDiscInput" type="number" step="0.01" value="0.00"/>
        </div>
        <div class="disc-sum">
          <div class="pay-line"><span>ยอดรวมก่อนส่วนลด</span><strong id="editDiscBillAmt">0.00</strong></div>
          <div class="pay-line"><span>ส่วนลด</span><strong id="editDiscResolved">0.00</strong></div>
          <div class="pay-line pay-net"><span>ยอดสุทธิ</span><strong id="editDiscNetAmt">0.00</strong></div>
        </div>
      </div>
      <div class="edit-actions">
        <button type="button" class="btn primary" id="btnSaveEdit">บันทึกการแก้ไข</button>
        <button type="button" class="btn danger" id="btnCancelNote">ยกเลิกใบวางบิล</button>
      </div>
      <div id="editMsg"></div>
    </div>
  </section>

  <section id="panelPending" class="panel">
    <p class="panel-intro">ขั้นที่ 2 · รอบันทึกรับชำระ · แก้ไขบิล/ส่วนลดได้</p>
    <div class="card toolbar">
      <div class="field grow">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
        <input id="pfQ" placeholder="ค้นหาลูกหนี้ / เลขใบวางบิล" autocomplete="off"/>
      </div>
      <div class="field" style="min-width:11rem">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg></span>
        <input id="pfDue" class="date-ce" type="date" lang="en" inputmode="none" aria-label="กำหนดชำระ"/>
      </div>
      <div class="field" style="min-width:9.5rem">
        <input id="pfBillMonth" type="month" class="inp" aria-label="บิลเดือน" title="กรองตามบิลเดือน"/>
      </div>
      <div class="field" style="min-width:13rem">
        <select id="pfSort" aria-label="เรียงลำดับ">
          <option value="due">เรียงตามกำหนดชำระ</option>
        </select>
      </div>
      <button type="button" class="btn soft" id="btnRefreshPending">↻ รีเฟรช</button>
    </div>
    <div class="kpis">
      <button type="button" class="kpi kpi-all on" data-bucket="all">
        <span class="mark">▤</span>
        <span><b>รอรับชำระทั้งหมด</b><span id="kpiAll">0 รายการ · 0.00 บาท</span></span>
      </button>
      <button type="button" class="kpi kpi-overdue" data-bucket="overdue">
        <span class="mark">!</span>
        <span><b>เกินกำหนด</b><span id="kpiOverdue">0 รายการ · 0.00 บาท</span></span>
      </button>
      <button type="button" class="kpi kpi-today" data-bucket="today">
        <span class="mark">▦</span>
        <span><b>ครบกำหนดวันนี้</b><span id="kpiToday">0 รายการ · 0.00 บาท</span></span>
      </button>
      <button type="button" class="kpi kpi-soon" data-bucket="soon">
        <span class="mark">◷</span>
        <span><b>ใกล้ครบกำหนด</b><span id="kpiSoon">0 รายการ · 0.00 บาท</span></span>
      </button>
    </div>
    <div class="card card-table">
      <div class="table-wrap mob-cards">
        <table>
          <thead>
            <tr>
              <th>รหัสลูกหนี้</th>
              <th>เลขใบวางบิล</th>
              <th class="num">ยอดที่ต้องรับ</th>
              <th>กำหนดชำระ</th>
              <th>หมายเหตุ</th>
              <th>สถานะ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="pendingBody"></tbody>
        </table>
      </div>
      <div id="pendingEmpty" class="empty hidden">ยังไม่มีรายการรอรับชำระ</div>
      <div class="table-foot">
        <div class="table-foot-meta">
          <p class="hint">ⓘ รับชำระแล้วจะย้ายไปแท็บรอแนบหลักฐาน (ยกเว้นเงินสด / RVI)</p>
        </div>
        <div class="table-foot-nav">
          <div class="pager" id="pendingPager"></div>
        </div>
      </div>
    </div>
  </section>

  <section id="panelAwaitProof" class="panel">
    <p class="panel-intro">ขั้นที่ 3 · รับชำระแล้ว · รออัปโหลดหลักฐาน</p>
    <div class="card toolbar">
      <div class="field grow">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
        <input id="afQ" placeholder="ค้นหาเลขใบเสร็จรับเงิน / ลูกหนี้ / เลขใบวางบิล" autocomplete="off"/>
      </div>
      <button type="button" class="btn soft" id="btnRefreshAwaitProof">↻ รีเฟรช</button>
      <div class="field" style="min-width:9.5rem">
        <input id="afBillMonth" type="month" class="inp" aria-label="บิลเดือน" title="กรองตามบิลเดือน"/>
      </div>
    </div>
    <div class="card card-table">
      <div class="table-wrap mob-cards">
        <table>
          <thead>
            <tr>
              <th>เลขใบเสร็จรับเงิน</th>
              <th>รหัสลูกหนี้</th>
              <th>เลขใบวางบิล</th>
              <th>วันที่รับเงิน</th>
              <th>หมายเหตุ</th>
              <th class="num">ยอดรับ</th>
              <th>วิธีรับชำระ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="awaitProofBody"></tbody>
        </table>
      </div>
      <div id="awaitProofEmpty" class="empty hidden">ไม่มีรายการรอแนบหลักฐาน</div>
      <div class="table-foot">
        <div class="table-foot-meta" id="awaitProofCount">แสดง 0 รายการ</div>
        <div class="table-foot-nav">
          <div class="pager" id="awaitProofPager"></div>
        </div>
      </div>
    </div>
  </section>

  <section id="panelVoucher" class="panel">
    <p class="panel-intro">ขั้นที่ 4 · มีหลักฐานครบแล้ว · ดูรายละเอียดบิลและหลักฐานรับเงิน</p>
    <div class="card toolbar">
      <div class="field grow">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
        <input id="vfQ" placeholder="เลขใบเสร็จรับเงิน / รหัสลูกหนี้ / เลขใบวางบิล" autocomplete="off"/>
      </div>
      <div class="field" style="min-width:12rem">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg></span>
        <input id="vfFrom" class="date-ce" type="date" lang="en" inputmode="none" aria-label="ตั้งแต่"/>
        <span>–</span>
        <input id="vfTo" class="date-ce" type="date" lang="en" inputmode="none" aria-label="ถึง"/>
      </div>
      <div class="field" style="min-width:9.5rem">
        <select id="vfMethod" aria-label="วิธีรับชำระ">
          <option value="">วิธีรับชำระ: ทั้งหมด</option>
          <option value="transfer">โอนเงิน</option>
          <option value="cheque">เช็ค</option>
          <option value="cash">เงินสด</option>
        </select>
      </div>
      <button type="button" class="btn ghost" id="btnClearVoucherFilters">↻ ล้างตัวกรอง</button>
      <div class="field" style="min-width:9.5rem">
        <input id="vfBillMonth" type="month" class="inp" aria-label="บิลเดือน" title="กรองตามบิลเดือน"/>
      </div>
    </div>
    <div class="card card-table">
      <div class="table-wrap mob-cards">
        <table>
          <thead>
            <tr>
              <th>เลขใบเสร็จรับเงิน</th>
              <th>รหัสลูกหนี้</th>
              <th>เลขใบวางบิล</th>
              <th>วันที่รับเงิน</th>
              <th>หมายเหตุ</th>
              <th class="num">ยอดรับ (บาท)</th>
              <th>วิธีรับชำระ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="voucherBody"></tbody>
        </table>
      </div>
      <div id="voucherEmpty" class="empty hidden">ยังไม่มีใบเสร็จรับเงิน</div>
      <div class="table-foot">
        <div class="table-foot-meta">
          <span id="voucherCount">แสดง 0 รายการ</span>
          <span class="muted" id="voucherTotal">ทั้งหมด 0 รายการ</span>
        </div>
        <div class="table-foot-nav">
          <label class="page-size">แสดงต่อหน้า
            <select id="vfSize" class="inp page-size-select">
              <option value="10">10</option>
              <option value="20">20</option>
              <option value="50">50</option>
            </select>
          </label>
          <div class="pager" id="voucherPager"></div>
        </div>
      </div>
    </div>
  </section>

  <section id="panelByAp" class="panel">
    <p class="panel-intro">ค้นหารายการใบวางบิล / ใบเสร็จรับเงินตามลูกหนี้</p>
    <div class="card toolbar">
      <div class="combo grow">
        <div class="field">
          <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
          <input id="byApVendorQ" placeholder="ค้นหาลูกหนี้ (รหัส / ชื่อ)" autocomplete="off"/>
        </div>
        <div id="byApVendorResults" class="combo-list hidden"></div>
      </div>
      <button type="button" class="btn soft" id="btnRefreshByAp">↻ รีเฟรช</button>
      <div class="field" style="min-width:9.5rem">
        <input id="byApBillMonth" type="month" class="inp" aria-label="บิลเดือน" title="กรองตามบิลเดือน"/>
      </div>
    </div>
    <div id="byApPicked" class="picked hidden"></div>
    <div class="card card-table">
      <div class="table-wrap mob-cards">
        <table>
          <thead>
            <tr>
              <th>เลขใบวางบิล</th>
              <th>เลขใบเสร็จรับเงิน</th>
              <th class="num">ยอดสุทธิ</th>
              <th>กำหนดชำระ</th>
              <th>หมายเหตุ</th>
              <th>สถานะ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="byApBody"></tbody>
        </table>
      </div>
      <div id="byApEmpty" class="empty hidden">เลือกลูกหนี้เพื่อดูรายการ</div>
      <div class="table-foot">
        <div class="table-foot-meta" id="byApCount">แสดง 0 รายการ</div>
        <div class="table-foot-nav">
          <div class="pager" id="byApPager"></div>
        </div>
      </div>
    </div>
  </section>
</main>

<dialog id="dlgPay" class="dlg">
  <div class="dlg-head">
    <h2 id="payDlgTitle">บันทึกรับชำระ</h2>
    <button type="button" class="dlg-x" id="btnClosePay" aria-label="ปิด">×</button>
  </div>
  <div class="dlg-body">
    <div class="sum-box">
      <div><div class="k">รหัสลูกหนี้</div><div class="v" id="payAcct">—</div></div>
      <div><div class="k">ยอดบิล</div><div class="v" id="payBillAmt">0.00</div></div>
      <div><div class="k">เลขใบวางบิล</div><div class="v" id="payNote">—</div></div>
      <div><div class="k">ส่วนลด (จากใบวางบิล)</div><div class="v" id="payDiscountAmt">0.00</div></div>
      <div class="net"><div class="k" id="payNetLabel">ยอดสุทธิ</div><div class="v" id="payNetAmt">0.00</div></div>
      <div id="payRemainWrap" class="hidden"><div class="k">ยอดค้างคืน</div><div class="v" id="payRemainAmt">0.00</div></div>
    </div>
    <h3 style="margin:.2rem 0 .45rem;font-size:.95rem" id="paySectionTitle">ข้อมูลการรับชำระ</h3>
    <label class="lbl" id="payMethodLabel">วิธีรับชำระ</label>
    <div class="methods" role="group" aria-label="วิธีรับชำระ" id="payMethods">
      <button type="button" class="method on" id="settleTransfer" data-settle="transfer">🏦<span>โอนเงิน</span></button>
      <button type="button" class="method" id="settleCheque" data-settle="cheque">✎<span>เช็ค</span></button>
      <button type="button" class="method" id="settleCash" data-settle="cash">💵<span>เงินสด</span></button>
    </div>
    <div class="grid-2">
      <div>
        <label class="lbl" for="payChkamt" id="payChkamtLabel">จำนวนเงินที่รับ (บาท)</label>
        <input class="inp" id="payChkamt" type="number" inputmode="decimal" step="0.01" min="0"/>
      </div>
      <div>
        <label class="lbl" for="payChkdate" id="payChkdateLabel">วันที่รับเงิน</label>
        <input class="inp date-ce" id="payChkdate" type="date" lang="en" inputmode="none"/>
      </div>
    </div>
    <div id="payChknoWrap" class="hidden" style="margin-top:.65rem">
      <label class="lbl" id="payChknoLabel" for="payChkno">เลขที่เช็ค</label>
      <input class="inp" id="payChkno" maxlength="15"/>
    </div>
    <div id="payBankWrap" style="margin-top:.65rem">
      <label class="lbl" for="payBankSelect" id="payBankLabel">บัญชีที่รับเงิน</label>
      <select class="inp" id="payBankSelect"></select>
    </div>
    <div id="payProofWrap" class="hidden" style="margin-top:.65rem">
      <label class="lbl" id="payProofLabel">แนบหลักฐาน (ไม่บังคับ)</label>
      <div class="drop-wrap" id="dropPayProofWrap">
        <div class="drop" id="dropPayProof" tabindex="0">
          <div style="font-size:1.4rem;margin-bottom:.25rem">☁</div>
          <div id="payProofHint">แตะหรือคลิกเพื่อเลือกไฟล์ · หรือลากมาวาง</div>
          <div class="date-hint">รองรับ JPG, PNG, PDF (ขนาดไม่เกิน 10 MB) · ไม่บังคับ</div>
        </div>
        <input id="payProofFiles" class="drop-file-input" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf" multiple aria-label="เลือกไฟล์หลักฐาน"/>
      </div>
      <div style="margin-top:.45rem;display:flex;gap:.4rem;flex-wrap:wrap;align-items:center">
        <label class="btn sm outline" for="payProofCamera" style="cursor:pointer">ถ่ายภาพ</label>
        <input id="payProofCamera" class="hidden" type="file" accept="image/*" capture="environment" aria-label="ถ่ายภาพหลักฐาน"/>
        <span class="date-hint">หรือเลือกไฟล์ด้านบน</span>
      </div>
      <div class="thumbs" id="payProofThumbs" style="margin-top:.45rem"></div>
    </div>
    <div id="payMsg"></div>
  </div>
  <div class="dlg-foot">
    <button type="button" class="btn ghost" id="btnCancelPay">ยกเลิก</button>
    <button type="button" class="btn primary" id="btnConfirmPay">รับชำระ</button>
  </div>
</dialog>

<dialog id="dlgDetail" class="dlg">
  <div class="dlg-head">
    <h2 id="detTitle">รายละเอียด</h2>
    <button type="button" class="dlg-x" id="btnCloseDetail" aria-label="ปิด">×</button>
  </div>
  <div class="dlg-body">
    <div id="detMeta" class="muted"></div>
    <div id="detReuseWrap" class="note-reuse-hint hidden"></div>
    <div id="detRemark"></div>
    <div id="detDueWrap" class="hidden" style="margin-top:.75rem">
      <label class="lbl">วันครบกำหนดชำระ</label>
      <div style="display:flex;gap:.4rem;align-items:center;flex-wrap:wrap">
        <span id="detDueView"></span>
        <button type="button" class="linkish" id="detDueEdit">แก้ไข</button>
        <input type="date" class="inp date-ce hidden" id="detDueInput" lang="en" inputmode="none" style="width:auto"/>
        <button type="button" class="btn sm primary hidden" id="detDueSave">บันทึก</button>
        <button type="button" class="linkish hidden" id="detDueCancel">ยกเลิก</button>
      </div>
    </div>
    <div id="detPayMethodWrap" style="margin-top:.55rem">
      <label class="lbl" id="detPayMethodLabel">บัญชีสำหรับรับชำระ</label>
      <div id="detPayMethodView">—</div>
    </div>
    <div id="detReceiveMetaWrap" class="hidden" style="margin-top:.65rem">
      <div class="date-hint" id="detIssueDateLine"></div>
      <div style="margin-top:.35rem"><span class="lbl">วันที่รับชำระ</span> <span id="detReceivedAtView">—</span></div>
      <div style="margin-top:.25rem"><span class="lbl">บัญชีที่รับเงิน</span> <span id="detPayBankView">—</span></div>
    </div>
    <div id="detEditHistoryWrap" class="hidden" style="margin-top:.75rem">
      <h3 style="margin:0 0 .35rem;font-size:.9rem">ประวัติการแก้ไข</h3>
      <div id="detEditHistory" class="muted" style="font-size:.82rem"></div>
    </div>
    <div id="detBills"></div>
    <div id="detBillSum"></div>
    <div id="detProofWrap" class="hidden">
      <h3 style="margin:1rem 0 .4rem;font-size:.95rem">หลักฐานรับเงิน</h3>
      <div class="thumbs" id="detProofThumbs"></div>
      <div id="detUploadWrap" class="hidden" style="margin-top:.55rem">
        <label class="lbl" id="detUploadLabel" for="detProofFiles">อัปโหลดหลักฐาน</label>
        <div class="drop-wrap" id="dropProofWrap">
          <div class="drop" id="dropProof" tabindex="0">
            <div style="font-size:1.4rem;margin-bottom:.25rem">☁</div>
            <div id="detUploadHint">แตะหรือคลิกเพื่อเลือกไฟล์ · หรือลากมาวาง</div>
            <div class="date-hint">รองรับไฟล์ JPG, PNG, PDF (ขนาดไม่เกิน 10 MB) · ต้องมีอย่างน้อย 1 รูป</div>
          </div>
          <input id="detProofFiles" class="drop-file-input" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf" multiple aria-label="อัปโหลดหลักฐาน"/>
        </div>
        <div id="detProofVerify" class="ai-panel hidden" style="margin-top:.55rem"></div>
        <div id="proofMismatchAckWrap" class="ai-panel ai-warn hidden" style="margin-top:.55rem">
          <label class="ai-warn">
            <input type="checkbox" id="proofMismatchAck"/>
            ยืนยันว่ายอดสลิปถูกต้อง (AI อ่านผิด)
          </label>
        </div>
        <button type="button" class="btn primary hidden" id="btnProofDone" style="margin-top:.55rem">เสร็จสิ้น</button>
      </div>
    </div>
  </div>
  <div class="dlg-foot">
    <button type="button" class="btn ghost" id="btnCloseDetail2">ปิด</button>
    <button type="button" class="btn danger hidden" id="detCancelNoteBtn">ยกเลิกใบวางบิล</button>
    <button type="button" class="btn outline hidden" id="detEditMetaBtn">แก้ไข</button>
    <button type="button" class="btn outline" id="btnPrintDetail">พิมพ์</button>
    <button type="button" class="btn primary hidden" id="detPayBtn">รับชำระ</button>
  </div>
</dialog>

<dialog id="dlgEditReceipt" class="dlg">
  <div class="dlg-head">
    <h2 id="editRcptTitle">แก้ไขข้อมูลรับชำระ</h2>
    <button type="button" class="dlg-x" id="btnCloseEditRcpt" aria-label="ปิด">×</button>
  </div>
  <div class="dlg-body">
    <p class="date-hint" id="editRcptHint">แก้ไขได้เฉพาะวันที่รับชำระ · หมายเหตุ · บัญชีธนาคาร · ไม่เปลี่ยนยอดเงิน วิธีชำระ หรือวันที่ออกใบเสร็จ</p>
    <div style="margin-top:.55rem">
      <label class="lbl" for="editRcptReceivedAt">วันที่รับชำระ</label>
      <input class="inp date-ce" id="editRcptReceivedAt" type="date" lang="en" inputmode="none"/>
    </div>
    <div style="margin-top:.55rem">
      <label class="lbl" for="editRcptRemark">หมายเหตุ</label>
      <textarea class="area" id="editRcptRemark" maxlength="500" rows="3" placeholder="หมายเหตุ"></textarea>
    </div>
    <div id="editRcptBankWrap" style="margin-top:.55rem">
      <label class="lbl" for="editRcptBank">บัญชีธนาคารที่รับเงิน</label>
      <select class="inp" id="editRcptBank"></select>
    </div>
    <div id="editRcptGateWrap" class="ai-panel ai-warn hidden" style="margin-top:.75rem">
      <p id="editRcptGateMsg" style="margin:0 0 .45rem">รายการนี้กระทบยอดธนาคารหรือปิดงวดบัญชีแล้ว · ต้องให้บัญชีตรวจสอบก่อนแก้ไข</p>
      <label>
        <input type="checkbox" id="editRcptAcctAck"/>
        บัญชีตรวจสอบและอนุมัติให้แก้ไขแล้ว
      </label>
    </div>
    <div id="editRcptMsg" style="margin-top:.55rem"></div>
  </div>
  <div class="dlg-foot">
    <button type="button" class="btn ghost" id="btnCancelEditRcpt">ยกเลิก</button>
    <button type="button" class="btn primary" id="btnSaveEditRcpt">บันทึกการแก้ไข</button>
  </div>
</dialog>

<div id="printSheet" aria-hidden="true"></div>

<script>
const WRITE_ENABLED = __WRITE__;
const AI_ENABLED = __AI__;
const USER_NAME = __USER_JSON__;
const SITE = "__SITE__";
const PAGE_SIZE = 10;
const DUE_SOON_DAYS = 7;
const MAX_FILE_BYTES = 10 * 1024 * 1024;
const RVI_ACCTNOS = new Set(__RVI_ACCTNOS_JSON__);

let picked = null;
let payTarget = null;
let discMode = 'amount';
let editDiscMode = 'amount';
let settleMethod = 'transfer';
let noteReceiveBankKey = '';
let editReceiveBankKey = '';
let pendingRows = [];
let awaitProofRows = [];
let voucherRows = [];
let byApRows = [];
let byApVendor = null;
let pendingPage = 1;
let awaitProofPage = 1;
let voucherPage = 1;
let byApPage = 1;
let voucherPageSize = 10;
let pendingBucket = 'all';
let detailRow = null;
let detailPayload = null;
let proofVerifyResult = null;
let proofPendingComplete = false;
let editTarget = null;
let editReturnTab = 'pending';
let payProofPending = [];
let payProofObjectUrls = [];

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
  ));
}
function fmtMoney(n) {
  return Number(n || 0).toLocaleString('th-TH', {minimumFractionDigits:2, maximumFractionDigits:2});
}
/** When discount_mode is percent, show both % and baht; amount mode stays baht-only. */
function formatDiscountLabel(rem, amount, opts) {
  const disc = Number(amount != null ? amount : ((rem || {}).discount_amount || 0));
  const mode = String((rem || {}).discount_mode || 'amount').toLowerCase();
  if (mode === 'percent') {
    const pct = Number((rem || {}).discount_input || 0);
    const pctTxt = Number.isInteger(pct) ? String(pct) : String(pct);
    const body = `${pctTxt}% (${fmtMoney(disc)} บาท)`;
    return (opts && opts.withPrefix) ? (`ส่วนลด ${body}`) : body;
  }
  return fmtMoney(disc);
}
function formatBankDisplay(text) {
  const s = String(text || '').replace(/\s+#\s*$/, '').trim();
  if (!s || s.includes('\n')) return s;
  const dashed = s.match(/^(.*\S)\s+#\s*(\d{3}-\d-\d{4,6}-\d)\s*$/)
    || s.match(/^(.*\S)\s+(\d{3}-\d-\d{4,6}-\d)\s*$/);
  if (dashed) return dashed[1] + '\n' + dashed[2];
  const hashed = s.match(/^(.*\S)\s+#\s*(\S+)\s*$/);
  if (hashed) return hashed[1] + '\n' + hashed[2];
  return s;
}
function fmtTokens(n) {
  return Number(n || 0).toLocaleString('en-US');
}
function scanUsageText(usage) {
  if (!usage) return '';
  const inTok = Number(usage.input_tokens || 0);
  const outTok = Number(usage.output_tokens || 0);
  const totalTok = Number(usage.total_tokens || (inTok + outTok));
  if (!totalTok) return '';
  return ` · โทเคน in ${fmtTokens(inTok)} · out ${fmtTokens(outTok)} · รวม ${fmtTokens(totalTok)}`;
}
function fmtDate(iso, short) {
  const s = String(iso || '').slice(0, 10);
  if (!s || s.length < 10) return '—';
  const [y, m, d] = s.split('-');
  return short ? `${d}/${m}/${y.slice(2)}` : `${d}/${m}/${y}`;
}
function fmtDateTime(iso) {
  const s = String(iso || '').trim();
  if (!s) return '—';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleString('th-TH', {
    dateStyle: 'short', timeStyle: 'short', hour12: false, timeZone: 'Asia/Bangkok',
  });
}
function bangkokTodayISO() {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Bangkok', year: 'numeric', month: '2-digit', day: '2-digit',
  }).format(new Date());
}
function toDatetimeLocal(iso) {
  const s = String(iso || '').trim();
  if (!s) return '';
  const d = new Date(s);
  if (Number.isNaN(d.getTime())) return '';
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}
function comparePending(a, b) {
  const due = String(remDue(a)).localeCompare(String(remDue(b)));
  if (due) return due;
  return String(a.acctno || '').localeCompare(String(b.acctno || ''));
}
function todayISO() {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;
}
function addDaysISO(iso, days) {
  const [y, m, d] = iso.split('-').map(Number);
  const dt = new Date(y, m - 1, d);
  dt.setDate(dt.getDate() + days);
  return `${dt.getFullYear()}-${String(dt.getMonth()+1).padStart(2,'0')}-${String(dt.getDate()).padStart(2,'0')}`;
}
function remDue(r) { return String(((r.reminder || {}).due_date) || '').slice(0, 10); }
function netAmt(r) {
  if (r.stage === 'voucher' || r.stage === 'await_proof' || r.voucno) {
    return Number(r.NETAMT != null ? r.NETAMT : r.BILLAMT || 0);
  }
  const disc = Number((r.reminder || {}).discount_amount || 0);
  // Allow negative nets (ใบลดหนี้); do not clamp to 0.
  return Number(r.BILLAMT || 0) - disc;
}
function dueBucket(due) {
  const today = todayISO();
  if (!due) return 'later';
  if (due < today) return 'overdue';
  if (due === today) return 'today';
  if (due <= addDaysISO(today, DUE_SOON_DAYS)) return 'soon';
  return 'later';
}
function workflowBadge(r) {
  if (r.canceled || r.stage === 'canceled' || r.workflow_status === 'ยกเลิก') {
    return `<span class="badge b-canceled">ยกเลิก</span>`;
  }
  const st = r.workflow_status || '—';
  if (r.stage === 'await_proof') return `<span class="badge b-wait">${esc(st)}</span>`;
  if (r.stage === 'voucher') return `<span class="badge b-done">${esc(st)}</span>`;
  const ps = pendingStatus(r);
  return `<span class="badge ${ps.cls}">${esc(st || ps.label)}</span>`;
}
function isCanceledRow(r) {
  return !!(r && (r.canceled || r.stage === 'canceled' || r.workflow_status === 'ยกเลิก'
    || String((r.reminder || {}).status || '').toLowerCase() === 'canceled'));
}
function isRefundNote(r) {
  if (!r) return false;
  if (r.is_refund) return true;
  if (String(r.voucno || '').toUpperCase().startsWith('PVN')) return true;
  return netAmt(r) < -1e-9;
}
function remainingRefundOf(r) {
  if (r && r.remaining_refund != null) return Math.max(0, Number(r.remaining_refund));
  if (r && r.refund && r.refund.remaining_refund != null) {
    return Math.max(0, Number(r.refund.remaining_refund));
  }
  const net = netAmt(r);
  return net < -1e-9 ? Math.abs(net) : 0;
}
function pendingStatus(r) {
  if (isCanceledRow(r)) return {cls:'b-canceled', label:'ยกเลิก', bucket:'canceled'};
  if (isRefundNote(r)) return {cls:'b-pending', label:'รอคืนเงิน', bucket:'later'};
  const b = dueBucket(remDue(r));
  if (b === 'overdue') return {cls:'b-overdue', label:'เกินกำหนด', bucket:'overdue'};
  if (b === 'today') return {cls:'b-today', label:'ครบกำหนดวันนี้', bucket:'today'};
  if (b === 'soon') return {cls:'b-soon', label:'ใกล้ครบกำหนด', bucket:'soon'};
  return {cls:'b-pending', label:'รอรับชำระ', bucket:'later'};
}
function receiveBankLabel(key) {
  const k = String(key || '').trim();
  if (!k) return '';
  const acct = (COMPANY_PAY_ACCOUNTS || []).find(a => a.key === k);
  return acct ? (acct.label || acct.bank_name || k) : k;
}
function noteReceiveBankKeyOf(r) {
  const rem = (r && r.reminder) || {};
  return String((r && r.receive_bank_key) || rem.receive_bank_key || '').trim();
}
function settleLabel(m) {
  return m === 'cheque' ? 'เช็ค' : (m === 'cash' ? 'เงินสด' : (m === 'transfer' ? 'โอนเงิน' : '—'));
}
function noteSettleMethod(r) {
  const rem = (r && r.reminder) || {};
  const m = String((r && r.settle_method) || rem.settle_method || '').trim().toLowerCase();
  if (m === 'cheque' || m === 'cash' || m === 'transfer') return m;
  return 'transfer';
}
function settleBadge(m) {
  const method = (m || '').trim().toLowerCase();
  if (method === 'cheque') return `<span class="badge b-cheque">เช็ค</span>`;
  if (method === 'cash') return `<span class="badge b-pending">เงินสด</span>`;
  if (method === 'transfer') return `<span class="badge b-transfer">โอนเงิน</span>`;
  return '—';
}
function keyOf(r) { return `${r.acctno}|${r.noteno}`; }
function displayNoteno(stored) {
  const s = String(stored || '');
  const m = s.match(/^(.+)_(\d+)$/);
  return m ? m[1] : s;
}
function notenoReuseMeta(r) {
  if (!r) return { reused: false, display: '', badge: '', hint: '', stored: '', kss: '' };
  const stored = String(r.noteno || '');
  if (r.is_reused_label != null) {
    return {
      reused: !!r.is_reused_label,
      display: r.noteno_display || displayNoteno(stored),
      badge: r.reuse_badge || '',
      hint: r.reuse_hint || '',
      stored,
      kss: stored,
      round: r.reuse_round || null,
    };
  }
  const display = displayNoteno(stored);
  const m = stored.match(/^(.+)_(\d+)$/);
  const reused = !!m;
  const round = reused ? Number(m[2]) + 1 : 1;
  return {
    reused,
    display,
    badge: reused ? `ใช้ซ้ำ·รอบ ${round}` : '',
    hint: reused ? `เลขใบวางบิล ${display} เคยถูกใช้ใน KSS แล้ว ระบบบันทึกเป็น ${stored} (รอบที่ ${round})` : '',
    stored,
    kss: stored,
    round,
  };
}
function notenoCellHtml(r) {
  const m = notenoReuseMeta(r);
  const badge = m.reused
    ? `<span class="note-reuse-badge" title="${esc(m.hint)}">${esc(m.badge || 'ใช้ซ้ำ')}</span>`
    : '';
  return `${esc(m.display)}${badge}`;
}
function renderNotenoReuseHint(el, r) {
  if (!el) return;
  const m = notenoReuseMeta(r);
  if (!m.reused) {
    el.classList.add('hidden');
    el.innerHTML = '';
    return;
  }
  el.classList.remove('hidden');
  el.innerHTML = `${esc(m.hint)}<div class="note-kss-id">KSS NOTENO: <code>${esc(m.kss)}</code></div>`;
}

function noteQs(acctno, noteno) {
  return `?acctno=${encodeURIComponent(acctno)}&noteno=${encodeURIComponent(noteno)}`;
}

async function api(path, opts) {
  const r = await fetch('/receive-notes/api' + path, opts || {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    const err = new Error(j.detail || j.error || r.statusText);
    err.code = j.code || '';
    throw err;
  }
  return j;
}

async function confirmUnmappedOrThrow(err) {
  if (err && err.code === 'staff_unmapped') {
    const ok = confirm(err.message + '\\n\\nยืนยันออกเอกสารด้วยชื่อ LINE ชั่วคราวหรือไม่?');
    if (ok) return true;
  }
  throw err;
}

function wireDatePicker(el) {
  if (!el || el.dataset.dateWired === '1') return;
  el.dataset.dateWired = '1';
  el.setAttribute('lang', 'en');
  el.setAttribute('inputmode', 'none');
  el.classList.add('date-ce');
  const open = () => { try { if (typeof el.showPicker === 'function') el.showPicker(); } catch (_) {} };
  el.addEventListener('pointerdown', open);
  el.addEventListener('focus', open);
  el.addEventListener('keydown', (e) => {
    if (e.key === 'Tab' || e.key === 'Escape' || e.key === 'Enter') return;
    e.preventDefault();
    open();
  });
}
function wireDatePickers(root) {
  (root || document).querySelectorAll('input[type="date"]').forEach(wireDatePicker);
}

function applyTheme(t) {
  const next = t === 'dark' ? 'dark' : 'light';
  document.documentElement.setAttribute('data-theme', next);
  const meta = $('themeColor');
  if (meta) meta.setAttribute('content', next === 'light' ? '#f3f5f9' : '#0c1014');
  try { localStorage.setItem('kcw.receive_notes.theme', next); } catch (e) {}
}
$('themeBtn').onclick = () => {
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
};
applyTheme(document.documentElement.getAttribute('data-theme') || 'light');

function setCrumb(tab, extra) {
  const flow = 'สร้าง → รอรับชำระ → รอแนบหลักฐาน → ใบเสร็จรับเงิน';
  const base = `${USER_NAME} · HQ only · ${flow}`;
  const labels = {
    create: 'สร้างใบวางบิล',
    pending: 'รอรับชำระ',
    awaitproof: 'รอแนบหลักฐาน',
    voucher: 'ใบเสร็จรับเงิน',
    byap: 'ค้นหาตามลูกหนี้',
    edit: 'แก้ไขใบวางบิล',
  };
  $('pageCrumb').textContent = extra ? `${base} → ${extra}` : (labels[tab] ? `${base} → ${labels[tab]}` : base);
}

function showEditPanel(on) {
  document.querySelectorAll('main > .panel').forEach(p => p.classList.remove('on'));
  $('panelEdit').classList.toggle('hidden', !on);
  $('panelEdit').classList.toggle('on', on);
  document.querySelectorAll('header .tabs button').forEach(b => b.classList.remove('on'));
}

function closeDialogs() {
  ['dlgDetail', 'dlgPay', 'dlgEditReceipt'].forEach((id) => {
    const el = $(id);
    if (el && typeof el.close === 'function' && el.open) el.close();
  });
}

function showTab(name) {
  closeDialogs();
  showEditPanel(false);
  const map = {
    create: 'Create', pending: 'Pending', awaitproof: 'AwaitProof',
    voucher: 'Voucher', byap: 'ByAp',
  };
  Object.keys(map).forEach(k => {
    $('tab' + map[k]).classList.toggle('on', name === k);
    $('panel' + map[k]).classList.toggle('on', name === k);
  });
  $('pageTitle').textContent = `รับชำระลูกหนี้ · ${SITE}`;
  setCrumb(name);
  if (name === 'create' && !$('dueDate').value) $('dueDate').value = todayISO();
  if (name === 'pending') loadPending();
  if (name === 'awaitproof') loadAwaitProof();
  if (name === 'voucher') loadVouchers();
  if (name === 'byap') loadByAp();
  try { history.replaceState(null, '', name === 'create' ? '#' : '#' + name); } catch (e) {}
}
$('tabCreate').onclick = () => showTab('create');
$('tabPending').onclick = () => showTab('pending');
$('tabAwaitProof').onclick = () => showTab('awaitproof');
$('tabVoucher').onclick = () => showTab('voucher');
$('tabByAp').onclick = () => showTab('byap');
$('btnCancelEdit').onclick = () => { editTarget = null; showTab(editReturnTab); };

function pageItems(page, pages) {
  if (pages <= 1) return [1];
  if (pages <= 7) return [...Array(pages)].map((_, i) => i + 1);
  const items = [1];
  const start = Math.max(2, page - 1);
  const end = Math.min(pages - 1, page + 1);
  if (start > 2) items.push('…');
  for (let i = start; i <= end; i++) items.push(i);
  if (end < pages - 1) items.push('…');
  items.push(pages);
  return items;
}
function renderPager(el, page, pages, onPage) {
  if (!el) return;
  const prev = `<button type="button" data-p="${page-1}" ${page<=1?'disabled':''}>&lt;</button>`;
  const next = `<button type="button" data-p="${page+1}" ${page>=pages?'disabled':''}>&gt;</button>`;
  const nums = pageItems(page, pages).map(n => n === '…'
    ? `<span style="padding:0 .2rem">…</span>`
    : `<button type="button" data-p="${n}" class="${n===page?'on':''}">${n}</button>`
  ).join('');
  el.innerHTML = prev + nums + next;
  el.querySelectorAll('button[data-p]').forEach(btn => {
    btn.onclick = () => {
      const p = Number(btn.dataset.p);
      if (p >= 1 && p <= pages) onPage(p);
    };
  });
}
function slicePage(rows, page, size) {
  const pages = Math.max(1, Math.ceil(rows.length / size) || 1);
  const p = Math.min(Math.max(1, page), pages);
  const start = (p - 1) * size;
  return { rows: rows.slice(start, start + size), page: p, pages, start, end: Math.min(start + size, rows.length), total: rows.length };
}

async function loadPending() {
  $('pendingBody').innerHTML = `<tr><td colspan="7" class="empty">กำลังโหลด…</td></tr>`;
  try {
    pendingRows = await api('/pending');
    renderPending();
  } catch (e) {
    $('pendingBody').innerHTML = `<tr><td colspan="7" class="err">${esc(e.message)}</td></tr>`;
  }
}
function pendingNet(r) {
  return Number(r.BILLAMT || 0) - Number((r.reminder || {}).discount_amount || 0);
}
function filteredPending() {
  const q = ($('pfQ').value || '').trim().toLowerCase();
  const due = ($('pfDue').value || '').trim();
  const billMonth = ($('pfBillMonth').value || '').trim();
  let rows = pendingRows.filter(r => {
    // Canceled notes are audit/history only (ค้นหาตามลูกหนี้), not the pending board.
    if (isCanceledRow(r)) return false;
    const st = pendingStatus(r);
    if (pendingBucket !== 'all' && st.bucket !== pendingBucket) return false;
    if (due && remDue(r) !== due) return false;
    if (billMonth && remBillMonth(r) !== billMonth) return false;
    if (q) {
      const hay = [r.acctno, r.acctname, r.noteno, remDue(r), remarkSearchHay(r), receiveBankLabel(noteReceiveBankKeyOf(r))].map(x => String(x||'').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort(comparePending);
  return rows;
}
function renderKpis() {
  const active = pendingRows.filter(r => !isCanceledRow(r));
  const groups = {all: active, overdue: [], today: [], soon: []};
  active.forEach(r => {
    const b = pendingStatus(r).bucket;
    if (groups[b]) groups[b].push(r);
  });
  const line = (rows) => `${rows.length} รายการ · ${fmtMoney(rows.reduce((s, r) => s + pendingNet(r), 0))} บาท`;
  $('kpiAll').textContent = line(groups.all);
  $('kpiOverdue').textContent = line(groups.overdue);
  $('kpiToday').textContent = line(groups.today);
  $('kpiSoon').textContent = line(groups.soon);
  document.querySelectorAll('.kpi[data-bucket]').forEach(el => {
    el.classList.toggle('on', el.dataset.bucket === pendingBucket);
  });
}
function renderPending() {
  renderKpis();
  const all = filteredPending();
  const pg = slicePage(all, pendingPage, PAGE_SIZE);
  pendingPage = pg.page;
  $('pendingEmpty').classList.toggle('hidden', pg.total !== 0);
  $('pendingBody').innerHTML = pg.rows.map(r => {
    const st = pendingStatus(r);
    const canceled = st.bucket === 'canceled';
    const refund = isRefundNote(r);
    const remain = remainingRefundOf(r);
    const payLabel = refund ? 'คืนเงิน' : 'รับชำระ';
    const amtLabel = refund
      ? (remain < Math.abs(pendingNet(r)) - 1e-9
          ? `ค้างคืน ${fmtMoney(remain)} บาท`
          : `${fmtMoney(pendingNet(r))} บาท`)
      : `${fmtMoney(pendingNet(r))} บาท`;
    const actions = canceled
      ? `<button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดูรายละเอียด</button>
         <button type="button" class="btn sm outline" data-print-pending="${esc(keyOf(r))}">พิมพ์</button>`
      : `<button type="button" class="btn sm outline" data-edit="${esc(keyOf(r))}">แก้ไข</button>
        <button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดูรายละเอียด</button>
        ${WRITE_ENABLED ? `<button type="button" class="btn sm danger" data-cancel="${esc(keyOf(r))}">ยกเลิก</button>` : ''}
        <button type="button" class="btn sm primary"
          data-pay-acct="${esc(r.acctno)}" data-pay-note="${esc(r.noteno)}"
          data-pay-amt="${Number(r.BILLAMT||0)}" data-pay-disc="${Number((r.reminder||{}).discount_amount||0)}"
          data-pay-refund="${refund ? '1' : '0'}">${payLabel}</button>`;
    return `<tr>
      <td data-label="รหัสลูกหนี้">${esc(r.acctno)}</td>
      <td data-label="เลขใบวางบิล">${notenoCellHtml(r)}</td>
      <td class="num" data-label="ยอดที่ต้องรับ">${amtLabel}</td>
      <td data-label="กำหนดชำระ">${fmtDate(remDue(r))}</td>
      <td data-label="หมายเหตุ">${esc(formatRemarkShort(r))}</td>
      <td data-label="สถานะ"><span class="badge ${st.cls}">${st.label}</span></td>
      <td class="td-actions" data-label=""><div class="row-actions">${actions}</div></td>
    </tr>`;
  }).join('');
  renderPager($('pendingPager'), pg.page, pg.pages, p => { pendingPage = p; renderPending(); });
}
document.querySelectorAll('.kpi[data-bucket]').forEach(btn => {
  btn.onclick = () => { pendingBucket = btn.dataset.bucket; pendingPage = 1; renderPending(); };
});
$('btnRefreshPending').onclick = loadPending;
['pfQ','pfDue','pfBillMonth','pfSort'].forEach(id => {
  const el = $(id);
  if (!el) return;
  const ev = (el.type === 'date' || el.type === 'month' || el.tagName === 'SELECT') ? 'change' : 'input';
  el.addEventListener(ev, () => { pendingPage = 1; renderPending(); });
});
$('pendingBody').addEventListener('click', (e) => {
  const edit = e.target.closest('[data-edit]');
  if (edit) { openEditNote(edit.dataset.edit, 'pending'); return; }
  const cancel = e.target.closest('[data-cancel]');
  if (cancel) { cancelNoteByKey(cancel.dataset.cancel, 'pending'); return; }
  const pay = e.target.closest('[data-pay-acct]');
  if (pay) {
    openPay(pay.dataset.payAcct, pay.dataset.payNote, pay.dataset.payAmt, pay.dataset.payDisc);
    return;
  }
  const printPending = e.target.closest('[data-print-pending]');
  if (printPending) { openDetailByKey(printPending.dataset.printPending, {print: true}); return; }
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {canPay: true});
});

async function loadAwaitProof() {
  $('awaitProofBody').innerHTML = `<tr><td colspan="8" class="empty">กำลังโหลด…</td></tr>`;
  try {
    awaitProofRows = await api('/vouchered?proof=awaiting');
    renderAwaitProof();
  } catch (e) {
    $('awaitProofBody').innerHTML = `<tr><td colspan="8" class="err">${esc(e.message)}</td></tr>`;
  }
}
function filteredAwaitProof() {
  const q = ($('afQ').value || '').trim().toLowerCase();
  const billMonth = ($('afBillMonth').value || '').trim();
  return awaitProofRows.filter(r => {
    if (billMonth && remBillMonth(r) !== billMonth) return false;
    if (!q) return true;
    const hay = [r.acctno, r.acctname, r.noteno, r.voucno, voucDate(r), remarkSearchHay(r)].map(x => String(x||'').toLowerCase()).join(' ');
    return hay.includes(q);
  });
}
function renderAwaitProof() {
  const all = filteredAwaitProof();
  const pg = slicePage(all, awaitProofPage, PAGE_SIZE);
  awaitProofPage = pg.page;
  $('awaitProofEmpty').classList.toggle('hidden', pg.total !== 0);
  $('awaitProofCount').textContent = pg.total ? `แสดง ${pg.start + 1} - ${pg.end} จาก ${pg.total} รายการ` : 'แสดง 0 รายการ';
  $('awaitProofBody').innerHTML = pg.rows.map(r => `<tr>
    <td data-label="เลขใบเสร็จรับเงิน"><button type="button" class="linkish" data-open="${esc(keyOf(r))}">${esc(r.voucno || '—')}</button></td>
    <td data-label="รหัสลูกหนี้">${esc(r.acctno)}</td>
    <td data-label="เลขใบวางบิล">${notenoCellHtml(r)}</td>
    <td data-label="วันที่รับเงิน">${fmtDate(voucDate(r))}</td>
    <td data-label="หมายเหตุ">${esc(formatRemarkShort(r))}</td>
    <td class="num" data-label="ยอดรับ">${fmtMoney(r.NETAMT != null ? r.NETAMT : r.BILLAMT)}</td>
    <td data-label="วิธีรับชำระ">${esc(settleLabel(r.settle_method))}</td>
    <td class="td-actions" data-label=""><button type="button" class="btn sm primary" data-open="${esc(keyOf(r))}" data-upload="1">แนบหลักฐาน</button></td>
  </tr>`).join('');
  renderPager($('awaitProofPager'), pg.page, pg.pages, p => { awaitProofPage = p; renderAwaitProof(); });
}
$('btnRefreshAwaitProof').onclick = loadAwaitProof;
$('afQ').addEventListener('input', () => { awaitProofPage = 1; renderAwaitProof(); });
$('afBillMonth')?.addEventListener('change', () => { awaitProofPage = 1; renderAwaitProof(); });
$('awaitProofBody').addEventListener('click', (e) => {
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {awaitProof: true, canUpload: !!open.dataset.upload});
});

async function loadVouchers() {
  $('voucherBody').innerHTML = `<tr><td colspan="8" class="empty">กำลังโหลด…</td></tr>`;
  try {
    voucherRows = await api('/vouchered?proof=done');
    renderVouchers();
  } catch (e) {
    $('voucherBody').innerHTML = `<tr><td colspan="8" class="err">${esc(e.message)}</td></tr>`;
  }
}
function voucDate(r) { return String(r.VOUCDATE || '').slice(0, 10); }
function filteredVouchers() {
  const q = ($('vfQ').value || '').trim().toLowerCase();
  const from = ($('vfFrom').value || '').trim();
  const to = ($('vfTo').value || '').trim();
  const method = $('vfMethod').value;
  const billMonth = ($('vfBillMonth').value || '').trim();
  let rows = voucherRows.filter(r => {
    const d = voucDate(r);
    if (from && (!d || d < from)) return false;
    if (to && (!d || d > to)) return false;
    if (method && (r.settle_method || '') !== method) return false;
    if (billMonth && remBillMonth(r) !== billMonth) return false;
    if (q) {
      const hay = [r.acctno, r.acctname, r.noteno, r.voucno, d, remarkSearchHay(r)].map(x => String(x||'').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort((a, b) => String(voucDate(b)).localeCompare(String(voucDate(a))) || String(b.voucno||'').localeCompare(String(a.voucno||'')));
  return rows;
}
function renderVouchers() {
  const all = filteredVouchers();
  const pg = slicePage(all, voucherPage, voucherPageSize);
  voucherPage = pg.page;
  $('voucherTotal').textContent = `ทั้งหมด ${voucherRows.length} รายการ`;
  $('voucherEmpty').classList.toggle('hidden', pg.total !== 0);
  $('voucherCount').textContent = pg.total
    ? `แสดง ${pg.start + 1} - ${pg.end} จาก ${pg.total} รายการ`
    : 'แสดง 0 รายการ';
  $('voucherBody').innerHTML = pg.rows.map(r => `<tr>
    <td data-label="เลขใบเสร็จรับเงิน"><button type="button" class="linkish" data-open="${esc(keyOf(r))}">${esc(r.voucno || '—')}</button></td>
    <td data-label="รหัสลูกหนี้">${esc(r.acctno)}</td>
    <td data-label="เลขใบวางบิล">${notenoCellHtml(r)}</td>
    <td data-label="วันที่รับเงิน">${fmtDate(voucDate(r))}</td>
    <td data-label="หมายเหตุ">${esc(formatRemarkShort(r))}</td>
    <td class="num" data-label="ยอดรับ">${fmtMoney(r.NETAMT != null ? r.NETAMT : r.BILLAMT)}</td>
    <td data-label="วิธีรับชำระ">${esc(settleLabel(r.settle_method))}</td>
    <td class="td-actions" data-label=""><div class="row-actions">
      <button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดู</button>
      ${WRITE_ENABLED ? `<button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}" data-upload="1">อัปเดตรูป</button>` : ''}
      <button type="button" class="btn sm outline" data-print="${esc(keyOf(r))}">พิมพ์</button>
    </div></td>
  </tr>`).join('');
  renderPager($('voucherPager'), pg.page, pg.pages, p => { voucherPage = p; renderVouchers(); });
}
function clearVoucherFilters() {
  $('vfQ').value = ''; $('vfFrom').value = ''; $('vfTo').value = '';
  $('vfMethod').value = ''; $('vfBillMonth').value = '';
  voucherPage = 1; renderVouchers();
}
$('btnClearVoucherFilters').onclick = clearVoucherFilters;
$('vfSize').onchange = () => { voucherPageSize = Number($('vfSize').value || 10); voucherPage = 1; renderVouchers(); };
['vfQ','vfFrom','vfTo','vfMethod','vfBillMonth'].forEach(id => {
  const el = $(id);
  el.addEventListener(el.tagName === 'SELECT' || el.type === 'date' || el.type === 'month' ? 'change' : 'input', () => { voucherPage = 1; renderVouchers(); });
});
$('voucherBody').addEventListener('click', (e) => {
  const printBtn = e.target.closest('[data-print]');
  if (printBtn) { openDetailByKey(printBtn.dataset.print, {voucher: true, print: true}); return; }
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {voucher: true, canUpload: !!open.dataset.upload});
});

async function loadByAp() {
  if (!byApVendor) {
    $('byApBody').innerHTML = '';
    $('byApEmpty').classList.remove('hidden');
    $('byApEmpty').textContent = 'เลือกลูกหนี้เพื่อดูรายการ';
    $('byApCount').textContent = 'แสดง 0 รายการ';
    $('byApPager').innerHTML = '';
    return;
  }
  $('byApBody').innerHTML = `<tr><td colspan="7" class="empty">กำลังโหลด…</td></tr>`;
  try {
    byApRows = await api('/notes?acctno=' + encodeURIComponent(byApVendor.acctno));
    renderByAp();
  } catch (e) {
    $('byApBody').innerHTML = `<tr><td colspan="7" class="err">${esc(e.message)}</td></tr>`;
  }
}
function filteredByAp() {
  const billMonth = ($('byApBillMonth').value || '').trim();
  if (!billMonth) return byApRows;
  return byApRows.filter(r => remBillMonth(r) === billMonth);
}
function renderByAp() {
  const all = filteredByAp();
  const pg = slicePage(all, byApPage, PAGE_SIZE);
  byApPage = pg.page;
  $('byApEmpty').classList.toggle('hidden', pg.total !== 0);
  $('byApCount').textContent = pg.total ? `แสดง ${pg.start + 1} - ${pg.end} จาก ${pg.total} รายการ` : 'แสดง 0 รายการ';
  $('byApBody').innerHTML = pg.rows.map(r => {
    const canceled = isCanceledRow(r);
    const actions = (r.is_editable && !canceled)
      ? `<button type="button" class="btn sm outline" data-edit="${esc(keyOf(r))}">แก้ไข</button>
         ${WRITE_ENABLED ? `<button type="button" class="btn sm danger" data-cancel="${esc(keyOf(r))}">ยกเลิก</button>` : ''}
         <button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดู</button>`
      : `<button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดู</button>`;
    return `<tr>
      <td data-label="เลขใบวางบิล">${notenoCellHtml(r)}</td>
      <td data-label="เลขใบเสร็จรับเงิน">${esc(r.voucno || '—')}</td>
      <td class="num" data-label="ยอดสุทธิ">${fmtMoney(netAmt(r))}</td>
      <td data-label="กำหนดชำระ">${fmtDate(remDue(r), true)}</td>
      <td data-label="หมายเหตุ">${esc(formatRemarkShort(r))}</td>
      <td data-label="สถานะ">${workflowBadge(r)}</td>
      <td class="td-actions" data-label=""><div class="row-actions">${actions}</div></td>
    </tr>`;
  }).join('');
  renderPager($('byApPager'), pg.page, pg.pages, p => { byApPage = p; renderByAp(); });
}
$('btnRefreshByAp').onclick = loadByAp;
$('byApBillMonth')?.addEventListener('change', () => { byApPage = 1; renderByAp(); });
$('byApBody').addEventListener('click', (e) => {
  const edit = e.target.closest('[data-edit]');
  if (edit) { openEditNote(edit.dataset.edit, 'byap'); return; }
  const cancel = e.target.closest('[data-cancel]');
  if (cancel) { cancelNoteByKey(cancel.dataset.cancel, 'byap'); return; }
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open);
});

let byApVendorTimer = null;
async function searchByApVendors() {
  const q = $('byApVendorQ').value.trim();
  if (!q) { $('byApVendorResults').classList.add('hidden'); return; }
  $('byApVendorResults').classList.remove('hidden');
  $('byApVendorResults').innerHTML = '<div class="muted" style="padding:.6rem">กำลังค้นหา…</div>';
  try {
    const rows = await api('/vendors?q=' + encodeURIComponent(q));
    $('byApVendorResults').innerHTML = rows.map(v =>
      `<button type="button" data-acct="${esc(v.acctno)}" data-name="${esc(v.acctname)}">${esc(v.acctno)} — ${esc(v.acctname)}</button>`
    ).join('') || '<div class="muted" style="padding:.6rem">ไม่พบ</div>';
    $('byApVendorResults').querySelectorAll('button[data-acct]').forEach(b => {
      b.onclick = () => pickByApVendor(b.dataset.acct, b.dataset.name);
    });
  } catch (e) { $('byApVendorResults').innerHTML = `<div class="err" style="padding:.6rem">${esc(e.message)}</div>`; }
}
function pickByApVendor(acctno, acctname) {
  byApVendor = {acctno, acctname};
  $('byApPicked').textContent = `${acctno} — ${acctname}`;
  $('byApPicked').classList.remove('hidden');
  $('byApVendorResults').classList.add('hidden');
  byApPage = 1;
  loadByAp();
}
$('byApVendorQ').addEventListener('input', () => {
  clearTimeout(byApVendorTimer);
  byApVendorTimer = setTimeout(searchByApVendors, 280);
});

function findRow(key) {
  const all = [...pendingRows, ...awaitProofRows, ...voucherRows, ...byApRows];
  return all.find(r => keyOf(r) === key);
}
function thumbsHtml(images, opts) {
  opts = opts || {};
  const list = (images || []).filter(x => x && (x.url || x.path));
  if (!list.length) return opts.emptyHtml != null ? opts.emptyHtml : '<p class="muted">ไม่มีรูป</p>';
  const canDelete = !!opts.canDelete;
  const allowLast = !!opts.allowDeleteLast;
  return list.map(img => {
    const url = esc(img.url || '');
    const name = String(img.name || img.path || '');
    const path = esc(img.path || '');
    let body = '';
    if (/\.pdf$/i.test(name)) body = `<a class="file-chip" href="${url}" target="_blank" rel="noopener">${esc(name)}</a>`;
    else body = url ? `<a href="${url}" target="_blank" rel="noopener"><img src="${url}" alt=""/></a>` : '';
    if (!body) return '';
    if (!canDelete || !img.path) return body;
    const lastOnly = !allowLast && list.length <= 1;
    const title = lastOnly ? 'ต้องมีอย่างน้อย 1 รูป' : 'ลบรูปนี้';
    return `<span class="thumb-item">${body}<button type="button" class="thumb-del" data-del-path="${path}" title="${esc(title)}" aria-label="${esc(title)}" ${lastOnly ? 'disabled' : ''}>×</button></span>`;
  }).join('');
}
function billMonthLabel(bills) {
  const months = [];
  (bills || []).forEach(b => {
    const s = String(b.BILLDATE || '').slice(0, 7);
    if (s.length === 7 && !months.includes(s)) months.push(s);
  });
  months.sort();
  const fmt = (ym) => {
    const [y, m] = ym.split('-');
    return `${Number(m)}/${y}`;
  };
  if (!months.length) return '';
  if (months.length === 1) return fmt(months[0]);
  return `${fmt(months[0])} – ${fmt(months[months.length - 1])}`;
}
function suggestBillMonthYm(bills) {
  const months = [];
  (bills || []).forEach(b => {
    const s = String(b.BILLDATE || '').slice(0, 7);
    if (s.length === 7 && !months.includes(s)) months.push(s);
  });
  months.sort();
  return months.length ? months[months.length - 1] : '';
}
const _REMARK_RE = /^(.+?)-บิลเดือน\s+(\d{1,2})\/(\d{4})(?:\s*\/\s*(.+))?$/;
function parseRemark(rem) {
  rem = rem || {};
  let billMonth = String(rem.bill_month || '').slice(0, 7);
  let remarkExtra = String(rem.remark_extra || '').trim();
  if (!billMonth && rem.remark) {
    const m = String(rem.remark).trim().match(_REMARK_RE);
    if (m) {
      billMonth = `${m[3]}-${String(m[2]).padStart(2, '0')}`;
      if (!remarkExtra && m[4]) remarkExtra = m[4].trim();
    } else if (!remarkExtra) {
      remarkExtra = String(rem.remark || '').trim();
    }
  }
  return { billMonth, remarkExtra };
}
function composeRemarkPreview(acctno, billMonth, remarkExtra) {
  const acct = String(acctno || '').trim();
  const extra = String(remarkExtra || '').trim();
  if (billMonth) {
    const [y, m] = billMonth.split('-');
    const label = `${acct}-บิลเดือน ${Number(m)}/${y}`;
    return extra ? `${label} / ${extra}` : label;
  }
  return extra;
}
function getRemarkEls(prefix) {
  return {
    ap: $(prefix + 'RemarkAp'),
    month: $(prefix + 'BillMonth'),
    extraToggle: $(prefix + 'RemarkExtraToggle'),
    extraWrap: $(prefix + 'RemarkExtraWrap'),
    extra: $(prefix + 'RemarkExtra'),
    preview: $(prefix + 'RemarkPreview'),
  };
}
function syncRemarkPreview(prefix, acctno) {
  const els = getRemarkEls(prefix);
  if (!els.preview) return;
  const composed = composeRemarkPreview(acctno, els.month?.value || '', els.extra?.value || '');
  els.preview.textContent = composed
    ? `ตัวอย่าง: ${composed}`
    : 'เก็บในระบบรับชำระลูกหนี้เท่านั้น · ไม่เขียนลง KSS';
}
function fillRemarkForm(prefix, rem, acctno) {
  const els = getRemarkEls(prefix);
  const parsed = parseRemark(rem);
  if (els.ap) els.ap.textContent = acctno || '—';
  if (els.month) els.month.value = parsed.billMonth || '';
  const hasExtra = !!parsed.remarkExtra;
  if (els.extraToggle) els.extraToggle.checked = hasExtra;
  if (els.extraWrap) els.extraWrap.classList.toggle('hidden', !hasExtra);
  if (els.extra) els.extra.value = parsed.remarkExtra || '';
  syncRemarkPreview(prefix, acctno);
}
function readRemarkForm(prefix) {
  const els = getRemarkEls(prefix);
  const billMonth = (els.month?.value || '').trim();
  const remarkExtra = els.extraToggle?.checked ? (els.extra?.value || '').trim() : '';
  return { bill_month: billMonth || null, remark_extra: remarkExtra };
}
function resetRemarkForm(prefix, acctno) {
  fillRemarkForm(prefix, {}, acctno || '');
}
function remBillMonth(r) {
  const bm = (r.reminder || {}).bill_month;
  return bm ? String(bm).slice(0, 7) : '';
}
function formatBillMonthDisplay(ym) {
  if (!ym || ym.length < 7) return '';
  const [y, m] = ym.split('-');
  return `${Number(m)}/${y}`;
}
function formatRemarkShort(r) {
  const rem = r.reminder || {};
  const acctno = r.acctno || '';
  const bm = remBillMonth(r);
  if (bm) {
    const extra = String(rem.remark_extra || '').trim();
    const base = `${acctno} ${formatBillMonthDisplay(bm)}`;
    return extra ? `${base} / ${extra.slice(0, 24)}${extra.length > 24 ? '…' : ''}` : base;
  }
  const text = String(rem.remark || '').trim();
  if (!text) return '—';
  return text.length > 40 ? `${text.slice(0, 40)}…` : text;
}
function remarkSearchHay(r) {
  const rem = r.reminder || {};
  const bm = remBillMonth(r);
  return [
    r.acctno, rem.remark, rem.remark_extra,
    bm, formatBillMonthDisplay(bm),
  ].map(x => String(x || '').toLowerCase()).join(' ');
}
function wireRemarkForm(prefix, acctnoGetter) {
  const els = getRemarkEls(prefix);
  const sync = () => syncRemarkPreview(prefix, typeof acctnoGetter === 'function' ? acctnoGetter() : acctnoGetter);
  els.extraToggle?.addEventListener('change', () => {
    if (els.extraWrap) els.extraWrap.classList.toggle('hidden', !els.extraToggle.checked);
    if (!els.extraToggle.checked && els.extra) els.extra.value = '';
    sync();
  });
  els.month?.addEventListener('change', sync);
  els.extra?.addEventListener('input', sync);
}
wireRemarkForm('note', () => picked?.acctno || '');
wireRemarkForm('edit', () => editTarget?.acctno || '');
function renderDetBills(det) {
  const bills = (det && det.bills) || [];
  const due = String(((det.reminder || {}).due_date) || remDue(detailRow || {}) || '').slice(0, 10);
  const totals = (det && det.totals) || {};
  if (!bills.length) {
    $('detBills').innerHTML = '<p class="muted">ไม่พบบิลซื้อในโน้ตนี้</p>';
    $('detBillSum').innerHTML = '';
    return;
  }
  const rows = bills.map(b => `<tr class="bill-row">
      <td data-label="วันที่บิล">${fmtDate(b.BILLDATE)}</td>
      <td data-label="เลขที่บิล">${esc(b.BILLNO)}</td>
      <td class="num" data-label="จำนวนเงิน">${fmtMoney(b.AFTERTAX)}</td>
      <td data-label="กำหนดชำระ">${fmtDate(due)}</td>
    </tr>`).join('');
  $('detBills').innerHTML = `
    <h3 style="margin:1rem 0 .4rem;font-size:.95rem">รายละเอียดบิลซื้อ</h3>
    <div class="table-wrap">
      <table class="det-bills">
        <thead><tr>
          <th>วันที่บิล</th><th>เลขที่บิล</th>
          <th class="num">จำนวนเงิน</th><th>กำหนดชำระ</th>
        </tr></thead>
        <tbody>${rows}</tbody>
      </table>
    </div>`;
  const rem = (det && det.reminder) || (detailRow && detailRow.reminder) || {};
  const disc = Number(totals.discount || 0);
  const net = Number(totals.netamt != null ? totals.netamt : 0);
  $('detBillSum').innerHTML = `<div class="det-sum">
    <div class="pay-line"><span>จำนวนบิล</span><strong>${totals.billcnt || bills.length} ฉบับ</strong></div>
    <div class="pay-line"><span>จำนวนเงินรวม</span><strong>${fmtMoney(totals.billamt)}</strong></div>
    <div class="pay-line"><span>ส่วนลด</span><strong>${esc(formatDiscountLabel(rem, disc))}</strong></div>
    <div class="pay-line pay-net"><span>ยอดสุทธิ</span><strong>${fmtMoney(net)}</strong></div>
    ${totals.net_text ? `<div class="muted" style="margin-top:.35rem">${esc(totals.net_text)}</div>` : ''}
  </div>`;
}
function fillPrintSheet(det, row) {
  const header = (det && det.header) || {};
  const bills = (det && det.bills) || [];
  const rem = (det && det.reminder) || (row && row.reminder) || {};
  const totals = (det && det.totals) || {};
  const payments = (det && det.payments) || [];
  const debtor = (det && det.debtor) || {};
  const receiveBank = (det && det.receive_bank)
    || resolveOptionalReceiveBank(noteReceiveBankKeyOf(row) || rem.receive_bank_key);
  const voucno = String((row && row.voucno) || header.voucno || '').trim();
  const noteno = String((row && row.noteno) || header.noteno || '').trim();
  const acctno = String((row && row.acctno) || header.acctno || debtor.acctno || '').trim();
  const acctname = String((row && row.acctname) || header.acctname || debtor.acctname || '').trim();
  const address = String(debtor.address || '').trim();
  const taxId = String(debtor.tax_id || '').trim();
  const due = String(rem.due_date || remDue(row || {}) || '').slice(0, 10);
  const docDate = String(voucno ? (header.VOUCDATE || (row && row.VOUCDATE) || header.NOTEDATE) : (header.NOTEDATE || todayISO())).slice(0, 10);
  const disc = Number(totals.discount || 0);
  const billamt = Number(totals.billamt != null ? totals.billamt : 0);
  const net = Number(totals.netamt != null ? totals.netamt : (billamt - disc));
  const isPvn = String(voucno || '').toUpperCase().startsWith('PVN')
    || net < -1e-9
    || isRefundNote(row);
  const title = voucno
    ? (isPvn ? 'ใบสำคัญจ่าย' : 'ใบเสร็จรับเงิน')
    : 'ใบวางบิล';
  const docno = voucno || displayNoteno(noteno);
  const monthRaw = rem.bill_month || billMonthLabel(bills);
  const month = monthRaw ? String(monthRaw).slice(0, 7) : '';
  const billcnt = totals.billcnt || bills.length;
  const words = totals.net_text || '';
  const remarkNote = String(rem.remark || '').trim();
  const canceled = !!(det && det.canceled) || isCanceledRow(row) || !!(header && header.canceled);
  const bodyRows = bills.map(b => {
    const billRemark = String(b.REMARKS || '').trim() || remarkNote;
    return `<tr>
      <td>${esc(fmtDate(b.BILLDATE))}</td>
      <td>${esc(b.BILLNO || '')}</td>
      <td class="num">${fmtMoney(b.AFTERTAX)}</td>
      <td>${esc(fmtDate(due))}</td>
      <td>${esc(billRemark)}</td>
    </tr>`;
  });
  if (!bodyRows.length) {
    bodyRows.push('<tr><td colspan="5" style="text-align:center;color:#666">ไม่พบบิล</td></tr>');
  }
  // Actual payment method from BRDET only (never fall back to note intent).
  const settle = payments.length
    ? String(payments[0].settle_method || '').trim().toLowerCase()
    : '';
  const isCash = settle === 'cash';
  const isTransfer = settle === 'transfer';
  const isCheque = settle === 'cheque';
  const payRows = payments.map(p => {
    const method = String(p.settle_method || '').trim().toLowerCase();
    const kind = method === 'cash' ? 'เงินสด'
      : (method === 'transfer' ? (String(p.CHKNO || '').trim() || 'โอน')
        : (String(p.CHKNO || '').trim() || 'เช็ค'));
    return `<tr>
      <td>${esc(kind)}</td>
      <td class="pv-amt-red">${esc(fmtDate(p.CHKDATE || docDate))}</td>
      <td class="pv-bank">${esc(formatBankDisplay(p.BANKNAME || '')).replace(/\n/g, '<br>')}</td>
      <td class="num pv-amt-red">${fmtMoney(p.CHKAMT != null ? p.CHKAMT : net)}</td>
    </tr>`;
  }).join('');
  const rightFields = [
    `<div class="pv-k">เลขที่เอกสาร</div><div class="pv-docno">${esc(docno)}</div>`,
    `<div class="pv-k">วันที่</div><div>${esc(fmtDate(docDate))}</div>`,
  ];
  if (voucno) {
    rightFields.push(`<div class="pv-k">เลขที่ใบวางบิลอ้างอิง</div><div>${esc(displayNoteno(noteno))}</div>`);
  }
  if (month) {
    rightFields.push(`<div class="pv-k">บิลเดือน</div><div>${esc(month)}</div>`);
  }
  const bankHint = (!voucno && receiveBank)
    ? `<div class="pv-bank-hint"><b>บัญชีสำหรับรับชำระ</b><br/>${esc(receiveBank.label || receiveBank.bank_name || '')}</div>`
    : '';
  const payBlock = voucno ? `
      <div class="pv-pay">
        <div class="pv-checks">
          <div>${isCash ? '☑' : '☐'} เงินสด</div>
          <div style="margin-top:.35rem">${isCheque ? '☑' : '☐'} เช็ค</div>
          <div style="margin-top:.35rem">${isTransfer ? '☑' : '☐'} โอน
            <span class="pv-amt-red" style="margin-left:.6rem">${fmtMoney(net)}</span>
          </div>
        </div>
        ${payRows ? `<table class="pv-paytbl">
          <thead><tr><th>วิธีรับชำระ</th><th>ลงวันที่</th><th>ธนาคาร</th><th>จำนวนเงิน</th></tr></thead>
          <tbody>${payRows}</tbody>
        </table>` : ''}
      </div>` : bankHint;
  $('printSheet').innerHTML = `
    <div class="pv">
      ${canceled ? '<div class="pv-void">ยกเลิก</div>' : ''}
      <div class="pv-top">
        <div class="pv-brand">
          <div class="pv-logo">KCW</div>
          <div class="pv-co-name">บริษัท เกียรติชัยอะไหล่ยนต์ 2007 จำกัด</div>
          <div class="pv-co-addr">305 ม.1 ต.ชุมแสง อ.วังจันทร์ จ.ระยอง 21210<br/>โทร 038-666-078, 093-399-6490 · สำนักงานใหญ่</div>
          <div class="pv-co-addr">เลขประจำตัวผู้เสียภาษี 0215560000262</div>
        </div>
        <div class="pv-doc">
          <h1 class="pv-title">${esc(title)}</h1>
        </div>
      </div>
      <div class="pv-rule"></div>
      <div class="pv-boxes">
        <div class="pv-box">
          <div class="pv-fields">
            <div class="pv-k">รหัสลูกค้า</div><div class="pv-docno">${esc(acctno)}</div>
            <div class="pv-k">ชื่อลูกค้า</div><div class="pv-name">${esc(acctname || '—')}</div>
            <div class="pv-k">ที่อยู่</div><div class="pv-pre">${esc(address || '—')}</div>
            ${taxId ? `<div class="pv-k">เลขประจำตัวผู้เสียภาษี</div><div>${esc(taxId)}</div>` : ''}
          </div>
        </div>
        <div class="pv-box">
          <div class="pv-fields">${rightFields.join('')}</div>
        </div>
      </div>
      <table class="pv-table">
        <thead>
          <tr>
            <th>วันที่บิล</th>
            <th>เลขที่บิล</th>
            <th class="num">จำนวนเงิน</th>
            <th>วันที่ครบกำหนด</th>
            <th>หมายเหตุ</th>
          </tr>
        </thead>
        <tbody>${bodyRows.join('')}</tbody>
      </table>
      <div class="pv-foot">
        <div class="pv-words">${esc(billcnt)} ฉบับ<br/>${esc(words)}</div>
        <div class="pv-tot">
          <div class="row"><span>จำนวนเงินรวม</span><span class="n">${fmtMoney(billamt)}</span></div>
          <div class="row"><span>ส่วนลด</span><span class="n">${esc(formatDiscountLabel(rem, disc))}</span></div>
          <div class="row pv-net"><span>ยอดสุทธิ</span><span class="n">${fmtMoney(net)}</span></div>
        </div>
      </div>
      ${payBlock}
      <div class="pv-sign">
        <div class="col">${voucno ? 'ผู้รับเงิน' : 'ผู้รับเอกสาร'}<div class="line"></div>วันที่<div class="line"></div></div>
        <div class="col" style="text-align:right">ผู้จัดทำ<div class="line">${esc((rem.issuer_label || '').trim() || USER_NAME || '')}</div></div>
      </div>
    </div>`;
}
function printDetail() {
  if (!detailPayload) { alert('กำลังโหลดรายละเอียด'); return; }
  fillPrintSheet(detailPayload, detailRow || {});
  window.print();
}

async function openDetailByKey(key, opts) {
  opts = opts || {};
  const row = findRow(key) || pendingRows.find(r => keyOf(r) === key) || voucherRows.find(r => keyOf(r) === key);
  if (!row) return;
  detailRow = row;
  detailPayload = null;
  const rem = row.reminder || {};
  const canceled = isCanceledRow(row);
  const refundRow = isRefundNote(row);
  const voUpper = String(row.voucno || '').toUpperCase();
  $('detTitle').textContent = row.voucno
    ? `${voUpper.startsWith('PVN') || refundRow ? 'ใบสำคัญจ่าย' : 'ใบเสร็จรับเงิน'} ${row.voucno}`
    : `ใบวางบิล ${notenoReuseMeta(row).display}${canceled ? ' · ยกเลิก' : ''}${!canceled && refundRow ? ' · รอคืนเงิน' : ''}`;
  $('detMeta').textContent = `${row.acctno} · ${row.acctname || ''} · ${notenoReuseMeta(row).display}`;
  renderNotenoReuseHint($('detReuseWrap'), row);
  const remark = String(rem.remark || '').trim();
  $('detRemark').innerHTML = remark ? `<div class="remark">${esc(remark)}</div>` : '';
  const canEditDue = row.is_editable === true && !canceled;
  $('detDueWrap').classList.toggle('hidden', !remDue(row));
  $('detDueView').textContent = remDue(row) || '—';
  $('detDueEdit').classList.add('hidden');
  $('detDueInput').classList.add('hidden');
  $('detDueSave').classList.add('hidden');
  $('detDueCancel').classList.add('hidden');
  if ($('detPayMethodLabel')) {
    $('detPayMethodLabel').textContent = row.voucno
      ? (refundRow || voUpper.startsWith('PVN') ? 'วิธีคืนเงิน' : 'วิธีรับชำระ')
      : 'บัญชีสำหรับรับชำระ';
  }
  if ($('detPayMethodView')) {
    if (row.voucno) {
      $('detPayMethodView').innerHTML = settleBadge(noteSettleMethod(row));
    } else {
      const bankLbl = receiveBankLabel(noteReceiveBankKeyOf(row));
      $('detPayMethodView').textContent = bankLbl || '— ไม่ระบุ —';
    }
  }
  if ($('detPayMethodWrap')) $('detPayMethodWrap').classList.remove('hidden');
  if ($('detPayBtn')) $('detPayBtn').textContent = refundRow ? 'คืนเงิน' : 'รับชำระ';
  $('detPayBtn').classList.toggle('hidden', !(opts.canPay && canEditDue && WRITE_ENABLED));
  $('detCancelNoteBtn')?.classList.toggle('hidden', !(canEditDue && WRITE_ENABLED));
  $('detEditMetaBtn')?.classList.add('hidden');
  $('detReceiveMetaWrap')?.classList.add('hidden');
  $('detEditHistoryWrap')?.classList.add('hidden');
  // Cash / RVI skip proof tab (stage already voucher even without images).
  const skipProof = row.proof_required === false;
  const hasProofImgs = !!(row.payment_images || []).length;
  $('detProofWrap').classList.toggle('hidden', !row.voucno || (skipProof && !hasProofImgs));
  const isAwaitProof = row.stage === 'await_proof'
    || (!!row.voucno && !row.has_proof && row.stage !== 'voucher' && !skipProof);
  const isDoneVoucher = row.stage === 'voucher' || !!row.has_proof || skipProof;
  const canUpload = WRITE_ENABLED && !!row.voucno && !skipProof
    && (opts.canUpload || isAwaitProof);
  $('detUploadWrap').classList.toggle('hidden', !canUpload);
  if ($('detUploadLabel')) {
    $('detUploadLabel').textContent = isDoneVoucher ? 'อัปเดตหลักฐาน' : 'อัปโหลดหลักฐาน';
  }
  if ($('detUploadHint')) {
    $('detUploadHint').textContent = isDoneVoucher
      ? 'อัปโหลดรูปใหม่เพื่อเพิ่ม/แทนที่ · ลบได้แต่ต้องเหลืออย่างน้อย 1 รูป'
      : 'แตะหรือคลิกเพื่อเลือกไฟล์ · หรือลากมาวาง';
  }
  $('detBills').innerHTML = '<p class="muted">กำลังโหลดบิลซื้อ…</p>';
  $('detBillSum').innerHTML = '';
  $('detProofThumbs').innerHTML = thumbsHtml(row.payment_images || [], {canDelete: canUpload});
  if (!opts.keepVerify) {
    proofVerifyResult = null;
    proofPendingComplete = false;
    $('detProofVerify')?.classList.add('hidden');
    $('proofMismatchAckWrap')?.classList.add('hidden');
    $('btnProofDone')?.classList.add('hidden');
    if ($('proofMismatchAck')) $('proofMismatchAck').checked = false;
  }
  const dlg = $('dlgDetail');
  if (!dlg.open) dlg.showModal();
  try {
    const det = await api(`/notes${noteQs(row.acctno, row.noteno)}`);
    detailPayload = det;
    if (det.stage) row.stage = det.stage;
    if (det.workflow_status) row.workflow_status = det.workflow_status;
    if (det.proof_required != null) row.proof_required = det.proof_required;
    if (det.has_proof != null) row.has_proof = det.has_proof;
    if (det.settle_method) row.settle_method = det.settle_method;
    renderDetBills(det);
    renderNotenoReuseHint($('detReuseWrap'), {...row, ...det});
    if (det.canceled || det.workflow_status === 'ยกเลิก') {
      row.canceled = true;
      row.stage = 'canceled';
      row.workflow_status = 'ยกเลิก';
      row.is_editable = false;
      $('detTitle').textContent = `ใบวางบิล ${notenoReuseMeta(row).display} · ยกเลิก`;
      $('detPayBtn').classList.add('hidden');
      $('detCancelNoteBtn')?.classList.add('hidden');
    }
    // Re-apply proof UI after detail (cash/RVI may skip proof).
    {
      const skip = row.proof_required === false;
      const imgs = det.payment_images || row.payment_images || [];
      $('detProofWrap').classList.toggle('hidden', !row.voucno || (skip && !imgs.length));
      const awaitP = row.stage === 'await_proof'
        || (!!row.voucno && !row.has_proof && row.stage !== 'voucher' && !skip);
      const canUp = WRITE_ENABLED && !!row.voucno && !skip && (opts.canUpload || awaitP);
      $('detUploadWrap').classList.toggle('hidden', !canUp);
      if ($('detUploadLabel')) {
        $('detUploadLabel').textContent = (row.stage === 'voucher' || row.has_proof || skip)
          ? 'อัปเดตหลักฐาน' : 'อัปโหลดหลักฐาน';
      }
    }
    if ($('detPayMethodView')) {
      const pay0 = (det.payments || [])[0];
      if (row.voucno || pay0) {
        const paySettle = (pay0 && pay0.settle_method) || '';
        if ($('detPayMethodLabel')) $('detPayMethodLabel').textContent = 'วิธีรับชำระ';
        $('detPayMethodView').innerHTML = settleBadge(paySettle);
      } else if (det.receive_bank) {
        if ($('detPayMethodLabel')) $('detPayMethodLabel').textContent = 'บัญชีสำหรับรับชำระ';
        $('detPayMethodView').textContent = det.receive_bank.label || det.receive_bank.bank_name || '—';
      } else {
        if ($('detPayMethodLabel')) $('detPayMethodLabel').textContent = 'บัญชีสำหรับรับชำระ';
        $('detPayMethodView').textContent = receiveBankLabel((det.reminder || {}).receive_bank_key) || '— ไม่ระบุ —';
      }
    }
    if (det.payment_images) {
      $('detProofThumbs').innerHTML = thumbsHtml(det.payment_images, {canDelete: canUpload});
    }
    renderDetReceiveMeta(det, row);
    fillPrintSheet(det, row);
    if (opts.print) printDetail();
  } catch (e) {
    $('detBills').innerHTML = `<p class="err">${esc(e.message)}</p>`;
  }
}
function renderDetReceiveMeta(det, row) {
  const voucno = String((row && row.voucno) || (det && det.header && det.header.voucno) || '').trim();
  const canceled = !!(det && det.canceled) || isCanceledRow(row);
  const wrap = $('detReceiveMetaWrap');
  const histWrap = $('detEditHistoryWrap');
  const editBtn = $('detEditMetaBtn');
  if (!voucno || canceled) {
    wrap?.classList.add('hidden');
    histWrap?.classList.add('hidden');
    editBtn?.classList.add('hidden');
    return;
  }
  wrap?.classList.remove('hidden');
  const issue = String((det && det.issue_date) || (det && det.header && det.header.VOUCDATE) || row.VOUCDATE || '').slice(0, 10);
  const recv = String((det && det.received_at) || '').slice(0, 10) || issue;
  if ($('detIssueDateLine')) {
    $('detIssueDateLine').textContent = issue
      ? `วันที่ออกใบเสร็จ ${fmtDate(issue)} (แก้ไม่ได้)`
      : '';
  }
  if ($('detReceivedAtView')) $('detReceivedAtView').textContent = fmtDate(recv) || '—';
  const bankKey = (det && det.pay_bank_key) || '';
  const bankLbl = receiveBankLabel(bankKey)
    || ((det.payments || [])[0] && formatBankDisplay((det.payments || [])[0].BANKNAME))
    || '—';
  if ($('detPayBankView')) $('detPayBankView').textContent = bankLbl || '—';
  const canEdit = WRITE_ENABLED && det.can_edit_meta !== false;
  editBtn?.classList.toggle('hidden', !canEdit);

  const history = (det && det.edit_history) || [];
  if (histWrap && $('detEditHistory')) {
    if (!history.length) {
      histWrap.classList.add('hidden');
      $('detEditHistory').innerHTML = '';
    } else {
      histWrap.classList.remove('hidden');
      $('detEditHistory').innerHTML = history.slice(0, 8).map((h) => {
        const when = String(h.edited_at || '').replace('T', ' ').slice(0, 19);
        const who = esc(h.edited_by || '—');
        const oldV = h.old_values || {};
        const newV = h.new_values || {};
        const bits = [];
        if (oldV.received_at !== newV.received_at) {
          bits.push(`วันที่ ${esc(oldV.received_at || '—')} → ${esc(newV.received_at || '—')}`);
        }
        if ((oldV.remark || '') !== (newV.remark || '')) {
          bits.push('หมายเหตุ');
        }
        if ((oldV.receive_bank_key || '') !== (newV.receive_bank_key || '')) {
          bits.push(`บัญชี ${esc(receiveBankLabel(oldV.receive_bank_key) || oldV.receive_bank_key || '—')} → ${esc(receiveBankLabel(newV.receive_bank_key) || newV.receive_bank_key || '—')}`);
        }
        return `<div style="margin:.2rem 0">${esc(when)} · ${who}${h.accounting_reviewed ? ' · บัญชีอนุมัติ' : ''}${bits.length ? ' · ' + bits.join(' · ') : ''}</div>`;
      }).join('');
    }
  }
}
async function openEditReceiptMeta() {
  if (!detailRow || !detailPayload || !WRITE_ENABLED) return;
  if (!detailRow.voucno && !(detailPayload.header || {}).voucno) return;
  const det = detailPayload;
  const settle = String(det.settle_method || noteSettleMethod(detailRow) || '').toLowerCase();
  const refund = isRefundNote(detailRow);
  $('editRcptTitle').textContent = refund ? 'แก้ไขข้อมูลคืนเงิน' : 'แก้ไขข้อมูลรับชำระ';
  $('editRcptHint').textContent = refund
    ? 'แก้ไขได้เฉพาะวันที่คืนเงิน · หมายเหตุ · บัญชี · ไม่เปลี่ยนยอดเงิน วิธีชำระ หรือวันที่ออกใบสำคัญ'
    : 'แก้ไขได้เฉพาะวันที่รับชำระ · หมายเหตุ · บัญชีธนาคาร · ไม่เปลี่ยนยอดเงิน วิธีชำระ หรือวันที่ออกใบเสร็จ';
  if ($('editRcptReceivedAt')) {
    $('editRcptReceivedAt').value = String(det.received_at || todayISO()).slice(0, 10);
  }
  if ($('editRcptRemark')) {
    $('editRcptRemark').value = String((det.reminder || {}).remark || '').trim();
  }
  const bankWrap = $('editRcptBankWrap');
  const bankSel = $('editRcptBank');
  if (settle === 'cash') {
    bankWrap?.classList.add('hidden');
  } else {
    bankWrap?.classList.remove('hidden');
    if (bankSel) {
      const accounts = (typeof COMPANY_PAY_ACCOUNTS !== 'undefined' ? COMPANY_PAY_ACCOUNTS : []) || [];
      bankSel.innerHTML = accounts.map(a =>
        `<option value="${esc(a.key)}">${esc(a.label || a.bank_name || a.key)}</option>`
      ).join('');
      bankSel.value = det.pay_bank_key || (accounts[0] && accounts[0].key) || '';
    }
  }
  const gate = det.edit_gate || {};
  const needsGate = !!gate.needs_accounting_review;
  $('editRcptGateWrap')?.classList.toggle('hidden', !needsGate);
  if ($('editRcptAcctAck')) $('editRcptAcctAck').checked = false;
  if ($('editRcptGateMsg') && needsGate) {
    const reasons = (gate.reasons || []).map(r =>
      r === 'bank_reconciled' ? 'กระทบยอดธนาคารแล้ว'
        : (r === 'period_closed' ? 'ปิดงวดบัญชีแล้ว' : r)
    ).join(' · ');
    $('editRcptGateMsg').textContent = reasons
      ? `รายการนี้${reasons} · ต้องให้บัญชีตรวจสอบก่อนแก้ไข`
      : 'รายการนี้กระทบยอดธนาคารหรือปิดงวดบัญชีแล้ว · ต้องให้บัญชีตรวจสอบก่อนแก้ไข';
  }
  if ($('editRcptMsg')) $('editRcptMsg').innerHTML = '';
  const dlg = $('dlgEditReceipt');
  if (dlg && !dlg.open) dlg.showModal();
}
async function saveEditReceiptMeta() {
  if (!detailRow || !WRITE_ENABLED) return;
  const gate = (detailPayload && detailPayload.edit_gate) || {};
  if (gate.needs_accounting_review && !($('editRcptAcctAck') && $('editRcptAcctAck').checked)) {
    alert('ต้องให้บัญชีตรวจสอบและติ๊กยืนยันก่อนแก้ไข');
    return;
  }
  const settle = String((detailPayload && detailPayload.settle_method) || noteSettleMethod(detailRow) || '').toLowerCase();
  const body = {
    acctno: detailRow.acctno,
    noteno: detailRow.noteno,
    received_at: ($('editRcptReceivedAt') && $('editRcptReceivedAt').value) || null,
    remark: ($('editRcptRemark') && $('editRcptRemark').value) || '',
    accounting_reviewed: !!(gate.needs_accounting_review && $('editRcptAcctAck') && $('editRcptAcctAck').checked),
  };
  if (settle !== 'cash' && $('editRcptBank')) {
    body.receive_bank_key = $('editRcptBank').value.trim();
  }
  if ($('editRcptMsg')) $('editRcptMsg').innerHTML = '<span class="muted">กำลังบันทึก…</span>';
  $('btnSaveEditRcpt').disabled = true;
  try {
    const r = await fetch('/receive-notes/api/vouchers/meta', {
      method: 'PATCH',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(body),
    });
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      if (j.code === 'needs_accounting_review') {
        $('editRcptGateWrap')?.classList.remove('hidden');
        if (j.edit_gate) detailPayload.edit_gate = j.edit_gate;
      }
      throw new Error(j.error || j.detail || 'บันทึกไม่สำเร็จ');
    }
    try { $('dlgEditReceipt').close(); } catch (_) {}
    await loadAwaitProof();
    await loadVouchers();
    const fresh = voucherRows.find(x => keyOf(x) === keyOf(detailRow))
      || awaitProofRows.find(x => keyOf(x) === keyOf(detailRow))
      || detailRow;
    openDetailByKey(keyOf(fresh), {voucher: true, canUpload: true});
  } catch (e) {
    if ($('editRcptMsg')) $('editRcptMsg').innerHTML = `<span class="err">${esc(e.message)}</span>`;
  } finally {
    $('btnSaveEditRcpt').disabled = false;
  }
}
$('detEditMetaBtn')?.addEventListener('click', () => openEditReceiptMeta());
$('btnCloseEditRcpt')?.addEventListener('click', () => { try { $('dlgEditReceipt').close(); } catch (_) {} });
$('btnCancelEditRcpt')?.addEventListener('click', () => { try { $('dlgEditReceipt').close(); } catch (_) {} });
$('btnSaveEditRcpt')?.addEventListener('click', () => saveEditReceiptMeta());
$('dlgEditReceipt')?.addEventListener('click', (e) => {
  if (e.target === $('dlgEditReceipt')) { try { $('dlgEditReceipt').close(); } catch (_) {} }
});
$('detPayBtn').onclick = () => {
  if (!detailRow) return;
  $('dlgDetail').close();
  openPay(
    detailRow.acctno, detailRow.noteno, detailRow.BILLAMT,
    (detailRow.reminder || {}).discount_amount || 0
  );
};
$('detCancelNoteBtn')?.addEventListener('click', () => {
  if (!detailRow) return;
  cancelNoteByKey(keyOf(detailRow), detailRow.stage === 'pending' ? 'pending' : 'byap', {
    closeDetail: true,
  });
});
function wireDropZone(dropEl, inputEl, onFiles) {
  if (!dropEl || !inputEl) return;
  // Overlay .drop-file-input receives taps natively (works on mobile). Fallback click for older markup.
  const overlay = inputEl.classList.contains('drop-file-input');
  if (!overlay) {
    dropEl.onclick = () => inputEl.click();
  }
  dropEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputEl.click(); }
  });
  const dragTarget = inputEl.closest('.drop-wrap') || dropEl;
  dragTarget.addEventListener('dragover', (e) => { e.preventDefault(); dropEl.classList.add('drag'); });
  dragTarget.addEventListener('dragleave', () => dropEl.classList.remove('drag'));
  dragTarget.addEventListener('drop', async (e) => {
    e.preventDefault(); dropEl.classList.remove('drag');
    await onFiles(e.dataTransfer.files);
  });
  inputEl.onchange = async (ev) => {
    await onFiles(ev.target.files);
    ev.target.value = '';
  };
}
async function uploadProofFiles(files) {
  if (!detailRow || !detailRow.voucno) return;
  const wasDone = !!detailRow.has_proof || detailRow.stage === 'voucher';
  let lastFile = null;
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); continue; }
    lastFile = file;
    const fd = new FormData();
    fd.append('voucno', detailRow.voucno);
    fd.append('file', file);
    const r = await fetch('/receive-notes/api/images/payment', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { alert(j.detail || j.error); return; }
  }
  await loadAwaitProof();
  await loadVouchers();
  const fresh = voucherRows.find(x => keyOf(x) === keyOf(detailRow)) || awaitProofRows.find(x => keyOf(x) === keyOf(detailRow));
  if (fresh) detailRow = fresh;

  let verifyResult = null;
  if (AI_ENABLED && lastFile && !wasDone) {
    try {
      const vfd = new FormData();
      vfd.append('voucno', detailRow.voucno);
      vfd.append('file', lastFile);
      const vr = await fetch('/receive-notes/api/ai/verify-payment', {method:'POST', body: vfd});
      verifyResult = await vr.json().catch(() => ({}));
      if (!vr.ok) verifyResult = null;
    } catch (_) { verifyResult = null; }
  }

  if (wasDone) {
    openDetailByKey(keyOf(fresh || detailRow), {voucher: true, canUpload: true});
    return;
  }

  if (fresh && fresh.has_proof) {
    if (verifyResult) {
      renderProofVerify(verifyResult);
      openDetailByKey(keyOf(fresh), {awaitProof: true, canUpload: true, keepVerify: true});
      if (verifyResult.match) {
        setTimeout(() => completeProofFlow(fresh), 300);
      }
      return;
    }
    $('dlgDetail').close();
    showTab('voucher');
    openDetailByKey(keyOf(fresh), {voucher: true});
  } else if (fresh) {
    openDetailByKey(keyOf(fresh), {awaitProof: true, canUpload: true});
  }
}
async function deleteProofImage(path) {
  if (!detailRow || !detailRow.voucno || !path) return;
  if (!confirm('ลบรูปหลักฐานนี้?')) return;
  const qs = new URLSearchParams({voucno: detailRow.voucno, path});
  const r = await fetch('/receive-notes/api/images/payment?' + qs.toString(), {method:'DELETE'});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) {
    alert(j.error === 'cannot remove last payment image'
      ? 'ต้องมีอย่างน้อย 1 รูปหลักฐาน'
      : (j.detail || j.error || 'ลบไม่สำเร็จ'));
    return;
  }
  await loadAwaitProof();
  await loadVouchers();
  const fresh = voucherRows.find(x => keyOf(x) === keyOf(detailRow)) || awaitProofRows.find(x => keyOf(x) === keyOf(detailRow));
  if (fresh) detailRow = fresh;
  const done = !!(detailRow.has_proof) || detailRow.stage === 'voucher';
  openDetailByKey(keyOf(detailRow), done
    ? {voucher: true, canUpload: true}
    : {awaitProof: true, canUpload: true});
}
function tryCloseDetail() {
  if (proofPendingComplete && !proofCanComplete()) {
    alert('กรุณายืนยันว่ายอดสลิปถูกต้อง (AI อ่านผิด) ก่อนปิด');
    return;
  }
  $('dlgDetail').close();
}
$('btnCloseDetail').onclick = tryCloseDetail;
$('btnCloseDetail2').onclick = tryCloseDetail;
$('btnPrintDetail').onclick = printDetail;
$('dlgDetail').addEventListener('click', (e) => {
  if (e.target === $('dlgDetail')) tryCloseDetail();
});
wireDropZone($('dropProof'), $('detProofFiles'), uploadProofFiles);
$('detProofThumbs').addEventListener('click', (e) => {
  const btn = e.target.closest('[data-del-path]');
  if (!btn || btn.disabled) return;
  e.preventDefault();
  e.stopPropagation();
  deleteProofImage(btn.dataset.delPath);
});


let COMPANY_PAY_ACCOUNTS = __COMPANY_PAY_JSON__;
const DEFAULT_PAY_BANK = __DEFAULT_PAY_BANK__;

function resolveOptionalReceiveBank(key) {
  const k = String(key || '').trim();
  if (!k) return null;
  return (COMPANY_PAY_ACCOUNTS || []).find(a => a.key === k) || null;
}
function fillReceiveBankSelect(sel, selected) {
  if (!sel) return;
  const accounts = COMPANY_PAY_ACCOUNTS || [];
  sel.innerHTML = `<option value="">— ไม่ระบุ —</option>` + accounts.map(a =>
    `<option value="${esc(a.key)}">${esc(a.label)}</option>`
  ).join('');
  sel.value = selected || '';
}
async function initPayBankSelect() {
  const sel = $('payBankSelect');
  let accounts = COMPANY_PAY_ACCOUNTS || [];
  let defKey = DEFAULT_PAY_BANK || '';
  try {
    const j = await fetch('/receive-notes/api/company-receive-accounts').then(r => r.json());
    if (Array.isArray(j) && j.length) accounts = j;
    else if (j && Array.isArray(j.accounts) && j.accounts.length) {
      accounts = j.accounts;
      if (j.default) defKey = j.default;
    }
  } catch (e) {}
  COMPANY_PAY_ACCOUNTS = accounts;
  if (sel) {
    sel.innerHTML = accounts.map(a =>
      `<option value="${esc(a.key)}">${esc(a.label)}</option>`
    ).join('');
    sel.value = defKey || (accounts[0] && accounts[0].key) || '';
  }
  fillReceiveBankSelect($('noteReceiveBank'), noteReceiveBankKey);
  fillReceiveBankSelect($('editReceiveBank'), editReceiveBankKey);
}

function isRviAcct(acctno) {
  return RVI_ACCTNOS.has(String(acctno || '').trim().toUpperCase());
}
function revokePayProofObjectUrls() {
  payProofObjectUrls.forEach(u => { try { URL.revokeObjectURL(u); } catch (_) {} });
  payProofObjectUrls = [];
}
function clearPayProofPending() {
  payProofPending = [];
  revokePayProofObjectUrls();
  if ($('payProofFiles')) $('payProofFiles').value = '';
  if ($('payProofCamera')) $('payProofCamera').value = '';
  renderPayProofThumbs();
}
function renderPayProofThumbs() {
  const box = $('payProofThumbs');
  if (!box) return;
  revokePayProofObjectUrls();
  if (!payProofPending.length) {
    box.innerHTML = '';
    return;
  }
  box.innerHTML = payProofPending.map((file, idx) => {
    const name = esc(file.name || ('file-' + (idx + 1)));
    const isPdf = /\.pdf$/i.test(file.name || '') || file.type === 'application/pdf';
    let body = '';
    if (isPdf) {
      body = `<span class="file-chip">${name}</span>`;
    } else {
      const url = URL.createObjectURL(file);
      payProofObjectUrls.push(url);
      body = `<img src="${url}" alt="${name}"/>`;
    }
    return `<span class="thumb-item">${body}<button type="button" class="thumb-del" data-pay-proof-del="${idx}" title="ลบ" aria-label="ลบ">×</button></span>`;
  }).join('');
}
function addPayProofFiles(fileList) {
  const files = Array.from(fileList || []);
  if (!files.length) return;
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); continue; }
    payProofPending.push(file);
  }
  renderPayProofThumbs();
}
function updatePayProofVisibility() {
  const wrap = $('payProofWrap');
  if (!wrap) return;
  const acct = payTarget && payTarget.acctno;
  const show = (settleMethod === 'transfer' || settleMethod === 'cheque') && !isRviAcct(acct);
  wrap.classList.toggle('hidden', !show);
  if (!show) clearPayProofPending();
}
async function uploadPayProofFiles(voucno, files) {
  const vo = String(voucno || '').trim();
  if (!vo || !(files && files.length)) return false;
  let any = false;
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); continue; }
    const fd = new FormData();
    fd.append('voucno', vo);
    fd.append('file', file);
    const r = await fetch('/receive-notes/api/images/payment', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) {
      alert(j.detail || j.error || 'อัปโหลดหลักฐานไม่สำเร็จ');
      return any;
    }
    any = true;
  }
  return any;
}
function setSettleMethod(method) {
  settleMethod = method === 'cheque' ? 'cheque' : (method === 'cash' ? 'cash' : 'transfer');
  ['transfer','cheque','cash'].forEach(m => {
    const el = $('settle' + m.charAt(0).toUpperCase() + m.slice(1));
    if (el) el.classList.toggle('on', settleMethod === m);
  });
  $('payChknoWrap').classList.toggle('hidden', settleMethod !== 'cheque');
  $('payBankWrap').classList.toggle('hidden', settleMethod === 'cash');
  if (settleMethod === 'transfer') {
    if (!$('payChkno').value.trim() || $('payChkno').dataset.auto === '1') {
      $('payChkno').value = 'โอน';
      $('payChkno').dataset.auto = '1';
    }
  } else if ($('payChkno').value.trim() === 'โอน' || $('payChkno').dataset.auto === '1') {
    $('payChkno').value = '';
    $('payChkno').dataset.auto = '1';
  }
  updatePayProofVisibility();
}
$('settleTransfer').onclick = () => setSettleMethod('transfer');
$('settleCheque').onclick = () => setSettleMethod('cheque');
$('settleCash').onclick = () => setSettleMethod('cash');
$('payChkno').addEventListener('input', () => { $('payChkno').dataset.auto = '0'; });
wireDropZone($('dropPayProof'), $('payProofFiles'), async (files) => {
  addPayProofFiles(files);
});
if ($('payProofCamera')) {
  $('payProofCamera').onchange = (ev) => {
    addPayProofFiles(ev.target.files);
    ev.target.value = '';
  };
}
if ($('payProofThumbs')) {
  $('payProofThumbs').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-pay-proof-del]');
    if (!btn) return;
    e.preventDefault();
    const idx = Number(btn.dataset.payProofDel);
    if (!Number.isFinite(idx) || idx < 0 || idx >= payProofPending.length) return;
    payProofPending.splice(idx, 1);
    renderPayProofThumbs();
  });
}

function applyPayDialogMode(isRefund, remain) {
  const refund = !!isRefund;
  if ($('payDlgTitle')) $('payDlgTitle').textContent = refund ? 'บันทึกคืนเงินลูกค้า' : 'บันทึกรับชำระ';
  if ($('paySectionTitle')) $('paySectionTitle').textContent = refund ? 'ข้อมูลการคืนเงิน' : 'ข้อมูลการรับชำระ';
  if ($('payMethodLabel')) $('payMethodLabel').textContent = refund ? 'วิธีคืนเงิน' : 'วิธีรับชำระ';
  if ($('payChkamtLabel')) $('payChkamtLabel').textContent = refund ? 'จำนวนเงินที่คืน (บาท)' : 'จำนวนเงินที่รับ (บาท)';
  if ($('payChkdateLabel')) $('payChkdateLabel').textContent = refund ? 'วันที่คืนเงิน' : 'วันที่รับเงิน';
  if ($('payBankLabel')) $('payBankLabel').textContent = refund ? 'บัญชีที่จ่ายคืน' : 'บัญชีที่รับเงิน';
  if ($('payNetLabel')) $('payNetLabel').textContent = refund ? 'ยอดเครดิต' : 'ยอดสุทธิ';
  if ($('payRemainWrap')) $('payRemainWrap').classList.toggle('hidden', !refund);
  if ($('payRemainAmt')) $('payRemainAmt').textContent = fmtMoney(remain || 0);
  if ($('btnConfirmPay')) $('btnConfirmPay').textContent = refund ? 'คืนเงินลูกค้า' : 'รับชำระ';
  if ($('payMethods')) $('payMethods').setAttribute('aria-label', refund ? 'วิธีคืนเงิน' : 'วิธีรับชำระ');
}
function openPay(acct, note, billamt, discount) {
  const bill = Number(billamt || 0);
  const disc = Number(discount || 0);
  const net = bill - disc;
  const row = pendingRows.find(r => r.acctno === acct && r.noteno === note)
    || findRow(`${acct}|${note}`);
  const refund = isRefundNote(row) || net < -1e-9;
  const remain = refund ? remainingRefundOf(row) || Math.abs(net) : 0;
  const payAmt = refund ? remain : net;
  payTarget = {
    acctno: acct, noteno: note, billamt: bill, discount: disc, netamt: net,
    is_refund: refund, remaining_refund: remain
  };
  $('payAcct').textContent = acct;
  $('payNote').textContent = displayNoteno(note);
  $('payBillAmt').textContent = fmtMoney(bill);
  $('payDiscountAmt').textContent = formatDiscountLabel((row || {}).reminder || {}, disc);
  $('payNetAmt').textContent = fmtMoney(refund ? -Math.abs(net) : net);
  applyPayDialogMode(refund, remain);
  $('payChkamt').value = (refund ? remain : net).toFixed(2);
  $('payChkdate').value = todayISO();
  const preferBank = noteReceiveBankKeyOf(row) || DEFAULT_PAY_BANK || '';
  if ($('payBankSelect') && preferBank) $('payBankSelect').value = preferBank;
  $('payMsg').innerHTML = '';
  $('payChkno').dataset.auto = '1';
  clearPayProofPending();
  const confirmBtn = $('btnConfirmPay');
  if (confirmBtn) { confirmBtn.dataset.busy = '0'; confirmBtn.disabled = false; }
  // Actual settle chosen at receive/refund time (default transfer).
  setSettleMethod('transfer');
  stopTigerPoll();
  wireDatePickers($('dlgPay'));
  $('dlgPay').showModal();
}
let tigerPollTimer = null;
function stopTigerPoll() {
  if (tigerPollTimer) { clearTimeout(tigerPollTimer); tigerPollTimer = null; }
}
function tigerVoucherImgSrc(image) {
  const raw = String(image || '').trim();
  if (!raw) return '';
  if (raw.startsWith('data:') || raw.startsWith('http://') || raw.startsWith('https://')) return raw;
  return 'data:image/png;base64,' + raw;
}
function renderTigerAwaiting(res, { refund }) {
  const st = esc(res.tiger_status || 'pending');
  if (!refund) {
    const tno = esc(res.tiger_payment_no || res.tiger_attempt_id || '');
    $('payMsg').innerHTML =
      `<p class="ok">รอ Tiger ยืนยันรับเงินสด… (${st}` +
      (tno ? ` · ${tno}` : '') + `)</p>`;
    return;
  }
  // Cash refund: show voucher QR for staff to scan at Tiger (KCN payout pattern).
  const v = res.voucher || {};
  const code = esc(v.voucher_num || v.code || res.tiger_payment_no || '');
  const imgSrc = tigerVoucherImgSrc(v.qr_image || v.image || '');
  let html = `<p class="ok">สร้าง Voucher คืนเงินแล้ว — สแกน QR ที่ตู้ Tiger เพื่อจ่ายเงินสด</p>`;
  html += `<div class="tiger-voucher-box">`;
  if (code) html += `<div class="tiger-voucher-code">${code}</div>`;
  if (imgSrc) {
    html += `<img alt="Tiger voucher QR" src="${imgSrc}"/>`;
  } else if (code) {
    html += `<p class="muted" style="margin:.45rem 0 0">พิมพ์รหัสด้านบนที่ตู้ Tiger</p>`;
  } else {
    html += `<p class="muted" style="margin:.45rem 0 0">รอเลข voucher จาก Tiger…</p>`;
  }
  html += `</div>`;
  html += `<p class="muted">รอเครื่องยืนยันจ่ายคืนเงินสด… (${st})</p>`;
  $('payMsg').innerHTML = html;
}
async function finishPaySuccess(res, method, opts) {
  opts = opts || {};
  const attachedProof = !!opts.attachedProof;
  const refund = !!(payTarget && payTarget.is_refund) || !!res.is_refund;
  const vouc = esc(res.voucno || '');
  if (refund && (res.partial || res.kss_deferred || !vouc)) {
    const remain = Number(res.remaining_refund != null ? res.remaining_refund : 0);
    $('payMsg').innerHTML =
      `<p class="ok">บันทึกคืนเงินแล้ว · ค้างคืน ${fmtMoney(remain)}` +
      (vouc ? ` · ${vouc}` : '') + `</p>`;
    clearPayProofPending();
    setTimeout(() => { $('dlgPay').close(); showTab('pending'); }, 700);
    return;
  }
  $('payMsg').innerHTML = `<p class="ok">บันทึกแล้ว · ${vouc || (refund ? 'ใบสำคัญจ่าย' : '')}` +
    (attachedProof ? ' · แนบหลักฐานแล้ว' : '') + `</p>`;
  const skipProof = attachedProof
    || res.proof_required === false
    || method === 'cash'
    || String(res.voucno || '').toUpperCase().startsWith('RVI')
    || String(res.voucno || '').toUpperCase().startsWith('PVN');
  clearPayProofPending();
  setTimeout(() => { $('dlgPay').close(); showTab(skipProof ? 'voucher' : 'awaitproof'); }, 700);
}
async function pollTigerVoucher(receiptId, method) {
  const rid = String(receiptId || '').trim();
  if (!rid) return;
  const refund = !!(payTarget && payTarget.is_refund);
  try {
    const res = await api('/vouchers/tiger-status?receipt_id=' + encodeURIComponent(rid));
    if (res.awaiting_tiger) {
      renderTigerAwaiting(res, { refund });
      tigerPollTimer = setTimeout(() => pollTigerVoucher(rid, method), 1500);
      return;
    }
    stopTigerPoll();
    await finishPaySuccess(res, method);
  } catch (e) {
    stopTigerPoll();
    $('payMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    const btn = $('btnConfirmPay');
    if (btn) { btn.dataset.busy = '0'; btn.disabled = false; }
  }
}
$('btnConfirmPay').onclick = async () => {
  const btn = $('btnConfirmPay');
  if (btn && btn.dataset.busy === '1') return;
  if (!WRITE_ENABLED) { $('payMsg').innerHTML = '<p class="err">KSS write ปิดอยู่</p>'; return; }
  if (!payTarget) return;
  stopTigerPoll();
  const refund = !!payTarget.is_refund;
  const chkno = settleMethod === 'transfer' ? ($('payChkno').value.trim() || 'โอน')
    : settleMethod === 'cash' ? $('payChkno').value.trim()
    : $('payChkno').value.trim();
  const chkamt = Number($('payChkamt').value || 0);
  if (settleMethod === 'cheque' && !chkno) {
    $('payMsg').innerHTML = '<p class="err">กรอกเลขที่เช็ค</p>'; return;
  }
  if (chkamt <= 0 && (payTarget.netamt > 0 || refund)) {
    $('payMsg').innerHTML = `<p class="err">${refund ? 'กรอกจำนวนเงินที่คืน' : 'กรอกจำนวนเงินที่รับ'}</p>`; return;
  }
  if (refund && payTarget.remaining_refund != null && chkamt - Number(payTarget.remaining_refund) > 0.01) {
    $('payMsg').innerHTML = '<p class="err">จำนวนเงินเกินยอดค้างคืน</p>'; return;
  }
  if (btn) { btn.dataset.busy = '1'; btn.disabled = true; }
  const pendingProof = payProofPending.slice();
  const canAttachNow = (settleMethod === 'transfer' || settleMethod === 'cheque')
    && !isRviAcct(payTarget.acctno)
    && pendingProof.length > 0;
  try {
    const res = await api('/vouchers', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: payTarget.acctno, noteno: payTarget.noteno,
        settle_method: settleMethod, chkno, chkamt,
        chkdate: $('payChkdate').value,
        pay_bank: $('payBankSelect').value.trim()
      })
    });
    if (res.awaiting_tiger && res.receipt_id) {
      renderTigerAwaiting(res, { refund });
      pollTigerVoucher(res.receipt_id, settleMethod);
      return;
    }
    let attachedProof = false;
    if (canAttachNow && res.voucno) {
      $('payMsg').innerHTML = '<p class="muted">กำลังแนบหลักฐาน…</p>';
      attachedProof = await uploadPayProofFiles(res.voucno, pendingProof);
      if (attachedProof) {
        try { await loadAwaitProof(); } catch (_) {}
        try { await loadVouchers(); } catch (_) {}
      }
    }
    await finishPaySuccess(res, settleMethod, { attachedProof });
  } catch (e) {
    stopTigerPoll();
    $('payMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    if (btn) { btn.dataset.busy = '0'; btn.disabled = false; }
  }
};
$('btnClosePay').onclick = () => { stopTigerPoll(); $('dlgPay').close(); };
$('btnCancelPay').onclick = () => { stopTigerPoll(); $('dlgPay').close(); };

let vendorTimer = null;
async function searchVendors() {
  const q = $('vendorQ').value.trim();
  if (!q) { $('vendorResults').classList.add('hidden'); return; }
  $('vendorResults').classList.remove('hidden');
  $('vendorResults').innerHTML = '<div class="muted" style="padding:.6rem">กำลังค้นหา…</div>';
  try {
    const rows = await api('/vendors?q=' + encodeURIComponent(q));
    $('vendorResults').innerHTML = rows.map(v =>
      `<button type="button" data-acct="${esc(v.acctno)}" data-name="${esc(v.acctname)}">${esc(v.acctno)} — ${esc(v.acctname)}</button>`
    ).join('') || '<div class="muted" style="padding:.6rem">ไม่พบ</div>';
    $('vendorResults').querySelectorAll('button[data-acct]').forEach(b => {
      b.onclick = () => pickVendor(b.dataset.acct, b.dataset.name);
    });
  } catch (e) { $('vendorResults').innerHTML = `<div class="err" style="padding:.6rem">${esc(e.message)}</div>`; }
}
$('vendorQ').addEventListener('input', () => {
  clearTimeout(vendorTimer);
  vendorTimer = setTimeout(searchVendors, 280);
});
$('vendorQ').addEventListener('keydown', (e) => {
  if (e.key === 'Enter') { e.preventDefault(); searchVendors(); }
});
document.addEventListener('click', (e) => {
  if (!e.target.closest('.combo')) {
    $('vendorResults').classList.add('hidden');
    $('byApVendorResults').classList.add('hidden');
  }
});

async function pickVendor(acctno, acctname) {
  picked = {acctno, acctname};
  $('vendorQ').value = `${acctno} — ${acctname}`;
  $('pickedVendor').textContent = `${acctno} — ${acctname}`;
  $('pickedVendor').classList.remove('hidden');
  $('vendorResults').classList.add('hidden');
  fillRemarkForm('note', {}, acctno);
  if (!$('dueDate').value) $('dueDate').value = todayISO();
  await loadBills();
}

async function loadBills() {
  if (!picked) {
    $('billList').innerHTML = `<tr><td colspan="4" class="empty">เลือกลูกหนี้ก่อน</td></tr>`;
    updateBillSelectStatus();
    return;
  }
  $('billList').innerHTML = `<tr><td colspan="4" class="empty">กำลังโหลดบิล…</td></tr>`;
  try {
    const rows = await api('/bills?acctno=' + encodeURIComponent(picked.acctno));
    $('billList').innerHTML = rows.map(b =>
      `<tr>
        <td data-label=""><input type="checkbox" value="${esc(b.BILLNO)}" data-amt="${Number(b.AFTERTAX)||0}" data-billdate="${esc(String(b.BILLDATE||'').slice(0,10))}" aria-label="เลือกบิล ${esc(b.BILLNO)}"/></td>
        <td data-label="เลขที่บิล">${esc(b.BILLNO)}</td>
        <td data-label="วันที่">${fmtDate(b.BILLDATE)}</td>
        <td class="num" data-label="ยอด (บาท)">${fmtMoney(b.AFTERTAX)}</td>
      </tr>`
    ).join('') || `<tr><td colspan="4" class="empty">ไม่มีบิลว่าง (บิลที่ผูกโน้ตแล้วจะไม่แสดง)</td></tr>`;
    $('billList').querySelectorAll('input[type=checkbox]').forEach(cb => {
      cb.addEventListener('change', updateBillSelectStatus);
    });
  } catch (e) {
    $('billList').innerHTML = `<tr><td colspan="4" class="err">${esc(e.message)}</td></tr>`;
  }
  updateBillSelectStatus();
}
function selectedBillTotal() {
  const checked = [...$('billList').querySelectorAll('input[type=checkbox]:checked')];
  return { n: checked.length, total: checked.reduce((s, cb) => s + (Number(cb.dataset.amt) || 0), 0) };
}
/** Discount overflow only applies to non-negative bill totals; negative CN nets are valid. */
function discExceedsBill(disc, bill) {
  return Number(bill) >= 0 && Number(disc) - Number(bill) > 1e-9;
}
function resolveDiscAmount(bill) {
  const raw = Number($('discInput').value || 0);
  if (discMode === 'percent') return Math.round(bill * Math.min(raw, 100) / 100 * 100) / 100;
  return Math.round(raw * 100) / 100;
}
function syncCreatePayButton() {
  const btn = $('btnCreateAndPay');
  if (!btn) return;
  const { total } = selectedBillTotal();
  const net = total - resolveDiscAmount(total);
  btn.textContent = net < -1e-9 ? 'บันทึกและคืนเงินลูกค้า' : 'บันทึกและรับชำระ';
}
function syncDiscPreview() {
  const { total } = selectedBillTotal();
  const disc = resolveDiscAmount(total);
  $('discBillAmt').textContent = fmtMoney(total);
  $('discResolved').textContent = fmtMoney(disc);
  $('discNetAmt').textContent = fmtMoney(total - disc);
  $('discResolved').style.color = discExceedsBill(disc, total) ? 'var(--down)' : '';
  syncCreatePayButton();
}
function setDiscMode(mode) {
  discMode = mode === 'percent' ? 'percent' : 'amount';
  $('discModeAmount').classList.toggle('on', discMode === 'amount');
  $('discModePercent').classList.toggle('on', discMode === 'percent');
  $('discInputLabel').textContent = discMode === 'percent' ? 'ส่วนลด (%)' : 'ส่วนลด (บาท)';
  $('discInput').max = discMode === 'percent' ? '100' : '';
  syncDiscPreview();
}
$('discModeAmount').onclick = () => setDiscMode('amount');
$('discModePercent').onclick = () => setDiscMode('percent');
$('discInput').addEventListener('input', syncDiscPreview);
function updateBillSelectStatus() {
  const { n, total } = selectedBillTotal();
  $('billSelectStatus').textContent = `เลือก ${n} บิล`;
  $('billSelectTotal').textContent = `ยอดรวม ${fmtMoney(total)} บาท`;
  syncDiscPreview();
  if (!$('noteBillMonth').value) {
    const bills = [...$('billList').querySelectorAll('input:checked')].map(cb => ({ BILLDATE: cb.dataset.billdate }));
    const ym = suggestBillMonthYm(bills);
    if (ym) {
      $('noteBillMonth').value = ym;
      syncRemarkPreview('note', picked?.acctno || '');
    }
  }
}

function renderProofVerify(result) {
  const box = $('detProofVerify');
  const ackWrap = $('proofMismatchAckWrap');
  const btnDone = $('btnProofDone');
  if (!box) return;
  proofVerifyResult = result;
  if (!result || !AI_ENABLED) {
    box.classList.add('hidden');
    ackWrap?.classList.add('hidden');
    btnDone?.classList.add('hidden');
    return;
  }
  if (result.match) {
    box.className = 'ai-panel ai-ok';
    box.innerHTML = `✓ ยอดสลิปตรงกับยอดชำระ ${fmtMoney(result.expected_amount)} บาท`;
    ackWrap?.classList.add('hidden');
    if ($('proofMismatchAck')) $('proofMismatchAck').checked = false;
    btnDone?.classList.add('hidden');
    proofPendingComplete = false;
  } else {
    box.className = 'ai-panel ai-warn';
    box.innerHTML = `⚠ ยอดสลิป ${fmtMoney(result.extracted_amount)} บาท ไม่ตรงกับยอดชำระ ${fmtMoney(result.expected_amount)} บาท (ต่าง ${fmtMoney(result.difference)})`;
    ackWrap?.classList.remove('hidden');
    if ($('proofMismatchAck')) $('proofMismatchAck').checked = false;
    btnDone?.classList.remove('hidden');
    if (btnDone) btnDone.disabled = true;
    proofPendingComplete = true;
  }
  box.classList.remove('hidden');
}

function proofCanComplete() {
  if (!proofPendingComplete) return true;
  return !!($('proofMismatchAck') && $('proofMismatchAck').checked);
}

function completeProofFlow(fresh) {
  if (!proofCanComplete()) return;
  proofPendingComplete = false;
  $('dlgDetail').close();
  showTab('voucher');
  if (fresh) openDetailByKey(keyOf(fresh), {voucher: true});
}

$('proofMismatchAck')?.addEventListener('change', () => {
  if ($('btnProofDone')) $('btnProofDone').disabled = !proofCanComplete();
});
$('btnProofDone')?.addEventListener('click', () => {
  const fresh = voucherRows.find(x => keyOf(x) === keyOf(detailRow)) || awaitProofRows.find(x => keyOf(x) === keyOf(detailRow));
  completeProofFlow(fresh);
});

$('btnRefreshBills').onclick = () => loadBills();

let createInFlight = false;
async function createNote({ openPayAfter = false } = {}) {
  const btnCreate = $('btnCreateNote');
  const btnAndPay = $('btnCreateAndPay');
  const createBusy = createInFlight
    || (btnCreate && btnCreate.dataset.busy === '1')
    || (btnAndPay && btnAndPay.dataset.busy === '1');
  if (createBusy) return;
  const due = $('dueDate').value || todayISO();
  const billnos = [...$('billList').querySelectorAll('input:checked')].map(x => x.value);
  $('createMsg').innerHTML = '';
  if (!WRITE_ENABLED) { $('createMsg').innerHTML = '<p class="err">KSS write ปิดอยู่ (RECEIVE_NOTES_WRITE_ENABLED)</p>'; return; }
  if (!picked) { $('createMsg').innerHTML = '<p class="err">เลือกลูกหนี้</p>'; return; }
  if (!billnos.length) { $('createMsg').innerHTML = '<p class="err">เลือกบิลอย่างน้อย 1</p>'; return; }
  const { total } = selectedBillTotal();
  if (discExceedsBill(resolveDiscAmount(total), total)) {
    $('createMsg').innerHTML = '<p class="err">ส่วนลดมากกว่ายอดบิล</p>'; return;
  }
  const setCreateBusy = (on) => {
    [btnCreate, btnAndPay].forEach((btn) => {
      if (!btn) return;
      btn.dataset.busy = on ? '1' : '0';
      btn.disabled = !!on;
    });
  };
  // Sync lock before any await so double-click create-and-pay cannot race.
  createInFlight = true;
  setCreateBusy(true);
  let confirmUnmapped = false;
  try {
    let res;
    while (true) {
      try {
        res = await api('/notes', {
          method:'POST', headers:{'Content-Type':'application/json'},
          body: JSON.stringify({
            acctno: picked.acctno,
            acctname: picked.acctname,
            billnos,
            discount_mode: discMode,
            discount_input: Number($('discInput').value || 0),
            receive_bank_key: ($('noteReceiveBank') && $('noteReceiveBank').value) || '',
            due_date: due,
            ...readRemarkForm('note'),
            confirm_unmapped: confirmUnmapped
          })
        });
        break;
      } catch (e) {
        await confirmUnmappedOrThrow(e);
        confirmUnmapped = true;
      }
    }
    const rem = res.reminder || {};
    const discShow = Number(rem.discount_amount != null ? rem.discount_amount : resolveDiscAmount(total));
    const netShow = Number(res.billamt || total) - discShow;
    const noteLabel = esc(res.noteno_display || displayNoteno(res.noteno));
    const discLabel = esc(formatDiscountLabel(rem, discShow, {withPrefix: true}));
    const reuseNote = res.is_reused_label && res.reuse_hint
      ? `<br/><span class="note-reuse-hint" style="display:inline-block;margin-top:.45rem">${esc(res.reuse_hint)}</span>`
      : '';
    const discBit = discShow ? ` · ${discLabel}` : '';
    const isRefundNet = netShow < -1e-9;
    const okExtra = openPayAfter
      ? (isRefundNet ? ' · เปิดคืนเงินลูกค้า' : ' · เปิดรับชำระ')
      : '';
    const amtWord = isRefundNet ? 'เครดิต' : 'รับ';
    $('createMsg').innerHTML = `<p class="ok">บันทึกใบวางบิลแล้ว · ${noteLabel}${discBit} · ${amtWord} ${fmtMoney(netShow)}${okExtra}${reuseNote}</p>`;
    $('discInput').value = '0.00';
    resetRemarkForm('note', picked?.acctno || '');
    noteReceiveBankKey = '';
    fillReceiveBankSelect($('noteReceiveBank'), '');
    setDiscMode('amount');
    await loadBills();
    if (openPayAfter) {
      // Keep note in รอรับชำระ/รอคืนเงิน if modal is closed without settle.
      await loadPending();
      openPay(
        res.acctno || picked.acctno,
        res.noteno,
        Number(res.billamt || total),
        discShow
      );
    } else {
      setTimeout(() => { showTab('pending'); }, 600);
    }
  } catch (e) {
    $('createMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    await loadBills();
  } finally {
    createInFlight = false;
    setCreateBusy(false);
  }
}
$('btnCreateNote').onclick = () => createNote({ openPayAfter: false });
$('btnCreateAndPay').onclick = () => createNote({ openPayAfter: true });

async function openEditNote(key, returnTab) {
  const row = findRow(key) || pendingRows.find(r => keyOf(r) === key);
  if (!row || !row.is_editable) { alert('ใบวางบิลนี้แก้ไขไม่ได้'); return; }
  editTarget = row;
  editReturnTab = returnTab || 'pending';
  showEditPanel(true);
  setCrumb('edit', `${notenoReuseMeta(row).display} · ${row.acctno}`);
  $('editTitle').textContent = `แก้ไขใบวางบิล ${notenoReuseMeta(row).display}`;
  $('editVendor').value = `${row.acctno} — ${row.acctname || ''}`;
  $('editNoteno').value = notenoReuseMeta(row).display;
  renderNotenoReuseHint($('editReuseWrap'), row);
  const rem = row.reminder || {};
  $('editDueDate').value = remDue(row);
  fillRemarkForm('edit', rem, row.acctno);
  editReceiveBankKey = noteReceiveBankKeyOf(row);
  fillReceiveBankSelect($('editReceiveBank'), editReceiveBankKey);
  editDiscMode = rem.discount_mode === 'percent' ? 'percent' : 'amount';
  $('editDiscInput').value = rem.discount_input != null ? rem.discount_input : (rem.discount_amount || 0);
  setEditDiscMode(editDiscMode);
  $('editMsg').innerHTML = '';
  if ($('btnCancelNote')) $('btnCancelNote').classList.toggle('hidden', !WRITE_ENABLED);
  await loadEditBills();
  wireDatePickers($('panelEdit'));
}
async function loadEditBills() {
  if (!editTarget) return;
  $('editBillList').innerHTML = `<tr><td colspan="4" class="empty">กำลังโหลด…</td></tr>`;
  const rows = await api('/bills?acctno=' + encodeURIComponent(editTarget.acctno) + '&noteno=' + encodeURIComponent(editTarget.noteno));
  $('editBillList').innerHTML = rows.map(b =>
    `<tr>
      <td data-label=""><input type="checkbox" value="${esc(b.BILLNO)}" data-amt="${Number(b.AFTERTAX)||0}" data-billdate="${esc(String(b.BILLDATE||'').slice(0,10))}" ${b.attached ? 'checked' : ''} aria-label="เลือกบิล ${esc(b.BILLNO)}"/></td>
      <td data-label="เลขที่บิล">${esc(b.BILLNO)}</td>
      <td data-label="วันที่">${fmtDate(b.BILLDATE)}</td>
      <td class="num" data-label="ยอด (บาท)">${fmtMoney(b.AFTERTAX)}</td>
    </tr>`
  ).join('') || `<tr><td colspan="4" class="empty">ไม่มีบิล</td></tr>`;
  $('editBillList').querySelectorAll('input[type=checkbox]').forEach(cb => cb.addEventListener('change', updateEditBillSelectStatus));
  updateEditBillSelectStatus();
}
function editSelectedBillTotal() {
  const checked = [...$('editBillList').querySelectorAll('input[type=checkbox]:checked')];
  return { n: checked.length, total: checked.reduce((s, cb) => s + (Number(cb.dataset.amt) || 0), 0) };
}
function resolveEditDiscAmount(bill) {
  const raw = Number($('editDiscInput').value || 0);
  if (editDiscMode === 'percent') return Math.round(bill * Math.min(raw, 100) / 100 * 100) / 100;
  return Math.round(raw * 100) / 100;
}
function syncEditDiscPreview() {
  const { total } = editSelectedBillTotal();
  const disc = resolveEditDiscAmount(total);
  $('editDiscBillAmt').textContent = fmtMoney(total);
  $('editDiscResolved').textContent = fmtMoney(disc);
  $('editDiscNetAmt').textContent = fmtMoney(total - disc);
  if ($('editDiscResolved')) {
    $('editDiscResolved').style.color = discExceedsBill(disc, total) ? 'var(--down)' : '';
  }
}
function setEditDiscMode(mode) {
  editDiscMode = mode === 'percent' ? 'percent' : 'amount';
  $('editDiscModeAmount').classList.toggle('on', editDiscMode === 'amount');
  $('editDiscModePercent').classList.toggle('on', editDiscMode === 'percent');
  $('editDiscInputLabel').textContent = editDiscMode === 'percent' ? 'ส่วนลด (%)' : 'ส่วนลด (บาท)';
  syncEditDiscPreview();
}
function updateEditBillSelectStatus() {
  const { n, total } = editSelectedBillTotal();
  $('editBillSelectStatus').textContent = `เลือก ${n} บิล`;
  $('editBillSelectTotal').textContent = `ยอดรวม ${fmtMoney(total)} บาท`;
  syncEditDiscPreview();
  if (!$('editBillMonth').value) {
    const bills = [...$('editBillList').querySelectorAll('input:checked')].map(cb => ({ BILLDATE: cb.dataset.billdate }));
    const ym = suggestBillMonthYm(bills);
    if (ym) {
      $('editBillMonth').value = ym;
      syncRemarkPreview('edit', editTarget?.acctno || '');
    }
  }
}
$('editDiscModeAmount').onclick = () => setEditDiscMode('amount');
$('editDiscModePercent').onclick = () => setEditDiscMode('percent');
$('editDiscInput').addEventListener('input', syncEditDiscPreview);
$('btnRefreshEditBills').onclick = () => loadEditBills();
$('btnSaveEdit').onclick = async () => {
  if (!editTarget || !WRITE_ENABLED) { $('editMsg').innerHTML = '<p class="err">KSS write ปิดอยู่</p>'; return; }
  const billnos = [...$('editBillList').querySelectorAll('input:checked')].map(x => x.value);
  if (!billnos.length) { $('editMsg').innerHTML = '<p class="err">เลือกบิลอย่างน้อย 1</p>'; return; }
  const { total } = editSelectedBillTotal();
  if (discExceedsBill(resolveEditDiscAmount(total), total)) {
    $('editMsg').innerHTML = '<p class="err">ส่วนลดมากกว่ายอดบิล</p>'; return;
  }
  try {
    await api(`/notes${noteQs(editTarget.acctno, editTarget.noteno)}`, {
      method:'PATCH', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        billnos,
        due_date: $('editDueDate').value,
        ...readRemarkForm('edit'),
        receive_bank_key: ($('editReceiveBank') && $('editReceiveBank').value) || '',
        discount_mode: editDiscMode,
        discount_input: Number($('editDiscInput').value || 0),
      })
    });
    $('editMsg').innerHTML = '<p class="ok">บันทึกแล้ว</p>';
    editTarget = null;
    setTimeout(() => showTab(editReturnTab), 500);
  } catch (e) { $('editMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`; }
};

async function cancelNoteByKey(key, returnTab, opts) {
  opts = opts || {};
  if (!WRITE_ENABLED) { alert('KSS write ปิดอยู่'); return; }
  const row = findRow(key) || pendingRows.find(r => keyOf(r) === key) || (editTarget && keyOf(editTarget) === key ? editTarget : null);
  if (!row) { alert('ไม่พบใบวางบิล'); return; }
  if (isCanceledRow(row)) {
    alert('ใบวางบิลนี้ยกเลิกแล้ว');
    return;
  }
  if (row.is_editable === false || (row.voucno || '').trim()) {
    alert('ไม่สามารถยกเลิกใบวางบิลที่มีการรับชำระแล้ว');
    return;
  }
  const label = notenoReuseMeta(row).display || row.noteno;
  const ok = confirm(
    `ยกเลิกใบวางบิล ${label} ของ ${row.acctno}?\n\nคงเลขเอกสารเดิม · สถานะเป็น "ยกเลิก" ทั้งระบบใหม่และ KSS · บิลที่ผูกไว้จะกลับมาเลือกได้ใหม่`
  );
  if (!ok) return;
  try {
    await api(`/notes${noteQs(row.acctno, row.noteno)}`, { method: 'DELETE' });
    if (opts.closeDetail) {
      try { $('dlgDetail').close(); } catch (_) {}
      detailRow = null;
    }
    if (editTarget && keyOf(editTarget) === keyOf(row)) {
      editTarget = null;
      showEditPanel(false);
    }
    await Promise.all([loadPending(), loadAwaitProof(), loadVouchers()]);
    if (byApVendor?.acctno === row.acctno) await loadByAp();
    if (returnTab) showTab(returnTab === 'byap' ? 'byap' : 'pending');
    else showTab('pending');
  } catch (e) {
    alert(e.message || 'ยกเลิกไม่สำเร็จ');
  }
}
$('btnCancelNote')?.addEventListener('click', () => {
  if (!editTarget) return;
  cancelNoteByKey(keyOf(editTarget), editReturnTab || 'pending');
});

wireDatePickers(document);
setDiscMode('amount');
noteReceiveBankKey = '';
$('billList').innerHTML = `<tr><td colspan="4" class="empty">เลือกลูกหนี้ก่อน</td></tr>`;
initPayBankSelect();
(function boot() {
  const h = (location.hash || '').replace('#','');
  if (h === 'pending') showTab('pending');
  else if (h === 'awaitproof') showTab('awaitproof');
  else if (h === 'voucher' || h === 'vouchers') showTab('voucher');
  else if (h === 'byap') showTab('byap');
  else showTab('create');
})();
</script>
</body>
</html>
"""

from __future__ import annotations

import html as html_lib
import json
import re

APP = "pay-notes"
SESSION_COOKIE = "kcw_pay_notes"


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
    ai_flag = "true" if ai_enabled else "false"
    return (
        _HTML.replace("__USER_JSON__", json.dumps(who, ensure_ascii=False))
        .replace("__USER__", html_lib.escape(who))
        .replace("__SITE__", site_u)
        .replace("__WRITE__", write_flag)
        .replace("__AI__", ai_flag)
        .replace("__INITIALS__", html_lib.escape(initials(who)))
    )


_HTML = r"""<!doctype html>
<html lang="th" data-theme="light">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover"/>
<meta name="color-scheme" content="light dark"/>
<meta name="theme-color" content="#f3f5f9" id="themeColor"/>
<title>ชำระเจ้าหนี้</title>
<script>
(function () {
  try {
    var t = localStorage.getItem("kcw.pay_notes.theme");
    if (t !== "light" && t !== "dark") t = "light";
    document.documentElement.setAttribute("data-theme", t);
  } catch (e) {}
})();
</script>
<link href="https://fonts.googleapis.com/css2?family=Prompt:wght@400;500;600;700&display=swap" rel="stylesheet"/>
<style>
:root {
  --acc:#2f6bff; --acc-soft:#e8f0ff; --on-acc:#fff;
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
  --chip:#243040; --inset:#0a0e12; --acc-soft:#1a2744;
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
  border-bottom:1px solid var(--line); padding:.85rem var(--space-page-x) 0;
}
.topbar { display:flex; align-items:center; justify-content:space-between; gap:.75rem; }
h1 { margin:0; font-size:1.2rem; font-weight:700; letter-spacing:-.01em; }
.crumb { font-size:.78rem; color:var(--muted); margin-top:.15rem; }
.avatar {
  width:2.15rem; height:2.15rem; border-radius:50%; border:0;
  background:#dbeafe; color:#1d4ed8; font-weight:700; font-size:.78rem;
  flex:0 0 auto;
}
html[data-theme="dark"] .avatar { background:#1e3a5f; color:#93c5fd; }
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
.btn.outline { color:var(--acc); border-color:#bfdbfe; background:var(--card); }
.btn.block { width:100%; }
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
.kpi-all .mark { background:#dbeafe; color:var(--acc); }
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
.thumbs { display:flex; gap:.4rem; flex-wrap:wrap; margin-top:.5rem; }
.thumbs img { width:72px; height:72px; object-fit:cover; border-radius:.4rem; border:1px solid var(--line); }
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
.sum-box .net .k, .sum-box .net .v { font-weight:700; }
.sum-box .net .v { color:var(--acc); }
.methods { display:grid; grid-template-columns:repeat(3, 1fr); gap:.45rem; margin:.25rem 0 .75rem; }
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
  @page { size: A4 portrait; margin: 10mm 9mm; }
  html, body { background:#fff !important; }
  body > *:not(#printSheet) { display:none !important; }
  #printSheet {
    display:block !important; position:static; width:100%;
    color:#111; background:#fff; font-family: "Prompt", "TH Sarabun New", sans-serif;
    -webkit-print-color-adjust: exact; print-color-adjust: exact;
  }
}
.pv { font-size:11pt; color:#111; }
.pv-top { display:flex; justify-content:space-between; align-items:flex-start; gap:12px; }
.pv-logo {
  font-weight:800; font-size:28pt; color:#c41e3a; letter-spacing:-.03em; line-height:1;
  font-family: Impact, "Arial Black", Prompt, sans-serif;
}
.pv-co { font-size:9.5pt; line-height:1.35; }
.pv-co-name { font-weight:700; font-size:12pt; margin:.15rem 0 .1rem; }
.pv-title-wrap { text-align:right; min-width:14rem; }
.pv-title {
  display:inline-block; background:#f5d76e; font-weight:800; font-size:13pt;
  padding:.28rem .7rem; border:1px solid #111; letter-spacing:.01em;
}
.pv-month { margin-top:.45rem; font-size:10.5pt; }
.pv-meta {
  display:grid; grid-template-columns:1fr 1fr; gap:.2rem 1.2rem;
  margin:.7rem 0 .5rem; font-size:11pt; border-top:1px solid #111; padding-top:.45rem;
}
.pv-meta .span2 { grid-column:1 / -1; }
.pv-table { width:100%; border-collapse:collapse; margin-top:.15rem; font-size:10pt; }
.pv-table th, .pv-table td { border:1px solid #111; padding:.22rem .35rem; vertical-align:top; }
.pv-table th { font-weight:700; text-align:center; background:#f7f7f7; font-size:9.5pt; }
.pv-table .num { text-align:right; font-variant-numeric:tabular-nums; }
.pv-table .item { font-size:9pt; }
.pv-table .bill td { font-weight:600; background:#f3f3f3; }
.pv-foot { display:flex; justify-content:space-between; gap:1rem; margin-top:.55rem; align-items:flex-start; }
.pv-words { flex:1; font-size:10.5pt; padding-top:.35rem; }
.pv-tot { min-width:16rem; font-size:11pt; }
.pv-tot .row { display:flex; justify-content:space-between; gap:1rem; padding:.12rem 0; }
.pv-tot .n { font-variant-numeric:tabular-nums; }
.pv-pay { margin-top:.7rem; display:flex; justify-content:space-between; gap:1rem; align-items:flex-start; }
.pv-checks { font-size:11pt; }
.pv-amt-red { color:#c41e3a; font-weight:800; font-size:13pt; font-variant-numeric:tabular-nums; }
.pv-paytbl { border-collapse:collapse; font-size:10pt; min-width:22rem; }
.pv-paytbl th, .pv-paytbl td { border:1px solid #111; padding:.2rem .4rem; }
.pv-sign { display:flex; justify-content:space-between; margin-top:1.6rem; font-size:10.5pt; }
.pv-sign .col { width:48%; }
.pv-sign .line { border-bottom:1px dotted #333; min-height:1.6rem; margin:.15rem 0 .35rem; }
</style>
</head>
<body>
<header>
  <div class="topbar">
    <div>
      <h1 id="pageTitle">ชำระเจ้าหนี้ · __SITE__</h1>
      <div class="crumb" id="pageCrumb">__USER__ · HQ only</div>
    </div>
    <button type="button" class="avatar" id="themeBtn" title="สลับธีม" aria-label="สลับธีม">__INITIALS__</button>
  </div>
  <nav class="tabs" aria-label="ขั้นตอนงาน">
    <button type="button" id="tabCreate" class="on"><span class="t-full">1. สร้าง</span><span class="t-short">1. สร้าง</span></button>
    <button type="button" id="tabPending"><span class="t-full">2. รอชำระ</span><span class="t-short">2. รอจ่าย</span></button>
    <button type="button" id="tabAwaitProof"><span class="t-full">3. รอแนบหลักฐาน</span><span class="t-short">3. หลักฐาน</span></button>
    <button type="button" id="tabVoucher"><span class="t-full">4. ใบสำคัญจ่าย</span><span class="t-short">4. สำคัญจ่าย</span></button>
    <button type="button" id="tabByAp"><span class="t-full">ค้นหาตามเจ้าหนี้</span><span class="t-short">ค้นหาเจ้าหนี้</span></button>
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

      <div class="create-mode" id="createModeToggle">
        <button type="button" data-mode="manual" class="on" id="btnModeManual">กรอกเอง</button>
        <button type="button" data-mode="assist" id="btnModeAssist">ช่วยอ่านเอกสาร</button>
      </div>
      <div class="wizard-nav hidden" id="wizardNav">
        <span class="muted" id="wizardProgress">ขั้น 1/6</span>
        <div style="display:flex;gap:.4rem">
          <button type="button" class="btn sm ghost" id="btnWizardBack">ย้อนกลับ</button>
          <button type="button" class="btn sm primary" id="btnWizardNext">ถัดไป</button>
        </div>
      </div>

        <div class="step wizard-block" data-assist-step="1" id="wizardStepVendor">
          <div class="step-num">1</div>
          <div class="step-body">
            <h3>เลือกเจ้าหนี้</h3>
            <div class="combo">
              <div class="field">
                <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
                <input id="vendorQ" placeholder="ค้นหา รหัส / ชื่อเจ้าหนี้" autocomplete="off"/>
              </div>
              <div id="vendorResults" class="combo-list hidden"></div>
            </div>
            <div id="pickedVendor" class="picked hidden"></div>
          </div>
        </div>

        <div class="step wizard-block hidden" data-assist-step="2" id="wizardScanBlock">
          <div class="step-num">2</div>
          <div class="step-body">
            <h3>สแกนเอกสารจากเจ้าหนี้</h3>
            <p class="date-hint">อ่านเลขบิลและยอดจากใบวางบิล/statement แล้วเลือกบิลในระบบให้ตรง</p>
            <div class="drop" id="dropScan" tabindex="0">
              <div style="font-size:1.4rem;margin-bottom:.25rem">📄</div>
              <div>คลิกหรือลากเอกสารมาวางที่นี่</div>
              <div class="date-hint">JPG, PNG, PDF (ไม่เกิน 10 MB)</div>
            </div>
            <input id="scanFiles" class="hidden" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf"/>
            <div id="scanStatus" class="muted" style="margin-top:.45rem"></div>
            <button type="button" class="btn sm ghost hidden" id="btnScanSkip" style="margin-top:.45rem">ข้ามไปเลือกบิลเอง</button>
          </div>
        </div>

        <div class="step wizard-block" data-assist-step="5" id="wizardStepDetails">
          <div class="step-num">2</div>
          <div class="step-body">
            <h3>ข้อมูลใบวางบิล</h3>
            <div class="grid-3">
              <div>
                <label class="lbl" for="noteno">เลขที่ใบวางบิล</label>
                <input class="inp" id="noteno" maxlength="15" placeholder="สูงสุด 15 ตัวอักษร"/>
              </div>
              <div>
                <label class="lbl" for="dueDate">วันครบกำหนดชำระ</label>
                <input class="inp date-ce" id="dueDate" type="date" lang="en" inputmode="none"/>
              </div>
              <div>
                <label class="lbl" for="bankSelect">บัญชีธนาคารปลายทาง</label>
                <select class="inp" id="bankSelect"><option value="">— เลือกบัญชี —</option></select>
              </div>
            </div>
            <p class="date-hint">แตะวันที่เพื่อเปิดปฏิทิน · ใช้ปี ค.ศ. เช่น 2026</p>
            <details style="margin-top:.35rem">
              <summary class="muted">เพิ่มบัญชีใหม่</summary>
              <div class="grid-3" style="margin-top:.45rem">
                <div><label class="lbl">ธนาคาร</label><input class="inp" id="newBankName"/></div>
                <div><label class="lbl">ชื่อบัญชี</label><input class="inp" id="newAcctName"/></div>
                <div><label class="lbl">เลขบัญชี</label><input class="inp" id="newAcctNo"/></div>
              </div>
              <button type="button" class="btn sm" id="btnAddBank" style="margin-top:.45rem">บันทึกบัญชี</button>
            </details>
            <div style="margin-top:.65rem">
              <label class="lbl" for="noteRemark">หมายเหตุ (optional)</label>
              <textarea class="area" id="noteRemark" maxlength="500" placeholder="เช่น รอใบลดหนี้ / นัดโอนวันศุกร์"></textarea>
              <p class="date-hint">เก็บในระบบชำระเจ้าหนี้เท่านั้น · ไม่เขียนลง KSS</p>
            </div>
          </div>
        </div>

        <div class="step wizard-block" data-assist-step="3" id="wizardStepBills">
          <div class="step-num">3</div>
          <div class="step-body">
            <div class="bill-head">
              <h3 style="margin:0">เลือกบิล <span class="sub">(เลือกได้มากกว่า 1 บิล)</span></h3>
              <div class="toggle">
                <input type="checkbox" checked disabled/>
                แสดงบิลที่ยังไม่ถูกวางบิลเท่านั้น
                <button type="button" class="linkish" id="btnRefreshBills">รีเฟรช</button>
              </div>
            </div>
            <div id="aiLineMatch" class="ai-panel hidden"></div>
            <div id="billMatchAckWrap" class="ai-panel ai-warn hidden">
              <label>
                <input type="checkbox" id="billMatchAck"/>
                ยืนยันว่าตรวจบิลแล้ว
              </label>
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

        <div class="step wizard-block" data-assist-step="4" id="wizardStepDiscount">
          <div class="step-num">4</div>
          <div class="step-body">
            <h3>ส่วนลด (ถ้ามี)</h3>
            <div class="disc-layout">
              <div>
                <div class="seg" role="group" aria-label="ประเภทส่วนลด">
                  <button type="button" class="on" id="discModeAmount" data-mode="amount">จำนวนเงิน (บาท)</button>
                  <button type="button" id="discModePercent" data-mode="percent">% จากยอดรวม</button>
                </div>
                <label class="lbl" id="discInputLabel" for="discInput" style="margin-top:.65rem">ส่วนลด (บาท)</label>
                <input class="inp" id="discInput" type="number" inputmode="decimal" step="0.01" min="0" value="0.00"/>
              </div>
              <div class="disc-sum">
                <div class="pay-line"><span>ยอดรวมก่อนส่วนลด</span><strong id="discBillAmt">0.00</strong></div>
                <div class="pay-line"><span>ส่วนลด</span><strong id="discResolved">0.00</strong></div>
                <div class="pay-line pay-net"><span>ยอดสุทธิ</span><strong id="discNetAmt">0.00</strong></div>
              </div>
            </div>
          </div>
        </div>

        <div class="step wizard-block" data-assist-step="6" id="wizardStepUpload">
          <div class="step-num">5</div>
          <div class="step-body">
            <h3>เอกสารแนบ</h3>
            <div class="drop" id="dropBill" tabindex="0">
              <div style="font-size:1.4rem;margin-bottom:.25rem">☁</div>
              <div>คลิกหรือลากไฟล์มาวางที่นี่</div>
              <div class="date-hint">รองรับไฟล์ JPG, PNG, PDF (ขนาดไม่เกิน 10 MB)</div>
            </div>
            <input id="billImages" class="hidden" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf" multiple/>
            <div class="thumbs" id="billThumbs"></div>
          </div>
        </div>

        <button type="button" class="btn primary block" id="btnCreateNote">บันทึกใบวางบิล</button>
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
        <div><label class="lbl">เจ้าหนี้</label><input class="inp" id="editVendor" readonly/></div>
        <div><label class="lbl">เลขที่ใบวางบิล</label><input class="inp" id="editNoteno" readonly/></div>
        <div>
          <label class="lbl" for="editDueDate">วันครบกำหนดชำระ</label>
          <input class="inp date-ce" id="editDueDate" type="date" lang="en" inputmode="none"/>
        </div>
      </div>
      <div class="grid-3" style="margin-bottom:.85rem">
        <div>
          <label class="lbl" for="editBankSelect">บัญชีธนาคารปลายทาง</label>
          <select class="inp" id="editBankSelect"><option value="">— เลือกบัญชี —</option></select>
        </div>
        <div style="grid-column:span 2">
          <label class="lbl" for="editNoteRemark">หมายเหตุ</label>
          <textarea class="area" id="editNoteRemark" maxlength="500" style="min-height:2.6rem"></textarea>
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
          <input class="inp" id="editDiscInput" type="number" step="0.01" min="0" value="0.00"/>
        </div>
        <div class="disc-sum">
          <div class="pay-line"><span>ยอดรวมก่อนส่วนลด</span><strong id="editDiscBillAmt">0.00</strong></div>
          <div class="pay-line"><span>ส่วนลด</span><strong id="editDiscResolved">0.00</strong></div>
          <div class="pay-line pay-net"><span>ยอดสุทธิ</span><strong id="editDiscNetAmt">0.00</strong></div>
        </div>
      </div>
      <label class="lbl">เพิ่มเอกสารแนบ (optional)</label>
      <div class="drop" id="dropEditBill" tabindex="0">
        <div style="font-size:1.4rem;margin-bottom:.25rem">☁</div>
        <div>คลิกหรือลากไฟล์มาวางที่นี่</div>
        <div class="date-hint">รองรับไฟล์ JPG, PNG, PDF (ขนาดไม่เกิน 10 MB)</div>
      </div>
      <input id="editBillImages" class="hidden" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf" multiple/>
      <div class="thumbs" id="editBillThumbs"></div>
      <button type="button" class="btn primary block" id="btnSaveEdit" style="margin-top:.85rem">บันทึกการแก้ไข</button>
      <div id="editMsg"></div>
    </div>
  </section>

  <section id="panelPending" class="panel">
    <p class="panel-intro">ขั้นที่ 2 · รอบันทึกการจ่าย · แก้ไขบิล/ส่วนลดได้</p>
    <div class="card toolbar">
      <div class="field grow">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
        <input id="pfQ" placeholder="ค้นหาเจ้าหนี้ / เลขใบวางบิล" autocomplete="off"/>
      </div>
      <div class="field" style="min-width:11rem">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg></span>
        <input id="pfDue" class="date-ce" type="date" lang="en" inputmode="none" aria-label="กำหนดชำระ"/>
      </div>
      <button type="button" class="btn soft" id="btnRefreshPending">↻ รีเฟรช</button>
    </div>
    <div class="kpis">
      <button type="button" class="kpi kpi-all on" data-bucket="all">
        <span class="mark">▤</span>
        <span><b>รอชำระทั้งหมด</b><span id="kpiAll">0 รายการ · 0.00 บาท</span></span>
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
              <th>รหัสเจ้าหนี้</th>
              <th>เลขใบวางบิล</th>
              <th class="num">ยอดที่ต้องจ่าย</th>
              <th>กำหนดชำระ</th>
              <th>สถานะ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="pendingBody"></tbody>
        </table>
      </div>
      <div id="pendingEmpty" class="empty hidden">ยังไม่มีรายการรอชำระ</div>
      <div class="table-foot">
        <div class="table-foot-meta">
          <p class="hint">ⓘ บันทึกการจ่ายแล้วจะย้ายไปแท็บรอแนบหลักฐาน</p>
        </div>
        <div class="table-foot-nav">
          <div class="pager" id="pendingPager"></div>
        </div>
      </div>
    </div>
  </section>

  <section id="panelAwaitProof" class="panel">
    <p class="panel-intro">ขั้นที่ 3 · บันทึกการจ่ายแล้ว · รออัปโหลดหลักฐาน</p>
    <div class="card toolbar">
      <div class="field grow">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
        <input id="afQ" placeholder="ค้นหาเลขใบสำคัญจ่าย / เจ้าหนี้ / เลขใบวางบิล" autocomplete="off"/>
      </div>
      <button type="button" class="btn soft" id="btnRefreshAwaitProof">↻ รีเฟรช</button>
    </div>
    <div class="card card-table">
      <div class="table-wrap mob-cards">
        <table>
          <thead>
            <tr>
              <th>เลขใบสำคัญจ่าย</th>
              <th>รหัสเจ้าหนี้</th>
              <th>เลขใบวางบิล</th>
              <th>วันที่จ่าย</th>
              <th class="num">ยอดจ่าย</th>
              <th>วิธีชำระ</th>
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
    <p class="panel-intro">ขั้นที่ 4 · มีหลักฐานครบแล้ว · ดูรูปบิลและหลักฐานชำระ</p>
    <div class="card toolbar">
      <div class="field grow">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
        <input id="vfQ" placeholder="เลขใบสำคัญจ่าย / รหัสเจ้าหนี้ / เลขใบวางบิล" autocomplete="off"/>
      </div>
      <div class="field" style="min-width:12rem">
        <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M8 3v4M16 3v4M3 10h18"/></svg></span>
        <input id="vfFrom" class="date-ce" type="date" lang="en" inputmode="none" aria-label="ตั้งแต่"/>
        <span>–</span>
        <input id="vfTo" class="date-ce" type="date" lang="en" inputmode="none" aria-label="ถึง"/>
      </div>
      <div class="field" style="min-width:9.5rem">
        <select id="vfMethod" aria-label="วิธีชำระ">
          <option value="">วิธีชำระ: ทั้งหมด</option>
          <option value="transfer">โอนเงิน</option>
          <option value="cheque">เช็ค</option>
          <option value="cash">เงินสด</option>
        </select>
      </div>
      <button type="button" class="btn ghost" id="btnClearVoucherFilters">↻ ล้างตัวกรอง</button>
    </div>
    <div class="card card-table">
      <div class="table-wrap mob-cards">
        <table>
          <thead>
            <tr>
              <th>เลขใบสำคัญจ่าย</th>
              <th>รหัสเจ้าหนี้</th>
              <th>เลขใบวางบิล</th>
              <th>วันที่จ่าย</th>
              <th class="num">ยอดจ่าย (บาท)</th>
              <th>วิธีชำระ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="voucherBody"></tbody>
        </table>
      </div>
      <div id="voucherEmpty" class="empty hidden">ยังไม่มีใบสำคัญจ่าย</div>
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
    <p class="panel-intro">ค้นหารายการใบวางบิล / ใบสำคัญจ่ายตามเจ้าหนี้</p>
    <div class="card toolbar">
      <div class="combo grow">
        <div class="field">
          <span class="ico"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.2-3.2"/></svg></span>
          <input id="byApVendorQ" placeholder="ค้นหาเจ้าหนี้ (รหัส / ชื่อ)" autocomplete="off"/>
        </div>
        <div id="byApVendorResults" class="combo-list hidden"></div>
      </div>
      <button type="button" class="btn soft" id="btnRefreshByAp">↻ รีเฟรช</button>
    </div>
    <div id="byApPicked" class="picked hidden"></div>
    <div class="card card-table">
      <div class="table-wrap mob-cards">
        <table>
          <thead>
            <tr>
              <th>เลขใบวางบิล</th>
              <th>เลขใบสำคัญจ่าย</th>
              <th class="num">ยอดสุทธิ</th>
              <th>กำหนดชำระ</th>
              <th>สถานะ</th>
              <th></th>
            </tr>
          </thead>
          <tbody id="byApBody"></tbody>
        </table>
      </div>
      <div id="byApEmpty" class="empty hidden">เลือกเจ้าหนี้เพื่อดูรายการ</div>
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
    <h2>บันทึกการจ่าย</h2>
    <button type="button" class="dlg-x" id="btnClosePay" aria-label="ปิด">×</button>
  </div>
  <div class="dlg-body">
    <div class="sum-box">
      <div><div class="k">รหัสเจ้าหนี้</div><div class="v" id="payAcct">—</div></div>
      <div><div class="k">ยอดบิล</div><div class="v" id="payBillAmt">0.00</div></div>
      <div><div class="k">เลขใบวางบิล</div><div class="v" id="payNote">—</div></div>
      <div><div class="k">ส่วนลด (จากใบวางบิล)</div><div class="v" id="payDiscountAmt">0.00</div></div>
      <div><div class="k">บัญชีปลายทาง</div><div class="v" id="payBankLine">—</div></div>
      <div class="net"><div class="k">ยอดสุทธิ</div><div class="v" id="payNetAmt">0.00</div></div>
    </div>
    <h3 style="margin:.2rem 0 .45rem;font-size:.95rem">ข้อมูลการจ่าย</h3>
    <label class="lbl">วิธีชำระ</label>
    <div class="methods" role="group" aria-label="วิธีชำระ">
      <button type="button" class="method on" id="settleTransfer" data-settle="transfer">🏦<span>โอนเงิน</span></button>
      <button type="button" class="method" id="settleCheque" data-settle="cheque">✎<span>เช็ค</span></button>
      <button type="button" class="method" id="settleCash" data-settle="cash">💵<span>เงินสด</span></button>
    </div>
    <div class="grid-2">
      <div>
        <label class="lbl" for="payChkamt">จำนวนเงินที่จ่าย (บาท)</label>
        <input class="inp" id="payChkamt" type="number" inputmode="decimal" step="0.01" min="0"/>
      </div>
      <div>
        <label class="lbl" for="payChkdate">วันที่จ่าย</label>
        <input class="inp date-ce" id="payChkdate" type="date" lang="en" inputmode="none"/>
      </div>
    </div>
    <div id="payChknoWrap" class="hidden" style="margin-top:.65rem">
      <label class="lbl" id="payChknoLabel" for="payChkno">เลขที่เช็ค</label>
      <input class="inp" id="payChkno" maxlength="15"/>
    </div>
    <div style="margin-top:.65rem">
      <label class="lbl" for="payBankGl">บัญชีที่ใช้จ่าย</label>
      <select class="inp" id="payBankGl">
        <option value="2101.7">2101.7 - ธนาคารกรุงไทย กระแสรายวัน</option>
        <option value="2101.1">2101.1 - ธนาคารไทยพาณิชย์</option>
        <option value="2101.2">2101.2 - ธนาคารกสิกรไทย</option>
        <option value="2101.3">2101.3 - ธนาคารกรุงเทพ</option>
      </select>
    </div>
    <div id="payMsg"></div>
  </div>
  <div class="dlg-foot">
    <button type="button" class="btn ghost" id="btnCancelPay">ยกเลิก</button>
    <button type="button" class="btn primary" id="btnConfirmPay">บันทึกการจ่าย</button>
  </div>
</dialog>

<dialog id="dlgDetail" class="dlg">
  <div class="dlg-head">
    <h2 id="detTitle">รายละเอียด</h2>
    <button type="button" class="dlg-x" id="btnCloseDetail" aria-label="ปิด">×</button>
  </div>
  <div class="dlg-body">
    <div id="detMeta" class="muted"></div>
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
    <div id="detBills"></div>
    <div id="detBillSum"></div>
    <h3 style="margin:1rem 0 .4rem;font-size:.95rem">รูปใบวางบิล</h3>
    <div class="thumbs" id="detBillThumbs"></div>
    <div id="detProofWrap" class="hidden">
      <h3 style="margin:1rem 0 .4rem;font-size:.95rem">หลักฐานชำระ</h3>
      <div class="thumbs" id="detProofThumbs"></div>
      <div id="detUploadWrap" class="hidden" style="margin-top:.55rem">
        <label class="lbl">อัปโหลดหลักฐาน</label>
        <div class="drop" id="dropProof" tabindex="0">
          <div style="font-size:1.4rem;margin-bottom:.25rem">☁</div>
          <div>คลิกหรือลากไฟล์มาวางที่นี่</div>
          <div class="date-hint">รองรับไฟล์ JPG, PNG, PDF (ขนาดไม่เกิน 10 MB)</div>
        </div>
        <input id="detProofFiles" class="hidden" type="file" accept="image/jpeg,image/png,image/jpg,application/pdf" multiple/>
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
    <button type="button" class="btn outline" id="btnPrintDetail">พิมพ์</button>
    <button type="button" class="btn primary hidden" id="detPayBtn">บันทึกการจ่าย</button>
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

let picked = null;
let uploadedPaths = [];
let payTarget = null;
let discMode = 'amount';
let editDiscMode = 'amount';
let settleMethod = 'transfer';
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
let createMode = 'manual';
let wizardStep = 1;
let scanResult = null;
let proofVerifyResult = null;
let proofPendingComplete = false;
let editTarget = null;
let editReturnTab = 'pending';

function $(id) { return document.getElementById(id); }
function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, c => (
    {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]
  ));
}
function fmtMoney(n) {
  return Number(n || 0).toLocaleString('th-TH', {minimumFractionDigits:2, maximumFractionDigits:2});
}
function fmtDate(iso, short) {
  const s = String(iso || '').slice(0, 10);
  if (!s || s.length < 10) return '—';
  const [y, m, d] = s.split('-');
  return short ? `${d}/${m}/${y.slice(2)}` : `${d}/${m}/${y}`;
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
  return Math.max(0, Number(r.BILLAMT || 0) - disc);
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
  const st = r.workflow_status || '—';
  if (r.stage === 'await_proof') return `<span class="badge b-wait">${esc(st)}</span>`;
  if (r.stage === 'voucher') return `<span class="badge b-done">${esc(st)}</span>`;
  const ps = pendingStatus(r);
  return `<span class="badge ${ps.cls}">${esc(st || ps.label)}</span>`;
}
function pendingStatus(r) {
  const b = dueBucket(remDue(r));
  if (b === 'overdue') return {cls:'b-overdue', label:'เกินกำหนด', bucket:'overdue'};
  if (b === 'today') return {cls:'b-today', label:'ครบกำหนดวันนี้', bucket:'today'};
  if (b === 'soon') return {cls:'b-soon', label:'ใกล้ครบกำหนด', bucket:'soon'};
  return {cls:'b-pending', label:'รอชำระ', bucket:'later'};
}
function settleLabel(m) {
  return m === 'cheque' ? 'เช็ค' : (m === 'cash' ? 'เงินสด' : (m === 'transfer' ? 'โอนเงิน' : '—'));
}
function keyOf(r) { return `${r.acctno}|${r.noteno}`; }

async function api(path, opts) {
  const r = await fetch('/pay-notes/api' + path, opts || {});
  const j = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(j.detail || j.error || r.statusText);
  return j;
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
  try { localStorage.setItem('kcw.pay_notes.theme', next); } catch (e) {}
}
$('themeBtn').onclick = () => {
  applyTheme(document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark');
};
applyTheme(document.documentElement.getAttribute('data-theme') || 'light');

function setCrumb(tab, extra) {
  const flow = 'สร้าง → รอชำระ → รอแนบหลักฐาน → ใบสำคัญจ่าย';
  const base = `${USER_NAME} · HQ only · ${flow}`;
  const labels = {
    create: 'สร้างใบวางบิล',
    pending: 'รอชำระ',
    awaitproof: 'รอแนบหลักฐาน',
    voucher: 'ใบสำคัญจ่าย',
    byap: 'ค้นหาตามเจ้าหนี้',
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
  ['dlgDetail', 'dlgPay'].forEach((id) => {
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
  $('pageTitle').textContent = `ชำระเจ้าหนี้ · ${SITE}`;
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
  $('pendingBody').innerHTML = `<tr><td colspan="6" class="empty">กำลังโหลด…</td></tr>`;
  try {
    pendingRows = await api('/pending');
    renderPending();
  } catch (e) {
    $('pendingBody').innerHTML = `<tr><td colspan="6" class="err">${esc(e.message)}</td></tr>`;
  }
}
function pendingNet(r) {
  return Math.max(0, Number(r.BILLAMT || 0) - Number((r.reminder || {}).discount_amount || 0));
}
function filteredPending() {
  const q = ($('pfQ').value || '').trim().toLowerCase();
  const due = ($('pfDue').value || '').trim();
  let rows = pendingRows.filter(r => {
    const st = pendingStatus(r);
    if (pendingBucket !== 'all' && st.bucket !== pendingBucket) return false;
    if (due && remDue(r) !== due) return false;
    if (q) {
      const hay = [r.acctno, r.acctname, r.noteno, remDue(r)].map(x => String(x||'').toLowerCase()).join(' ');
      if (!hay.includes(q)) return false;
    }
    return true;
  });
  rows.sort((a, b) => String(remDue(a)).localeCompare(String(remDue(b))) || String(a.acctno).localeCompare(String(b.acctno)));
  return rows;
}
function renderKpis() {
  const groups = {all: pendingRows, overdue: [], today: [], soon: []};
  pendingRows.forEach(r => {
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
    const bank = ((r.reminder || {}).vendor_bank || {});
    const bankname = `${bank.bank_name || ''} ${bank.bank_account_name || ''} # ${bank.bank_account_number || ''}`.trim();
    return `<tr>
      <td data-label="รหัสเจ้าหนี้">${esc(r.acctno)}</td>
      <td data-label="เลขใบวางบิล">${esc(r.noteno)}</td>
      <td class="num" data-label="ยอดที่ต้องจ่าย">${fmtMoney(pendingNet(r))} บาท</td>
      <td data-label="กำหนดชำระ">${fmtDate(remDue(r))}</td>
      <td data-label="สถานะ"><span class="badge ${st.cls}">${st.label}</span></td>
      <td class="td-actions" data-label=""><div class="row-actions">
        <button type="button" class="btn sm outline" data-edit="${esc(keyOf(r))}">แก้ไข</button>
        <button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดูรายละเอียด</button>
        <button type="button" class="btn sm primary"
          data-pay-acct="${esc(r.acctno)}" data-pay-note="${esc(r.noteno)}"
          data-pay-amt="${Number(r.BILLAMT||0)}" data-pay-disc="${Number((r.reminder||{}).discount_amount||0)}"
          data-pay-bank="${esc(bankname)}">บันทึกการจ่าย</button>
      </div></td>
    </tr>`;
  }).join('');
  renderPager($('pendingPager'), pg.page, pg.pages, p => { pendingPage = p; renderPending(); });
}
document.querySelectorAll('.kpi[data-bucket]').forEach(btn => {
  btn.onclick = () => { pendingBucket = btn.dataset.bucket; pendingPage = 1; renderPending(); };
});
$('btnRefreshPending').onclick = loadPending;
['pfQ','pfDue'].forEach(id => {
  const el = $(id);
  el.addEventListener(el.type === 'date' ? 'change' : 'input', () => { pendingPage = 1; renderPending(); });
});
$('pendingBody').addEventListener('click', (e) => {
  const edit = e.target.closest('[data-edit]');
  if (edit) { openEditNote(edit.dataset.edit, 'pending'); return; }
  const pay = e.target.closest('[data-pay-acct]');
  if (pay) {
    openPay(pay.dataset.payAcct, pay.dataset.payNote, pay.dataset.payAmt, pay.dataset.payDisc, pay.dataset.payBank || '');
    return;
  }
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {canPay: true});
});

async function loadAwaitProof() {
  $('awaitProofBody').innerHTML = `<tr><td colspan="7" class="empty">กำลังโหลด…</td></tr>`;
  try {
    awaitProofRows = await api('/vouchered?proof=awaiting');
    renderAwaitProof();
  } catch (e) {
    $('awaitProofBody').innerHTML = `<tr><td colspan="7" class="err">${esc(e.message)}</td></tr>`;
  }
}
function filteredAwaitProof() {
  const q = ($('afQ').value || '').trim().toLowerCase();
  return awaitProofRows.filter(r => {
    if (!q) return true;
    const hay = [r.acctno, r.acctname, r.noteno, r.voucno, voucDate(r)].map(x => String(x||'').toLowerCase()).join(' ');
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
    <td data-label="เลขใบสำคัญจ่าย"><button type="button" class="linkish" data-open="${esc(keyOf(r))}">${esc(r.voucno || '—')}</button></td>
    <td data-label="รหัสเจ้าหนี้">${esc(r.acctno)}</td>
    <td data-label="เลขใบวางบิล">${esc(r.noteno)}</td>
    <td data-label="วันที่จ่าย">${fmtDate(voucDate(r))}</td>
    <td class="num" data-label="ยอดจ่าย">${fmtMoney(r.NETAMT != null ? r.NETAMT : r.BILLAMT)}</td>
    <td data-label="วิธีชำระ">${esc(settleLabel(r.settle_method))}</td>
    <td class="td-actions" data-label=""><button type="button" class="btn sm primary" data-open="${esc(keyOf(r))}" data-upload="1">แนบหลักฐาน</button></td>
  </tr>`).join('');
  renderPager($('awaitProofPager'), pg.page, pg.pages, p => { awaitProofPage = p; renderAwaitProof(); });
}
$('btnRefreshAwaitProof').onclick = loadAwaitProof;
$('afQ').addEventListener('input', () => { awaitProofPage = 1; renderAwaitProof(); });
$('awaitProofBody').addEventListener('click', (e) => {
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {awaitProof: true, canUpload: !!open.dataset.upload});
});

async function loadVouchers() {
  $('voucherBody').innerHTML = `<tr><td colspan="7" class="empty">กำลังโหลด…</td></tr>`;
  try {
    voucherRows = await api('/vouchered?proof=done');
    renderVouchers();
  } catch (e) {
    $('voucherBody').innerHTML = `<tr><td colspan="7" class="err">${esc(e.message)}</td></tr>`;
  }
}
function voucDate(r) { return String(r.VOUCDATE || '').slice(0, 10); }
function filteredVouchers() {
  const q = ($('vfQ').value || '').trim().toLowerCase();
  const from = ($('vfFrom').value || '').trim();
  const to = ($('vfTo').value || '').trim();
  const method = $('vfMethod').value;
  let rows = voucherRows.filter(r => {
    const d = voucDate(r);
    if (from && (!d || d < from)) return false;
    if (to && (!d || d > to)) return false;
    if (method && (r.settle_method || '') !== method) return false;
    if (q) {
      const hay = [r.acctno, r.acctname, r.noteno, r.voucno, d].map(x => String(x||'').toLowerCase()).join(' ');
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
    <td data-label="เลขใบสำคัญจ่าย"><button type="button" class="linkish" data-open="${esc(keyOf(r))}">${esc(r.voucno || '—')}</button></td>
    <td data-label="รหัสเจ้าหนี้">${esc(r.acctno)}</td>
    <td data-label="เลขใบวางบิล">${esc(r.noteno)}</td>
    <td data-label="วันที่จ่าย">${fmtDate(voucDate(r))}</td>
    <td class="num" data-label="ยอดจ่าย">${fmtMoney(r.NETAMT != null ? r.NETAMT : r.BILLAMT)}</td>
    <td data-label="วิธีชำระ">${esc(settleLabel(r.settle_method))}</td>
    <td class="td-actions" data-label=""><div class="row-actions">
      <button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดู</button>
      <button type="button" class="btn sm outline" data-print="${esc(keyOf(r))}">พิมพ์</button>
    </div></td>
  </tr>`).join('');
  renderPager($('voucherPager'), pg.page, pg.pages, p => { voucherPage = p; renderVouchers(); });
}
function clearVoucherFilters() {
  $('vfQ').value = ''; $('vfFrom').value = ''; $('vfTo').value = '';
  $('vfMethod').value = '';
  voucherPage = 1; renderVouchers();
}
$('btnClearVoucherFilters').onclick = clearVoucherFilters;
$('vfSize').onchange = () => { voucherPageSize = Number($('vfSize').value || 10); voucherPage = 1; renderVouchers(); };
['vfQ','vfFrom','vfTo','vfMethod'].forEach(id => {
  const el = $(id);
  el.addEventListener(el.tagName === 'SELECT' || el.type === 'date' ? 'change' : 'input', () => { voucherPage = 1; renderVouchers(); });
});
$('voucherBody').addEventListener('click', (e) => {
  const printBtn = e.target.closest('[data-print]');
  if (printBtn) { openDetailByKey(printBtn.dataset.print, {voucher: true, print: true}); return; }
  const open = e.target.closest('[data-open]');
  if (open) openDetailByKey(open.dataset.open, {voucher: true});
});

async function loadByAp() {
  if (!byApVendor) {
    $('byApBody').innerHTML = '';
    $('byApEmpty').classList.remove('hidden');
    $('byApEmpty').textContent = 'เลือกเจ้าหนี้เพื่อดูรายการ';
    $('byApCount').textContent = 'แสดง 0 รายการ';
    $('byApPager').innerHTML = '';
    return;
  }
  $('byApBody').innerHTML = `<tr><td colspan="6" class="empty">กำลังโหลด…</td></tr>`;
  try {
    byApRows = await api('/notes?acctno=' + encodeURIComponent(byApVendor.acctno));
    renderByAp();
  } catch (e) {
    $('byApBody').innerHTML = `<tr><td colspan="6" class="err">${esc(e.message)}</td></tr>`;
  }
}
function renderByAp() {
  const pg = slicePage(byApRows, byApPage, PAGE_SIZE);
  byApPage = pg.page;
  $('byApEmpty').classList.toggle('hidden', pg.total !== 0);
  $('byApCount').textContent = pg.total ? `แสดง ${pg.start + 1} - ${pg.end} จาก ${pg.total} รายการ` : 'แสดง 0 รายการ';
  $('byApBody').innerHTML = pg.rows.map(r => {
    const actions = r.is_editable
      ? `<button type="button" class="btn sm outline" data-edit="${esc(keyOf(r))}">แก้ไข</button>
         <button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดู</button>`
      : `<button type="button" class="btn sm outline" data-open="${esc(keyOf(r))}">ดู</button>`;
    return `<tr>
      <td data-label="เลขใบวางบิล">${esc(r.noteno)}</td>
      <td data-label="เลขใบสำคัญจ่าย">${esc(r.voucno || '—')}</td>
      <td class="num" data-label="ยอดสุทธิ">${fmtMoney(netAmt(r))}</td>
      <td data-label="กำหนดชำระ">${fmtDate(remDue(r), true)}</td>
      <td data-label="สถานะ">${workflowBadge(r)}</td>
      <td class="td-actions" data-label=""><div class="row-actions">${actions}</div></td>
    </tr>`;
  }).join('');
  renderPager($('byApPager'), pg.page, pg.pages, p => { byApPage = p; renderByAp(); });
}
$('btnRefreshByAp').onclick = loadByAp;
$('byApBody').addEventListener('click', (e) => {
  const edit = e.target.closest('[data-edit]');
  if (edit) { openEditNote(edit.dataset.edit, 'byap'); return; }
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
function thumbsHtml(images) {
  const list = (images || []).filter(x => x && (x.url || x.path));
  if (!list.length) return '<p class="muted">ไม่มีรูป</p>';
  return list.map(img => {
    const url = esc(img.url || '');
    const name = String(img.name || img.path || '');
    if (/\.pdf$/i.test(name)) return `<a class="file-chip" href="${url}" target="_blank" rel="noopener">${esc(name)}</a>`;
    return url ? `<a href="${url}" target="_blank" rel="noopener"><img src="${url}" alt=""/></a>` : '';
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
  const disc = Number(totals.discount || 0);
  const net = Number(totals.netamt != null ? totals.netamt : 0);
  $('detBillSum').innerHTML = `<div class="det-sum">
    <div class="pay-line"><span>จำนวนบิล</span><strong>${totals.billcnt || bills.length} ฉบับ</strong></div>
    <div class="pay-line"><span>จำนวนเงินรวม</span><strong>${fmtMoney(totals.billamt)}</strong></div>
    <div class="pay-line"><span>ส่วนลด</span><strong>${fmtMoney(disc)}</strong></div>
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
  const voucno = String((row && row.voucno) || header.voucno || '').trim();
  const noteno = String((row && row.noteno) || header.noteno || '').trim();
  const acctno = String((row && row.acctno) || header.acctno || '').trim();
  const acctname = String((row && row.acctname) || header.acctname || '').trim();
  const due = String(rem.due_date || remDue(row || {}) || '').slice(0, 10);
  const docDate = String(voucno ? (header.VOUCDATE || (row && row.VOUCDATE) || header.NOTEDATE) : (header.NOTEDATE || todayISO())).slice(0, 10);
  const title = voucno ? 'ใบสำคัญจ่าย / PAYMENT VOUCHER' : 'ใบวางบิล / BILLING NOTE';
  const docno = voucno || noteno;
  const month = billMonthLabel(bills);
  const disc = Number(totals.discount || 0);
  const net = Number(totals.netamt != null ? totals.netamt : 0);
  const billamt = Number(totals.billamt != null ? totals.billamt : 0);
  const billcnt = totals.billcnt || bills.length;
  const words = totals.net_text || '';
  const remarkNote = String(rem.remark || '').trim();
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
    bodyRows.push('<tr><td colspan="5" style="text-align:center;color:#666">ไม่พบบิลซื้อ</td></tr>');
  }
  const settle = (row && row.settle_method) || (payments[0] && payments[0].settle_method) || '';
  const isCash = settle === 'cash';
  const isChequeOrTransfer = settle === 'cheque' || settle === 'transfer' || (!isCash && !!voucno);
  const payLines = payments.length ? payments : (voucno ? [{
    CHKNO: settle === 'transfer' ? 'โอน' : (settle === 'cash' ? 'เงินสด' : ''),
    CHKDATE: docDate,
    BANKNAME: (() => {
      const bank = rem.vendor_bank || {};
      return [bank.bank_name, bank.bank_account_name, bank.bank_account_number ? ('# ' + bank.bank_account_number) : '']
        .filter(Boolean).join(' ');
    })(),
    CHKAMT: net,
    settle_method: settle,
  }] : []);
  const payRows = payLines.map(p => {
    const kind = p.settle_method === 'cash' ? 'เงินสด' : (String(p.CHKNO || '').trim() || 'โอน');
    return `<tr>
      <td>${esc(kind)}</td>
      <td class="pv-amt-red">${esc(fmtDate(p.CHKDATE || docDate))}</td>
      <td>${esc(p.BANKNAME || '')}</td>
      <td class="num pv-amt-red">${fmtMoney(p.CHKAMT != null ? p.CHKAMT : net)}</td>
    </tr>`;
  }).join('');
  $('printSheet').innerHTML = `
    <div class="pv">
      <div class="pv-top">
        <div class="pv-co">
          <div class="pv-logo">KCW</div>
          <div class="pv-co-name">บริษัท เกียรติชัยอะไหล่ยนต์ 2007 จำกัด</div>
          <div>305 ม.1 ต.ชุมแสง อ.วังจันทร์ จ.ระยอง 21210</div>
          <div>โทร. 038-666078</div>
        </div>
        <div class="pv-title-wrap">
          <div class="pv-title">${esc(title)}</div>
          <div class="pv-month">บิลเดือน ${esc(month || '…………………………')}</div>
        </div>
      </div>
      <div class="pv-meta">
        <div>รหัสบัญชี &nbsp; <b>${esc(acctno)}</b></div>
        <div>ชื่อบัญชี &nbsp; <b>${esc(acctname)}</b></div>
        <div>วันที่ &nbsp; <b>${esc(fmtDate(docDate))}</b></div>
        <div>เลขที่ &nbsp; <b>${esc(docno)}</b></div>
        <div class="span2">เลขที่ใบวางบิล &nbsp; <b>${esc(noteno)}</b></div>
      </div>
      <table class="pv-table">
        <thead>
          <tr>
            <th>วันที่บิล</th>
            <th>เลขที่บิล</th>
            <th>จำนวนเงิน</th>
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
          <div class="row"><span>ส่วนลด</span><span class="n">${fmtMoney(disc)}</span></div>
        </div>
      </div>
      <div class="pv-pay">
        <div class="pv-checks">
          <div>${isCash ? '☑' : '☐'} เงินสด</div>
          <div style="margin-top:.35rem">${isChequeOrTransfer ? '☑' : '☐'} เช็ค / โอน
            ${voucno ? `<span class="pv-amt-red" style="margin-left:.6rem">${fmtMoney(net)}</span>` : ''}
          </div>
        </div>
        ${voucno && payRows ? `<table class="pv-paytbl">
          <thead><tr><th>โอน/เช็ค</th><th>ลงวันที่</th><th>ธนาคาร</th><th>จำนวนเงิน</th></tr></thead>
          <tbody>${payRows}</tbody>
        </table>` : ''}
      </div>
      <div class="pv-sign">
        <div class="col">ผู้รับเงิน / เช็ค<div class="line"></div>วันที่<div class="line"></div></div>
        <div class="col" style="text-align:right">ผู้จัดทำ<div class="line">${esc(USER_NAME || '')}</div></div>
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
  $('detTitle').textContent = row.voucno ? `ใบสำคัญจ่าย ${row.voucno}` : `ใบวางบิล ${row.noteno}`;
  $('detMeta').textContent = `${row.acctno} · ${row.acctname || ''} · ${row.noteno}`;
  const remark = String(rem.remark || '').trim();
  $('detRemark').innerHTML = remark ? `<div class="remark">${esc(remark)}</div>` : '';
  const canEditDue = row.is_editable === true;
  $('detDueWrap').classList.toggle('hidden', !remDue(row));
  $('detDueView').textContent = remDue(row) || '—';
  $('detDueEdit').classList.add('hidden');
  $('detDueInput').classList.add('hidden');
  $('detDueSave').classList.add('hidden');
  $('detDueCancel').classList.add('hidden');
  $('detPayBtn').classList.toggle('hidden', !(opts.canPay && canEditDue && WRITE_ENABLED));
  $('detProofWrap').classList.toggle('hidden', !row.voucno);
  const canUpload = opts.canUpload || (row.voucno && !row.has_proof && row.stage === 'await_proof');
  $('detUploadWrap').classList.toggle('hidden', !canUpload);
  $('detBills').innerHTML = '<p class="muted">กำลังโหลดบิลซื้อ…</p>';
  $('detBillSum').innerHTML = '';
  $('detBillThumbs').innerHTML = 'กำลังโหลด…';
  $('detProofThumbs').innerHTML = thumbsHtml(row.payment_images || []);
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
    const det = await api(`/notes/${encodeURIComponent(row.acctno)}/${encodeURIComponent(row.noteno)}`);
    detailPayload = det;
    renderDetBills(det);
    $('detBillThumbs').innerHTML = thumbsHtml(det.bill_images || []);
    if (det.payment_images) $('detProofThumbs').innerHTML = thumbsHtml(det.payment_images);
    fillPrintSheet(det, row);
    if (opts.print) printDetail();
  } catch (e) {
    $('detBills').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    $('detBillThumbs').innerHTML = `<p class="err">${esc(e.message)}</p>`;
  }
}
$('detPayBtn').onclick = () => {
  if (!detailRow) return;
  const bank = (detailRow.reminder || {}).vendor_bank || {};
  $('dlgDetail').close();
  openPay(
    detailRow.acctno, detailRow.noteno, detailRow.BILLAMT,
    (detailRow.reminder || {}).discount_amount || 0,
    `${bank.bank_name || ''} ${bank.bank_account_name || ''} # ${bank.bank_account_number || ''}`
  );
};
function appendUploadThumb(container, file, j) {
  if (j.url && !/\.pdf$/i.test(file.name)) {
    container.innerHTML += `<img src="${esc(j.url)}" alt=""/>`;
  } else {
    container.innerHTML += `<span class="file-chip">${esc(file.name)}</span>`;
  }
}
function wireDropZone(dropEl, inputEl, onFiles) {
  if (!dropEl || !inputEl) return;
  dropEl.onclick = () => inputEl.click();
  dropEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); inputEl.click(); }
  });
  dropEl.addEventListener('dragover', (e) => { e.preventDefault(); dropEl.classList.add('drag'); });
  dropEl.addEventListener('dragleave', () => dropEl.classList.remove('drag'));
  dropEl.addEventListener('drop', async (e) => {
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
  let lastFile = null;
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); continue; }
    lastFile = file;
    const fd = new FormData();
    fd.append('voucno', detailRow.voucno);
    fd.append('file', file);
    const r = await fetch('/pay-notes/api/images/payment', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { alert(j.detail || j.error); return; }
  }
  await loadAwaitProof();
  await loadVouchers();
  const fresh = voucherRows.find(x => keyOf(x) === keyOf(detailRow)) || awaitProofRows.find(x => keyOf(x) === keyOf(detailRow));
  if (fresh) detailRow = fresh;

  let verifyResult = null;
  if (AI_ENABLED && lastFile) {
    try {
      const vfd = new FormData();
      vfd.append('voucno', detailRow.voucno);
      vfd.append('file', lastFile);
      const vr = await fetch('/pay-notes/api/ai/verify-payment', {method:'POST', body: vfd});
      verifyResult = await vr.json().catch(() => ({}));
      if (!vr.ok) verifyResult = null;
    } catch (_) { verifyResult = null; }
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


function setSettleMethod(method) {
  settleMethod = method === 'cheque' ? 'cheque' : (method === 'cash' ? 'cash' : 'transfer');
  ['transfer','cheque','cash'].forEach(m => {
    const el = $('settle' + m.charAt(0).toUpperCase() + m.slice(1));
    if (el) el.classList.toggle('on', settleMethod === m);
  });
  $('payChknoWrap').classList.toggle('hidden', settleMethod !== 'cheque');
  if (settleMethod === 'transfer') {
    if (!$('payChkno').value.trim() || $('payChkno').dataset.auto === '1') {
      $('payChkno').value = 'โอน';
      $('payChkno').dataset.auto = '1';
    }
  } else if ($('payChkno').value.trim() === 'โอน' || $('payChkno').dataset.auto === '1') {
    $('payChkno').value = '';
    $('payChkno').dataset.auto = '1';
  }
}
$('settleTransfer').onclick = () => setSettleMethod('transfer');
$('settleCheque').onclick = () => setSettleMethod('cheque');
$('settleCash').onclick = () => setSettleMethod('cash');
$('payChkno').addEventListener('input', () => { $('payChkno').dataset.auto = '0'; });

function openPay(acct, note, billamt, discount, bankname) {
  const bill = Number(billamt || 0);
  const disc = Number(discount || 0);
  const net = Math.max(0, bill - disc);
  payTarget = {acctno: acct, noteno: note, billamt: bill, discount: disc, netamt: net};
  $('payAcct').textContent = acct;
  $('payNote').textContent = note;
  $('payBillAmt').textContent = fmtMoney(bill);
  $('payDiscountAmt').textContent = fmtMoney(disc);
  $('payNetAmt').textContent = fmtMoney(net);
  $('payBankLine').textContent = (bankname || '').replace(/\s+#\s+$/,'').trim() || '— ไม่พบบัญชีธนาคาร —';
  $('payChkamt').value = net.toFixed(2);
  $('payChkdate').value = todayISO();
  $('payBankGl').value = '2101.7';
  $('payMsg').innerHTML = '';
  $('payChkno').dataset.auto = '1';
  setSettleMethod('transfer');
  wireDatePickers($('dlgPay'));
  $('dlgPay').showModal();
}
$('btnClosePay').onclick = () => $('dlgPay').close();
$('btnCancelPay').onclick = () => $('dlgPay').close();
$('btnConfirmPay').onclick = async () => {
  if (!WRITE_ENABLED) { $('payMsg').innerHTML = '<p class="err">KSS write ปิดอยู่</p>'; return; }
  if (!payTarget) return;
  const chkno = settleMethod === 'transfer' ? ($('payChkno').value.trim() || 'โอน')
    : settleMethod === 'cash' ? $('payChkno').value.trim()
    : $('payChkno').value.trim();
  const chkamt = Number($('payChkamt').value || 0);
  if (settleMethod === 'cheque' && !chkno) {
    $('payMsg').innerHTML = '<p class="err">กรอกเลขที่เช็ค</p>'; return;
  }
  if (chkamt <= 0 && payTarget.netamt > 0) {
    $('payMsg').innerHTML = '<p class="err">กรอกจำนวนเงินที่จ่าย</p>'; return;
  }
  try {
    const res = await api('/vouchers', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: payTarget.acctno, noteno: payTarget.noteno,
        settle_method: settleMethod, chkno, chkamt,
        chkdate: $('payChkdate').value, bank_gl: $('payBankGl').value.trim()
      })
    });
    $('payMsg').innerHTML = `<p class="ok">บันทึกแล้ว · ${esc(res.voucno)}</p>`;
    setTimeout(() => { $('dlgPay').close(); showTab('awaitproof'); }, 700);
  } catch (e) { $('payMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`; }
};

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
  if (!$('dueDate').value) $('dueDate').value = todayISO();
  uploadedPaths = [];
  $('billThumbs').innerHTML = '';
  scanResult = null;
  $('aiLineMatch')?.classList.add('hidden');
  $('billMatchAckWrap')?.classList.add('hidden');
  if ($('billMatchAck')) $('billMatchAck').checked = false;
  await loadBanks();
  await loadBills();
  if (createMode === 'assist' && AI_ENABLED) {
    wizardStep = 2;
    applyCreateMode();
  }
}

async function loadBanks() {
  if (!picked) return;
  const rows = await api('/banks?acctno=' + encodeURIComponent(picked.acctno));
  $('bankSelect').innerHTML = (rows.length ? '' : '<option value="">— เพิ่มบัญชี —</option>') + rows.map(b =>
    `<option value="${esc(b.bank_id)}">${esc(b.bank_name)} · ${esc(b.bank_account_number)}${b.is_default?' ★':''}</option>`
  ).join('');
}

async function loadBills() {
  if (!picked) {
    $('billList').innerHTML = `<tr><td colspan="4" class="empty">เลือกเจ้าหนี้ก่อน</td></tr>`;
    updateBillSelectStatus();
    return;
  }
  $('billList').innerHTML = `<tr><td colspan="4" class="empty">กำลังโหลดบิล…</td></tr>`;
  try {
    const rows = await api('/bills?acctno=' + encodeURIComponent(picked.acctno));
    $('billList').innerHTML = rows.map(b =>
      `<tr>
        <td data-label=""><input type="checkbox" value="${esc(b.BILLNO)}" data-amt="${Number(b.AFTERTAX)||0}" aria-label="เลือกบิล ${esc(b.BILLNO)}"/></td>
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
function resolveDiscAmount(bill) {
  const raw = Math.max(0, Number($('discInput').value || 0));
  if (discMode === 'percent') return Math.round(bill * Math.min(raw, 100) / 100 * 100) / 100;
  return Math.round(raw * 100) / 100;
}
function syncDiscPreview() {
  const { total } = selectedBillTotal();
  const disc = resolveDiscAmount(total);
  $('discBillAmt').textContent = fmtMoney(total);
  $('discResolved').textContent = fmtMoney(disc);
  $('discNetAmt').textContent = fmtMoney(Math.max(0, total - disc));
  $('discResolved').style.color = (disc - total > 1e-9) ? 'var(--down)' : '';
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
  updateWizardNextState();
}

function billMatchNeedsAck() {
  if (!scanResult) return false;
  const badLines = (scanResult.lines || []).some(ln => ln.status !== 'matched');
  const totalBad = scanResult.total_match === false;
  return badLines || totalBad || (scanResult.unmatched || []).length || (scanResult.ambiguous || []).length;
}

function renderAiLineMatch(result) {
  const box = $('aiLineMatch');
  if (!box) return;
  if (!result || !(result.lines || []).length) {
    box.classList.add('hidden');
    box.innerHTML = '';
    return;
  }
  const rows = (result.lines || []).map(ln => {
    const ex = ln.extracted || {};
    const m = ln.matched;
    const kssBill = m ? esc(m.billno) : '—';
    const kssAmt = m ? fmtMoney(m.aftertax) : '—';
    const reason = m ? esc(m.match_label || m.match || '') : esc(ln.status || '');
    const st = m ? '✓' : '⚠';
    return `<tr>
      <td>${esc(ex.billno || '—')}</td>
      <td class="num">${fmtMoney(ex.amount)}</td>
      <td>${kssBill}</td>
      <td class="num">${kssAmt}</td>
      <td>${reason}</td>
      <td>${st}</td>
    </tr>`;
  }).join('');
  const docTotal = result.document_total != null ? result.document_total : result.extracted_total;
  const selTotal = result.selected_total;
  const totalCls = result.total_match ? 'ai-ok' : 'ai-warn';
  box.className = `ai-panel ${totalCls}`;
  box.innerHTML = `
    <div><strong>ผลการจับคู่จากเอกสาร</strong></div>
    <table class="ai-line-table">
      <thead><tr>
        <th>เอกสาร</th><th class="num">ยอดเอกสาร</th>
        <th>บิล KSS</th><th class="num">ยอด KSS</th>
        <th>วิธีจับคู่</th><th></th>
      </tr></thead>
      <tbody>${rows}</tbody>
    </table>
    <div style="margin-top:.45rem">ยอดเอกสาร (ก่อนส่วนลด) <strong>${fmtMoney(docTotal)}</strong>
      · ยอดเลือก <strong>${fmtMoney(selTotal)}</strong></div>
    ${(result.unmatched || []).length ? `<div class="ai-warn" style="margin-top:.35rem">ไม่พบในระบบ: ${(result.unmatched||[]).map(esc).join(', ')}</div>` : ''}
  `;
  box.classList.remove('hidden');
}

function applyScanResult(result) {
  scanResult = result;
  renderAiLineMatch(result);
  const auto = new Set(result.auto_selected_billnos || []);
  $('billList').querySelectorAll('input[type=checkbox]').forEach(cb => {
    if (auto.has(cb.value)) cb.checked = true;
  });
  updateBillSelectStatus();
  $('billMatchAckWrap').classList.toggle('hidden', createMode !== 'assist' || !billMatchNeedsAck());
  if ($('billMatchAck')) $('billMatchAck').checked = false;
}

async function scanBillDocument(files) {
  if (!picked) { alert('เลือกเจ้าหนี้ก่อน'); return false; }
  const file = files && files[0];
  if (!file) return false;
  if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); return false; }
  $('scanStatus').textContent = 'กำลังอ่านรายการบิล…';
  $('btnScanSkip').classList.add('hidden');
  const fd = new FormData();
  fd.append('acctno', picked.acctno);
  fd.append('file', file);
  try {
    const r = await fetch('/pay-notes/api/ai/scan-bills', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(j.detail || j.error || r.statusText);
    await loadBills();
    applyScanResult(j);
    $('scanStatus').textContent = `อ่านได้ ${(j.lines||[]).length} รายการ · จับคู่ ${(j.auto_selected_billnos||[]).length} บิล`;
    if (createMode === 'assist') wizardStep = 3;
    applyCreateMode();
    return true;
  } catch (e) {
    $('scanStatus').innerHTML = `<span class="err">${esc(e.message)}</span>`;
    $('btnScanSkip').classList.remove('hidden');
    return false;
  }
}

function applyCreateMode() {
  const assist = createMode === 'assist' && AI_ENABLED;
  $('createModeToggle')?.classList.toggle('hidden', !AI_ENABLED);
  $('wizardNav')?.classList.toggle('hidden', !assist);
  $('btnModeManual')?.classList.toggle('on', createMode === 'manual' || !AI_ENABLED);
  $('btnModeAssist')?.classList.toggle('on', assist);
  $('wizardScanBlock')?.classList.toggle('hidden', !assist);
  document.querySelectorAll('.wizard-block').forEach(el => {
    const n = Number(el.dataset.assistStep || 0);
    if (!assist) {
      el.classList.remove('wizard-hidden');
    } else {
      el.classList.toggle('wizard-hidden', n !== wizardStep);
    }
  });
  $('btnCreateNote').classList.toggle('hidden', assist && wizardStep < 6);
  $('wizardProgress').textContent = `ขั้น ${wizardStep}/6`;
  $('btnWizardBack').classList.toggle('hidden', wizardStep <= 1);
  $('btnWizardNext').classList.toggle('hidden', wizardStep >= 6);
  updateWizardNextState();
  try { localStorage.setItem('kcw.pay_notes.create_mode', createMode); } catch (e) {}
}

function updateWizardNextState() {
  if (createMode !== 'assist' || !AI_ENABLED) return;
  let blocked = false;
  if (wizardStep === 1 && !picked) blocked = true;
  if (wizardStep === 3 && billMatchNeedsAck() && !($('billMatchAck') && $('billMatchAck').checked)) blocked = true;
  $('btnWizardNext').disabled = blocked;
}

function setCreateMode(mode) {
  if (mode === 'assist' && !AI_ENABLED) return;
  createMode = mode === 'assist' ? 'assist' : 'manual';
  if (createMode === 'assist') wizardStep = picked ? Math.max(wizardStep, 1) : 1;
  applyCreateMode();
}

$('btnModeManual').onclick = () => setCreateMode('manual');
$('btnModeAssist').onclick = () => setCreateMode('assist');
$('btnWizardBack').onclick = () => {
  if (wizardStep > 1) { wizardStep -= 1; applyCreateMode(); }
};
$('btnWizardNext').onclick = () => {
  if (wizardStep === 1 && !picked) { alert('เลือกเจ้าหนี้ก่อน'); return; }
  if (wizardStep < 6) { wizardStep += 1; applyCreateMode(); }
};
$('billMatchAck')?.addEventListener('change', updateWizardNextState);
$('btnScanSkip').onclick = () => {
  scanResult = null;
  $('aiLineMatch').classList.add('hidden');
  $('billMatchAckWrap').classList.add('hidden');
  wizardStep = 3;
  applyCreateMode();
};
wireDropZone($('dropScan'), $('scanFiles'), scanBillDocument);

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
  $('btnProofDone').disabled = !proofCanComplete();
});
$('btnProofDone').onclick = () => {
  const fresh = voucherRows.find(x => keyOf(x) === keyOf(detailRow)) || awaitProofRows.find(x => keyOf(x) === keyOf(detailRow));
  completeProofFlow(fresh);
};

$('btnRefreshBills').onclick = () => loadBills();
$('btnAddBank').onclick = async () => {
  if (!picked) { alert('เลือกเจ้าหนี้ก่อน'); return; }
  try {
    await api('/banks', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: picked.acctno,
        bank_name: $('newBankName').value.trim(),
        bank_account_name: $('newAcctName').value.trim(),
        bank_account_number: $('newAcctNo').value.trim(),
      })
    });
    await loadBanks();
  } catch (e) { alert(e.message); }
};

async function uploadBillFiles(files) {
  const noteno = $('noteno').value.trim();
  if (!picked || !noteno) { alert('เลือกเจ้าหนี้และกรอกเลขที่ใบวางบิลก่อน'); return; }
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); continue; }
    const fd = new FormData();
    fd.append('acctno', picked.acctno);
    fd.append('noteno', noteno);
    fd.append('file', file);
    const r = await fetch('/pay-notes/api/images/bill', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { alert(j.detail || j.error); continue; }
    uploadedPaths.push(j.path);
    appendUploadThumb($('billThumbs'), file, j);
  }
}
wireDropZone($('dropBill'), $('billImages'), uploadBillFiles);

$('btnCreateNote').onclick = async () => {
  const noteno = $('noteno').value.trim();
  const due = $('dueDate').value;
  const bank_id = $('bankSelect').value;
  const billnos = [...$('billList').querySelectorAll('input:checked')].map(x => x.value);
  $('createMsg').innerHTML = '';
  if (!WRITE_ENABLED) { $('createMsg').innerHTML = '<p class="err">KSS write ปิดอยู่ (PAY_NOTES_WRITE_ENABLED)</p>'; return; }
  if (!picked) { $('createMsg').innerHTML = '<p class="err">เลือกเจ้าหนี้</p>'; return; }
  if (!noteno || !due || !bank_id) { $('createMsg').innerHTML = '<p class="err">กรอกเลขใบวางบิล เลือกวันครบกำหนด และบัญชีธนาคาร</p>'; return; }
  if (!billnos.length) { $('createMsg').innerHTML = '<p class="err">เลือกบิลอย่างน้อย 1</p>'; return; }
  if (!uploadedPaths.length) { $('createMsg').innerHTML = '<p class="err">อัปโหลดเอกสารอย่างน้อย 1</p>'; return; }
  const { total } = selectedBillTotal();
  if (resolveDiscAmount(total) - total > 1e-9) {
    $('createMsg').innerHTML = '<p class="err">ส่วนลดมากกว่ายอดบิล</p>'; return;
  }
  try {
    const res = await api('/notes', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        acctno: picked.acctno, acctname: picked.acctname, noteno, due_date: due,
        bank_id, billnos, discount_mode: discMode,
        discount_input: Number($('discInput').value || 0),
        remark: ($('noteRemark').value || '').trim()
      })
    });
    const rem = res.reminder || {};
    const discShow = Number(rem.discount_amount != null ? rem.discount_amount : resolveDiscAmount(total));
    const netShow = Math.max(0, Number(res.billamt || total) - discShow);
    $('createMsg').innerHTML = `<p class="ok">บันทึกใบวางบิลแล้ว · ${esc(res.noteno)} · จ่าย ${fmtMoney(netShow)}</p>`;
    uploadedPaths = [];
    $('billThumbs').innerHTML = '';
    $('discInput').value = '0.00';
    $('noteRemark').value = '';
    setDiscMode('amount');
    await loadBills();
    setTimeout(() => { showTab('pending'); }, 600);
  } catch (e) {
    $('createMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`;
    await loadBills();
  }
};

async function openEditNote(key, returnTab) {
  const row = findRow(key) || pendingRows.find(r => keyOf(r) === key);
  if (!row || !row.is_editable) { alert('ใบวางบิลนี้แก้ไขไม่ได้'); return; }
  editTarget = row;
  editReturnTab = returnTab || 'pending';
  showEditPanel(true);
  setCrumb('edit', `${row.noteno} · ${row.acctno}`);
  $('editTitle').textContent = `แก้ไขใบวางบิล ${row.noteno}`;
  $('editVendor').value = `${row.acctno} — ${row.acctname || ''}`;
  $('editNoteno').value = row.noteno;
  const rem = row.reminder || {};
  $('editDueDate').value = remDue(row);
  $('editNoteRemark').value = rem.remark || '';
  editDiscMode = rem.discount_mode === 'percent' ? 'percent' : 'amount';
  $('editDiscInput').value = rem.discount_input != null ? rem.discount_input : (rem.discount_amount || 0);
  setEditDiscMode(editDiscMode);
  $('editMsg').innerHTML = '';
  $('editBillThumbs').innerHTML = '';
  const banks = await api('/banks?acctno=' + encodeURIComponent(row.acctno));
  $('editBankSelect').innerHTML = banks.map(b =>
    `<option value="${esc(b.bank_id)}">${esc(b.bank_name)} · ${esc(b.bank_account_number)}</option>`
  ).join('');
  if (rem.bank_id) $('editBankSelect').value = rem.bank_id;
  await loadEditBills();
  const det = await api(`/notes/${encodeURIComponent(row.acctno)}/${encodeURIComponent(row.noteno)}`);
  $('editBillThumbs').innerHTML = thumbsHtml(det.bill_images || []);
  wireDatePickers($('panelEdit'));
}
async function loadEditBills() {
  if (!editTarget) return;
  $('editBillList').innerHTML = `<tr><td colspan="4" class="empty">กำลังโหลด…</td></tr>`;
  const rows = await api('/bills?acctno=' + encodeURIComponent(editTarget.acctno) + '&noteno=' + encodeURIComponent(editTarget.noteno));
  $('editBillList').innerHTML = rows.map(b =>
    `<tr>
      <td data-label=""><input type="checkbox" value="${esc(b.BILLNO)}" data-amt="${Number(b.AFTERTAX)||0}" ${b.attached ? 'checked' : ''} aria-label="เลือกบิล ${esc(b.BILLNO)}"/></td>
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
  const raw = Math.max(0, Number($('editDiscInput').value || 0));
  if (editDiscMode === 'percent') return Math.round(bill * Math.min(raw, 100) / 100 * 100) / 100;
  return Math.round(raw * 100) / 100;
}
function syncEditDiscPreview() {
  const { total } = editSelectedBillTotal();
  const disc = resolveEditDiscAmount(total);
  $('editDiscBillAmt').textContent = fmtMoney(total);
  $('editDiscResolved').textContent = fmtMoney(disc);
  $('editDiscNetAmt').textContent = fmtMoney(Math.max(0, total - disc));
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
}
$('editDiscModeAmount').onclick = () => setEditDiscMode('amount');
$('editDiscModePercent').onclick = () => setEditDiscMode('percent');
$('editDiscInput').addEventListener('input', syncEditDiscPreview);
$('btnRefreshEditBills').onclick = () => loadEditBills();
async function uploadEditBillFiles(files) {
  if (!editTarget) return;
  for (const file of files) {
    if (file.size > MAX_FILE_BYTES) { alert(`${file.name} เกิน 10 MB`); continue; }
    const fd = new FormData();
    fd.append('acctno', editTarget.acctno);
    fd.append('noteno', editTarget.noteno);
    fd.append('file', file);
    const r = await fetch('/pay-notes/api/images/bill', {method:'POST', body: fd});
    const j = await r.json().catch(() => ({}));
    if (!r.ok) { alert(j.detail || j.error); continue; }
    appendUploadThumb($('editBillThumbs'), file, j);
  }
}
wireDropZone($('dropEditBill'), $('editBillImages'), uploadEditBillFiles);

$('btnSaveEdit').onclick = async () => {
  if (!editTarget || !WRITE_ENABLED) { $('editMsg').innerHTML = '<p class="err">KSS write ปิดอยู่</p>'; return; }
  const billnos = [...$('editBillList').querySelectorAll('input:checked')].map(x => x.value);
  if (!billnos.length) { $('editMsg').innerHTML = '<p class="err">เลือกบิลอย่างน้อย 1</p>'; return; }
  const { total } = editSelectedBillTotal();
  if (resolveEditDiscAmount(total) - total > 1e-9) {
    $('editMsg').innerHTML = '<p class="err">ส่วนลดมากกว่ายอดบิล</p>'; return;
  }
  try {
    await api(`/notes/${encodeURIComponent(editTarget.acctno)}/${encodeURIComponent(editTarget.noteno)}`, {
      method:'PATCH', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({
        billnos,
        due_date: $('editDueDate').value,
        bank_id: $('editBankSelect').value,
        remark: ($('editNoteRemark').value || '').trim(),
        discount_mode: editDiscMode,
        discount_input: Number($('editDiscInput').value || 0),
      })
    });
    $('editMsg').innerHTML = '<p class="ok">บันทึกแล้ว</p>';
    editTarget = null;
    setTimeout(() => showTab(editReturnTab), 500);
  } catch (e) { $('editMsg').innerHTML = `<p class="err">${esc(e.message)}</p>`; }
};

wireDatePickers(document);
setDiscMode('amount');
$('billList').innerHTML = `<tr><td colspan="4" class="empty">เลือกเจ้าหนี้ก่อน</td></tr>`;
try {
  const saved = localStorage.getItem('kcw.pay_notes.create_mode');
  if (saved === 'assist' && AI_ENABLED) createMode = 'assist';
} catch (e) {}
applyCreateMode();
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

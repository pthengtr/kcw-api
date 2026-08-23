from src.handlers.explorer_entry import is_explorer_command
from src.parts9_explorer.net import is_tailscale_cg_nat
from src.parts9_explorer.query import infer_doc_kind, maybe_document_query, parse_query
from src.parts9_explorer.search import _DOC_SPECS, _pack_doc, product_image_urls
from src.parts9_explorer.config import get_explorer_settings
from src.parts9_explorer.ui import page


def test_explorer_commands():
    assert is_explorer_command("parts9")
    assert is_explorer_command("ค้นหา")
    assert is_explorer_command("สำรวจ")
    assert not is_explorer_command("สินค้า 22010585")
    assert not is_explorer_command("เช็คสต็อก")


def test_tailscale_cgnat():
    assert is_tailscale_cg_nat("100.113.143.97")
    assert is_tailscale_cg_nat("100.64.0.1")
    assert is_tailscale_cg_nat("100.127.255.1")
    assert not is_tailscale_cg_nat("192.168.1.21")
    assert not is_tailscale_cg_nat("100.63.0.1")
    assert not is_tailscale_cg_nat("127.0.0.1")
    assert is_tailscale_cg_nat("fd7a:115c:a1e0::7b3a:8f62")


def test_parse_bcode_and_seal_sizes():
    p = parse_query("22010585")
    assert p.kind == "product"
    assert p.bcode_prefix == "22010585"
    s = parse_query("ซีล 31 46 7")
    assert s.code1 == "C"
    assert s.sizes == ["31", "46", "7"]
    d = parse_query("KCPN6901-12")
    assert d.kind == "document"
    assert d.docno.startswith("KCPN")
    assert d.doc_kind == "pv"
    po = parse_query("PO6905-392")
    assert po.doc_kind == "po"
    assert po.want_product is False
    pi = parse_query("pi 254929")
    assert pi.doc_kind == "pi"
    assert pi.docno == "254929"
    thai = parse_query("ค้างรับ PO6905-392")
    assert thai.doc_kind == "iclow"
    assert infer_doc_kind("8K69-0013225") == "si"
    assert infer_doc_kind("RC6907-001") == "rv"
    note = parse_query("โน้ต 103772300")
    assert note.doc_kind == "pv"
    assert note.docno == "103772300"
    assert parse_query("note BA25656").doc_kind == "pv"
    assert maybe_document_query("103772300")
    assert maybe_document_query("PACO4-260700251")
    assert not maybe_document_query("ซีล 31 46")


def test_product_image_urls(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    get_explorer_settings.cache_clear()
    urls = product_image_urls("ABC")
    assert urls[0].endswith("/pictures/product/ABC/ABC.jpg")
    get_explorer_settings.cache_clear()


def test_pv_sql_matches_note_and_voucher():
    sql = _DOC_SPECS["pv"]["header"]
    assert "NOTENO" in sql
    assert "VOUCNO" in sql
    assert "NOTENO" in _DOC_SPECS["pi"]["header"]


def test_explorer_page_has_theme_toggle():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert 'id="themeBtn"' in html
    assert 'data-theme' in html
    assert "kcw.parts9.theme" in html
    assert 'html[data-theme="light"]' in html
    assert 'html[data-theme="dark"]' in html


def test_parse_oem_mcode_and_code1():
    oem = parse_query("12371-0L040")
    assert oem.kind == "product"
    assert oem.want_product is True
    assert oem.bcode_prefix is None
    assert oem.text_terms == ["12371-0L040"]

    mfr = parse_query("ME201571")
    assert mfr.kind == "product"
    assert mfr.want_product is True
    assert mfr.text_terms == ["ME201571"]

    labeled = parse_query("oem 90915-YZZD3")
    assert labeled.kind == "product"
    assert labeled.text_terms == ["90915-YZZD3"]
    assert parse_query("mcode MD075760").text_terms == ["MD075760"]
    assert parse_query("เบอร์แท้ 12371-0L040").text_terms == ["12371-0L040"]

    assert parse_query("I").code1 == "I"
    assert parse_query("K").code1 == "K"
    assert parse_query("code1 I").code1 == "I"
    assert parse_query("ประเภท K").code1 == "K"
    combo = parse_query("I 6201")
    assert combo.kind == "product"
    assert combo.code1 == "I"
    assert combo.sizes == ["6201"]

    # Known bill prefixes stay documents
    assert parse_query("KCPN6901-12").kind == "document"
    assert parse_query("PO6905-392").want_product is False


def test_product_search_matches_pcode_mcode_and_code1():
    from src.parts9_explorer.search import _term_match_sql

    sql = _term_match_sql("t0")
    assert "PCODE LIKE :t0" in sql
    assert "MCODE LIKE :t0" in sql
    assert "CODE1" in sql
    sized = _term_match_sql("sz1", include_size_slot=1)
    assert "SIZE1" in sized
    assert "PCODE LIKE :sz1" in sized


def test_explorer_page_mentions_oem_and_code1():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert "เบอร์แท้" in html
    assert "เบอร์โรงงาน" in html
    assert "PCODE" in html
    assert "MCODE" in html


def test_pack_note_only_pv_uses_noteno():
    packed = _pack_doc(
        "pv",
        "hq",
        {"VOUCNO": "", "NOTENO": "103772300", "ACCTNAME": "STATE"},
        [],
    )
    assert packed["docno"] == "103772300"
    assert packed["kind_label"] == "โน้ตจ่าย NP"


def test_explorer_page_hides_pyodbc_timeout():
    html = page(
        user_name="t",
        site="hq",
        probes={
            "hq": {"ok": True, "server": "KSS"},
            "syp": {
                "ok": False,
                "error": "(pyodbc.OperationalError) ('HYT00', 'Login timeout expired')",
            },
        },
    )
    assert "HQ SQL KSS" in html
    assert "SYP SQL down" in html
    assert "HYT00" not in html
    assert "pyodbc" not in html


def test_format_sql_timeout_is_short():
    from src.parts9_explorer.db import format_sql_error

    msg = format_sql_error(
        Exception("(pyodbc.OperationalError) ('HYT00', '[HYT00] Login timeout expired')"),
        site="syp",
    )
    assert "HYT00" not in msg
    assert "pyodbc" not in msg
    assert "SYP SQL" in msg
    assert "ไม่เชื่อมต่อ" in msg


def _explorer_html():
    return page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})


def test_explorer_page_uses_thai_headers_and_formats_billamt():
    html = _explorer_html()
    assert 'BILLAMT:"ยอดบิล"' in html
    assert 'JOURTYPE:"ประเภทสมุด"' in html
    assert 'NOTENO:"เลขโน้ต"' in html
    assert 'LINE:"ลำดับ"' in html
    assert 'BCODE:"รหัสสินค้า"' in html
    assert 'DETAIL:"รายละเอียด"' in html
    assert 'QTY:"จำนวน"' in html
    assert 'UI:"หน่วย"' in html
    assert 'PRICE:"ราคา"' in html
    assert 'AMOUNT:"จำนวนเงิน"' in html
    assert "MONEY_KEYS.has(k) ? money(obj[k])" in html
    assert 'if (c === "LINE") return "<td>"+(i+1)+"</td>"' in html
    assert 'minimumFractionDigits: 2' in html


def test_explorer_js_renders_comma_billamt_and_sequential_lines(tmp_path):
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        raise AssertionError("node is required to verify explorer money/LINE rendering")
    html = _explorer_html()
    start = html.index("const STATUS_TH")
    end = html.index("function jumpProduct")
    helpers = html[start:end]
    script = helpers + r"""
const header = {
  JOURTYPE: "NP", VOUCED: "N", NOTED: "Y", NOTEDATE: "2026-08-22",
  NOTENO: "ABC7/69", ACCTNO: "123", ACCTNAME: "บจก. ทดสอบ",
  BILLCNT: "5", BILLAMT: "31809.14", CANCELED: "N"
};
const lines = [
  {LINE:"10", BCODE:"2201", DETAIL:"สายพาน", QTY:"2", UI:"เส้น", PRICE:"1000.5", AMOUNT:"2001"},
  {LINE:"20", BCODE:"2202", DETAIL:"สายพาน 2", QTY:"1", UI:"เส้น", PRICE:"50", AMOUNT:"50"},
];
process.stdout.write(JSON.stringify({
  kv: kvTable(header),
  table: lineTable(lines, ["LINE","BCODE","DETAIL","QTY","UI","PRICE","AMOUNT"]),
  money: money("31809.14"),
  lineLabel: colTh("LINE"),
}));
"""
    script_path = tmp_path / "render_explorer.js"
    script_path.write_text(script, encoding="utf-8")
    result = subprocess.run([node, str(script_path)], capture_output=True, text=True, check=True)
    out = json.loads(result.stdout)
    assert "31,809.14" in out["money"]
    assert "ยอดบิล" in out["kv"]
    assert "ประเภทสมุด" in out["kv"]
    assert "เลขโน้ต" in out["kv"]
    assert "ชื่อบัญชี" in out["kv"]
    assert "BILLAMT" not in out["kv"]
    assert "JOURTYPE" not in out["kv"]
    assert "31,809.14" in out["kv"]
    assert "31809.14" not in out["kv"]
    assert out["lineLabel"] == "ลำดับ"
    assert "<th>ลำดับ</th>" in out["table"]
    assert "<th>รหัสสินค้า</th>" in out["table"]
    assert "<th>รายละเอียด</th>" in out["table"]
    assert "<th>LINE</th>" not in out["table"]
    assert "<th>BCODE</th>" not in out["table"]
    assert "<td>1</td>" in out["table"]
    assert "<td>2</td>" in out["table"]
    assert "<td>10</td>" not in out["table"]
    assert "<td>20</td>" not in out["table"]

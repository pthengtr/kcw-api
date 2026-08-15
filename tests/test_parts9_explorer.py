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


def test_pack_note_only_pv_uses_noteno():
    packed = _pack_doc(
        "pv",
        "hq",
        {"VOUCNO": "", "NOTENO": "103772300", "ACCTNAME": "STATE"},
        [],
    )
    assert packed["docno"] == "103772300"
    assert packed["kind_label"] == "โน้ตจ่าย NP"

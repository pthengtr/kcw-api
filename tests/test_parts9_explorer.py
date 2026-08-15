from src.handlers.explorer_entry import is_explorer_command
from src.parts9_explorer.net import is_tailscale_cg_nat
from src.parts9_explorer.query import parse_query
from src.parts9_explorer.search import product_image_urls
from src.parts9_explorer.config import get_explorer_settings


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


def test_product_image_urls(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    get_explorer_settings.cache_clear()
    urls = product_image_urls("ABC")
    assert urls[0].endswith("/pictures/product/ABC/ABC.jpg")
    get_explorer_settings.cache_clear()

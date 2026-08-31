from src.handlers.services_menu import (
    handle_services_menu,
    is_services_menu_request,
    services_menu_handlers_match,
)
from src.handlers.transfer_entry import _rewrite_worker_transfer_urls, is_transfer_command
from src.transfer.net import rewrite_base_port
from src.transfer.ui import page


def test_transfer_commands():
    assert is_transfer_command("โอนสินค้า")
    assert is_transfer_command("transfer")
    assert is_transfer_command(" โอน ")
    assert not is_transfer_command("โอนเงิน")


def test_services_menu_triggers():
    assert is_services_menu_request("menu")
    assert is_services_menu_request("เมนู")
    assert is_services_menu_request("services")
    assert not is_services_menu_request("help")


def test_services_menu_flex():
    msg = handle_services_menu()
    assert msg["type"] == "flex"
    assert msg["contents"]["type"] == "bubble"


def test_services_menu_handlers():
    m = services_menu_handlers_match()
    assert m["transfer"] and m["stock_check"] and m["pay_notes"]


def test_rewrite_port():
    assert rewrite_base_port("http://100.113.143.97:8788", 8792) == "http://100.113.143.97:8792"


def test_rewrite_worker_transfer_urls_keeps_syp_lan(monkeypatch):
    monkeypatch.setenv("TRANSFER_PUBLIC_BASE_URL", "http://192.168.1.21:8792")
    monkeypatch.setenv("TRANSFER_TAILSCALE_BASE_URL", "http://100.113.143.97:8792")
    workers = [
        {
            "worker_name": "HQ-UBUNTU-SERVER",
            "explorer_public_base_url": "http://192.168.1.21:8788",
        },
        {
            "worker_name": "SYP-UBUNTU-SERVER",
            "transfer_public_base_url": "http://192.168.1.216:8792",
            "transfer_tailscale_base_url": "http://100.94.98.18:8792",
        },
    ]
    out = _rewrite_worker_transfer_urls(workers)
    by_name = {w["worker_name"]: w for w in out}
    assert by_name["HQ-UBUNTU-SERVER"]["transfer_public_base_url"] == "http://192.168.1.21:8792"
    assert by_name["SYP-UBUNTU-SERVER"]["transfer_public_base_url"] == "http://192.168.1.216:8792"
    assert by_name["SYP-UBUNTU-SERVER"]["transfer_tailscale_base_url"] == "http://100.94.98.18:8792"


def test_transfer_page_renders():
    html = page(
        user_name="ทดสอบ",
        site="SYP",
        hq_ship_enabled=False,
        syp_ship_enabled=False,
        hq_receive_enabled=False,
        syp_receive_enabled=False,
    )
    assert "โอนสินค้า · SYP" in html
    assert "ขอสินค้าจาก" in html
    assert "จัดส่งไป" in html
    assert "ตรวจสอบสถานะ" in html
    assert "ขั้นตอนโอนสินค้า" in html

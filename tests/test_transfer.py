from src.handlers.services_menu import (
    handle_services_menu,
    is_services_menu_request,
    services_menu_handlers_match,
)
from src.handlers.transfer_entry import is_transfer_command
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
    assert "แนะนำโอน" in html
    assert "รอจัด (ออก)" in html

from src.handlers.services_menu import (
    handle_services_menu,
    is_services_menu_request,
    iter_services_menu_buttons,
)
from src.staff_shell.catalog import line_menu_sections


def test_menu_not_help():
    assert is_services_menu_request("menu")
    assert is_services_menu_request("เมนู")


def test_menu_has_transfer_button():
    msg = handle_services_menu()
    buttons = iter_services_menu_buttons(msg)
    labels = [c["action"]["label"] for c in buttons]
    texts = [c["action"]["text"] for c in buttons]
    assert "โอนสินค้า" in labels
    assert "โอนสินค้า" in texts
    assert "สถานะใบสั่งซื้อ" not in labels
    assert "สถานะใบสั่งซื้อ" not in texts


def test_menu_is_categorized_two_column():
    msg = handle_services_menu()
    body = msg["contents"]["body"]["contents"]
    titles = [c["text"] for c in body if c.get("type") == "text" and c.get("size") == "xs"]
    assert "สินค้าและสต็อก" in titles
    assert "คลังและจัดซื้อ" in titles
    assert "ขายและการเงิน" in titles
    assert "เครื่องมือ" in titles

    rows = [c for c in body if c.get("type") == "box" and c.get("layout") == "horizontal"]
    assert rows, "expected horizontal button rows"
    for row in rows:
        buttons = [n for n in row["contents"] if n.get("type") == "button"]
        assert 1 <= len(buttons) <= 2
        assert all(b.get("flex") == 1 for b in buttons)
        assert all(b["action"]["type"] == "message" for b in buttons)

    sections = line_menu_sections()
    assert all(services for _title, services in sections)
    # Every menu button still launches the service command directly (no submenu).
    for _title, services in sections:
        for svc in services:
            assert svc.line_command

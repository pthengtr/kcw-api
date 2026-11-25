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
    assert body[0]["text"] == "KCW Services"
    assert not any(
        c.get("type") == "text" and "กดเลือกบริการ" in (c.get("text") or "")
        for c in body
    )
    titles = [c["text"] for c in body if c.get("type") == "text" and c.get("size") == "xs"]
    assert titles == ["สินค้า", "ขาย", "จัดซื้อ", "บัญชี"]

    # Grid rows: horizontal boxes whose children are tappable service cells.
    grid_rows = [
        c
        for c in body
        if c.get("type") == "box"
        and c.get("layout") == "horizontal"
        and any(
            isinstance(n, dict) and n.get("backgroundColor") == "#F5F6F8"
            for n in (c.get("contents") or [])
        )
    ]
    assert grid_rows, "expected horizontal service rows"
    for row in grid_rows:
        cells = [
            n
            for n in row["contents"]
            if isinstance(n, dict) and n.get("backgroundColor") == "#F5F6F8"
        ]
        assert 1 <= len(cells) <= 2
        assert all(c.get("flex") == 1 for c in cells)
        assert all(c["action"]["type"] == "message" for c in cells)
        for cell in cells:
            icon = next(n for n in cell["contents"] if n.get("type") == "icon")
            assert icon["size"] == "xxs"
            assert icon["url"].endswith(".png")
            label = next(n for n in cell["contents"] if n.get("type") == "text")
            assert label.get("align") == "start"

    sections = line_menu_sections()
    assert [t for t, _ in sections] == ["สินค้า", "ขาย", "จัดซื้อ", "บัญชี"]
    assert all(services for _title, services in sections)
    # Help is footer-only, not a category grid item.
    assert all(svc.id != "help" for _t, svcs in sections for svc in svcs)
    # Every menu cell still launches the service command directly (no submenu).
    for _title, services in sections:
        for svc in services:
            assert svc.line_command

    help_btns = [
        b for b in iter_services_menu_buttons(msg) if b["action"]["text"] == "help"
    ]
    assert len(help_btns) == 1
    assert help_btns[0]["action"]["label"] == "วิธีใช้ทั้งหมด"

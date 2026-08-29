from src.handlers.services_menu import handle_services_menu, is_services_menu_request


def test_menu_not_help():
    assert is_services_menu_request("menu")
    assert is_services_menu_request("เมนู")


def test_menu_has_transfer_button():
    msg = handle_services_menu()
    body = msg["contents"]["body"]["contents"]
    labels = [c["action"]["label"] for c in body if c.get("type") == "button"]
    texts = [c["action"]["text"] for c in body if c.get("type") == "button"]
    assert "โอนสินค้า" in labels
    assert "โอนสินค้า" in texts

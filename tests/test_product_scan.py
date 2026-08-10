"""Tests for LIFF product-scan intent, callback contract, and routing."""

from unittest.mock import MagicMock, patch

from src.handlers.product_scan import (
    handle_product_scan_callback,
    handle_product_scan_command,
    is_product_scan_callback,
    is_product_scan_command,
)
from src.handlers.router import route_user_text
from src.liff.product_scan_contract import (
    PRODUCT_SCAN_CALLBACK_PREFIX,
    format_product_scan_callback,
    parse_product_scan_callback,
    sanitize_barcode,
)


ACCESS = {"access_group": "staff"}


def test_product_scan_command_aliases():
    for text in (
        "สแกน",
        " สแกน ",
        "สแกนสินค้า",
        " สแกนสินค้า ",
        "สแกน บาร์โค้ด",
        "สแกนบาร์โค้ด",
        "scan",
        "Scan",
        "scan product",
        "Scan Product",
        "scanproduct",
        "scan barcode",
        "scanbarcode",
    ):
        assert is_product_scan_command(text), text


def test_product_scan_command_does_not_match_unrelated():
    for text in (
        "สแกนตาราง",
        "เช็ค 22010585",
        "สินค้า 22010585",
        f"{PRODUCT_SCAN_CALLBACK_PREFIX} 22010585",
        "เฮียช้า สแกนสินค้า",
        "",
    ):
        assert not is_product_scan_command(text), text


def test_router_bare_scan_opens_liff_not_table_printout():
    with patch(
        "src.handlers.product_scan.KCW_LIFF_PRODUCT_SCANNER_URL",
        "https://liff.line.me/test-liff",
    ):
        result = route_user_text(MagicMock(), "สแกน", ACCESS)

    assert result["type"] == "messages"
    assert result["messages"][0]["type"] == "template"
    assert result["messages"][0]["template"]["actions"][0]["type"] == "uri"

def test_format_and_parse_callback_roundtrip():
    msg = format_product_scan_callback("8851234567890")
    assert msg == "📦 สแกนสินค้า: 8851234567890"
    assert parse_product_scan_callback(msg) == "8851234567890"
    assert is_product_scan_callback(msg)


def test_parse_callback_without_emoji_prefix():
    assert parse_product_scan_callback("สแกนสินค้า: ABC-123") == "ABC-123"


def test_sanitize_barcode_rejects_bad_values():
    assert sanitize_barcode("") is None
    assert sanitize_barcode("   ") is None
    assert sanitize_barcode("bad code") is None
    assert sanitize_barcode("emoji😀") is None
    assert sanitize_barcode("x" * 65) is None
    assert sanitize_barcode("22010585") == "22010585"
    assert sanitize_barcode("*22010585*") == "22010585"
    assert sanitize_barcode("SKU_01.2-A") == "SKU_01.2-A"


def test_handle_product_scan_command_returns_liff_button():
    with patch(
        "src.handlers.product_scan.KCW_LIFF_PRODUCT_SCANNER_URL",
        "https://liff.line.me/1234567890-AbCdEfGh",
    ):
        result = handle_product_scan_command()

    assert result["type"] == "messages"
    msg = result["messages"][0]
    assert msg["type"] == "template"
    assert msg["template"]["type"] == "buttons"
    action = msg["template"]["actions"][0]
    assert action["type"] == "uri"
    assert action["uri"] == "https://liff.line.me/1234567890-AbCdEfGh"
    assert "สแกน" in action["label"]


def test_handle_product_scan_command_missing_env():
    with patch("src.handlers.product_scan.KCW_LIFF_PRODUCT_SCANNER_URL", ""):
        result = handle_product_scan_command()
    assert result["type"] == "text"
    assert "KCW_LIFF_PRODUCT_SCANNER_URL" in result["text"]


def test_handle_product_scan_callback_calls_check_lookup():
    engine = MagicMock()
    expected = {"type": "text", "text": "สินค้า 22010585\nTest Product"}

    with patch(
        "src.handlers.product_scan.handle_check_response",
        return_value=expected,
    ) as check:
        result = handle_product_scan_callback(
            engine, "📦 สแกนสินค้า: 22010585"
        )

    check.assert_called_once_with(engine, "เช็ค 22010585")
    assert result is expected


def test_handle_product_scan_callback_malformed():
    # Prefix present but empty barcode after sanitize
    result = handle_product_scan_callback(MagicMock(), "📦 สแกนสินค้า: ")
    assert result["type"] == "text"
    assert "ไม่สำเร็จ" in result["text"]


def test_router_scan_command_returns_liff_not_table_printout():
    with patch(
        "src.handlers.product_scan.KCW_LIFF_PRODUCT_SCANNER_URL",
        "https://liff.line.me/test-liff",
    ):
        result = route_user_text(MagicMock(), "สแกนสินค้า", ACCESS)

    assert result["type"] == "messages"
    assert result["messages"][0]["type"] == "template"


def test_router_callback_bypasses_product_search_and_ai():
    engine = MagicMock()
    expected = {"type": "text", "text": "สินค้า 885\nFound"}

    with (
        patch(
            "src.handlers.product_scan.handle_check_response",
            return_value=expected,
        ) as check,
        patch("src.handlers.router.handle_product_query_response") as search,
        patch("src.handlers.router.build_kb_quick_reply_result") as ai,
        patch("src.handlers.router.is_ai_chat_request", return_value=True),
    ):
        result = route_user_text(
            engine,
            "📦 สแกนสินค้า: 8851234567890",
            ACCESS,
        )

    check.assert_called_once_with(engine, "เช็ค 8851234567890")
    search.assert_not_called()
    ai.assert_not_called()
    assert result is expected


def test_router_unknown_barcode_uses_check_not_found_message():
    engine = MagicMock()
    with patch(
        "src.handlers.product_scan.handle_check_response",
        return_value={"type": "text", "text": "ไม่พบรหัสสินค้า 99999999"},
    ):
        result = route_user_text(
            engine,
            "📦 สแกนสินค้า: 99999999",
            ACCESS,
        )

    assert "ไม่พบ" in result["text"]
    assert "99999999" in result["text"]

"""Tests for LINE camera product-scan session, decode helpers, and routing."""

from io import BytesIO
from unittest.mock import MagicMock, patch

from PIL import Image

from src.barcode import pick_best_barcode, sanitize_barcode
from src.barcode.decode import BarcodeDecodeUnavailable, decode_barcodes_from_image
from src.handlers.product_scan import (
    PRODUCT_SCAN_SESSIONS,
    clear_product_scan_session,
    handle_product_scan_callback,
    handle_product_scan_command,
    handle_product_scan_image,
    handle_product_scan_session_text,
    is_product_scan_callback,
    is_product_scan_command,
)
from src.handlers.router import route_user_text
from src.liff.product_scan_contract import (
    PRODUCT_SCAN_CALLBACK_PREFIX,
    format_product_scan_callback,
    parse_product_scan_callback,
)


ACCESS = {"access_group": "staff"}
USER = "U_test_scan_user"


def setup_function():
    PRODUCT_SCAN_SESSIONS.clear()


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


def test_router_bare_scan_opens_camera_session():
    result = route_user_text(MagicMock(), "สแกน", ACCESS, line_user_id=USER)

    assert result["type"] == "text"
    assert "บาร์โค้ด" in result["text"]
    labels = [item["action"]["type"] for item in result["quickReply"]["items"]]
    assert "camera" in labels
    assert "cameraRoll" in labels
    assert USER in PRODUCT_SCAN_SESSIONS


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


def test_pick_best_barcode():
    assert pick_best_barcode([]) is None
    assert pick_best_barcode(["bad code", "22010585"]) == "22010585"
    assert pick_best_barcode(["*22010585*"]) == "22010585"


def test_handle_product_scan_command_starts_session():
    result = handle_product_scan_command(line_user_id=USER)
    assert result["type"] == "text"
    assert "ถ่าย" in result["text"] or "บาร์โค้ด" in result["text"]
    assert result["quickReply"]["items"][0]["action"]["type"] == "camera"
    assert USER in PRODUCT_SCAN_SESSIONS


def test_handle_product_scan_command_missing_user():
    result = handle_product_scan_command(line_user_id=None)
    assert result["type"] == "text"
    assert "user id" in result["text"].lower() or "LINE" in result["text"]


def test_session_text_cancel_clears_session():
    handle_product_scan_command(line_user_id=USER)
    result = handle_product_scan_session_text(USER, "ยกเลิก")
    assert result is not None
    assert "จบ" in result["text"]
    assert USER not in PRODUCT_SCAN_SESSIONS


def test_session_text_blocks_free_text():
    handle_product_scan_command(line_user_id=USER)
    result = handle_product_scan_session_text(USER, "ลูกปืน 6207")
    assert result is not None
    assert "โหมดสแกน" in result["text"]


def test_session_allows_check_followup_to_escape():
    handle_product_scan_command(line_user_id=USER)
    result = handle_product_scan_session_text(USER, "เช็ค 22010585")
    assert result is None
    assert USER not in PRODUCT_SCAN_SESSIONS


def test_handle_product_scan_callback_uses_product_search():
    engine = MagicMock()
    expected = {"type": "text", "text": "สินค้า 22010585\nTest Product"}

    with patch(
        "src.handlers.product_scan.handle_product_query_response",
        return_value=expected,
    ) as search:
        result = handle_product_scan_callback(
            engine,
            "📦 สแกนสินค้า: 22010585",
            access=ACCESS,
            line_user_id=USER,
        )

    search.assert_called_once_with(engine, "22010585", access=ACCESS)
    assert "อ่านรหัส" not in (result.get("text") or "")
    assert result["quickReply"]["items"]
    assert any(
        item["action"].get("text") == "เช็ค 22010585"
        for item in result["quickReply"]["items"]
        if item["action"].get("type") == "message"
    )


def test_handle_product_scan_callback_malformed():
    result = handle_product_scan_callback(MagicMock(), "📦 สแกนสินค้า: ")
    assert result["type"] == "text"
    assert "ไม่สำเร็จ" in result["text"]


def test_router_scan_command_returns_camera_not_liff():
    result = route_user_text(MagicMock(), "สแกนสินค้า", ACCESS, line_user_id=USER)
    assert result["type"] == "text"
    assert result.get("quickReply")
    assert "template" not in str(result).lower() or "uri" not in str(result).lower()
    labels = [item["action"]["type"] for item in result["quickReply"]["items"]]
    assert "camera" in labels


def test_router_callback_uses_product_search_not_check_or_ai():
    engine = MagicMock()
    expected = {"type": "text", "text": "Found 885"}

    with (
        patch(
            "src.handlers.product_scan.handle_product_query_response",
            return_value=expected,
        ) as search,
        patch("src.handlers.router.handle_product_query_response") as free_search,
        patch("src.handlers.router.build_kb_quick_reply_result") as ai,
        patch("src.handlers.router.is_ai_chat_request", return_value=True),
    ):
        result = route_user_text(
            engine,
            "📦 สแกนสินค้า: 8851234567890",
            ACCESS,
            line_user_id=USER,
        )

    search.assert_called_once_with(engine, "8851234567890", access=ACCESS)
    free_search.assert_not_called()
    ai.assert_not_called()
    assert "Found 885" in result["text"]


def test_handle_product_scan_image_no_session_returns_none():
    clear_product_scan_session(USER)
    result = handle_product_scan_image(
        MagicMock(),
        line_user_id=USER,
        message_id="mid",
        access=ACCESS,
    )
    assert result is None


def test_handle_product_scan_image_decodes_and_searches():
    handle_product_scan_command(line_user_id=USER)
    engine = MagicMock()
    expected = {"type": "text", "text": "สินค้า 22010585\nOK"}

    with (
        patch(
            "src.handlers.product_scan.download_line_message_content",
            return_value=(b"fake-image", "image/jpeg"),
        ),
        patch(
            "src.handlers.product_scan.decode_barcodes_from_image",
            return_value=["22010585"],
        ),
        patch(
            "src.handlers.product_scan.handle_product_query_response",
            return_value=expected,
        ) as search,
    ):
        result = handle_product_scan_image(
            engine,
            line_user_id=USER,
            message_id="mid-1",
            access=ACCESS,
        )

    search.assert_called_once_with(engine, "22010585", access=ACCESS)
    assert result["type"] == "text"
    assert result["text"].startswith("อ่านรหัส: 22010585")
    assert "OK" in result["text"]
    assert USER in PRODUCT_SCAN_SESSIONS


def test_handle_product_scan_image_no_barcode():
    handle_product_scan_command(line_user_id=USER)

    with (
        patch(
            "src.handlers.product_scan.download_line_message_content",
            return_value=(b"fake-image", "image/jpeg"),
        ),
        patch(
            "src.handlers.product_scan.decode_barcodes_from_image",
            return_value=[],
        ),
    ):
        result = handle_product_scan_image(
            MagicMock(),
            line_user_id=USER,
            message_id="mid-2",
            access=ACCESS,
        )

    assert "ไม่พบ" in result["text"]
    assert result["quickReply"]["items"][0]["action"]["type"] == "camera"


def test_handle_product_scan_image_decoder_unavailable():
    handle_product_scan_command(line_user_id=USER)

    with (
        patch(
            "src.handlers.product_scan.download_line_message_content",
            return_value=(b"fake-image", "image/jpeg"),
        ),
        patch(
            "src.handlers.product_scan.decode_barcodes_from_image",
            side_effect=BarcodeDecodeUnavailable("missing zbar"),
        ),
    ):
        result = handle_product_scan_image(
            MagicMock(),
            line_user_id=USER,
            message_id="mid-3",
            access=ACCESS,
        )

    assert "ยังไม่พร้อม" in result["text"]
    assert USER in PRODUCT_SCAN_SESSIONS


def test_zbar_not_loaded_at_import():
    import src.barcode.decode as decode_mod

    decode_mod._load_zbar.cache_clear()
    # Importing the module must not require libzbar.
    assert decode_mod.decode_barcodes_from_image.__name__ == "decode_barcodes_from_image"


def test_decode_barcodes_from_blank_image_returns_empty():
    buf = BytesIO()
    Image.new("RGB", (120, 80), color="white").save(buf, format="JPEG")
    assert decode_barcodes_from_image(buf.getvalue()) == []


def test_decode_barcodes_from_empty_bytes():
    assert decode_barcodes_from_image(b"") == []

"""Tests for pay-notes AI multi-image support."""

from unittest.mock import MagicMock, patch

from src.pay_notes.ai_vision import extract_bill_lines_from_image, extract_bill_lines_from_images


def _mock_response(payload: str, *, input_tokens=100, output_tokens=50):
    mock_response = MagicMock()
    mock_response.output_text = payload
    mock_response.usage = MagicMock(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=input_tokens + output_tokens,
    )
    return mock_response


def test_extract_bill_lines_from_images_single_image():
    mock_response = _mock_response(
        """{
        "lines": [{"billno": "INV-2401/001", "amount": 12500.0}],
        "total_amount": 12500.0,
        "warnings": []
    }"""
    )

    with patch("src.pay_notes.ai_vision.get_openai_client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.responses.create.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = extract_bill_lines_from_images([(b"fake_image_data", "image/jpeg")])

    assert len(result["lines"]) == 1
    assert result["lines"][0]["billno"] == "INV-2401/001"
    assert result["lines"][0]["amount"] == 12500.0
    assert result["total_amount"] == 12500.0
    assert result["usage"]["total_tokens"] == 150


def test_extract_bill_lines_from_images_multiple_images():
    pages = {
        b"fake_image_data_1": {
            "lines": [{"billno": "INV-2401/001", "amount": 12500.0}],
            "total_amount": 12500.0,
            "warnings": [],
            "usage": {"input_tokens": 80, "output_tokens": 20, "total_tokens": 100},
        },
        b"fake_image_data_2": {
            "lines": [{"billno": "INV-2401/002", "amount": 8900.0}],
            "total_amount": 8900.0,
            "warnings": [],
            "usage": {"input_tokens": 90, "output_tokens": 22, "total_tokens": 112},
        },
    }

    def _fake_page(image_bytes, content_type=None, **kwargs):
        return pages[image_bytes]

    with patch("src.pay_notes.ai_vision.extract_bill_lines_from_image", side_effect=_fake_page) as mock_page:
        result = extract_bill_lines_from_images(
            [
                (b"fake_image_data_1", "image/jpeg"),
                (b"fake_image_data_2", "image/png"),
            ]
        )

    assert mock_page.call_count == 2
    assert {ln["billno"] for ln in result["lines"]} == {"INV-2401/001", "INV-2401/002"}
    assert result["total_amount"] == 21400.0
    assert result["usage"]["total_tokens"] == 212
    page_kwargs = [call.kwargs for call in mock_page.call_args_list]
    assert {kw["page_index"] for kw in page_kwargs} == {1, 2}
    assert all(kw["page_count"] == 2 for kw in page_kwargs)


def test_extract_bill_lines_from_images_keeps_other_pages_if_one_fails():
    def _fake_page(image_bytes, content_type=None, **kwargs):
        if image_bytes == b"bad":
            raise RuntimeError("vision timeout")
        return {
            "lines": [{"billno": "IVE1", "amount": 100.0}],
            "total_amount": 100.0,
            "warnings": [],
            "usage": {"input_tokens": 10, "output_tokens": 2, "total_tokens": 12},
        }

    with patch("src.pay_notes.ai_vision.extract_bill_lines_from_image", side_effect=_fake_page):
        result = extract_bill_lines_from_images(
            [(b"good", "image/jpeg"), (b"bad", "image/jpeg")]
        )

    assert result["lines"] == [{"billno": "IVE1", "amount": 100.0}]
    assert any("scan failed" in w for w in result["warnings"])


def test_extract_bill_lines_from_image_sends_one_image_and_page_hint():
    mock_response = _mock_response(
        """{"lines": [{"billno": "IVE6932639", "amount": 5200.0}], "total_amount": 5200.0, "warnings": []}"""
    )
    with patch("src.pay_notes.ai_vision.get_openai_client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.responses.create.return_value = mock_response
        mock_client.return_value = mock_client_instance
        result = extract_bill_lines_from_image(
            b"page-bytes",
            "image/jpeg",
            page_index=2,
            page_count=4,
        )

    assert result["lines"][0]["billno"] == "IVE6932639"
    user_content = mock_client_instance.responses.create.call_args.kwargs["input"][1]["content"]
    image_blocks = [item for item in user_content if item.get("type") == "input_image"]
    assert len(image_blocks) == 1
    user_text = next(item["text"] for item in user_content if item.get("type") == "input_text")
    assert "page 2 of 4" in user_text
    assert "THIS page" in user_text


def test_extract_bill_lines_from_images_no_files():
    result = extract_bill_lines_from_images([])

    assert result["lines"] == []
    assert result["total_amount"] == 0.0
    assert "No images provided" in str(result["warnings"])


def test_extract_bill_lines_from_images_empty_file():
    result = extract_bill_lines_from_images([(b"", "image/jpeg")])

    assert result["lines"] == []
    assert result["total_amount"] == 0.0

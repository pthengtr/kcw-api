"""Tests for pay-notes AI multi-image support."""

from unittest.mock import MagicMock, patch

from src.pay_notes.ai_vision import extract_bill_lines_from_images


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
    mock_response = _mock_response(
        """{
        "lines": [
            {"billno": "INV-2401/001", "amount": 12500.0},
            {"billno": "INV-2401/002", "amount": 8900.0}
        ],
        "total_amount": 21400.0,
        "warnings": []
    }""",
        input_tokens=200,
        output_tokens=60,
    )

    with patch("src.pay_notes.ai_vision.get_openai_client") as mock_client:
        mock_client_instance = MagicMock()
        mock_client_instance.responses.create.return_value = mock_response
        mock_client.return_value = mock_client_instance

        result = extract_bill_lines_from_images(
            [
                (b"fake_image_data_1", "image/jpeg"),
                (b"fake_image_data_2", "image/png"),
            ]
        )

    assert len(result["lines"]) == 2
    assert result["total_amount"] == 21400.0
    assert result["usage"]["total_tokens"] == 260
    create_kwargs = mock_client_instance.responses.create.call_args.kwargs
    user_content = create_kwargs["input"][1]["content"]
    image_blocks = [item for item in user_content if item.get("type") == "input_image"]
    assert len(image_blocks) == 2


def test_extract_bill_lines_from_images_no_files():
    result = extract_bill_lines_from_images([])

    assert result["lines"] == []
    assert result["total_amount"] == 0.0
    assert "No images provided" in str(result["warnings"])


def test_extract_bill_lines_from_images_empty_file():
    result = extract_bill_lines_from_images([(b"", "image/jpeg")])

    assert result["lines"] == []
    assert result["total_amount"] == 0.0

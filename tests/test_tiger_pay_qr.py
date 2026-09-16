import json
from unittest.mock import MagicMock, patch

import jwt
import pytest

from src.tiger_pay.open_api import TigerPayOpenApiClient, TigerPayOpenApiError
from src.tiger_pay.payment_service import PaymentServiceError, poll_attempt_once, send_payment_for_bill
from src.tiger_pay.qr import (
    extract_companion_qr,
    has_displayable_qr,
    should_confirm_qr_payment,
)
from tests.test_tiger_pay_companion import MOCK_OPEN_BILL, _FakeResponse


def test_extract_companion_qr_builds_data_uri():
    qr = extract_companion_qr(
        {
            "data": {
                "type": "qr",
                "dynamicQR": {
                    "qrImage": "abc123",
                    "qrRawData": "000201",
                    "status": "I",
                    "paymentGateway": "KBANK",
                },
            }
        }
    )
    assert qr is not None
    assert qr["image"] == "data:image/png;base64,abc123"
    assert qr["raw_data"] == "000201"
    assert qr["payment_gateway"] == "KBANK"


def test_extract_companion_qr_renders_image_from_raw_data_when_image_empty():
    qr = extract_companion_qr(
        {
            "data": {
                "type": "qr",
                "dynamicQR": {
                    "qrImage": "",
                    "qrRawData": "00020101021230810016A000000677010112",
                    "status": "I",
                },
            }
        }
    )
    assert qr is not None
    assert qr["image"] is not None
    assert qr["image"].startswith("data:image/png;base64,")
    assert len(qr["image"]) > 40
    assert has_displayable_qr(
        {"data": {"dynamicQR": {"qrImage": "", "qrRawData": "000201"}}}
    )


def test_send_qr_with_raw_data_skips_create_qr_and_renders_image():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = None
    created_payment = {
        "id": 259,
        "paymentNo": "PA1",
        "status": "pending",
        "type": "qr",
        "dynamicQR": {
            "qrImage": "",
            "qrRawData": "00020101021230810016A000000677010112",
            "status": "I",
        },
    }
    open_api.create_payment.return_value = {
        "data": created_payment,
        "raw": {"data": created_payment},
        "message": "Success",
    }
    attempt_id = "a1b2c3d4e5f60718293a"
    updated_row = {
        "id": attempt_id,
        "pos_bill_id": "bill-1001",
        "status": "pending",
        "tiger_payment_id": 259,
        "tiger_payment_no": "PA1",
    }

    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.create_payment_attempt",
            return_value={"id": attempt_id, "status": "sending"},
        ),
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value=updated_row,
        ),
        patch(
            "src.tiger_pay.payment_service.new_payment_attempt_id",
            return_value=attempt_id,
        ),
    ):
        result = send_payment_for_bill(
            engine, "bill-1001", payment_type="qr", open_api=open_api
        )

    open_api.create_qr.assert_not_called()
    assert open_api.create_payment.call_args.kwargs["payment_gateway"] == "KBANK"
    assert result["qr"]["image"].startswith("data:image/png;base64,")
    assert len(result["qr"]["image"]) > 40


def test_should_confirm_qr_when_dynamic_qr_completed():
    assert should_confirm_qr_payment(
        {
            "type": "qr",
            "status": "pending",
            "amount": 100,
            "totalPay": 0,
            "dynamicQR": {"status": "C"},
        }
    )
    assert not should_confirm_qr_payment(
        {
            "type": "qr",
            "status": "success",
            "dynamicQR": {"status": "C"},
        }
    )
    assert not should_confirm_qr_payment(
        {"type": "cash", "status": "pending", "amount": 100, "totalPay": 100}
    )
    assert should_confirm_qr_payment(
        {
            "type": "cash",
            "status": "pending",
            "amount": 100,
            "totalPay": 40,
            "dynamicQR": {"status": "C"},
        }
    )


def test_send_qr_payment_returns_companion_qr():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = None
    payment = {
        "id": 259,
        "paymentNo": "PA1",
        "status": "pending",
        "type": "qr",
        "dynamicQR": {
            "qrImage": "abc123",
            "qrRawData": "000201",
            "status": "I",
            "paymentGateway": "KBANK",
        },
    }
    open_api.create_payment.return_value = {
        "data": payment,
        "raw": {"data": payment, "message": "Success"},
        "message": "Success",
    }
    attempt_id = "a1b2c3d4e5f60718293a"
    created_row = {"id": attempt_id, "pos_bill_id": "bill-1001", "status": "sending"}
    updated_row = {
        "id": attempt_id,
        "pos_bill_id": "bill-1001",
        "status": "pending",
        "tiger_payment_id": 259,
        "tiger_payment_no": "PA1",
        "raw_create_response": {"data": payment},
    }

    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.create_payment_attempt",
            return_value=created_row,
        ),
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value=updated_row,
        ),
        patch(
            "src.tiger_pay.payment_service.new_payment_attempt_id",
            return_value=attempt_id,
        ),
    ):
        result = send_payment_for_bill(
            engine, "bill-1001", payment_type="qr", open_api=open_api
        )

    assert result["payment_type"] == "qr"
    assert result["qr"]["image"] == "data:image/png;base64,abc123"
    open_api.create_qr.assert_not_called()
    kwargs = open_api.create_payment.call_args.kwargs
    assert kwargs["payment_type"] == "qr"
    assert kwargs["payment_gateway"] == "KBANK"


def test_send_qr_falls_back_to_kbank_create_qr():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = None
    created_payment = {
        "id": 259,
        "paymentNo": "PA1",
        "status": "pending",
        "type": "qr",
    }
    open_api.create_payment.return_value = {
        "data": created_payment,
        "raw": {"data": created_payment},
        "message": "Success",
    }
    open_api.create_qr.return_value = {
        "data": {"dynamicQR": {"qrImage": "zzz", "status": "I"}},
        "raw": {"data": {"dynamicQR": {"qrImage": "zzz", "status": "I"}}},
        "message": "Success",
    }
    attempt_id = "a1b2c3d4e5f60718293a"
    updated_row = {
        "id": attempt_id,
        "pos_bill_id": "bill-1001",
        "status": "pending",
        "tiger_payment_id": 259,
        "tiger_payment_no": "PA1",
    }

    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.create_payment_attempt",
            return_value={"id": attempt_id, "status": "sending"},
        ),
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value=updated_row,
        ),
        patch(
            "src.tiger_pay.payment_service.new_payment_attempt_id",
            return_value=attempt_id,
        ),
    ):
        result = send_payment_for_bill(
            engine, "bill-1001", payment_type="qr", open_api=open_api
        )

    open_api.create_qr.assert_called_once()
    assert open_api.create_qr.call_args.args[0] == 259
    assert open_api.create_qr.call_args.kwargs["payment_gateway"] == "KBANK"
    assert result["qr"]["image"] == "data:image/png;base64,zzz"


def test_send_payment_rejects_invalid_type():
    with pytest.raises(PaymentServiceError) as exc:
        send_payment_for_bill(MagicMock(), "bill-1001", payment_type="crypto")
    assert exc.value.code == "invalid_payment_type"


def test_poll_confirms_paid_qr():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_payment.return_value = {
        "id": 259,
        "type": "qr",
        "status": "pending",
        "amount": 100,
        "totalPay": 100,
        "refNo2": "att-1",
        "dynamicQR": {"status": "C", "qrImage": "x" * 40},
        "updatedAt": "now",
    }
    open_api.confirm_payment.return_value = {
        "data": {"id": 259, "status": "success", "type": "qr", "refNo2": "att-1"},
        "raw": {"data": {"id": 259, "status": "success"}},
        "message": "Success",
    }
    attempt = {"id": "att-1", "status": "pending", "tiger_payment_id": 259}

    with (
        patch(
            "src.tiger_pay.payment_service.repos.insert_payment_event",
            return_value={"id": 1},
        ),
        patch(
            "src.tiger_pay.payment_service.repos.find_attempt_by_tiger_or_ref",
            return_value=attempt,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value={**attempt, "status": "success"},
        ) as update,
    ):
        poll_attempt_once(engine, attempt, open_api=open_api)

    open_api.confirm_payment.assert_called_once_with(259)
    assert update.call_args.kwargs["status"] == "success"


def test_poll_cash_does_not_confirm():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_payment.return_value = {
        "id": 10,
        "type": "cash",
        "status": "pending",
        "amount": 100,
        "totalPay": 0,
        "updatedAt": "now",
    }
    attempt = {"id": "att-1", "status": "pending", "tiger_payment_id": 10}

    with (
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.find_attempt_by_tiger_or_ref",
            return_value=attempt,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value=attempt,
        ),
    ):
        poll_attempt_once(engine, attempt, open_api=open_api)

    open_api.confirm_payment.assert_not_called()


def test_open_api_create_qr_and_confirm(monkeypatch):
    settings = MagicMock()
    settings.tiger_pay_client_id = "cid"
    settings.tiger_pay_client_secret = "secret"
    settings.tiger_pay_api_host = "http://tiger.local/"
    client = TigerPayOpenApiClient(settings=settings)
    calls = []

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, content=None, headers=None):
            calls.append((method, url, content, headers))
            if method == "POST" and url.endswith("/qr/create"):
                return _FakeResponse(
                    200,
                    {"data": {"dynamicQR": {"qrImage": "img", "status": "I"}}, "message": "Success"},
                )
            if method == "PUT" and url.endswith("/confirm"):
                return _FakeResponse(
                    200,
                    {"data": {"id": 9, "status": "success"}, "message": "Success"},
                )
            raise AssertionError(f"unexpected {method} {url}")

    monkeypatch.setattr("src.tiger_pay.open_api.httpx.Client", FakeHttpClient)
    created = client.create_qr(9, payment_gateway="KBANK")
    assert created["data"]["dynamicQR"]["status"] == "I"
    confirmed = client.confirm_payment(9)
    assert confirmed["data"]["status"] == "success"
    qr_post = next(c for c in calls if c[0] == "POST")
    assert json.loads(qr_post[2].decode("utf-8")) == {"paymentGateway": "KBANK"}
    auth = jwt.decode(qr_post[3]["Authorization"].split(" ", 1)[1], "secret", algorithms=["HS256"])
    assert "messageDigest" in auth
    assert any(c[0] == "PUT" and c[1].endswith("/confirm") for c in calls)


def test_open_api_confirm_error(monkeypatch):
    settings = MagicMock()
    settings.tiger_pay_client_id = "cid"
    settings.tiger_pay_client_secret = "secret"
    settings.tiger_pay_api_host = "http://tiger.local/"

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, content=None, headers=None):
            return _FakeResponse(400, {"message": "cannot confirm"})

    monkeypatch.setattr("src.tiger_pay.open_api.httpx.Client", FakeHttpClient)
    client = TigerPayOpenApiClient(settings=settings)
    with pytest.raises(TigerPayOpenApiError):
        client.confirm_payment(1)


def test_poll_confirms_mixed_cash_qr():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_payment.return_value = {
        "id": 10,
        "type": "cash",
        "status": "pending",
        "amount": 250,
        "totalPay": 250,
        "refNo2": "att-mix-1",
        "dynamicQR": {"status": "C", "qrRawData": "000201"},
        "updatedAt": "now",
    }
    open_api.confirm_payment.return_value = {
        "data": {
            "id": 10,
            "status": "success",
            "type": "cash",
            "refNo2": "att-mix-1",
            "amount": 250,
            "totalPay": 250,
        },
        "raw": {"data": {"id": 10, "status": "success"}},
        "message": "Success",
    }
    attempt = {"id": "att-mix-1", "status": "pending", "tiger_payment_id": 10}

    with (
        patch(
            "src.tiger_pay.payment_service.repos.insert_payment_event",
            return_value={"id": 1},
        ),
        patch(
            "src.tiger_pay.payment_service.repos.find_attempt_by_tiger_or_ref",
            return_value=attempt,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value={**attempt, "status": "success"},
        ),
    ):
        poll_attempt_once(engine, attempt, open_api=open_api)

    open_api.confirm_payment.assert_called_once_with(10)


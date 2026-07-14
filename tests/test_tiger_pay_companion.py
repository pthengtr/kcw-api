import json
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.tiger_pay.digest import compute_body_sha256
from src.tiger_pay.open_api import TigerPayOpenApiClient, TigerPayOpenApiError, build_open_api_authorization
from src.tiger_pay.payment_service import (
    PaymentServiceError,
    cancel_payment_attempt,
    reconcile_from_tiger_payment,
    send_payment_for_bill,
)
from src.tiger_pay.status import is_active_status, is_terminal_status, normalize_status


def test_normalize_status_aliases_and_unknown():
    assert normalize_status("Pending") == "pending"
    assert normalize_status("Paid") == "success"
    assert normalize_status("canceled") == "cancelled"
    assert normalize_status("nope") == "unknown"
    assert is_active_status("paying")
    assert is_terminal_status("success")
    assert not is_active_status("success")


def test_build_open_api_authorization_with_and_without_digest():
    body = b'{"amount":1}'
    token_with = build_open_api_authorization(
        client_id="cid",
        client_secret="secret",
        raw_body=body,
    )
    claims = jwt.decode(token_with.split(" ", 1)[1], "secret", algorithms=["HS256"])
    assert claims["clientId"] == "cid"
    assert claims["messageDigest"] == compute_body_sha256(body)

    token_get = build_open_api_authorization(
        client_id="cid",
        client_secret="secret",
    )
    claims_get = jwt.decode(token_get.split(" ", 1)[1], "secret", algorithms=["HS256"])
    assert claims_get == {"clientId": "cid"}


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def test_open_api_get_current_none_and_create(monkeypatch):
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
            if url.endswith("payment/current"):
                return _FakeResponse(404, {"data": None, "message": "No current payment exists."})
            if method == "POST" and url.endswith("payment"):
                return _FakeResponse(
                    200,
                    {
                        "data": {
                            "id": 259,
                            "paymentNo": "PA1",
                            "status": "pending",
                            "refNo1": "B1",
                            "refNo2": "attempt-1",
                        },
                        "message": "Success",
                    },
                )
            raise AssertionError(f"unexpected {method} {url}")

    monkeypatch.setattr("src.tiger_pay.open_api.httpx.Client", FakeHttpClient)

    assert client.get_current() is None
    created = client.create_payment(
        amount=100,
        ref_no_1="B1",
        ref_no_2="attempt-1",
        note="POS bill B1",
    )
    assert created["data"]["id"] == 259
    assert any(c[0] == "POST" for c in calls)
    post = next(c for c in calls if c[0] == "POST")
    auth = jwt.decode(post[3]["Authorization"].split(" ", 1)[1], "secret", algorithms=["HS256"])
    assert "messageDigest" in auth


def test_open_api_error_on_create_failure(monkeypatch):
    settings = MagicMock()
    settings.tiger_pay_client_id = "cid"
    settings.tiger_pay_client_secret = "secret"
    settings.tiger_pay_api_host = "http://tiger.local"

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, content=None, headers=None):
            return _FakeResponse(500, {"message": "boom"})

    monkeypatch.setattr("src.tiger_pay.open_api.httpx.Client", FakeHttpClient)
    client = TigerPayOpenApiClient(settings=settings)
    with pytest.raises(TigerPayOpenApiError):
        client.create_payment(amount=1, ref_no_1="a", ref_no_2="b", note="n")


def test_send_payment_rejects_when_bill_has_active_attempt():
    engine = MagicMock()
    with patch(
        "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
        return_value={"id": "x", "status": "pending"},
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(engine, "bill-1001")
        assert exc.value.code == "active_attempt_exists"


def test_send_payment_rejects_when_tiger_busy():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = {"id": 1, "status": "pending"}
    with patch(
        "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
        return_value=None,
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(engine, "bill-1001", open_api=open_api)
        assert exc.value.code == "tiger_busy"


def test_send_payment_happy_path():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = None
    open_api.create_payment.return_value = {
        "data": {
            "id": 259,
            "paymentNo": "PA1",
            "status": "pending",
        },
        "raw": {"data": {"id": 259}},
        "message": "Success",
    }
    attempt_id = "a1b2c3d4e5f60718293a"
    assert len(attempt_id) <= 20
    created_row = {
        "id": attempt_id,
        "pos_bill_id": "bill-1001",
        "status": "sending",
    }
    updated_row = {
        "id": attempt_id,
        "pos_bill_id": "bill-1001",
        "status": "pending",
        "tiger_payment_id": 259,
        "tiger_payment_no": "PA1",
    }

    with (
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.create_payment_attempt",
            return_value=created_row,
        ) as create_attempt,
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
        result = send_payment_for_bill(engine, "bill-1001", open_api=open_api)

    assert result["attempt"]["status"] == "pending"
    assert result["attempt"]["tiger_payment_id"] == 259
    create_attempt.assert_called_once()
    open_api.create_payment.assert_called_once()
    kwargs = open_api.create_payment.call_args.kwargs
    assert kwargs["ref_no_1"] == "B2607140001"
    assert kwargs["ref_no_2"] == attempt_id
    assert len(kwargs["ref_no_2"]) <= 20
    assert kwargs["payment_type"] == "cash"


def test_new_payment_attempt_id_fits_tiger_refno2():
    from src.tiger_pay.payment_service import new_payment_attempt_id

    attempt_id = new_payment_attempt_id()
    assert len(attempt_id) <= 20
    assert attempt_id.isalnum()


def test_cancel_keeps_cancelling_until_confirmed():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.cancel_payment.return_value = {
        "data": {"id": 259, "status": "cancelled"},
        "raw": {},
    }
    attempt = {
        "id": "att-1",
        "status": "pending",
        "tiger_payment_id": 259,
        "tiger_payment_no": "PA1",
    }
    with (
        patch(
            "src.tiger_pay.payment_service.repos.get_payment_attempt",
            side_effect=[attempt, {**attempt, "status": "cancelling"}],
        ),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value={**attempt, "status": "cancelling"},
        ) as update,
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.list_payment_events",
            return_value=[],
        ),
    ):
        result = cancel_payment_attempt(engine, "att-1", open_api=open_api)

    assert result["attempt"]["status"] == "cancelling"
    assert update.called


def test_reconcile_matches_by_ref_no_2():
    engine = MagicMock()
    attempt = {"id": "att-1", "tiger_payment_no": None, "status": "pending"}
    with (
        patch(
            "src.tiger_pay.payment_service.repos.find_attempt_by_tiger_or_ref",
            return_value=attempt,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.insert_payment_event",
            return_value={"id": 1},
        ),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value={**attempt, "status": "success"},
        ) as update,
    ):
        updated = reconcile_from_tiger_payment(
            engine,
            {"id": 10, "refNo2": "att-1", "status": "success", "paymentNo": "PA9"},
            source="webhook",
            event_key="webhook:1",
        )
    assert updated["status"] == "success"
    assert update.call_args.kwargs["status"] == "success"


def test_companion_ui_and_bills_route():
    with (
        patch("app.routers.companion.get_engine", return_value=MagicMock()),
        patch(
            "app.routers.companion.list_bills_with_payment_status",
            return_value=[
                {
                    "id": "bill-1001",
                    "bill_number": "B1",
                    "amount": 10,
                    "pos_status": "open",
                    "tiger_payment_status": None,
                    "tiger_payment_no": None,
                    "payment_attempt_id": None,
                    "payment_attempt_active": False,
                }
            ],
        ),
    ):
        client = TestClient(app)
        ui = client.get("/companion")
        assert ui.status_code == 200
        assert "Tiger Pay Companion" in ui.text
        bills = client.get("/companion/bills")
        assert bills.status_code == 200
        assert bills.json()["bills"][0]["id"] == "bill-1001"


def test_companion_pay_conflict():
    with (
        patch("app.routers.companion.get_engine", return_value=MagicMock()),
        patch(
            "app.routers.companion.send_payment_for_bill",
            side_effect=PaymentServiceError("busy", code="tiger_busy"),
        ),
    ):
        client = TestClient(app)
        response = client.post("/companion/bills/bill-1001/pay")
        assert response.status_code == 409
        assert response.json()["detail"]["code"] == "tiger_busy"


def test_webhook_still_succeeds_when_reconcile_errors():
    from tests.test_tiger_pay_webhook import cash_payload, compact_json, make_authorization

    payload = cash_payload()
    body = compact_json(payload)
    with (
        patch(
            "src.tiger_pay.service.ingest_webhook_sync",
            return_value={
                "event_id": 1,
                "duplicate": False,
                "transaction_updated": True,
            },
        ),
        patch(
            "src.tiger_pay.service.reconcile_from_webhook_transaction",
            side_effect=RuntimeError("db down"),
        ),
    ):
        client = TestClient(app)
        response = client.post(
            "/webhooks/tiger-pay",
            content=body,
            headers={
                "Content-Type": "application/json",
                "Authorization": make_authorization(body),
            },
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True

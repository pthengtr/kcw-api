import copy
import hashlib
import json
from unittest.mock import patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.tiger_pay.config import get_tiger_pay_settings
from src.tiger_pay.digest import compute_body_sha256
from src.tiger_pay.normalize import normalize_tiger_timestamp
from src.tiger_pay.payload import sanitize_webhook_payload

TEST_SECRET = "test-tiger-pay-secret"


def compact_json(payload: dict) -> bytes:
    return json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def make_authorization(
    body: bytes,
    *,
    secret: str = TEST_SECRET,
    digest: str | None = None,
    algorithm: str = "HS256",
    claims: dict | None = None,
) -> str:
    payload = {"messageDigest": digest or compute_body_sha256(body)}
    if claims:
        payload.update(claims)
    token = jwt.encode(payload, secret, algorithm=algorithm)
    return f"Bearer {token}"


def base_payment(**overrides) -> dict:
    payment = {
        "id": 1001,
        "type": "Cash",
        "paymentNo": "PAY-1001",
        "status": "Paid",
        "amount": 150.5,
        "totalPay": 150.5,
        "createdAt": "2026-07-13T10:00:00",
        "updatedAt": "2026-07-13T10:00:05",
        "refNo1": "REF-1",
        "refNo2": "REF-2",
        "note": "note",
        "remark": "remark",
    }
    payment.update(overrides)
    return payment


def base_shop(**overrides) -> dict:
    shop = {
        "name": "SHOP01",
        "shopName": "KCW Shop",
        "branchName": "Bangkok",
    }
    shop.update(overrides)
    return shop


def cash_payload(**payment_overrides) -> dict:
    return {
        "payment": base_payment(**payment_overrides),
        "shop": base_shop(),
        "cashList": [{"denomination": 100, "count": 1}],
    }


def promptpay_payload(**payment_overrides) -> dict:
    payment = base_payment(
        type="PromptPay",
        paymentNo="PAY-PP-1",
        **payment_overrides,
    )
    return {
        "payment": payment,
        "shop": base_shop(),
        "promptPay": {"accountNumber": "1234567890"},
    }


def qr_payload(**payment_overrides) -> dict:
    payment = base_payment(
        type="QR",
        paymentNo="PAY-QR-1",
        **payment_overrides,
    )
    payment["dynamicQR"] = {
        "createdAt": "13 ก.ค. 2569 10:00",
        "qrImage": "x" * 120,
    }
    return {
        "payment": payment,
        "shop": base_shop(),
        "dynamicQR": payment["dynamicQR"],
    }


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def mock_ingest():
    with patch("src.tiger_pay.service.ingest_webhook_sync") as mocked:
        mocked.return_value = {
            "event_id": 1,
            "duplicate": False,
            "transaction_updated": True,
        }
        yield mocked


def post_webhook(client, body: bytes, authorization: str | None = None):
    headers = {"Content-Type": "application/json"}
    if authorization is not None:
        headers["Authorization"] = authorization
    return client.post("/webhooks/tiger-pay", content=body, headers=headers)


def test_missing_authorization_returns_401(client):
    body = compact_json(cash_payload())
    response = post_webhook(client, body)
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_wrong_authorization_scheme_returns_401(client):
    body = compact_json(cash_payload())
    response = post_webhook(client, body, authorization="Token abc")
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_missing_bearer_token_returns_401(client):
    body = compact_json(cash_payload())
    response = post_webhook(client, body, authorization="Bearer")
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_invalid_jwt_signature_returns_401(client):
    body = compact_json(cash_payload())
    response = post_webhook(client, body, authorization=make_authorization(body, secret="wrong-secret"))
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_non_hs256_algorithm_returns_401(client):
    body = compact_json(cash_payload())
    response = post_webhook(
        client,
        body,
        authorization=make_authorization(body, algorithm="HS384"),
    )
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_missing_message_digest_returns_401(client):
    body = compact_json(cash_payload())
    token = jwt.encode({}, TEST_SECRET, algorithm="HS256")
    response = post_webhook(client, body, authorization=f"Bearer {token}")
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_invalid_message_digest_format_returns_401(client):
    body = compact_json(cash_payload())
    response = post_webhook(
        client,
        body,
        authorization=make_authorization(body, digest="not-a-valid-digest"),
    )
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_incorrect_body_digest_returns_401(client):
    body = compact_json(cash_payload())
    wrong_digest = hashlib.sha256(b"other-body").hexdigest()
    response = post_webhook(
        client,
        body,
        authorization=make_authorization(body, digest=wrong_digest),
    )
    assert response.status_code == 401
    assert response.json() == {"ok": False, "error": "Unauthorized"}


def test_exact_raw_body_bytes_are_used_for_hashing(client, mock_ingest):
    payload = cash_payload()
    body = compact_json(payload)
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    _, body_sha256, _, _ = mock_ingest.call_args.args
    assert body_sha256 == compute_body_sha256(body)


def test_different_json_whitespace_produces_different_digest(client):
    payload = cash_payload()
    compact = compact_json(payload)
    spaced = json.dumps(payload, ensure_ascii=False).encode("utf-8")

    compact_digest = compute_body_sha256(compact)
    spaced_digest = compute_body_sha256(spaced)
    assert compact_digest != spaced_digest

    response = post_webhook(
        client,
        spaced,
        authorization=make_authorization(compact),
    )
    assert response.status_code == 401


def test_malformed_json_returns_400(client):
    body = b"{not-json"
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": "Invalid webhook payload"}


def test_missing_payment_returns_400(client):
    body = compact_json({"shop": base_shop()})
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": "Invalid webhook payload"}


def test_missing_shop_returns_400(client):
    body = compact_json({"payment": base_payment()})
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 400
    assert response.json() == {"ok": False, "error": "Invalid webhook payload"}


def test_valid_cash_webhook_calls_rpc(client, mock_ingest):
    body = compact_json(cash_payload())
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "duplicate": False,
        "transaction_updated": True,
    }
    mock_ingest.assert_called_once()
    _, body_sha256, transaction, payload = mock_ingest.call_args.args
    assert body_sha256 == compute_body_sha256(body)
    assert transaction["payment_type"] == "cash"
    assert transaction["status"] == "paid"
    assert transaction["amount"] == "150.5"
    assert payload["cashList"]


def test_valid_promptpay_webhook_calls_rpc(client, mock_ingest):
    body = compact_json(promptpay_payload())
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    mock_ingest.assert_called_once()
    transaction = mock_ingest.call_args.args[2]
    assert transaction["payment_type"] == "promptpay"


def test_valid_qr_webhook_calls_rpc(client, mock_ingest):
    body = compact_json(qr_payload())
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    mock_ingest.assert_called_once()
    transaction = mock_ingest.call_args.args[2]
    assert transaction["payment_type"] == "qr"


def test_payment_change_object_is_normalized(client, mock_ingest):
    body = compact_json(cash_payload(change={"amount": "12.50"}))
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    transaction = mock_ingest.call_args.args[2]
    assert transaction["change_amount"] == "12.50"


def test_payment_change_number_is_normalized(client, mock_ingest):
    body = compact_json(cash_payload(change=7))
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    transaction = mock_ingest.call_args.args[2]
    assert transaction["change_amount"] == "7"


def test_dynamic_qr_image_is_removed_before_rpc_storage(client, mock_ingest):
    body = compact_json(qr_payload())
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    payload = mock_ingest.call_args.args[3]
    dynamic_qr = payload["payment"]["dynamicQR"]
    assert dynamic_qr["qrImage"] is None
    assert dynamic_qr["qrImageOmitted"] is True
    assert dynamic_qr["qrImageLength"] == 120


def test_offsetless_timestamp_assigned_asia_bangkok():
    normalized = normalize_tiger_timestamp("2026-07-13T10:00:00")
    assert normalized.endswith("+07:00")


def test_timestamp_with_plus_seven_preserves_offset():
    normalized = normalize_tiger_timestamp("2026-07-13T10:00:00+07:00")
    assert normalized.endswith("+07:00")


def test_z_timestamp_is_handled_correctly():
    normalized = normalize_tiger_timestamp("2026-07-13T03:00:00Z")
    assert normalized.endswith("+00:00")


def test_duplicate_rpc_result_returns_duplicate_true(client, mock_ingest):
    mock_ingest.return_value = {
        "event_id": 2,
        "duplicate": True,
        "transaction_updated": False,
    }
    body = compact_json(cash_payload())
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "duplicate": True,
        "transaction_updated": False,
    }


def test_older_event_rpc_result_returns_transaction_updated_false(client, mock_ingest):
    mock_ingest.return_value = {
        "event_id": 3,
        "duplicate": False,
        "transaction_updated": False,
    }
    body = compact_json(cash_payload())
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "duplicate": False,
        "transaction_updated": False,
    }


def test_supabase_failure_returns_500(client):
    with patch("src.tiger_pay.service.ingest_webhook_sync", side_effect=RuntimeError("db down")):
        body = compact_json(cash_payload())
        response = post_webhook(client, body, authorization=make_authorization(body))
        assert response.status_code == 500
        assert response.json() == {"ok": False, "error": "Webhook processing failed"}


def test_ingest_rpc_single_object_response_shape(client):
    with patch("src.tiger_pay.service.ingest_webhook_sync") as mocked:
        mocked.return_value = {
            "event_id": 9,
            "duplicate": False,
            "transaction_updated": True,
        }
        body = compact_json(cash_payload())
        response = post_webhook(client, body, authorization=make_authorization(body))
        assert response.status_code == 200
        assert response.json()["ok"] is True


def test_parse_ingest_webhook_row_accepts_list_or_object():
    from src.tiger_pay.client import _parse_ingest_webhook_row

    row = {"event_id": 1, "duplicate": False, "transaction_updated": True}
    assert _parse_ingest_webhook_row([row]) == row
    assert _parse_ingest_webhook_row(row) == row


def test_oversized_request_returns_413(client, monkeypatch):
    monkeypatch.setenv("TIGER_PAY_MAX_BODY_BYTES", "32")
    get_tiger_pay_settings.cache_clear()

    body = compact_json(cash_payload(note="x" * 100))
    response = post_webhook(client, body, authorization=make_authorization(body))
    assert response.status_code == 413
    assert response.json() == {"ok": False, "error": "Webhook payload too large"}


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sanitize_payload_does_not_mutate_original():
    original = qr_payload()
    parsed = copy.deepcopy(original)
    sanitized = sanitize_webhook_payload(parsed)
    assert original["payment"]["dynamicQR"]["qrImage"] == "x" * 120
    assert sanitized["payment"]["dynamicQR"]["qrImage"] is None

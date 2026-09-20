import json
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import jwt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.companion.bills import PosBill
from src.tiger_pay.digest import compute_body_sha256
from src.tiger_pay.open_api import TigerPayOpenApiClient, TigerPayOpenApiError, build_open_api_authorization
from src.tiger_pay.payment_service import (
    PaymentServiceError,
    cancel_payment_attempt,
    reconcile_from_tiger_payment,
    send_payment_for_bill,
    tiger_create_amount,
)
from src.tiger_pay.status import is_active_status, is_terminal_status, normalize_status

MOCK_OPEN_BILL = PosBill(
    id="bill-1001",
    bill_number="B2607140001",
    amount=Decimal("250.00"),
    created_at=datetime(2026, 7, 14, 9, 15, tzinfo=timezone.utc),
    pos_status="N",
    salesperson="mock.user",
)


def test_tiger_create_amount_floors_cash_to_whole_baht():
    assert tiger_create_amount(Decimal("224.70"), payment_type="cash") == 224
    assert tiger_create_amount(Decimal("224.01"), payment_type="cash") == 224
    assert tiger_create_amount(Decimal("225.00"), payment_type="cash") == 225
    assert tiger_create_amount(Decimal("224.70"), payment_type="qr") == 224.7
    with pytest.raises(PaymentServiceError) as exc:
        tiger_create_amount(Decimal("0.70"), payment_type="cash")
    assert exc.value.code == "invalid_cash_amount"


def test_normalize_status_aliases_and_unknown():
    assert normalize_status("Pending") == "pending"
    assert normalize_status("Paid") == "success"
    assert normalize_status("canceled") == "cancelled"
    assert normalize_status("change") == "changing"
    assert is_active_status(normalize_status("change"))
    assert normalize_status("nope") == "unknown"
    assert is_active_status("paying")
    assert is_terminal_status("success")
    assert not is_active_status("success")


def test_list_bills_combined_limit_caps_collect_plus_cn():
    from datetime import datetime, timezone
    from decimal import Decimal

    from src.companion.bills import PosBill
    from src.tiger_pay.payment_service import list_bills_with_payment_status

    collect = [
        PosBill(
            id=f"c{i}",
            bill_number=f"8K-{i}",
            amount=Decimal("10"),
            created_at=datetime(2026, 9, 18, 10, i, tzinfo=timezone.utc),
            pos_status="N",
            kind="collect",
        )
        for i in range(5)
    ]
    payout = [
        PosBill(
            id=f"p{i}",
            bill_number=f"KCN-{i}",
            amount=Decimal("20"),
            created_at=datetime(2026, 9, 18, 11, i, tzinfo=timezone.utc),
            pos_status="N",
            kind="payout",
        )
        for i in range(5)
    ]
    with (
        patch(
            "src.tiger_pay.payment_service.list_open_bills",
            return_value=collect,
        ),
        patch(
            "src.tiger_pay.payment_service.list_cn_bills",
            return_value=payout,
        ),
        patch(
            "src.tiger_pay.payment_service.refresh_active_vouchers",
        ),
        patch(
            "src.tiger_pay.payment_service.repos.list_latest_attempts_by_bill_ids",
            return_value={},
        ),
        patch(
            "src.tiger_pay.payment_service.voucher_repos.list_latest_vouchers_by_bill_ids",
            return_value={},
        ),
    ):
        bills = list_bills_with_payment_status(MagicMock(), mode="latest", limit=3)
    assert len(bills) == 3
    # Newest first across both kinds (payout 11:4, 11:3, 11:2 …)
    assert [b["bill_number"] for b in bills] == ["KCN-4", "KCN-3", "KCN-2"]


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
    assert sum(1 for c in calls if c[0] == "GET") == 1


def test_open_api_reuses_http_client(monkeypatch):
    settings = MagicMock()
    settings.tiger_pay_client_id = "cid"
    settings.tiger_pay_client_secret = "secret"
    settings.tiger_pay_api_host = "http://tiger.local/"
    created = []

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            created.append(1)

        def request(self, method, url, content=None, headers=None):
            return _FakeResponse(404, {"data": None, "message": "No current payment exists."})

    monkeypatch.setattr("src.tiger_pay.open_api.httpx.Client", FakeHttpClient)
    client = TigerPayOpenApiClient(settings=settings)
    assert client.get_current() is None
    assert client.get_current() is None
    assert created == [1]


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
    open_api = MagicMock()
    open_api.get_current.return_value = None
    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value={"id": "x", "status": "pending"},
        ),
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(engine, "bill-1001", open_api=open_api)
        assert exc.value.code == "active_attempt_exists"


def test_send_payment_rejects_when_bill_already_completed():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = None
    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value={"id": "done", "status": "success"},
        ),
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(engine, "bill-1001", open_api=open_api)
        assert exc.value.code == "payment_already_completed"


def test_send_payment_ignores_legacy_pos_paid():
    """POS PAID=Y is display-only; Tiger attempt state gates sends."""
    engine = MagicMock()
    paid_bill = PosBill(
        id="bill-1003",
        bill_number="B2607140003",
        amount=Decimal("1250.00"),
        created_at=datetime(2026, 7, 14, 11, 40, tzinfo=timezone.utc),
        pos_status="Y",
        salesperson="mock.user",
    )
    open_api = MagicMock()
    open_api.get_current.return_value = None
    open_api.create_payment.return_value = {
        "data": {"id": 301, "paymentNo": "PA301", "status": "pending"},
        "raw": {"data": {"id": 301}},
        "message": "Success",
    }
    attempt_id = "pospaidignore000001"
    with (
        patch("src.tiger_pay.payment_service.get_open_bill", return_value=paid_bill),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.create_payment_attempt",
            return_value={"id": attempt_id, "pos_bill_id": "bill-1003", "status": "sending"},
        ),
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value={
                "id": attempt_id,
                "pos_bill_id": "bill-1003",
                "status": "pending",
                "tiger_payment_id": 301,
                "tiger_payment_no": "PA301",
            },
        ),
        patch(
            "src.tiger_pay.payment_service.new_payment_attempt_id",
            return_value=attempt_id,
        ),
    ):
        result = send_payment_for_bill(engine, "bill-1003", open_api=open_api)
    assert result["attempt"]["tiger_payment_id"] == 301
    open_api.create_payment.assert_called_once()


def test_send_payment_rejects_when_tiger_busy():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = {"id": 1, "status": "pending"}
    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(engine, "bill-1001", open_api=open_api)
        assert exc.value.code == "tiger_busy"


def test_send_payment_overlaps_get_current_with_bill_lookup():
    import time

    engine = MagicMock()
    open_api = MagicMock()

    def slow_current():
        time.sleep(0.08)
        return {"id": 1, "status": "pending"}

    def slow_bill(_pos_bill_id):
        time.sleep(0.08)
        return MOCK_OPEN_BILL

    open_api.get_current.side_effect = slow_current
    started = time.perf_counter()
    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            side_effect=slow_bill,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(engine, "bill-1001", open_api=open_api)
    elapsed = time.perf_counter() - started
    assert exc.value.code == "tiger_busy"
    assert elapsed < 0.12


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
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
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
        result = send_payment_for_bill(
            engine,
            "bill-1001",
            open_api=open_api,
            submitted_by="Uline",
            submitted_by_name="Cashier A",
        )

    assert result["attempt"]["status"] == "pending"
    assert result["attempt"]["tiger_payment_id"] == 259
    create_attempt.assert_called_once()
    create_kwargs = create_attempt.call_args.kwargs
    assert create_kwargs["submitted_by"] == "Uline"
    assert create_kwargs["submitted_by_name"] == "Cashier A"
    open_api.create_payment.assert_called_once()
    kwargs = open_api.create_payment.call_args.kwargs
    assert kwargs["ref_no_1"] == "B2607140001"
    assert kwargs["ref_no_2"] == attempt_id
    assert len(kwargs["ref_no_2"]) <= 20
    assert kwargs["payment_type"] == "cash"
    assert kwargs["amount"] == 250
    assert "payment_gateway" not in kwargs


def test_send_payment_floors_fractional_cash_amount():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = None
    open_api.create_payment.return_value = {
        "data": {"id": 260, "paymentNo": "PA2", "status": "pending"},
        "raw": {},
        "message": "Success",
    }
    fractional = PosBill(
        id="bill-tr",
        bill_number="TR6909-036",
        amount=Decimal("224.70"),
        created_at=datetime(2026, 9, 18, 15, 0, tzinfo=timezone.utc),
        pos_status="N",
        salesperson="mock.user",
    )
    attempt_id = "a1b2c3d4e5f60718293c"
    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=fractional,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.create_payment_attempt",
            return_value={"id": attempt_id, "status": "sending"},
        ) as create_attempt,
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value={"id": attempt_id, "status": "pending"},
        ),
        patch(
            "src.tiger_pay.payment_service.new_payment_attempt_id",
            return_value=attempt_id,
        ),
    ):
        send_payment_for_bill(engine, "bill-tr", open_api=open_api)

    assert create_attempt.call_args.kwargs["amount"] == Decimal("224.70")
    assert open_api.create_payment.call_args.kwargs["amount"] == 224


def test_send_payment_maps_tailscale_submitter():
    engine = MagicMock()
    open_api = MagicMock()
    open_api.get_current.return_value = None
    open_api.create_payment.return_value = {
        "data": {"id": 1, "paymentNo": "PA1", "status": "pending", "type": "cash"},
        "raw": {},
    }
    attempt_id = "a1b2c3d4e5f60718293b"
    with (
        patch(
            "src.tiger_pay.payment_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.create_payment_attempt",
            return_value={"id": attempt_id, "status": "sending"},
        ) as create_attempt,
        patch(
            "src.tiger_pay.payment_service.repos.insert_payment_event",
        ) as insert_event,
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value={"id": attempt_id, "status": "pending"},
        ),
        patch(
            "src.tiger_pay.payment_service.new_payment_attempt_id",
            return_value=attempt_id,
        ),
    ):
        send_payment_for_bill(
            engine,
            "bill-1001",
            open_api=open_api,
            submitted_by="tailscale",
            submitted_by_name="tailnet",
        )

    assert create_attempt.call_args.kwargs["submitted_by"] == "tailscale"
    assert create_attempt.call_args.kwargs["submitted_by_name"] == "Tailscale account"
    created_payload = insert_event.call_args_list[0].kwargs["payload"]
    assert created_payload["submitted_by"] == "tailscale"
    assert created_payload["submitted_by_name"] == "Tailscale account"


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


def test_companion_bills_is_sync():
    import inspect

    from app.routers.companion import companion_bills, companion_ui

    assert not inspect.iscoroutinefunction(companion_ui)
    assert not inspect.iscoroutinefunction(companion_bills)


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
        ) as list_bills,
        patch(
            "app.routers.companion.get_companion_bill_settings",
            return_value=MagicMock(pos_bills_mode="latest", pos_bills_limit=10),
        ),
    ):
        client = TestClient(app)
        ui = client.get("/companion")
        assert ui.status_code == 200
        assert "Tiger Pay Companion" in ui.text
        assert 'lang="th"' in ui.text
        assert "ส่งเงินสด" in ui.text
        assert "ส่ง QR" in ui.text
        assert 'id="qrDialog"' in ui.text
        assert "Request" in ui.text
        assert 'id="statusTabs"' in ui.text
        assert 'class="status-tabs-row"' in ui.text
        assert 'class="header-copy"' in ui.text
        assert 'id="billSearch"' in ui.text
        assert "ค้นหาบิล / พนักงาน / ยอด" in ui.text
        assert "billNoCompact" in ui.text
        assert "status-tabs-row" in ui.text
        assert "align-content: flex-start" in ui.text
        assert "สร้าง voucher / จ่ายคืน" in ui.text
        assert "ยังไม่ส่ง" in ui.text
        assert "รอดำเนินการ" in ui.text
        assert 'status === "failed") return "unsent"' in ui.text
        assert "status-unsent" in ui.text
        assert "PAID (POS · info)" in ui.text
        assert "pos_status" in ui.text  # still shown as info
        assert 'tiger_payment_status === "success"' in ui.text
        assert 'pos_status || "").trim().toUpperCase() === "Y"' not in ui.text
        assert "busyLabel" in ui.text
        assert "btn-busy" in ui.text
        assert "syncDialogCancelButton" in ui.text
        assert "กำลังยกเลิก" in ui.text
        assert "--fail-bg" in ui.text
        assert 'id="alertDialog"' in ui.text
        assert 'id="themeBtn"' in ui.text
        assert 'data-theme' in ui.text
        assert "ตกลง" in ui.text
        bills = client.get("/companion/bills")
        assert bills.status_code == 200
        payload = bills.json()
        assert payload["bills"][0]["id"] == "bill-1001"
        assert payload["mode"] == "latest"
        assert payload["limit"] == 10
        today = client.get("/companion/bills?mode=today&limit=all")
        assert today.status_code == 200
        assert today.json()["mode"] == "today"
        assert today.json()["limit"] == "all"
        assert list_bills.call_args_list[-1].kwargs.get("mode") == "today"
        assert list_bills.call_args_list[-1].kwargs.get("limit") == "all"
        latest = client.get("/companion/bills?mode=latest&limit=100")
        assert latest.status_code == 200
        assert latest.json()["limit"] == 100
        assert list_bills.call_args_list[-1].kwargs.get("limit") == "100"


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


def test_companion_pay_qr_passes_type():
    with (
        patch("app.routers.companion.get_engine", return_value=MagicMock()),
        patch(
            "app.routers.companion.send_payment_for_bill",
            return_value={
                "attempt": {"id": "att-1", "status": "pending"},
                "qr": {"image": "data:image/png;base64,xx", "status": "I"},
                "payment_type": "qr",
            },
        ) as send,
    ):
        client = TestClient(app)
        response = client.post(
            "/companion/bills/bill-1001/pay",
            json={"payment_type": "qr"},
        )
    assert response.status_code == 200
    assert response.json()["payment_type"] == "qr"
    assert response.json()["qr"]["image"].startswith("data:image")
    assert send.call_args.kwargs["payment_type"] == "qr"
    assert send.call_args.kwargs["submitted_by"] is None
    assert send.call_args.kwargs["submitted_by_name"] is None


def test_companion_pay_passes_line_submitter(monkeypatch):
    monkeypatch.setenv("COMPANION_REQUIRE_LINE_AUTH", "1")
    ident = MagicMock(line_user_id="U999", display_name="Pannawit")
    with (
        patch("app.routers.companion.get_engine", return_value=MagicMock()),
        patch(
            "app.routers.companion._require_companion_user",
            return_value=ident,
        ),
        patch(
            "app.routers.companion.send_payment_for_bill",
            return_value={"attempt": {"id": "att-1", "status": "pending"}},
        ) as send,
    ):
        client = TestClient(app)
        response = client.post("/companion/bills/bill-1001/pay")
    assert response.status_code == 200
    assert send.call_args.kwargs["submitted_by"] == "U999"
    assert send.call_args.kwargs["submitted_by_name"] == "Pannawit"


def test_webhook_still_succeeds_when_reconcile_errors():
    from src.tiger_pay.config import get_tiger_pay_settings
    from tests.test_tiger_pay_webhook import cash_payload, compact_json, make_authorization

    payload = cash_payload()
    body = compact_json(payload)
    secret = get_tiger_pay_settings().tiger_pay_client_secret
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
                "Authorization": make_authorization(body, secret=secret),
            },
        )
    assert response.status_code == 200
    assert response.json()["ok"] is True

def test_row_to_bill_skips_nan_aftertax():
    import pandas as pd
    from decimal import Decimal
    from src.companion.bill_mapping import row_to_bill

    row = pd.Series(
        {
            "ID": "1",
            "BILLNO": "8K69-001",
            "AFTERTAX": float("nan"),
            "BILLDATE": "2026-09-17",
            "BILLTIME": "10:00:00",
            "PAID": "N",
            "CASHED": "N",
            "SALE": "x",
        }
    )
    assert row_to_bill(row, kind="collect") is None
    row2 = row.copy()
    row2["AFTERTAX"] = Decimal("NaN")
    assert row_to_bill(row2, kind="collect") is None

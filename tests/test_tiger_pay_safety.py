from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.companion.bills import PosBill
from src.tiger_pay.open_api import TigerPayOpenApiError
from src.tiger_pay.payment_service import (
    PaymentServiceError,
    reconcile_from_tiger_payment,
    recover_sending_attempts,
    send_payment_for_bill,
    tiger_amount_compatible,
    tiger_create_amount,
)
from src.tiger_pay.status import can_replace_status, normalize_status
from datetime import datetime, timezone, timedelta


def test_can_replace_status_terminal_is_sticky():
    assert can_replace_status("pending", "success")
    assert can_replace_status("success", "success")
    assert can_replace_status("success", "paid")
    assert not can_replace_status("success", "pending")
    assert not can_replace_status("success", "cancelled")
    assert not can_replace_status("cancelled", "pending")
    assert not can_replace_status("failed", "sending")
    assert can_replace_status("cancelling", "success")
    assert can_replace_status("unknown", "success")


def test_tiger_amount_compatible_allows_cash_floor():
    attempt = {"amount": Decimal("224.70")}
    assert tiger_amount_compatible(attempt, {"amount": 224, "type": "cash"})
    assert tiger_amount_compatible(attempt, {"amount": "224.70", "type": "cash"})
    assert tiger_amount_compatible(attempt, {"amount": 100, "type": "cash"}) is False
    qr_attempt = {"amount": Decimal("224.70")}
    assert tiger_amount_compatible(qr_attempt, {"amount": "224.70", "type": "qr"})
    assert tiger_amount_compatible(qr_attempt, {"amount": 224, "type": "qr"}) is False
    assert tiger_amount_compatible({"amount": 10}, {"type": "cash"}) is True


def test_reconcile_ignores_success_downgrade_to_pending():
    engine = MagicMock()
    attempt = {
        "id": "att-1",
        "status": "success",
        "amount": Decimal("80"),
        "tiger_payment_no": "PA1",
    }
    with (
        patch(
            "src.tiger_pay.payment_service.repos.find_attempt_by_tiger_or_ref",
            return_value=attempt,
        ),
        patch("src.tiger_pay.payment_service.repos.insert_payment_event") as insert,
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value=attempt,
        ) as update,
    ):
        reconcile_from_tiger_payment(
            engine,
            {"id": 10, "refNo2": "att-1", "status": "pending", "amount": 80, "type": "cash"},
            source="polling",
        )
    assert insert.call_args.kwargs["payload"]["action"] == "polling_ignored_downgrade"
    assert "status" not in update.call_args.kwargs


def test_reconcile_rejects_qr_amount_mismatch_on_success():
    engine = MagicMock()
    attempt = {
        "id": "att-1",
        "status": "pending",
        "amount": Decimal("100.00"),
    }
    with (
        patch(
            "src.tiger_pay.payment_service.repos.find_attempt_by_tiger_or_ref",
            return_value=attempt,
        ),
        patch("src.tiger_pay.payment_service.repos.insert_payment_event") as insert,
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value=attempt,
        ) as update,
    ):
        reconcile_from_tiger_payment(
            engine,
            {
                "id": 10,
                "refNo2": "att-1",
                "status": "success",
                "amount": 90,
                "type": "qr",
            },
            source="webhook",
        )
    assert insert.call_args.kwargs["payload"]["action"] == "webhook_amount_mismatch"
    assert update.call_args.kwargs.get("status") is None


def test_send_payment_leaves_sending_on_timeout():
    engine = MagicMock()
    bill = PosBill(
        id="bill-1001",
        bill_number="B1",
        amount=Decimal("80"),
        created_at=datetime(2026, 9, 20, 1, 0, tzinfo=timezone.utc),
        pos_status="N",
    )
    open_api = MagicMock()
    open_api.get_current.return_value = None
    open_api.create_payment.side_effect = TigerPayOpenApiError(
        "Tiger Pay request timed out",
        no_response=True,
    )
    with (
        patch("src.tiger_pay.payment_service.get_open_bill", return_value=bill),
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
            return_value={"id": "aaaaaaaaaaaaaaaaaaaa", "status": "sending"},
        ),
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch("src.tiger_pay.payment_service.repos.update_payment_attempt") as update,
        patch(
            "src.tiger_pay.payment_service.new_payment_attempt_id",
            return_value="aaaaaaaaaaaaaaaaaaaa",
        ),
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(engine, "bill-1001", open_api=open_api)
    assert exc.value.code == "tiger_create_unconfirmed"
    assert not any(
        call.kwargs.get("status") == "failed" for call in update.call_args_list
    )


def test_recover_sending_expires_stale_row():
    engine = MagicMock()
    stale = {
        "id": "aaaaaaaaaaaaaaaaaaaa",
        "status": "sending",
        "tiger_payment_id": None,
        "created_at": (datetime.now(timezone.utc) - timedelta(seconds=90)).isoformat(),
    }
    open_api = MagicMock()
    open_api.find_payment_by_ref_no_2.return_value = None
    with (
        patch(
            "src.tiger_pay.payment_service.repos.list_sending_without_tiger_id",
            return_value=[stale],
        ),
        patch("src.tiger_pay.payment_service.repos.update_payment_attempt") as update,
        patch("src.tiger_pay.payment_service.repos.insert_payment_event"),
        patch(
            "src.tiger_pay.payment_service.repos.get_payment_attempt",
            return_value={**stale, "status": "failed"},
        ),
    ):
        recover_sending_attempts(engine, open_api=open_api)
    assert update.call_args.kwargs["status"] == "failed"


def test_tiger_create_amount_cash_floor_unchanged():
    assert tiger_create_amount(Decimal("224.70"), payment_type="cash") == 224
    assert normalize_status("paid") == "success"


def test_docs_and_internal_routes_are_closed():
    from fastapi.testclient import TestClient

    from app.main import _ENABLE_DOCS, _EXPOSE_INTERNAL_ROUTES, app

    client = TestClient(app)
    if not _ENABLE_DOCS:
        assert client.get("/docs").status_code == 404
    if not _EXPOSE_INTERNAL_ROUTES:
        assert client.post("/kcw-peak/sync", json={"x": 1}).status_code == 404
        assert client.post("/table-printout/extract").status_code == 404


def test_webhook_received_recently_window():
    from src.tiger_pay.poller import webhook_received_recently

    now = datetime(2026, 9, 20, 6, 0, tzinfo=timezone.utc)
    assert webhook_received_recently(
        now - timedelta(seconds=5), quiet_seconds=20, now=now
    )
    assert not webhook_received_recently(
        now - timedelta(seconds=20), quiet_seconds=20, now=now
    )
    assert not webhook_received_recently(None, quiet_seconds=20, now=now)
    assert not webhook_received_recently(now, quiet_seconds=0, now=now)


def test_poller_skips_device_get_when_webhook_fresh():
    import asyncio

    from src.tiger_pay.poller import PaymentStatusPoller

    engine = MagicMock()
    with (
        patch(
            "src.tiger_pay.poller.repos.latest_webhook_received_at",
            return_value=datetime.now(timezone.utc),
        ),
        patch("src.tiger_pay.poller.poll_attempt_once") as poll_once,
        patch("src.tiger_pay.poller.recover_sending_attempts") as recover,
        patch("src.tiger_pay.poller.repos.list_active_payment_attempts") as list_active,
        patch.object(PaymentStatusPoller, "_warn_if_webhooks_stale"),
    ):
        asyncio.run(PaymentStatusPoller()._poll_active_once(engine))
    list_active.assert_not_called()
    poll_once.assert_not_called()
    recover.assert_called_once_with(engine)


def test_poller_gets_device_when_webhook_is_old():
    import asyncio

    from src.tiger_pay.poller import PaymentStatusPoller

    engine = MagicMock()
    attempt = {"id": "a1", "status": "pending", "tiger_payment_id": 120}
    with (
        patch(
            "src.tiger_pay.poller.repos.latest_webhook_received_at",
            return_value=datetime.now(timezone.utc) - timedelta(seconds=60),
        ),
        patch("src.tiger_pay.poller.poll_attempt_once") as poll_once,
        patch("src.tiger_pay.poller.recover_sending_attempts"),
        patch(
            "src.tiger_pay.poller.repos.list_active_payment_attempts",
            return_value=[attempt],
        ),
        patch.object(PaymentStatusPoller, "_warn_if_webhooks_stale"),
    ):
        asyncio.run(PaymentStatusPoller()._poll_active_once(engine))
    poll_once.assert_called_once()

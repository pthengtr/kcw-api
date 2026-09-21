"""Admin force-complete for stuck pendingapproval payments."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.tiger_pay.force_auth import can_force_complete
from src.tiger_pay.payment_service import PaymentServiceError, force_complete_payment_attempt


def test_can_force_complete_tailscale():
    engine = MagicMock()
    ident = SimpleNamespace(line_user_id="tailscale", display_name="Tailscale account")
    assert can_force_complete(engine, ident) is True


def test_can_force_complete_admin(monkeypatch):
    engine = MagicMock()
    ident = SimpleNamespace(line_user_id="Uadmin", display_name="Admin")
    monkeypatch.setattr(
        "src.tiger_pay.force_auth.get_line_access",
        lambda _engine, uid: {"access_group": "admin", "is_allowed": True},
    )
    assert can_force_complete(engine, ident) is True


def test_can_force_complete_guest_denied(monkeypatch):
    engine = MagicMock()
    ident = SimpleNamespace(line_user_id="Uguest", display_name="Guest")
    monkeypatch.setattr(
        "src.tiger_pay.force_auth.get_line_access",
        lambda _engine, uid: {"access_group": "guest", "is_allowed": True},
    )
    assert can_force_complete(engine, ident) is False
    assert can_force_complete(engine, None) is False


def test_force_complete_rejects_non_pendingapproval():
    engine = MagicMock()
    with patch(
        "src.tiger_pay.payment_service.repos.get_payment_attempt",
        return_value={"id": "att1", "status": "pending", "amount": 100},
    ):
        with pytest.raises(PaymentServiceError) as exc:
            force_complete_payment_attempt(engine, "att1", actor_id="tailscale")
    assert exc.value.code == "not_pendingapproval"


def test_force_complete_unpaid_writes_pos_total_pay():
    engine = MagicMock()
    attempt = {
        "id": "att-unpaid",
        "status": "pendingapproval",
        "amount": 1930.0,
        "tiger_payment_id": 330,
        "tiger_payment_no": "PA2609210097",
        "pos_bill_number": "6K69-0011269",
    }
    unpaid_payment = {
        "id": 330,
        "type": "qr",
        "status": "pendingapproval",
        "amount": 1930,
        "totalPay": 0,
        "paymentNo": "PA2609210097",
        "dynamicQR": {"status": "I", "amount": 0, "requestAmount": 1930},
    }
    open_api = MagicMock()
    open_api.get_payment.return_value = unpaid_payment
    open_api.confirm_payment.return_value = {
        "data": {**unpaid_payment, "status": "success", "totalPay": 0},
        "raw": {"data": {**unpaid_payment, "status": "success"}},
        "message": "Success",
    }

    ensure_calls: list[dict] = []

    def fake_ensure(_engine, tid, **kwargs):
        ensure_calls.append({"tid": tid, **kwargs})
        return True

    success_attempt = {**attempt, "status": "success"}

    with (
        patch(
            "src.tiger_pay.payment_service.repos.get_payment_attempt",
            return_value=attempt,
        ) as get_attempt,
        patch(
            "src.tiger_pay.payment_service.repos.insert_payment_event",
            return_value={"id": 1},
        ),
        patch(
            "src.tiger_pay.payment_service.repos.update_payment_attempt",
            return_value=success_attempt,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.ensure_payment_transaction_success",
            side_effect=fake_ensure,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.list_payment_events",
            return_value=[],
        ),
        patch(
            "src.tiger_pay.payment_service.get_tiger_pay_settings",
            return_value=MagicMock(
                tiger_pay_default_shop_code="HQ",
                tiger_pay_id_epoch="2026-01-01T00:00:00+07:00",
            ),
        ),
    ):
        call_count = {"n": 0}

        def get_side_effect(*_a, **_k):
            call_count["n"] += 1
            return attempt if call_count["n"] == 1 else success_attempt

        get_attempt.side_effect = get_side_effect
        result = force_complete_payment_attempt(
            engine,
            "att-unpaid",
            actor_id="tailscale",
            actor_name="Tailscale account",
            clear_device=True,
            open_api=open_api,
        )

    assert result["attempt"]["status"] == "success"
    assert result["force"]["branch"] in {"unpaid_local", "unpaid_local_cleared"}
    open_api.confirm_payment.assert_called_once_with(330)
    assert ensure_calls
    assert all(float(c["total_pay"]) == 1930.0 for c in ensure_calls)
    assert all(float(c["amount"]) == 1930.0 for c in ensure_calls)


def test_force_complete_paid_confirms_then_ensures_totals():
    engine = MagicMock()
    attempt = {
        "id": "att-paid",
        "status": "pendingapproval",
        "amount": 950.0,
        "tiger_payment_id": 357,
        "tiger_payment_no": "PA2609210124",
        "pos_bill_number": "6K69-0001",
    }
    paid_payment = {
        "id": 357,
        "type": "qr",
        "status": "pendingapproval",
        "amount": 950,
        "totalPay": 950,
        "paymentNo": "PA2609210124",
        "dynamicQR": {"status": "C", "amount": 950, "requestAmount": 950},
    }
    confirmed = {**paid_payment, "status": "success"}
    open_api = MagicMock()
    open_api.get_payment.return_value = paid_payment
    open_api.confirm_payment.return_value = {
        "data": confirmed,
        "raw": {"data": confirmed},
        "message": "Success",
    }

    ensure_calls: list[dict] = []

    with (
        patch(
            "src.tiger_pay.payment_service.repos.get_payment_attempt",
            return_value=attempt,
        ) as get_attempt,
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
        patch(
            "src.tiger_pay.payment_service.repos.ensure_payment_transaction_success",
            side_effect=lambda *_a, **kw: ensure_calls.append(kw) or True,
        ),
        patch(
            "src.tiger_pay.payment_service.repos.list_payment_events",
            return_value=[],
        ),
        patch(
            "src.tiger_pay.payment_service.get_tiger_pay_settings",
            return_value=MagicMock(
                tiger_pay_default_shop_code="HQ",
                tiger_pay_id_epoch="2026-01-01T00:00:00+07:00",
            ),
        ),
    ):
        success = {**attempt, "status": "success"}
        call_count = {"n": 0}

        def get_side_effect(*_a, **_k):
            call_count["n"] += 1
            return attempt if call_count["n"] == 1 else success

        get_attempt.side_effect = get_side_effect
        result = force_complete_payment_attempt(
            engine,
            "att-paid",
            actor_id="tailscale",
            clear_device=True,
            open_api=open_api,
        )

    assert result["force"]["branch"] == "paid_confirm"
    open_api.confirm_payment.assert_called()
    assert ensure_calls
    assert float(ensure_calls[-1]["total_pay"]) == 950.0

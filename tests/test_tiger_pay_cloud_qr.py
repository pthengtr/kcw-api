from unittest.mock import MagicMock, patch

import pytest

from src.tiger_pay.backoffice_qr import TigerBackOfficeQrError
from src.tiger_pay.cloud_qr_service import (
    CloudQrServiceError,
    cancel_cloud_qr_payment,
    companion_qr_from_cloud_row,
    poll_cloud_qr_once,
    send_cloud_qr_for_bill,
)
from src.tiger_pay.payment_service import PaymentServiceError, send_payment_for_bill
from tests.test_tiger_pay_companion import MOCK_OPEN_BILL


def test_companion_qr_from_cloud_row_renders_emv():
    qr = companion_qr_from_cloud_row(
        {
            "status": "I",
            "qr_raw_data": "00020101021230810016A000000677010112",
            "qr_image": "",
            "uuid": "f909354c-2fa8-439d-981f-cc727c629a95",
            "ref1": "QRTS1",
            "ref2": "QRTS1",
        }
    )
    assert qr is not None
    assert qr["image"]
    assert qr["image"].startswith("data:image/png;base64,")
    assert qr["status"] == "I"
    assert qr["transaction_id"] == "f909354c-2fa8-439d-981f-cc727c629a95"


def test_send_cloud_qr_skips_get_current_and_stores_uuid():
    engine = MagicMock()
    bo = MagicMock()
    bo.create_qr.return_value = {
        "success": True,
        "uuid": "f909354c-2fa8-439d-981f-cc727c629a95",
        "qrRawData": "00020101021230810016A000000677010112",
        "qrImage": "",
        "ref1": "QRTS1795008061",
        "ref2": "QRTS1795008061",
    }
    created = {
        "id": "cloudqr001abcdefghij",
        "pos_bill_id": "bill-1001",
        "pos_bill_number": "B2607140001",
        "amount": 250.0,
        "status": "sending",
    }
    updated = {
        **created,
        "status": "I",
        "uuid": "f909354c-2fa8-439d-981f-cc727c629a95",
        "qr_raw_data": "00020101021230810016A000000677010112",
        "ref1": "QRTS1795008061",
        "ref2": "QRTS1795008061",
    }

    with (
        patch(
            "src.tiger_pay.cloud_qr_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.get_successful_cloud_qr_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.get_active_cloud_qr_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.create_cloud_qr_payment",
            return_value=created,
        ) as create_row,
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.update_cloud_qr_payment",
            return_value=updated,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.get_tiger_pay_settings",
        ) as settings,
    ):
        settings.return_value.tiger_box_serial = "4XcNjb5fFAvI1"
        settings.return_value.tiger_backoffice_qr_gateway = "KBANK"
        result = send_cloud_qr_for_bill(engine, "bill-1001", client=bo)

    bo.create_qr.assert_called_once()
    assert create_row.called
    assert result["payment_type"] == "cloud_qr"
    assert result["attempt"]["uuid"] == "f909354c-2fa8-439d-981f-cc727c629a95"
    assert result["qr"] is not None
    assert result["qr"]["raw_data"].startswith("000201")


def test_send_payment_for_bill_dispatches_cloud_qr():
    engine = MagicMock()
    with patch(
        "src.tiger_pay.payment_service.send_cloud_qr_for_bill",
        return_value={"payment_type": "cloud_qr", "attempt": {"id": "x"}},
    ) as send_cloud:
        result = send_payment_for_bill(
            engine, "bill-1001", payment_type="cloud_qr"
        )
    send_cloud.assert_called_once()
    assert result["payment_type"] == "cloud_qr"


def test_send_cash_blocked_when_cloud_qr_active():
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
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.cloud_qr_repos.get_successful_cloud_qr_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.payment_service.cloud_qr_repos.get_active_cloud_qr_for_bill",
            return_value={"id": "cloud1", "status": "I"},
        ),
    ):
        with pytest.raises(PaymentServiceError) as exc:
            send_payment_for_bill(
                engine, "bill-1001", payment_type="cash", open_api=open_api
            )
    assert exc.value.code == "active_attempt_exists"
    open_api.create_payment.assert_not_called()


def test_cancel_cloud_qr_marks_x():
    engine = MagicMock()
    row = {"id": "cloud1", "status": "I", "pos_bill_id": "bill-1001"}
    with (
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.get_cloud_qr_payment",
            return_value=row,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.update_cloud_qr_payment",
            return_value={**row, "status": "X"},
        ) as update,
    ):
        result = cancel_cloud_qr_payment(engine, "cloud1")
    update.assert_called_once()
    assert update.call_args.kwargs["status"] == "X"
    assert result["attempt"]["status"] == "X"


def test_poll_cloud_qr_once_marks_paid():
    engine = MagicMock()
    row = {
        "id": "cloud1",
        "status": "I",
        "uuid": "f909354c-2fa8-439d-981f-cc727c629a95",
    }
    bo = MagicMock()
    bo.get_qr_status.return_value = {
        "status": "C",
        "amount": 250,
        "payerName": "A",
        "payerAccountNumber": "1",
        "sendingBankCode": "004",
    }
    with patch(
        "src.tiger_pay.cloud_qr_service.cloud_qr_repos.update_cloud_qr_payment",
        return_value={**row, "status": "C", "paid_amount": 250},
    ) as update:
        poll_cloud_qr_once(engine, row, client=bo)
    assert update.call_args.kwargs["status"] == "C"
    assert update.call_args.kwargs["set_paid_at"] is True


def test_backoffice_create_error_marks_failed():
    engine = MagicMock()
    bo = MagicMock()
    bo.create_qr.side_effect = TigerBackOfficeQrError(
        "Failed", status_code=400, payload={"error": "Cannot generate QR code"}
    )
    with (
        patch(
            "src.tiger_pay.cloud_qr_service.get_open_bill",
            return_value=MOCK_OPEN_BILL,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.repos.get_successful_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.repos.get_active_attempt_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.get_successful_cloud_qr_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.get_active_cloud_qr_for_bill",
            return_value=None,
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.create_cloud_qr_payment",
            return_value={
                "id": "cloud1",
                "pos_bill_id": "bill-1001",
                "amount": 250.0,
                "status": "sending",
            },
        ),
        patch(
            "src.tiger_pay.cloud_qr_service.cloud_qr_repos.update_cloud_qr_payment"
        ) as update,
        patch(
            "src.tiger_pay.cloud_qr_service.get_tiger_pay_settings",
        ) as settings,
    ):
        settings.return_value.tiger_box_serial = "4XcNjb5fFAvI1"
        settings.return_value.tiger_backoffice_qr_gateway = "KBANK"
        with pytest.raises(CloudQrServiceError) as exc:
            send_cloud_qr_for_bill(engine, "bill-1001", client=bo)
    assert exc.value.code == "cloud_qr_create_failed"
    assert update.call_args.kwargs["status"] == "failed"

from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from src.companion.bill_mapping import is_cn_payout_bill_number
from src.companion.bills import PosBill
from src.tiger_pay.voucher_api import (
    TigerVoucherApiClient,
    TigerVoucherApiError,
    extract_voucher_display,
    extract_voucher_num,
    normalize_voucher_status,
    voucher_validity_window,
)
from src.tiger_pay.voucher_service import VoucherServiceError, create_voucher_for_bill


def test_is_cn_payout_bill_number():
    assert is_cn_payout_bill_number("KCN6908-0268")
    assert is_cn_payout_bill_number("kcn6908-0268")
    assert is_cn_payout_bill_number("CN2607140001")
    assert is_cn_payout_bill_number("3CN2607140001")
    assert not is_cn_payout_bill_number("CNTF2607140001")
    assert not is_cn_payout_bill_number("3CNTF2607140001")
    assert not is_cn_payout_bill_number("CNTAD2607140001")
    assert not is_cn_payout_bill_number("B2607140001")
    assert not is_cn_payout_bill_number("5K69-0001265")


def test_row_to_bill_negative_normal_bill_is_payout():
    from src.companion.bill_mapping import row_to_bill
    import pandas as pd

    row = pd.Series(
        {
            "ID": "572593",
            "BILLNO": "5K69-0001265",
            "AFTERTAX": "-400.00",
            "BILLDATE": "2026-09-18",
            "BILLTIME": "15:01:00",
            "PAID": "Y",
            "CASHED": "Y",
            "SALE": "toon",
        }
    )
    bill = row_to_bill(row)
    assert bill is not None
    assert bill.kind == "payout"
    assert bill.amount == Decimal("400.00")
    assert bill.bill_number == "5K69-0001265"


def test_normalize_voucher_status_and_extract():
    assert normalize_voucher_status("used") == "used"
    assert normalize_voucher_status("Y") == "used"
    assert normalize_voucher_status("pending") == "pending"
    assert normalize_voucher_status("cancelled") == "cancelled"
    assert extract_voucher_num({"data": {"voucher_num": "V123"}}) == "V123"
    assert extract_voucher_num({"voucherNumber": "ABC"}) == "ABC"
    # Live Tiger create shape: result list + success flag string.
    assert (
        extract_voucher_num(
            {
                "success": "true",
                "result": ["082475711990"],
                "ref_num": "CN6908-007",
            }
        )
        == "082475711990"
    )
    assert extract_voucher_num({"success": "false", "error": "not found"}) is None
    assert (
        extract_voucher_num(
            {"success": "true", "voucher": {"voucher_num": "082475711990", "used": 0}}
        )
        == "082475711990"
    )
    display = extract_voucher_display({"data": {"voucher_num": "V1", "qrImage": "img", "used": "N"}})
    assert display["voucher_num"] == "V1"
    assert display["qr_image"] == "img"
    assert display["raw_status"] == "N"


def test_companion_voucher_renders_qr_from_numeric_code():
    from src.tiger_pay.voucher_service import companion_voucher_from_attempt

    voucher = companion_voucher_from_attempt(
        {
            "status": "pending",
            "raw_status": "pending",
            "voucher_num": "false",
            "raw_create_response": {
                "success": "true",
                "result": ["082475711990"],
            },
            "raw_last_show": None,
        }
    )
    assert voucher["voucher_num"] == "082475711990"
    assert voucher["code"] == "082475711990"
    assert voucher["qr_image"].startswith("data:image/png;base64,")



def test_voucher_validity_window():
    now = datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc)
    window = voucher_validity_window(expire_hours=2, now=now)
    assert window["start_date"]
    assert window["expire_date"]
    assert window["start_time"]
    assert window["expire_time"]


def test_voucher_client_login_and_create(monkeypatch):
    settings = MagicMock()
    settings.tiger_voucher_api_host = "https://api.tigercashbox.com"
    settings.tiger_voucher_username = "user"
    settings.tiger_voucher_password = "pass"
    settings.tiger_voucher_mobile = "0800000000"
    settings.tiger_voucher_authen_required = "0"
    settings.tiger_voucher_approved_required = "0"
    settings.tiger_voucher_expire_hours = 8.0

    client = TigerVoucherApiClient(settings=settings)
    calls = []

    class FakeHttpClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def request(self, method, url, data=None, headers=None):
            calls.append((method, url, data, headers))
            if url.endswith("/api/tigerpay/login"):
                return _FakeResponse(200, {"success": {"token": "tok-1"}})
            if url.endswith("/api/voucher/create"):
                assert headers["Authorization"] == "Bearer tok-1"
                assert data["ref_num"] == "CN1"
                assert data["amount"] == "150"
                return _FakeResponse(200, {"data": {"voucher_num": "V-9", "used": "N"}})
            raise AssertionError(f"unexpected {method} {url}")

    monkeypatch.setattr("src.tiger_pay.voucher_api.httpx.Client", FakeHttpClient)
    created = client.create_voucher(amount=150, ref_num="CN1", note="CN bill CN1")
    assert extract_voucher_num(created["raw"]) == "V-9"
    assert any(url.endswith("/api/tigerpay/login") for _m, url, _d, _h in calls)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


MOCK_CN_BILL = PosBill(
    id="bill-cn-2001",
    bill_number="CN2607140001",
    amount=Decimal("150.00"),
    created_at=datetime(2026, 7, 14, 12, 5, tzinfo=timezone.utc),
    pos_status="N",
    salesperson="mock.user",
    kind="payout",
)


def test_create_voucher_for_bill_persists(monkeypatch):
    engine = MagicMock()
    voucher_api = MagicMock()
    voucher_api.create_voucher.return_value = {
        "raw": {"data": {"voucher_num": "V100", "used": "N"}},
        "data": {"voucher_num": "V100", "used": "N"},
    }

    with (
        patch("src.tiger_pay.voucher_service.get_open_bill", return_value=MOCK_CN_BILL),
        patch("src.tiger_pay.voucher_service.voucher_repos.get_active_voucher_for_bill", return_value=None),
        patch(
            "src.tiger_pay.voucher_service.voucher_repos.create_voucher_attempt",
            return_value={"id": "attempt1", "status": "creating"},
        ) as create_m,
        patch("src.tiger_pay.voucher_service.voucher_repos.insert_voucher_event"),
        patch(
            "src.tiger_pay.voucher_service.voucher_repos.update_voucher_attempt",
            return_value={
                "id": "attempt1",
                "status": "pending",
                "voucher_num": "V100",
                "raw_create_response": {"data": {"voucher_num": "V100"}},
            },
        ),
    ):
        result = create_voucher_for_bill(engine, "bill-cn-2001", voucher_api=voucher_api)

    assert result["voucher"]["voucher_num"] == "V100"
    create_m.assert_called_once()
    voucher_api.create_voucher.assert_called_once()


def test_create_voucher_rejects_collect_bill():
    engine = MagicMock()
    collect = PosBill(
        id="bill-1001",
        bill_number="B1",
        amount=Decimal("10"),
        created_at=datetime.now(timezone.utc),
        kind="collect",
    )
    with patch("src.tiger_pay.voucher_service.get_open_bill", return_value=collect):
        with pytest.raises(VoucherServiceError) as exc:
            create_voucher_for_bill(engine, "bill-1001", voucher_api=MagicMock())
    assert exc.value.code == "not_payout_bill"


def test_companion_voucher_route():
    client = TestClient(app)
    with (
        patch("app.routers.companion.get_engine", return_value=MagicMock()),
        patch(
            "app.routers.companion.create_voucher_for_bill",
            return_value={
                "attempt": {"id": "v1", "status": "pending"},
                "voucher": {"voucher_num": "V1"},
                "create_response": {},
            },
        ),
    ):
        res = client.post("/companion/bills/bill-cn-2001/voucher")
    assert res.status_code == 200
    assert res.json()["voucher"]["voucher_num"] == "V1"


def test_companion_voucher_route_conflict():
    client = TestClient(app)
    with (
        patch("app.routers.companion.get_engine", return_value=MagicMock()),
        patch(
            "app.routers.companion.create_voucher_for_bill",
            side_effect=VoucherServiceError("active", code="active_attempt_exists"),
        ),
    ):
        res = client.post("/companion/bills/bill-cn-2001/voucher")
    assert res.status_code == 409

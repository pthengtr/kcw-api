import json
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from app.main import app
from src.tiger_pay.cash_inventory import (
    build_daily_report,
    hopper_moved_by_webhook,
    parse_cash_items,
    score_change_level,
)
from src.tiger_pay.open_api import TigerPayOpenApiClient


WATCHED = (100, 50, 20, 10, 5, 1)


def test_parse_cash_items_value_amount_and_aliases():
    items = parse_cash_items(
        [
            {"type": "Banknote", "value": 1000, "amount": 2},
            {"denomination": 20, "quantity": 3},
            {"value": "nope"},
        ]
    )
    assert items == [
        {"type": "Banknote", "value": 1000, "amount": 2},
        {"type": "Banknote", "value": 20, "amount": 3},
    ]


def test_score_change_level_green_orange_red():
    green, reasons = score_change_level(
        [{"type": "Banknote", "value": 20, "amount": 15}, {"type": "Coin", "value": 10, "amount": 12}],
        change_ready=True,
        watched=WATCHED,
        warn_pieces=10,
        crit_pieces=2,
    )
    assert green == "green"
    assert reasons == []

    orange, orange_reasons = score_change_level(
        [{"type": "Banknote", "value": 20, "amount": 5}],
        change_ready=True,
        watched=WATCHED,
        warn_pieces=10,
        crit_pieces=2,
    )
    assert orange == "orange"
    assert any("20" in row for row in orange_reasons)

    red, red_reasons = score_change_level(
        [{"type": "Banknote", "value": 20, "amount": 0}],
        change_ready=True,
        watched=WATCHED,
        warn_pieces=10,
        crit_pieces=2,
    )
    assert red == "red"
    assert any("20" in row for row in red_reasons)

    blocked, blocked_reasons = score_change_level(
        [{"type": "Banknote", "value": 20, "amount": 40}],
        change_ready=False,
        watched=WATCHED,
        warn_pieces=10,
        crit_pieces=2,
    )
    assert blocked == "red"
    assert "เครื่องทอนเงินไม่พร้อม" in blocked_reasons


def test_score_ignores_watched_denoms_missing_from_device_list():
    level, _ = score_change_level(
        [{"type": "Banknote", "value": 100, "amount": 20}],
        change_ready=True,
        watched=WATCHED,
        warn_pieces=10,
        crit_pieces=2,
    )
    assert level == "green"


def test_hopper_moved_by_webhook_rules():
    cash_success = {
        "payment_type": "cash",
        "status": "success",
        "change_amount": "0",
    }
    assert hopper_moved_by_webhook(cash_success, duplicate=False) is True
    assert hopper_moved_by_webhook(cash_success, duplicate=True) is False
    assert (
        hopper_moved_by_webhook(
            {"payment_type": "qr", "status": "success", "change_amount": 0},
            duplicate=False,
        )
        is False
    )
    assert hopper_moved_by_webhook(
        {"payment_type": "qr", "status": "pending", "change_amount": 0},
        {"payment": {"cashList": [{"value": 100, "amount": 1}]}},
        duplicate=False,
    ) is False
    assert hopper_moved_by_webhook(
        {"payment_type": "cash", "status": "fail", "change_amount": 400},
        duplicate=False,
    ) is True


def test_build_daily_report_identity_and_unspecified_cash():
    txns = [
        {
            "payment_no": "PA1",
            "payment_type": "cash",
            "status": "success",
            "amount": "220.00",
            "total_pay": "1000.00",
            "change_amount": "780.00",
            "payload": {
                "payment": {
                    "cashList": [{"value": 1000, "amount": 1}],
                    "change": {
                        "cashList": [
                            {"type": "Banknote", "value": 500, "amount": 1},
                            {"type": "Banknote", "value": 100, "amount": 2},
                            {"type": "Banknote", "value": 50, "amount": 1},
                            {"type": "Banknote", "value": 20, "amount": 1},
                            {"type": "Coin", "value": 10, "amount": 1},
                        ]
                    },
                }
            },
        },
        {
            "payment_no": "PA2",
            "payment_type": "cash",
            "status": "success",
            "amount": "2188.00",
            "total_pay": "2188.00",
            "change_amount": "0.00",
            "payload": {"payment": {"cashList": []}},
        },
        {
            "payment_no": "PA3",
            "payment_type": "qr",
            "status": "success",
            "amount": "490.00",
            "total_pay": "490.00",
            "change_amount": "0.00",
            "payload": {"payment": {"cashList": []}},
        },
    ]
    report = build_daily_report(
        txns,
        vouchers=[],
        opening_items=[{"type": "Banknote", "value": 20, "amount": 10}],
        closing_items=[{"type": "Banknote", "value": 20, "amount": 9}, {"type": "Banknote", "value": 1000, "amount": 1}],
    )
    assert report["billed"] == 2898.0
    assert report["cash_in"] == 3188.0
    assert report["change_out"] == 780.0
    assert report["unspecified_in"] == 2188.0
    assert report["denom_in"]["1000"] == 1
    assert report["denom_out"]["100"] == 2
    assert report["hopper_expected"]["20"] == 9
    assert report["variance"]["20"] == 0
    assert report["qr_promptpay_in"] == 490.0


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.text = json.dumps(payload)

    def json(self):
        return self._payload


def test_open_api_get_cash_and_change_status(monkeypatch):
    settings = MagicMock()
    settings.tiger_pay_client_id = "cid"
    settings.tiger_pay_client_secret = "secret"
    settings.tiger_pay_api_host = "http://tiger.local/"
    client = TigerPayOpenApiClient(settings=settings)
    calls = []

    class FakeHttp:
        def request(self, method, url, content=None, headers=None):
            calls.append(url)
            if url.endswith("payment/cash"):
                return _FakeResponse(
                    200,
                    {
                        "data": [{"type": "Banknote", "value": 20, "amount": 4}],
                        "message": "Success",
                    },
                )
            if url.endswith("payment/change_status"):
                return _FakeResponse(200, {"data": True, "message": "Success"})
            raise AssertionError(url)

    monkeypatch.setattr(client, "_http_client", lambda: FakeHttp())
    assert client.get_cash() == [{"type": "Banknote", "value": 20, "amount": 4}]
    assert client.get_change_status() is True


def test_companion_cash_cached_endpoint():
    with patch(
        "app.routers.companion.cached_or_live_cash",
        return_value={
            "snapshot": {
                "change_level": "orange",
                "change_ready": True,
                "items": [{"type": "Banknote", "value": 20, "amount": 5}],
            },
            "live": False,
            "error": None,
        },
    ):
        res = TestClient(app).get("/companion/cash")
    assert res.status_code == 200
    assert res.json()["snapshot"]["change_level"] == "orange"

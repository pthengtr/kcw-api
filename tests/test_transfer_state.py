from src.transfer.state import (
    can_action,
    derive_line_status,
    derive_request_status,
    qty_open_prepare,
    qty_open_receive,
)


def test_qty_open():
    assert qty_open_prepare(10, 6) == 4
    assert qty_open_receive(6, 5) == 1


def test_line_status_partial_prepare():
    assert derive_line_status(qty_requested=10, qty_prepared=6, qty_received=0) == "partial_prepared"


def test_line_status_complete():
    assert derive_line_status(qty_requested=10, qty_prepared=10, qty_received=10) == "complete"


def test_cancel_request_denied_after_shipment():
    r = can_action("cancel_request", {"has_shipments": True, "status": "requested"})
    assert not r.allowed


def test_duplicate_bcode_denied():
    r = can_action(
        "submit_transfer",
        {"lines": [{"bcode": "A", "qty_requested": 1}, {"bcode": "A", "qty_requested": 2}]},
    )
    assert not r.allowed


def test_over_receive_denied():
    r = can_action(
        "syp_receive",
        {
            "tf_billno": "TF001",
            "qty_receive": 6,
            "qty_on_shipment": 5,
            "qty_received": 0,
            "qty_prepared": 5,
        },
    )
    assert not r.allowed


def test_request_status_awaiting_receive():
    lines = [{"qty_requested": 10, "qty_prepared": 10, "qty_received": 0, "line_status": "prepared"}]
    assert derive_request_status(header_status="requested", lines=lines, has_shipments=True) == "awaiting_receive"

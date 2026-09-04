from src.transfer.state import (
    can_action,
    derive_line_status,
    derive_request_status,
    prep_recv_mismatch,
    qty_open_prepare,
    qty_open_receive,
    qty_short_vs_order,
    request_has_open_prepare,
    shipment_lines_fully_received,
    summarize_request_progress,
)


def test_qty_open():
    assert qty_open_prepare(10, 6) == 4
    assert qty_open_receive(6, 5) == 1


def test_prep_recv_mismatch():
    assert prep_recv_mismatch(6, 5)
    assert prep_recv_mismatch(6, 0)
    assert not prep_recv_mismatch(0, 0)
    assert not prep_recv_mismatch(6, 6)


def test_line_status_partial_prepare():
    assert derive_line_status(qty_requested=10, qty_prepared=6, qty_received=0) == "partial_prepared"


def test_line_status_prepared_waiting_receive():
    assert derive_line_status(qty_requested=10, qty_prepared=10, qty_received=0) == "prepared"


def test_line_status_partial_received_vs_order():
    assert derive_line_status(qty_requested=10, qty_prepared=10, qty_received=6) == "partial_received"


def test_line_status_complete_when_order_fully_received():
    assert derive_line_status(qty_requested=10, qty_prepared=6, qty_received=10) == "complete"


def test_line_status_complete():
    assert derive_line_status(qty_requested=10, qty_prepared=10, qty_received=10) == "complete"


def test_summarize_request_progress_flags_mismatch():
    lines = [
        {
            "bcode": "A",
            "qty_requested": 10,
            "qty_prepared": 6,
            "qty_received": 3,
            "cancelled_at": None,
        }
    ]
    summary = summarize_request_progress(lines)
    assert summary["prep_recv_mismatch"] is True
    assert summary["prep_recv_mismatch_count"] == 1
    assert summary["qty_short_order_prepare"] == 4
    assert summary["qty_short_order_receive"] == 7
    assert summary["has_received"] is True
    assert summary["qty_received_total"] == 3
    assert summary["received_line_count"] == 1


def test_request_status_partial_prepared_vs_order():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 6,
            "qty_received": 0,
            "line_status": "partial_prepared",
            "cancelled_at": None,
        }
    ]
    assert (
        derive_request_status(header_status="requested", lines=lines, has_shipments=False)
        == "partial_prepared"
    )


def test_request_status_partial_received_vs_order():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 10,
            "qty_received": 6,
            "line_status": "partial_received",
            "cancelled_at": None,
        }
    ]
    assert (
        derive_request_status(header_status="requested", lines=lines, has_shipments=True)
        == "partial_received"
    )


def test_request_status_awaiting_receive_when_prep_done():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 10,
            "qty_received": 0,
            "line_status": "prepared",
            "cancelled_at": None,
        }
    ]
    assert (
        derive_request_status(header_status="requested", lines=lines, has_shipments=True)
        == "awaiting_receive"
    )


def test_shipment_lines_fully_received():
    assert shipment_lines_fully_received(
        [{"qty_shipped": 6, "qty_received": 6}, {"qty_shipped": 4, "qty_received": 2}]
    ) is False
    assert shipment_lines_fully_received(
        [{"qty_shipped": 6, "qty_received": 6}, {"qty_shipped": 4, "qty_received": 4}]
    ) is True


def test_request_has_open_prepare():
    assert request_has_open_prepare(
        [{"qty_requested": 10, "qty_prepared": 6, "qty_received": 0}]
    )
    assert not request_has_open_prepare(
        [{"qty_requested": 10, "qty_prepared": 10, "qty_received": 0}]
    )


def test_qty_short_vs_order():
    assert qty_short_vs_order(10, 6) == 4
    assert qty_short_vs_order(10, 10) == 0


def test_cancel_request_denied_after_shipment():
    r = can_action("cancel_request", {"has_shipments": True, "status": "requested"})
    assert not r.allowed


def test_cancel_request_allowed_when_requested():
    r = can_action("cancel_request", {"has_shipments": False, "status": "requested"})
    assert r.allowed


def test_cancel_request_allowed_without_shipments_if_status_drifted():
    r = can_action("cancel_request", {"has_shipments": False, "status": "partial_prepared"})
    assert r.allowed


def test_delete_draft_only():
    assert can_action("delete_draft", {"status": "draft"}).allowed
    assert not can_action("delete_draft", {"status": "requested"}).allowed


def test_edit_draft_only():
    assert can_action("edit_draft", {"status": "draft"}).allowed
    assert not can_action("edit_draft", {"status": "requested"}).allowed


def test_duplicate_bcode_denied():
    r = can_action(
        "submit_transfer",
        {"lines": [{"bcode": "A", "qty_requested": 1}, {"bcode": "A", "qty_requested": 2}]},
    )
    assert not r.allowed


def test_submit_transfer_accepts_qty_alias():
    r = can_action(
        "submit_transfer",
        {"lines": [{"bcode": "A", "qty": 3}, {"bcode": "B", "qty": 1}]},
    )
    assert r.allowed


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

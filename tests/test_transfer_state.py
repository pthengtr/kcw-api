from src.transfer.state import (
    can_action,
    derive_line_status,
    derive_request_status,
    last_received_at,
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


def test_line_status_prepared_when_short_of_order():
    assert derive_line_status(qty_requested=10, qty_prepared=6, qty_received=0) == "prepared"


def test_line_status_prepared_waiting_receive():
    assert derive_line_status(qty_requested=10, qty_prepared=10, qty_received=0) == "prepared"


def test_line_status_prepared_while_receive_is_open():
    assert derive_line_status(qty_requested=10, qty_prepared=10, qty_received=6) == "prepared"


def test_line_status_received_on_short_ship():
    assert derive_line_status(qty_requested=10, qty_prepared=6, qty_received=6) == "received"


def test_line_status_received():
    assert derive_line_status(qty_requested=10, qty_prepared=10, qty_received=10) == "received"


def test_line_status_received_when_cancelled_after_prepare():
    assert (
        derive_line_status(qty_requested=10, qty_prepared=6, qty_received=6, cancelled=True)
        == "received"
    )


def test_line_status_cancelled_when_never_prepared():
    assert (
        derive_line_status(qty_requested=10, qty_prepared=0, qty_received=0, cancelled=True)
        == "cancelled"
    )


def test_fulfill_line_is_not_an_action():
    assert not can_action(
        "fulfill_line",
        {"qty_requested": 10, "qty_prepared": 6, "qty_received": 6},
    ).allowed


def test_request_received_when_prepared_qty_is_in():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 6,
            "qty_received": 6,
            "cancelled_at": "2026-09-16T00:00:00+00:00",
        },
        {
            "qty_requested": 5,
            "qty_prepared": 5,
            "qty_received": 5,
            "cancelled_at": None,
        },
    ]
    assert (
        derive_request_status(
            header_status="prepared", lines=lines, has_shipments=True
        )
        == "received"
    )


def test_request_cancelled_when_only_unprepared_lines_cancelled():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 0,
            "qty_received": 0,
            "line_status": "cancelled",
            "cancelled_at": "2026-09-16T00:00:00+00:00",
        }
    ]
    assert (
        derive_request_status(header_status="requested", lines=lines, has_shipments=False)
        == "cancelled"
    )


def test_summarize_request_progress_counts_received():
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
    assert summary["has_received"] is True
    assert summary["qty_received_total"] == 3
    assert summary["received_line_count"] == 1


def test_summarize_not_received_before_any_receipt():
    lines = [
        {
            "bcode": "A",
            "qty_requested": 10,
            "qty_prepared": 10,
            "qty_received": 0,
            "cancelled_at": None,
        },
        {
            "bcode": "B",
            "qty_requested": 5,
            "qty_prepared": 2,
            "qty_received": 0,
            "cancelled_at": None,
        },
    ]
    summary = summarize_request_progress(lines)
    assert summary["has_received"] is False


def test_short_ship_with_unprepared_line_is_received():
    """Prepared qty is in. The unprepared remainder does not keep the request open."""
    lines = [
        {
            "bcode": "A",
            "qty_requested": 77,
            "qty_prepared": 77,
            "qty_received": 77,
            "cancelled_at": None,
        },
        {
            "bcode": "B",
            "qty_requested": 5,
            "qty_prepared": 0,
            "qty_received": 0,
            "cancelled_at": None,
        },
    ]
    assert (
        derive_request_status(header_status="prepared", lines=lines, has_shipments=True)
        == "received"
    )
    summary = summarize_request_progress(lines)
    assert summary["has_received"] is True


def test_last_received_at_picks_latest_receipt():
    ships = [{"shipment_id": "s1"}, {"shipment_id": "s2"}]
    receipts = {
        "s1": [{"created_at": "2026-09-05T02:00:00+00:00"}],
        "s2": [
            {"created_at": "2026-09-07T01:30:00+00:00"},
            {"created_at": "2026-09-07T02:13:00+00:00"},
        ],
    }
    assert last_received_at(ships, receipts) == "2026-09-07T02:13:00+00:00"
    assert last_received_at(ships, {}) is None
    assert last_received_at([], receipts) is None


def test_request_status_prepared_when_shipped_short():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 6,
            "qty_received": 0,
            "cancelled_at": None,
        }
    ]
    assert (
        derive_request_status(header_status="requested", lines=lines, has_shipments=True)
        == "prepared"
    )


def test_request_status_prepared_while_receive_open():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 10,
            "qty_received": 6,
            "cancelled_at": None,
        }
    ]
    assert (
        derive_request_status(header_status="requested", lines=lines, has_shipments=True)
        == "prepared"
    )


def test_request_status_prepared_when_nothing_received_yet():
    lines = [
        {
            "qty_requested": 10,
            "qty_prepared": 10,
            "qty_received": 0,
            "cancelled_at": None,
        }
    ]
    assert (
        derive_request_status(header_status="requested", lines=lines, has_shipments=True)
        == "prepared"
    )


def test_prepare_only_once_from_requested():
    assert can_action(
        "prepare_ship",
        {"status": "requested", "qty_ship": 6, "qty_requested": 10, "qty_prepared": 0},
    ).allowed
    second = can_action(
        "prepare_ship",
        {"status": "prepared", "qty_ship": 4, "qty_requested": 10, "qty_prepared": 6},
    )
    assert not second.allowed
    again = can_action(
        "prepare_ship",
        {
            "status": "requested",
            "qty_ship": 4,
            "qty_requested": 10,
            "qty_prepared": 6,
            "has_shipments": True,
        },
    )
    assert not again.allowed


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

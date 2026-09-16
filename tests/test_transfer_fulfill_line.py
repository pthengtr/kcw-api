from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.routers.transfer import api_fulfill_line


def _settings(*, site="SYP", iclow=True):
    s = MagicMock()
    s.site = site
    s.transfer_iclow_stamp_enabled = iclow
    return s


@patch("app.routers.transfer.insert_event")
@patch("app.routers.transfer.fulfill_line")
@patch("app.routers.transfer.revert_on_cancel")
@patch("app.routers.transfer.enrich_lines")
@patch("app.routers.transfer.list_lines")
@patch("app.routers.transfer.get_request")
@patch("app.routers.transfer._require_api")
@patch("app.routers.transfer._settings")
@patch("app.routers.transfer.get_transfer_supabase_client")
def test_fulfill_unprepared_reverts_iclow(
    mock_client_fn,
    mock_settings,
    mock_require_api,
    mock_get_request,
    mock_list_lines,
    mock_enrich,
    mock_revert,
    mock_fulfill,
    mock_event,
):
    mock_require_api.return_value = (MagicMock(display_name="op"), None)
    mock_settings.return_value = _settings(site="SYP", iclow=True)
    mock_client_fn.return_value = MagicMock()
    mock_get_request.return_value = {
        "transfer_id": "t1",
        "from_branch": "HQ",
        "to_branch": "SYP",
        "status": "partial_prepared",
    }
    line = {
        "line_id": "L1",
        "bcode": "A",
        "qty_requested": 10,
        "qty_prepared": 0,
        "qty_received": 0,
        "iclow_id": 99,
        "cancelled_at": None,
    }
    mock_enrich.return_value = [line]
    mock_fulfill.return_value = {
        "line": {**line, "cancelled_at": "now", "line_status": "cancelled"},
        "request": {"status": "cancelled"},
    }

    result = api_fulfill_line("t1", "L1", MagicMock())

    assert result["status"] == "fulfilled"
    assert result["iclow_reverted"] is True
    mock_revert.assert_called_once_with(iclow_id="99")
    mock_fulfill.assert_called_once()


@patch("app.routers.transfer.insert_event")
@patch("app.routers.transfer.fulfill_line")
@patch("app.routers.transfer.revert_on_cancel")
@patch("app.routers.transfer.enrich_lines")
@patch("app.routers.transfer.list_lines")
@patch("app.routers.transfer.get_request")
@patch("app.routers.transfer._require_api")
@patch("app.routers.transfer._settings")
@patch("app.routers.transfer.get_transfer_supabase_client")
def test_fulfill_short_ship_does_not_revert_iclow(
    mock_client_fn,
    mock_settings,
    mock_require_api,
    mock_get_request,
    mock_list_lines,
    mock_enrich,
    mock_revert,
    mock_fulfill,
    mock_event,
):
    mock_require_api.return_value = (MagicMock(display_name="op"), None)
    mock_settings.return_value = _settings(site="SYP", iclow=True)
    mock_client_fn.return_value = MagicMock()
    mock_get_request.return_value = {
        "transfer_id": "t1",
        "from_branch": "HQ",
        "to_branch": "SYP",
        "status": "partial_received",
    }
    line = {
        "line_id": "L1",
        "bcode": "A",
        "qty_requested": 10,
        "qty_prepared": 6,
        "qty_received": 6,
        "iclow_id": 99,
        "cancelled_at": None,
    }
    mock_enrich.return_value = [line]
    mock_fulfill.return_value = {
        "line": {**line, "cancelled_at": "now", "line_status": "complete"},
        "request": {"status": "complete"},
    }

    result = api_fulfill_line("t1", "L1", MagicMock())

    assert result["request_status"] == "complete"
    assert result["iclow_reverted"] is False
    mock_revert.assert_not_called()


@patch("app.routers.transfer.get_request")
@patch("app.routers.transfer._require_api")
@patch("app.routers.transfer._settings")
@patch("app.routers.transfer.get_transfer_supabase_client")
def test_fulfill_denied_for_shipper_site(
    mock_client_fn,
    mock_settings,
    mock_require_api,
    mock_get_request,
):
    mock_require_api.return_value = (MagicMock(display_name="op"), None)
    mock_settings.return_value = _settings(site="HQ", iclow=False)
    mock_client_fn.return_value = MagicMock()
    mock_get_request.return_value = {
        "transfer_id": "t1",
        "from_branch": "HQ",
        "to_branch": "SYP",
        "status": "partial_received",
    }

    resp = api_fulfill_line("t1", "L1", MagicMock())
    assert resp.status_code == 400
    assert "สาขาที่ขอโอน" in resp.body.decode()

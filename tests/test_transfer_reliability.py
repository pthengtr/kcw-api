from __future__ import annotations

from unittest.mock import MagicMock, patch

from app.routers.transfer import api_prepare


@patch("app.routers.transfer.refresh_request_status")
@patch("app.routers.transfer.bump_line_prepared")
@patch("app.routers.transfer.add_shipment_lines")
@patch("app.routers.transfer.create_shipment")
@patch("app.routers.transfer.post_transfer_ship")
@patch("app.routers.transfer.get_shipment_by_token")
@patch("app.routers.transfer.list_lines")
@patch("app.routers.transfer.get_request")
@patch("app.routers.transfer._require_api")
@patch("app.routers.transfer._settings")
@patch("app.routers.transfer.get_transfer_supabase_client")
def test_api_prepare_idempotent_short_circuit(
    mock_client_fn,
    mock_settings,
    mock_require_api,
    mock_get_request,
    mock_list_lines,
    mock_get_shipment_by_token,
    mock_post_ship,
    mock_create_shipment,
    mock_add_lines,
    mock_bump,
    mock_refresh,
):
    ident = MagicMock(display_name="op")
    mock_require_api.return_value = (ident, None)
    settings = MagicMock()
    settings.site = "HQ"
    settings.hq_ship_write_enabled = True
    settings.syp_ship_write_enabled = False
    mock_settings.return_value = settings
    mock_client_fn.return_value = MagicMock()
    mock_get_request.return_value = {
        "transfer_id": "t1",
        "from_branch": "HQ",
        "to_branch": "SYP",
        "status": "requested",
        "short_id": "TRF-abc",
    }
    mock_get_shipment_by_token.return_value = {
        "shipment_id": "ship-1",
        "ship_billno": "TF6808-001",
        "tf_billno": "TF6808-001",
    }

    request = MagicMock()
    body = MagicMock(client_token="tok-1", lines=[])

    result = api_prepare("t1", body, request)

    assert result["shipment_id"] == "ship-1"
    assert result["ship_billno"] == "TF6808-001"
    mock_post_ship.assert_not_called()
    mock_create_shipment.assert_not_called()
    mock_add_lines.assert_not_called()
    mock_bump.assert_not_called()
    mock_refresh.assert_not_called()

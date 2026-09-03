from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from src.transfer.writers.receive_pimas import TransferReceiveError, post_transfer_receive
from src.transfer.writers.ship_simas import TransferShipError, post_transfer_ship


def test_post_transfer_ship_empty_lines():
    with pytest.raises(TransferShipError, match="No lines provided"):
        post_transfer_ship(
            from_branch="HQ",
            transfer_id="test-id",
            short_id="test-short",
            lines=[],
            operator="test-operator",
            client_token="test-token",
        )


@patch("src.transfer.writers.ship_simas.writer_engine_for_branch")
@patch("src.transfer.writers.ship_simas.get_shipment_by_token")
def test_post_transfer_ship_idempotent(mock_get_shipment, mock_engine):
    mock_get_shipment.return_value = {
        "shipment_id": "existing-id",
        "ship_billno": "TF2308-00001",
    }
    result = post_transfer_ship(
        from_branch="HQ",
        transfer_id="test-id",
        short_id="test-short",
        lines=[{"line_id": "line1", "bcode": "BCODE1", "qty_ship": 10, "descr": "Test Item"}],
        operator="test-operator",
        client_token="test-token",
    )
    assert result["ship_billno"] == "TF2308-00001"
    assert result["shipment_id"] == "existing-id"
    mock_engine.assert_not_called()


@patch("src.transfer.writers.ship_simas.get_transfer_supabase_client")
@patch("src.transfer.writers.ship_simas.writer_engine_for_branch")
@patch("src.transfer.writers.ship_simas.get_shipment_by_token")
def test_post_transfer_ship_basic_creation(mock_get_shipment, mock_engine, mock_client):
    mock_get_shipment.return_value = None
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    with patch("src.transfer.writers.ship_simas.next_simas_billno", return_value="TF2308-00001"):
        result = post_transfer_ship(
            from_branch="HQ",
            transfer_id="test-id",
            short_id="test-short",
            lines=[{"line_id": "line1", "bcode": "BCODE1", "qty_ship": 10, "descr": "Test Item"}],
            operator="test-operator",
            client_token="test-token",
        )
    assert result["ship_billno"].startswith("TF")
    mock_engine.assert_called_once_with("HQ")
    simas_params = [
        call.args[1]
        for call in mock_conn.execute.call_args_list
        if "INSERT INTO dbo.SIMAS" in str(call.args[0])
    ]
    assert simas_params
    assert simas_params[0]["billtime"] == simas_params[0]["jourtime"]
    assert simas_params[0]["acctno"] == "KCW1"
    assert "สาขา" in (simas_params[0]["acctname"] or "")
    sidet_params = [
        call.args[1]
        for call in mock_conn.execute.call_args_list
        if "INSERT INTO dbo.SIDET" in str(call.args[0])
    ]
    assert sidet_params
    assert sidet_params[0]["qty"] == 10


@patch("src.transfer.writers.ship_simas.get_transfer_supabase_client")
@patch("src.transfer.writers.ship_simas.writer_engine_for_branch")
@patch("src.transfer.writers.ship_simas.get_shipment_by_token")
def test_post_transfer_ship_syp_uses_kcw_ap(mock_get_shipment, mock_engine, mock_client):
    mock_get_shipment.return_value = None
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = {
        "ACCTNAME": "บจก.เกียรติชัยอะไหล่ยนต์ (สำนักงานใหญ่)"
    }

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    with patch("src.transfer.writers.ship_simas.next_simas_billno", return_value="3TF6909-0001"):
        post_transfer_ship(
            from_branch="SYP",
            to_branch="HQ",
            transfer_id="test-id",
            short_id="AABBCCDD",
            lines=[{"line_id": "line1", "bcode": "B1", "qty_ship": 2, "descr": "x"}],
            operator="op",
            client_token="tok",
        )
    simas_params = next(
        call.args[1]
        for call in mock_conn.execute.call_args_list
        if "INSERT INTO dbo.SIMAS" in str(call.args[0])
    )
    assert simas_params["acctno"] == "KCW"
    assert "สำนักงานใหญ่" in simas_params["acctname"]

from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from src.transfer.direction import (
    branches_for_direction,
    can_prepare_at_site,
    can_receive_at_site,
    can_submit_at_site,
    receive_billno_prefix,
    ship_billno_prefix,
)
from src.transfer.writers.ship_simas import TransferShipError, post_transfer_ship, post_transfer_tf


def test_branches_for_direction():
    assert branches_for_direction("to_syp") == ("HQ", "SYP")
    assert branches_for_direction("to_hq") == ("SYP", "HQ")


def test_billno_prefixes():
    assert ship_billno_prefix(from_branch="HQ") == "TF"
    assert ship_billno_prefix(from_branch="SYP") == "3TF"
    assert receive_billno_prefix(from_branch="HQ", to_branch="SYP") == "TF"
    assert receive_billno_prefix(from_branch="SYP", to_branch="HQ") == "3TF"


def test_site_permissions():
    assert can_submit_at_site("SYP", "SYP")
    assert not can_submit_at_site("HQ", "SYP")
    assert can_prepare_at_site("HQ", "HQ")
    assert not can_prepare_at_site("SYP", "HQ")
    assert can_receive_at_site("SYP", "SYP")
    assert can_receive_at_site("HQ", "HQ")


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
def test_post_transfer_ship_hq_tf_prefix(mock_get_shipment, mock_engine, mock_client):
    mock_get_shipment.return_value = None
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    with patch("src.transfer.writers.ship_simas.next_simas_billno", return_value="TF6808-001"):
        result = post_transfer_ship(
            from_branch="HQ",
            transfer_id="test-id",
            short_id="test-short",
            lines=[{"line_id": "line1", "bcode": "BCODE1", "qty_ship": 10, "descr": "Test Item"}],
            operator="test-operator",
            client_token="test-token",
        )
    assert result["ship_billno"] == "TF6808-001"
    mock_engine.assert_called_once_with("HQ")


@patch("src.transfer.writers.ship_simas.get_transfer_supabase_client")
@patch("src.transfer.writers.ship_simas.writer_engine_for_branch")
@patch("src.transfer.writers.ship_simas.get_shipment_by_token")
def test_post_transfer_ship_syp_3tf_prefix(mock_get_shipment, mock_engine, mock_client):
    mock_get_shipment.return_value = None
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    with patch("src.transfer.writers.ship_simas.next_simas_billno", return_value="3TF6808-001"):
        result = post_transfer_ship(
            from_branch="SYP",
            transfer_id="test-id",
            short_id="test-short",
            lines=[{"line_id": "line1", "bcode": "BCODE1", "qty_ship": 5}],
            operator="test-operator",
            client_token="test-token",
        )
    assert result["ship_billno"].startswith("3TF")
    mock_engine.assert_called_once_with("SYP")


def test_post_transfer_tf_compat_alias():
    with pytest.raises(TransferShipError):
        post_transfer_tf(
            transfer_id="x",
            short_id="y",
            lines=[],
            operator="op",
            client_token="tok",
        )

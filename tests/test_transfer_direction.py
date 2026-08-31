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
    should_stamp_iclow,
)
from src.transfer.writers._engine import _next_billno_on_table, transfer_bill_yymm, transfer_write_permission_hint
from src.transfer.writers.ship_simas import TransferShipError, post_transfer_ship, post_transfer_tf
from datetime import datetime


def test_branches_for_direction():
    assert branches_for_direction("to_syp") == ("HQ", "SYP")
    assert branches_for_direction("to_hq") == ("SYP", "HQ")


def test_billno_prefixes():
    assert ship_billno_prefix(from_branch="HQ") == "TF"
    assert ship_billno_prefix(from_branch="SYP") == "3TF"
    assert receive_billno_prefix(from_branch="HQ", to_branch="SYP") == "TF"
    assert receive_billno_prefix(from_branch="SYP", to_branch="HQ") == "3TF"


def test_transfer_bill_yymm_buddhist_era():
    assert transfer_bill_yymm(datetime(2026, 8, 31)) == "6908"
    assert transfer_bill_yymm(datetime(2025, 1, 15)) == "6801"


def test_next_billno_uses_buddhist_yymm():
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = {"max_seq": None}
    when = datetime(2026, 8, 31)
    billno = _next_billno_on_table(conn, "SIMAS", "TF", when)
    assert billno == "TF6908-0001"


def test_next_billno_continues_existing_seq():
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = {"max_seq": 97}
    when = datetime(2026, 8, 31)
    billno = _next_billno_on_table(conn, "SIMAS", "TF", when)
    assert billno == "TF6908-0098"


def test_next_billno_numeric_max_beats_string_sort():
    """0098 must win over 097 — string MAX(BILLNO) would pick 097 incorrectly."""
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = {"max_seq": 98}
    when = datetime(2026, 8, 31)
    billno = _next_billno_on_table(conn, "SIMAS", "TF", when)
    assert billno == "TF6908-0099"


def test_transfer_write_permission_hint():
    exc = Exception("SELECT permission was denied on object 'PIMAS' (229)")
    hint = transfer_write_permission_hint(exc, branch="SYP", tables="PIMAS/PIDET")
    assert hint and "kss-pc" in hint and "grant_transfer_writer" in hint


def test_should_stamp_iclow_hq_to_syp_on_syp_only():
    assert should_stamp_iclow(
        enabled=True, site="SYP", from_branch="HQ", to_branch="SYP"
    )
    assert not should_stamp_iclow(
        enabled=True, site="HQ", from_branch="SYP", to_branch="HQ"
    )
    assert not should_stamp_iclow(
        enabled=True, site="HQ", from_branch="HQ", to_branch="SYP"
    )
    assert not should_stamp_iclow(
        enabled=False, site="SYP", from_branch="HQ", to_branch="SYP"
    )


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

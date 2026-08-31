from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from src.transfer.writers.receive_pimas import TransferReceiveError, post_transfer_receive


def test_post_transfer_receive_empty_lines():
    with pytest.raises(TransferReceiveError, match="No lines to receive"):
        post_transfer_receive(
            to_branch="SYP",
            from_branch="HQ",
            shipment={"shipment_id": "test-id", "tf_billno": "TF2308-00001"},
            lines_to_receive=[],
            operator="test-operator",
            client_token="test-token",
        )


def test_post_transfer_receive_invalid_qty():
    with pytest.raises(TransferReceiveError, match="Invalid quantity to receive"):
        post_transfer_receive(
            to_branch="SYP",
            from_branch="HQ",
            shipment={"shipment_id": "test-id", "tf_billno": "TF2308-00001"},
            lines_to_receive=[{"bcode": "BCODE1", "qty_receive": 0}],
            operator="test-operator",
            client_token="test-token",
        )


@patch("src.transfer.writers.receive_pimas.get_receipt_by_token", return_value=None)
@patch("src.transfer.writers.receive_pimas.writer_engine_for_branch")
def test_post_transfer_receive_writes_pimas_not_simas(mock_engine, mock_receipt):
    mock_conn = MagicMock()
    icmas_row = {
        "BCODE": "A1",
        "QTYOH2": 5,
        "PCODE": "P",
        "MCODE": "M",
        "UI1": "ea",
        "LOCATION1": "L1",
    }
    mock_conn.execute.return_value.mappings.return_value.first.return_value = icmas_row

    @contextmanager
    def fake_connect():
        yield mock_conn

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.connect = fake_connect
    mock_engine.return_value.begin = fake_begin
    with patch("src.transfer.writers.receive_pimas.next_pimas_billno", return_value="TF6808-099"):
        result = post_transfer_receive(
            to_branch="SYP",
            from_branch="HQ",
            shipment={"shipment_id": "s1", "ship_billno": "TF6808-001"},
            lines_to_receive=[{"bcode": "A1", "qty_receive": 3}],
            operator="op",
            client_token="tok",
        )
    assert result["receive_billno"] == "TF6808-099"
    sql_calls = [str(c.args[0]) for c in mock_conn.execute.call_args_list]
    assert any("PIMAS" in s for s in sql_calls)
    assert not any("SIMAS" in s for s in sql_calls)
    pimas_params = next(c.args[1] for c in mock_conn.execute.call_args_list if "PIMAS" in str(c.args[0]))
    assert pimas_params["bookno"] == "9"
    assert pimas_params["lines"] == 1


@patch("src.transfer.writers.receive_pimas.get_receipt_by_token")
def test_post_transfer_receive_idempotent_when_receipt_exists(mock_get_receipt):
    mock_get_receipt.return_value = {
        "receipt_id": "r1",
        "receive_billno": "TF6808-100",
        "client_token": "tok",
    }
    result = post_transfer_receive(
        to_branch="SYP",
        from_branch="HQ",
        shipment={"shipment_id": "s1", "ship_billno": "TF6808-001"},
        lines_to_receive=[{"bcode": "A1", "qty_receive": 3}],
        operator="op",
        client_token="tok",
    )
    assert result["receive_billno"] == "TF6808-100"
    assert result["status"] == "received"


@patch("src.transfer.writers.receive_pimas.get_receipt_by_token", return_value=None)
@patch("src.transfer.writers.receive_pimas.writer_engine_for_branch")
def test_post_transfer_receive_missing_icmas(mock_engine, mock_receipt):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None

    @contextmanager
    def fake_connect():
        yield mock_conn

    mock_engine.return_value.connect = fake_connect
    with pytest.raises(TransferReceiveError) as exc_info:
        post_transfer_receive(
            to_branch="SYP",
            from_branch="HQ",
            shipment={"shipment_id": "s1", "ship_billno": "TF6808-001"},
            lines_to_receive=[{"bcode": "MISSING", "qty_receive": 1}],
            operator="op",
            client_token="tok",
        )
    assert exc_info.value.code == "missing_icmas"

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


def test_post_transfer_receive_idempotent():
    result = post_transfer_receive(
        to_branch="SYP",
        from_branch="HQ",
        shipment={
            "shipment_id": "test-id",
            "tf_billno": "TF2308-00001",
            "posted_at": "2026-08-29T10:00:00+00:00",
        },
        lines_to_receive=[{"bcode": "BCODE1", "qty_receive": 10}],
        operator="test-operator",
        client_token="test-token",
    )
    assert result["status"] == "already_processed"


@patch("src.transfer.writers.receive_pimas.writer_engine_for_branch")
def test_post_transfer_receive_writes_pimas_not_simas(mock_engine):
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = {
        "BCODE": "A1",
        "QTYOH2": 5,
        "PCODE": "P",
        "MCODE": "M",
        "UI1": "ea",
        "LOCATION1": "L1",
    }

    @contextmanager
    def fake_begin():
        yield mock_conn

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

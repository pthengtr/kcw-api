from __future__ import annotations

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest

from src.transfer.writers.hq_tf import TransferTFError, post_transfer_tf
from src.transfer.writers.syp_receive import TransferReceiveError, post_transfer_receive


def test_post_transfer_tf_empty_lines():
    with pytest.raises(TransferTFError, match="No lines provided"):
        post_transfer_tf(
            transfer_id="test-id",
            short_id="test-short",
            lines=[],
            operator="test-operator",
            client_token="test-token",
        )


@patch("src.transfer.writers.hq_tf._writer_engine_hq")
@patch("src.transfer.writers.hq_tf.get_shipment_by_token")
def test_post_transfer_tf_idempotent(mock_get_shipment, mock_engine):
    mock_get_shipment.return_value = {
        "shipment_id": "existing-id",
        "tf_billno": "TF2308-00001",
    }
    result = post_transfer_tf(
        transfer_id="test-id",
        short_id="test-short",
        lines=[{"line_id": "line1", "bcode": "BCODE1", "qty_ship": 10, "descr": "Test Item"}],
        operator="test-operator",
        client_token="test-token",
    )
    assert result["tf_billno"] == "TF2308-00001"
    assert result["shipment_id"] == "existing-id"
    mock_engine.assert_not_called()


@patch("src.transfer.writers.hq_tf.get_transfer_supabase_client")
@patch("src.transfer.writers.hq_tf._writer_engine_hq")
@patch("src.transfer.writers.hq_tf.get_shipment_by_token")
def test_post_transfer_tf_basic_creation(mock_get_shipment, mock_engine, mock_client):
    mock_get_shipment.return_value = None
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = None

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    mock_client.return_value.schema.return_value.from_.return_value.insert.return_value.select.return_value.execute.return_value.data = [
        {"shipment_id": "new-ship"}
    ]

    result = post_transfer_tf(
        transfer_id="test-id",
        short_id="test-short",
        lines=[{"line_id": "line1", "bcode": "BCODE1", "qty_ship": 10, "descr": "Test Item"}],
        operator="test-operator",
        client_token="test-token",
    )
    assert "tf_billno" in result
    assert result["tf_billno"].startswith("TF")
    mock_engine.assert_called_once()

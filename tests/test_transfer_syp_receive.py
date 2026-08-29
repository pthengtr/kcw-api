from __future__ import annotations

from unittest.mock import patch

import pytest

from src.transfer.writers.syp_receive import TransferReceiveError, post_transfer_receive


def test_post_transfer_receive_empty_lines():
    with pytest.raises(TransferReceiveError, match="No lines to receive"):
        post_transfer_receive(
            shipment={"shipment_id": "test-id", "tf_billno": "TF2308-00001"},
            lines_to_receive=[],
            operator="test-operator",
            client_token="test-token",
        )


def test_post_transfer_receive_invalid_qty():
    with pytest.raises(TransferReceiveError, match="Invalid quantity to receive"):
        post_transfer_receive(
            shipment={"shipment_id": "test-id", "tf_billno": "TF2308-00001"},
            lines_to_receive=[{"bcode": "BCODE1", "qty_receive": 0}],
            operator="test-operator",
            client_token="test-token",
        )


def test_post_transfer_receive_idempotent():
    result = post_transfer_receive(
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

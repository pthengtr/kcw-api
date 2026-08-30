"""Backward-compat shim — use receive_pimas.post_transfer_receive."""

from __future__ import annotations

from typing import Any

from src.transfer.writers.receive_pimas import (
    TransferReceiveError,
    post_transfer_receive as _post_transfer_receive,
)

__all__ = ["TransferReceiveError", "post_transfer_receive"]


def post_transfer_receive(
    *,
    shipment: dict[str, Any],
    lines_to_receive: list[dict[str, Any]],
    operator: str,
    client_token: str,
    from_branch: str = "HQ",
    to_branch: str = "SYP",
) -> dict[str, Any]:
    return _post_transfer_receive(
        to_branch=to_branch,
        from_branch=from_branch,
        shipment=shipment,
        lines_to_receive=lines_to_receive,
        operator=operator,
        client_token=client_token,
    )

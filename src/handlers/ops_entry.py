from __future__ import annotations

import re

from src.access.helper import can_execute
from src.handlers.transfer_entry import handle_transfer_command

OPS_COMMAND = "สถานะใบสั่งซื้อ"
OPS_COMMANDS = {
    "สถานะใบสั่งซื้อ",
    "ใบสั่งซื้อ",
}


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_OPS_COMMANDS_NORM = {_normalize_cmd(c) for c in OPS_COMMANDS}


def is_ops_command(text: str) -> bool:
    return _normalize_cmd(text) in _OPS_COMMANDS_NORM


def handle_ops_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
    user_text: str | None = None,
) -> dict:
    """Retired. Purchase-order status is replaced by HQ↔SYP transfer."""
    _ = user_text
    group = ((access or {}).get("access_group") or "").strip().lower()
    if not can_execute(group, OPS_COMMAND):
        return {"type": "text", "text": "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"}
    return handle_transfer_command(
        engine,
        line_user_id=line_user_id,
        display_name=display_name,
        access=access,
    )

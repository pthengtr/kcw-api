from __future__ import annotations

import re

from src.handlers.online_sale_entry import handle_online_sale_command

TO_BILL_COMMANDS = {
    "ใบเต็ม",
    "ใบเต็มออนไลน์",
    "ใบกำกับ",
    "to bill",
    "tobill",
}


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_TO_BILL_COMMANDS_NORM = {_normalize_cmd(c) for c in TO_BILL_COMMANDS}


def is_to_bill_command(text: str) -> bool:
    return _normalize_cmd(text) in _TO_BILL_COMMANDS_NORM


def handle_to_bill_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    """Merged into online-sale (:8796) — opens the TO tab."""
    return handle_online_sale_command(
        engine,
        line_user_id=line_user_id,
        display_name=display_name,
        access=access,
        path="/online-sale/?tab=to",
        title="ใบเต็มออนไลน์",
    )

from __future__ import annotations

import re

from src.bot.branch_link_buttons import branch_uri_buttons
from src.handlers.branch_tool_links import (
    collect_branch_tool_links,
    elevated_wifi_hint,
    is_elevated_access,
)
from src.jobs.heartbeat import get_all_worker_status
from src.stock_check.config import get_stock_check_settings


COMPANION_COMMANDS = {
    "ไทเกอร์",
    "ไทเกอร์เพย์",
    "tiger",
    "tiger pay",
    "tigerpay",
    "companion",
    "เก็บเงิน",
    "รับเงิน",
    "ตู้เงิน",
}


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", "", t)
    return t


_COMPANION_COMMANDS_NORM = {_normalize_cmd(c) for c in COMPANION_COMMANDS}


def is_companion_command(text: str) -> bool:
    return _normalize_cmd(text) in _COMPANION_COMMANDS_NORM


def handle_companion_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    settings = get_stock_check_settings()
    if not settings.stock_check_token_secret:
        return {
            "type": "text",
            "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ",
        }

    elevated = is_elevated_access(access)
    workers = get_all_worker_status(engine, offline_after_seconds=60)
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=settings.stock_check_token_secret,
        ttl_seconds=settings.stock_check_token_ttl_seconds,
        path="/companion/",
        lan_url_key="companion_public_base_url",
        tailscale_url_key="companion_tailscale_base_url",
        include_tailscale=elevated,
        mint_app="companion",
    )

    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์ Tiger Pay ออนไลน์ครับ (รอ HQ/SYP heartbeat)",
        }

    return branch_uri_buttons(
        title="ไทเกอร์เพย์",
        alt_text="ไทเกอร์เพย์ — กดเลือกสาขา",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated),
    )

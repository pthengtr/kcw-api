from __future__ import annotations

import re

from src.bot.branch_link_buttons import branch_uri_buttons
from src.handlers.branch_tool_links import (
    collect_branch_tool_links,
    elevated_wifi_hint,
    is_elevated_access,
)
from src.jobs.heartbeat import get_all_worker_status
from src.parts9_explorer.config import get_explorer_settings
from src.parts9_explorer.ui import APP

EXPLORER_COMMANDS = {"parts9", "part9", "ค้นหา", "สำรวจ", "สำรวจสินค้า", "explorer"}


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_EXPLORER_COMMANDS_NORM = {_normalize_cmd(c) for c in EXPLORER_COMMANDS}


def is_explorer_command(text: str) -> bool:
    return _normalize_cmd(text) in _EXPLORER_COMMANDS_NORM


def handle_explorer_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    settings = get_explorer_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}

    elevated = is_elevated_access(access)
    workers = get_all_worker_status(engine, offline_after_seconds=60)
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=secret,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        path="/parts9/",
        lan_url_key="explorer_public_base_url",
        tailscale_url_key="explorer_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
    )
    if not links:
        return {"type": "text", "text": "ยังไม่พบเซิร์ฟเวอร์ PARTS9 explorer ออนไลน์ครับ (รอ heartbeat)"}
    return branch_uri_buttons(
        title="ค้นหา",
        alt_text="ค้นหา — กดเลือกสาขา",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

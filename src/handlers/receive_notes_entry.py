from __future__ import annotations

import os
import re

from src.bot.branch_link_buttons import branch_uri_buttons
from src.handlers.branch_tool_links import (
    collect_branch_tool_links,
    elevated_wifi_hint,
    is_elevated_access,
)
from src.jobs.heartbeat import get_all_worker_status
from src.receive_notes.config import get_receive_notes_settings
from src.receive_notes.net import rewrite_base_port
from src.receive_notes.ui import APP

RECEIVE_NOTES_COMMAND = "รับชำระลูกหนี้"
RECEIVE_NOTES_COMMANDS = {
    "รับชำระลูกหนี้",
    "รับชำระ",
    "receivenote",
    "receive note",
    "receive-notes",
}
RECEIVE_NOTES_PORT = int(os.getenv("RECEIVE_NOTES_LISTEN_PORT", "8797"))


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_RECEIVE_NOTES_COMMANDS_NORM = {_normalize_cmd(c) for c in RECEIVE_NOTES_COMMANDS}


def is_receive_notes_command(text: str) -> bool:
    return _normalize_cmd(text) in _RECEIVE_NOTES_COMMANDS_NORM


def _rewrite_worker_receive_notes_urls(workers: list[dict]) -> list[dict]:
    out = []
    for w in workers:
        row = dict(w)
        lan = (row.get("receive_notes_public_base_url") or "").strip()
        ts = (row.get("receive_notes_tailscale_base_url") or "").strip()
        if not lan:
            lan = rewrite_base_port(row.get("explorer_public_base_url"), RECEIVE_NOTES_PORT) or ""
        if not ts:
            ts = rewrite_base_port(row.get("explorer_tailscale_base_url"), RECEIVE_NOTES_PORT) or ""
        env_lan = (os.getenv("RECEIVE_NOTES_PUBLIC_BASE_URL") or "").strip()
        env_ts = (os.getenv("RECEIVE_NOTES_TAILSCALE_BASE_URL") or "").strip()
        row["receive_notes_public_base_url"] = env_lan or lan
        row["receive_notes_tailscale_base_url"] = env_ts or ts
        out.append(row)
    return out


def handle_receive_notes_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    settings = get_receive_notes_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}

    elevated = is_elevated_access(access)
    workers = _rewrite_worker_receive_notes_urls(
        get_all_worker_status(engine, offline_after_seconds=60)
    )
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=secret,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        path="/receive-notes/",
        lan_url_key="receive_notes_public_base_url",
        tailscale_url_key="receive_notes_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
    )
    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์รับชำระลูกหนี้ออนไลน์ครับ (รอ heartbeat จาก HQ)",
        }
    return branch_uri_buttons(
        title="รับชำระลูกหนี้",
        alt_text="รับชำระลูกหนี้ — กดเปิด",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

from __future__ import annotations

import os
import re

from src.bot.branch_link_buttons import branch_uri_buttons
from src.handlers.branch_tool_links import (
    branch_for_worker,
    collect_branch_tool_links,
    elevated_wifi_hint,
    is_elevated_access,
)
from src.jobs.hq_worker import filter_worker_status_rows
from src.jobs.heartbeat import get_all_worker_status
from src.transfer.config import get_transfer_settings
from src.transfer.net import rewrite_base_port
from src.transfer.ui import APP

TRANSFER_COMMAND = "โอนสินค้า"
TRANSFER_COMMANDS = {
    "โอนสินค้า",
    "โอนสินสินค้า",
    "โอน",
    "transfer",
    "stock transfer",
}
TRANSFER_PORT = int(os.getenv("TRANSFER_LISTEN_PORT", "8792"))


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_TRANSFER_COMMANDS_NORM = {_normalize_cmd(c) for c in TRANSFER_COMMANDS}


def is_transfer_command(text: str) -> bool:
    return _normalize_cmd(text) in _TRANSFER_COMMANDS_NORM


def _rewrite_worker_transfer_urls(workers: list[dict]) -> list[dict]:
    """Fill transfer URLs from explorer heartbeat; HQ env overrides HQ branch only."""
    env_lan = (os.getenv("TRANSFER_PUBLIC_BASE_URL") or "").strip()
    env_ts = (os.getenv("TRANSFER_TAILSCALE_BASE_URL") or "").strip()
    out = []
    for w in workers:
        row = dict(w)
        branch = branch_for_worker(str(row.get("worker_name") or ""))
        lan = (row.get("transfer_public_base_url") or "").strip()
        ts = (row.get("transfer_tailscale_base_url") or "").strip()
        if not lan:
            lan = rewrite_base_port(row.get("explorer_public_base_url"), TRANSFER_PORT) or ""
        if not ts:
            ts = rewrite_base_port(row.get("explorer_tailscale_base_url"), TRANSFER_PORT) or ""
        if branch == "HQ":
            if env_lan:
                lan = env_lan
            if env_ts:
                ts = env_ts
        row["transfer_public_base_url"] = lan
        row["transfer_tailscale_base_url"] = ts
        out.append(row)
    return out


def handle_transfer_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    settings = get_transfer_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}

    elevated = is_elevated_access(access)
    workers = _rewrite_worker_transfer_urls(
        filter_worker_status_rows(
            get_all_worker_status(engine, offline_after_seconds=60)
        )
    )
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=secret,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        path="/transfer/",
        lan_url_key="transfer_public_base_url",
        tailscale_url_key="transfer_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
    )
    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์โอนสินค้าออนไลน์ครับ (รอ heartbeat จาก HQ/SYP)",
        }
    return branch_uri_buttons(
        title="โอนสินค้า HQ↔SYP",
        alt_text="โอนสินค้า — กดเลือกสาขา",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

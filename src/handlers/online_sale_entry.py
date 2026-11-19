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
from src.staff_shell.auth import entry_link_ttl_seconds

from src.jobs.hq_worker import filter_worker_status_rows
from src.jobs.heartbeat import get_all_worker_status
from src.online_sale.config import get_online_sale_settings
from src.online_sale.ui import APP
from src.transfer.net import rewrite_base_port

ONLINE_SALE_COMMAND = "ขายออนไลน์"
ONLINE_SALE_COMMANDS = {
    "ขายออนไลน์",
    "ออนไลน์",
    "online sale",
    "onlinesale",
    "tad",
}
ONLINE_SALE_PORT = int(os.getenv("ONLINE_SALE_LISTEN_PORT", "8796"))


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_ONLINE_SALE_COMMANDS_NORM = {_normalize_cmd(c) for c in ONLINE_SALE_COMMANDS}


def is_online_sale_command(text: str) -> bool:
    return _normalize_cmd(text) in _ONLINE_SALE_COMMANDS_NORM


def _rewrite_worker_urls(workers: list[dict]) -> list[dict]:
    env_lan = (os.getenv("ONLINE_SALE_PUBLIC_BASE_URL") or "").strip()
    env_ts = (os.getenv("ONLINE_SALE_TAILSCALE_BASE_URL") or "").strip()
    out = []
    for worker in workers:
        row = dict(worker)
        branch = branch_for_worker(str(row.get("worker_name") or ""))
        lan = rewrite_base_port(row.get("explorer_public_base_url"), ONLINE_SALE_PORT) or ""
        ts = rewrite_base_port(row.get("explorer_tailscale_base_url"), ONLINE_SALE_PORT) or ""
        if branch == "HQ":
            if env_lan:
                lan = env_lan
            if env_ts:
                ts = env_ts
        row["online_sale_public_base_url"] = lan
        row["online_sale_tailscale_base_url"] = ts
        out.append(row)
    return out


def handle_online_sale_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
    path: str = "/online-sale/",
    title: str = "ขายออนไลน์",
) -> dict:
    settings = get_online_sale_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}

    elevated = is_elevated_access(access)
    workers = _rewrite_worker_urls(
        filter_worker_status_rows(get_all_worker_status(engine, offline_after_seconds=60))
    )
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=secret,
        ttl_seconds=entry_link_ttl_seconds(settings.stock_check_token_ttl_seconds),
        path=path,
        lan_url_key="online_sale_public_base_url",
        tailscale_url_key="online_sale_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
        branches={"HQ"},
    )
    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์ขายออนไลน์ครับ (รอ heartbeat จาก HQ)",
        }
    return branch_uri_buttons(
        title=title,
        alt_text=f"{title} — กดเปิด",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

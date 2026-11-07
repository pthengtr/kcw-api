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
from src.hq_receive.config import get_hq_receive_settings
from src.hq_receive.ui import APP
from src.jobs.hq_worker import filter_worker_status_rows
from src.jobs.heartbeat import get_all_worker_status
from src.transfer.net import rewrite_base_port

HQ_RECEIVE_COMMAND = "รับสินค้า"
HQ_RECEIVE_COMMANDS = {
    "รับสินค้า",
    "รับสินค้าเข้า",
    "รับเข้า",
    "hq receive",
    "hqreceive",
    "goods receipt",
}
HQ_RECEIVE_PORT = int(os.getenv("HQ_RECEIVE_LISTEN_PORT", "8795"))


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_HQ_RECEIVE_COMMANDS_NORM = {_normalize_cmd(c) for c in HQ_RECEIVE_COMMANDS}


def is_hq_receive_command(text: str) -> bool:
    return _normalize_cmd(text) in _HQ_RECEIVE_COMMANDS_NORM


def _rewrite_worker_hq_receive_urls(workers: list[dict]) -> list[dict]:
    env_lan = (os.getenv("HQ_RECEIVE_PUBLIC_BASE_URL") or "").strip()
    env_ts = (os.getenv("HQ_RECEIVE_TAILSCALE_BASE_URL") or "").strip()
    out = []
    for worker in workers:
        row = dict(worker)
        branch = branch_for_worker(str(row.get("worker_name") or ""))
        lan = rewrite_base_port(row.get("explorer_public_base_url"), HQ_RECEIVE_PORT) or ""
        ts = rewrite_base_port(row.get("explorer_tailscale_base_url"), HQ_RECEIVE_PORT) or ""
        if branch == "HQ":
            if env_lan:
                lan = env_lan
            if env_ts:
                ts = env_ts
        row["hq_receive_public_base_url"] = lan
        row["hq_receive_tailscale_base_url"] = ts
        out.append(row)
    return out


def handle_hq_receive_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    settings = get_hq_receive_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}

    elevated = is_elevated_access(access)
    workers = _rewrite_worker_hq_receive_urls(
        filter_worker_status_rows(get_all_worker_status(engine, offline_after_seconds=60))
    )
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=secret,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        path="/hq-receive/",
        lan_url_key="hq_receive_public_base_url",
        tailscale_url_key="hq_receive_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
        branches={"HQ"},
    )
    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์รับสินค้าเข้าออนไลน์ครับ (รอ heartbeat จาก HQ)",
        }
    return branch_uri_buttons(
        title="รับสินค้าเข้า HQ",
        alt_text="รับสินค้าเข้า HQ — กดเปิด",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

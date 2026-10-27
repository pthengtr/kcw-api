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
from src.to_bill.config import get_to_bill_settings
from src.to_bill.ui import APP
from src.transfer.net import rewrite_base_port

TO_BILL_COMMANDS = {
    "ใบเต็ม",
    "ใบกำกับ",
    "to bill",
    "tobill",
}
TO_BILL_PORT = int(os.getenv("TO_BILL_LISTEN_PORT", "8794"))


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_TO_BILL_COMMANDS_NORM = {_normalize_cmd(c) for c in TO_BILL_COMMANDS}


def is_to_bill_command(text: str) -> bool:
    return _normalize_cmd(text) in _TO_BILL_COMMANDS_NORM


def _rewrite_worker_urls(workers: list[dict]) -> list[dict]:
    env_lan = (os.getenv("TO_BILL_PUBLIC_BASE_URL") or "").strip()
    env_ts = (os.getenv("TO_BILL_TAILSCALE_BASE_URL") or "").strip()
    out = []
    for worker in workers:
        row = dict(worker)
        branch = branch_for_worker(str(row.get("worker_name") or ""))
        lan = rewrite_base_port(row.get("explorer_public_base_url"), TO_BILL_PORT) or ""
        ts = rewrite_base_port(row.get("explorer_tailscale_base_url"), TO_BILL_PORT) or ""
        if branch == "HQ":
            if env_lan:
                lan = env_lan
            if env_ts:
                ts = env_ts
        row["to_bill_public_base_url"] = lan
        row["to_bill_tailscale_base_url"] = ts
        out.append(row)
    return out


def handle_to_bill_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    settings = get_to_bill_settings()
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
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        path="/to-bill/",
        lan_url_key="to_bill_public_base_url",
        tailscale_url_key="to_bill_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
        branches={"HQ"},
    )
    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์ใบเต็มครับ (รอ heartbeat จาก HQ)",
        }
    return branch_uri_buttons(
        title="ใบเต็ม TAD",
        alt_text="ใบเต็ม TAD — กดเปิด",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

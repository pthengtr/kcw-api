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
from src.hq_po.config import get_hq_po_settings
from src.hq_po.ui import APP
from src.jobs.hq_worker import filter_worker_status_rows
from src.jobs.heartbeat import get_all_worker_status
from src.transfer.net import rewrite_base_port

HQ_PO_COMMAND = "สั่งซื้อ"
HQ_PO_COMMANDS = {
    "สั่งซื้อ",
    "สั่งซื้อhq",
    "สั่งซื้อ hq",
    "hq po",
    "hqpo",
}
HQ_PO_PORT = int(os.getenv("HQ_PO_LISTEN_PORT", "8793"))


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_HQ_PO_COMMANDS_NORM = {_normalize_cmd(c) for c in HQ_PO_COMMANDS}


def is_hq_po_command(text: str) -> bool:
    return _normalize_cmd(text) in _HQ_PO_COMMANDS_NORM


def _rewrite_worker_hq_po_urls(workers: list[dict]) -> list[dict]:
    """Fill HQ PO URLs from the explorer heartbeat. Env overrides the HQ box only."""
    env_lan = (os.getenv("HQ_PO_PUBLIC_BASE_URL") or "").strip()
    env_ts = (os.getenv("HQ_PO_TAILSCALE_BASE_URL") or "").strip()
    out = []
    for worker in workers:
        row = dict(worker)
        branch = branch_for_worker(str(row.get("worker_name") or ""))
        lan = rewrite_base_port(row.get("explorer_public_base_url"), HQ_PO_PORT) or ""
        ts = rewrite_base_port(row.get("explorer_tailscale_base_url"), HQ_PO_PORT) or ""
        if branch == "HQ":
            if env_lan:
                lan = env_lan
            if env_ts:
                ts = env_ts
        row["hq_po_public_base_url"] = lan
        row["hq_po_tailscale_base_url"] = ts
        out.append(row)
    return out


def handle_hq_po_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
) -> dict:
    settings = get_hq_po_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}

    elevated = is_elevated_access(access)
    workers = _rewrite_worker_hq_po_urls(
        filter_worker_status_rows(get_all_worker_status(engine, offline_after_seconds=60))
    )
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=secret,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        path="/hq-po/",
        lan_url_key="hq_po_public_base_url",
        tailscale_url_key="hq_po_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
        branches={"HQ"},
    )
    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์สั่งซื้อออนไลน์ครับ (รอ heartbeat จาก HQ)",
        }
    return branch_uri_buttons(
        title="สั่งซื้อ HQ",
        alt_text="สั่งซื้อ HQ — กดเปิด",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

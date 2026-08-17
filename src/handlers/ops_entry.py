from __future__ import annotations

import os
import re

from src.access.helper import can_execute
from src.bot.branch_link_buttons import branch_uri_buttons
from src.handlers.branch_tool_links import (
    collect_branch_tool_links,
    elevated_wifi_hint,
    is_elevated_access,
)
from src.jobs.heartbeat import get_all_worker_status
from src.ops.config import get_ops_settings
from src.ops.net import rewrite_base_port
from src.ops.ui import APP
from src.stock_check.auth import mint_access_token

OPS_COMMAND = "สถานะใบสั่งซื้อ"
OPS_COMMANDS = {
    "สถานะใบสั่งซื้อ",
    "ใบสั่งซื้อ",
    "ภาพรวมยอดขาย",
}
OPS_PORT = int(os.getenv("KCW_OPS_LISTEN_PORT", "8790"))


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_OPS_COMMANDS_NORM = {_normalize_cmd(c) for c in OPS_COMMANDS}


def is_ops_command(text: str) -> bool:
    return _normalize_cmd(text) in _OPS_COMMANDS_NORM


def _rewrite_worker_ops_urls(workers: list[dict]) -> list[dict]:
    out = []
    for w in workers:
        row = dict(w)
        lan = rewrite_base_port(row.get("explorer_public_base_url"), OPS_PORT)
        ts = rewrite_base_port(row.get("explorer_tailscale_base_url"), OPS_PORT)
        env_lan = (os.getenv("KCW_OPS_PUBLIC_BASE_URL") or "").strip()
        env_ts = (os.getenv("KCW_OPS_TAILSCALE_BASE_URL") or "").strip()
        row["ops_public_base_url"] = env_lan or lan
        row["ops_tailscale_base_url"] = env_ts or ts
        out.append(row)
    return out


def handle_ops_command(
    engine,
    *,
    line_user_id: str,
    display_name: str | None = None,
    access: dict | None = None,
    user_text: str | None = None,
) -> dict:
    group = ((access or {}).get("access_group") or "").strip().lower()
    if not can_execute(group, OPS_COMMAND) and not can_execute(group, "ภาพรวมยอดขาย"):
        return {"type": "text", "text": "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"}

    settings = get_ops_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}

    elevated = is_elevated_access(access)
    workers = _rewrite_worker_ops_urls(
        get_all_worker_status(engine, offline_after_seconds=60)
    )
    want_bi = _normalize_cmd(user_text or "") == _normalize_cmd("ภาพรวมยอดขาย")
    path = "/ops/bi/" if want_bi else "/ops/"
    title = "ภาพรวมยอดขาย" if want_bi else "ใบสั่งซื้อ"
    links = collect_branch_tool_links(
        workers,
        line_user_id=line_user_id,
        display_name=display_name,
        secret=secret,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        path=path,
        lan_url_key="ops_public_base_url",
        tailscale_url_key="ops_tailscale_base_url",
        include_tailscale=elevated,
        mint_app=APP,
    )
    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์ใบสั่งซื้อออนไลน์ครับ (รอ heartbeat จาก HQ)",
        }
    return branch_uri_buttons(
        title=title,
        alt_text=f"{title} — กดเปิด (ข้อมูลสดจาก PARTS9)",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated, allow_tailscale_copy=True),
    )

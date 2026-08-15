from __future__ import annotations

import re

from src.bot.branch_link_buttons import branch_uri_buttons
from src.handlers.branch_tool_links import (
    collect_branch_tool_links,
    elevated_wifi_hint,
    is_elevated_access,
)
from src.jobs.heartbeat import get_all_worker_status
from src.stock_check.auth import build_entry_url, mint_access_token
from src.stock_check.config import get_stock_check_settings


# Canonical phrases (after _normalize_cmd). Add readable forms here; spelling
# variants like เช็ก/สตอก are folded by normalization.
STOCK_CHECK_COMMANDS = {
    "เช็คสต็อก",
    "เช็คของ",
    "เช็คสินค้า",
    "เช็คสต็อค",
    "ตรวจนับสต็อก",
    "ตรวจนับ",
    "ตรวจนับของ",
    "ตรวจนับสินค้า",
    "นับสต็อก",
    "นับของ",
    "นับสินค้า",
    "check stock",
    "stock check",
    "checkstock",
    "stockcheck",
    "stock audit",
    "stockaudit",
}


def _normalize_cmd(text: str) -> str:
    """Fold common Thai/English typing variants into a comparable key."""
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", "", t)
    # check: เช็ก (ไม้เอก) → เช็ค (ไม้โท)
    t = t.replace("เช็ก", "เช็ค")
    # stock: tone / missing-vowel variants → สต็อก
    t = t.replace("สต๊อก", "สต็อก")
    t = t.replace("สต็อค", "สต็อก")
    t = t.replace("สตอค", "สต็อก")
    t = t.replace("สตอก", "สต็อก")
    return t


_STOCK_CHECK_COMMANDS_NORM = {_normalize_cmd(c) for c in STOCK_CHECK_COMMANDS}


def is_stock_check_command(text: str) -> bool:
    return _normalize_cmd(text) in _STOCK_CHECK_COMMANDS_NORM


def _branch_for_worker(worker_name: str) -> str | None:
    from src.handlers.branch_tool_links import branch_for_worker

    return branch_for_worker(worker_name)


def handle_stock_check_command(
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
        path="/stock-check/",
        lan_url_key="public_base_url",
        tailscale_url_key="tailscale_public_base_url",
        include_tailscale=elevated,
    )

    # Fallback: single configured local URL for this process branch only
    if not links and settings.stock_check_enabled:
        branch = settings.stock_check_branch
        token = mint_access_token(
            secret=settings.stock_check_token_secret,
            line_user_id=line_user_id,
            display_name=display_name or line_user_id,
            branch=branch,
            ttl_seconds=settings.stock_check_token_ttl_seconds,
        )
        url = build_entry_url(settings.resolved_public_base_url, token)
        links.append((branch, url, "local"))

    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์ตรวจนับสต็อกออนไลน์ครับ (รอ HQ/SYP heartbeat)",
        }

    return branch_uri_buttons(
        title="ตรวจนับสต็อก",
        alt_text="ตรวจนับสต็อก — กดเลือกสาขา",
        links=links,
        wifi_hint=elevated_wifi_hint(elevated),
    )

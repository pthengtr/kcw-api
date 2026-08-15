from __future__ import annotations

import re

from src.bot.branch_link_buttons import branch_uri_buttons
from src.jobs.heartbeat import get_all_worker_status
from src.jobs.hq_worker import hq_worker_sort_key
from src.handlers.stock_check_entry import _branch_for_worker
from src.parts9_explorer.config import get_explorer_settings
from src.parts9_explorer.ui import APP
from src.stock_check.auth import build_entry_url, mint_access_token

EXPLORER_COMMANDS = {"parts9", "part9", "ค้นหา", "สำรวจ", "สำรวจสินค้า", "explorer"}


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_EXPLORER_COMMANDS_NORM = {_normalize_cmd(c) for c in EXPLORER_COMMANDS}


def is_explorer_command(text: str) -> bool:
    return _normalize_cmd(text) in _EXPLORER_COMMANDS_NORM


def handle_explorer_command(engine, *, line_user_id: str, display_name: str | None = None) -> dict:
    settings = get_explorer_settings()
    secret = settings.token_secret
    if not secret:
        return {"type": "text", "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ"}
    workers = sorted(get_all_worker_status(engine, offline_after_seconds=60),
                     key=lambda w: hq_worker_sort_key(str(w.get("worker_name") or "")))
    links = []
    seen = set()
    for w in workers:
        branch = _branch_for_worker(str(w.get("worker_name") or ""))
        if not branch or branch in seen:
            continue
        base = (w.get("explorer_public_base_url") or "").strip().rstrip("/")
        online = w.get("online_status") == "online"
        if base:
            try:
                token = mint_access_token(
                    secret=secret, line_user_id=line_user_id,
                    display_name=display_name or line_user_id, branch=branch,
                    ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400), app=APP,
                )
                url = build_entry_url(base, token, path="/parts9/")
            except Exception:
                url = base + "/parts9/"
            links.append((branch, url if online else "", "online" if online else "offline"))
            seen.add(branch)
    if not links:
        return {"type": "text", "text": "ยังไม่พบเซิร์ฟเวอร์ PARTS9 explorer ออนไลน์ครับ (รอ heartbeat)"}
    return branch_uri_buttons(
        title="PARTS9 explorer",
        alt_text="PARTS9 explorer — กดเปิด HQ หรือ SYP",
        links=links,
        wifi_hint="กดปุ่มสาขา — ต้องอยู่ Wi‑Fi สาขา (หรือ Tailscale)",
    )

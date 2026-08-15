from __future__ import annotations

import re

from src.jobs.heartbeat import get_all_worker_status
from src.jobs.hq_worker import hq_worker_sort_key
from src.stock_check.auth import build_entry_url, mint_access_token
from src.stock_check.config import get_stock_check_settings
from src.handlers.stock_check_entry import _branch_for_worker


COMPANION_COMMANDS = {
    "ไทเกอร์",
    "ไทเกอร์เพย์",
    "tiger",
    "tiger pay",
    "tigerpay",
    "companion",
    "เก็บเงิน",
    "รับเงิน",
    "ตู้เงิน",
}


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"\s+", "", t)
    return t


_COMPANION_COMMANDS_NORM = {_normalize_cmd(c) for c in COMPANION_COMMANDS}


def is_companion_command(text: str) -> bool:
    return _normalize_cmd(text) in _COMPANION_COMMANDS_NORM


def handle_companion_command(engine, *, line_user_id: str, display_name: str | None = None) -> dict:
    settings = get_stock_check_settings()
    if not settings.stock_check_token_secret:
        return {
            "type": "text",
            "text": "ยังไม่ได้ตั้ง STOCK_CHECK_TOKEN_SECRET บนเซิร์ฟเวอร์ครับ",
        }

    workers = get_all_worker_status(engine, offline_after_seconds=60)
    workers = sorted(
        workers,
        key=lambda w: hq_worker_sort_key(str(w.get("worker_name") or "")),
    )
    links: list[tuple[str, str, str]] = []
    seen_branch: set[str] = set()
    for w in workers:
        branch = _branch_for_worker(str(w.get("worker_name") or ""))
        if not branch or branch in seen_branch:
            continue
        base = (w.get("companion_public_base_url") or "").strip().rstrip("/")
        online = w.get("online_status") == "online"
        if base:
            try:
                token = mint_access_token(
                    secret=settings.stock_check_token_secret,
                    line_user_id=line_user_id,
                    display_name=display_name or line_user_id,
                    branch=branch,
                    ttl_seconds=settings.stock_check_token_ttl_seconds,
                    app="companion",
                )
                url = build_entry_url(base, token, path="/companion/")
            except Exception:  # noqa: BLE001
                url = base + "/companion/"
            links.append((branch, url if online else "", "online" if online else "offline"))
            seen_branch.add(branch)

    if not links:
        return {
            "type": "text",
            "text": "ยังไม่พบเซิร์ฟเวอร์ Tiger Pay ออนไลน์ครับ (รอ HQ/SYP heartbeat)",
        }

    lines = ["Tiger Pay — เปิดลิงก์สาขาที่ต้องการ (ต้องอยู่ Wi‑Fi สาขา):\n"]
    label = {"HQ": "สำนักงานใหญ่ (HQ)", "SYP": "สี่แยกพัฒนา (SYP)"}
    for branch, url, status in links:
        name = label.get(branch, branch)
        if status == "offline" or not url:
            lines.append(f"• {name}: ออฟไลน์")
        else:
            lines.append(f"• {name}:\n{url}")
    return {"type": "text", "text": "\n".join(lines)}

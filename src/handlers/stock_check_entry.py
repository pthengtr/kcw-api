from __future__ import annotations

import re

from src.stock_check.auth import build_entry_url, mint_access_token
from src.stock_check.config import get_stock_check_settings
from src.jobs.heartbeat import get_all_worker_status
from src.jobs.hq_worker import hq_worker_sort_key


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
    name = (worker_name or "").upper()
    if name.startswith("HQ"):
        return "HQ"
    if name.startswith("SYP"):
        return "SYP"
    return None


def handle_stock_check_command(engine, *, line_user_id: str, display_name: str | None = None) -> dict:
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
    # Prefer heartbeat public_base_url when present
    links: list[tuple[str, str, str]] = []  # branch, url, status
    seen_branch: set[str] = set()
    for w in workers:
        branch = _branch_for_worker(str(w.get("worker_name") or ""))
        if not branch or branch in seen_branch:
            continue
        base = (w.get("public_base_url") or "").strip().rstrip("/")
        online = w.get("online_status") == "online"
        if base:
            try:
                token = mint_access_token(
                    secret=settings.stock_check_token_secret,
                    line_user_id=line_user_id,
                    display_name=display_name or line_user_id,
                    branch=branch,
                    ttl_seconds=settings.stock_check_token_ttl_seconds,
                )
                url = build_entry_url(base, token)
            except Exception:  # noqa: BLE001
                url = base + "/stock-check/"
            links.append((branch, url if online else "", "online" if online else "offline"))
            seen_branch.add(branch)

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

    lines = ["ตรวจนับสต็อก — เปิดลิงก์สาขาที่ต้องการ (ต้องอยู่ Wi‑Fi สาขา):\n"]
    label = {"HQ": "สำนักงานใหญ่ (HQ)", "SYP": "สี่แยกพัฒนา (SYP)"}
    for branch, url, status in links:
        name = label.get(branch, branch)
        if status == "offline" or not url:
            lines.append(f"• {name}: ออฟไลน์")
        else:
            lines.append(f"• {name}:\n{url}")
    return {"type": "text", "text": "\n".join(lines)}

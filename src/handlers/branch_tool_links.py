"""Shared HQ/SYP entry-link collection for stock-check / companion / explorer."""

from __future__ import annotations

from typing import Any

from src.jobs.hq_worker import hq_worker_sort_key
from src.stock_check.auth import build_entry_url, mint_access_token

ELEVATED_ACCESS_GROUPS = frozenset({"admin", "exec"})

TAILSCALE_BUTTON_LABEL = {
    "HQ": "สนญ · Tailscale",
    "SYP": "สี่แยก · Tailscale",
}

# branch, url, status[, label]
BranchLink = tuple[str, str, str] | tuple[str, str, str, str]


def branch_for_worker(worker_name: str) -> str | None:
    name = (worker_name or "").upper()
    if name.startswith("HQ"):
        return "HQ"
    if name.startswith("SYP"):
        return "SYP"
    return None


def is_elevated_access(access: dict | None) -> bool:
    group = ((access or {}).get("access_group") or "").strip().lower()
    return group in ELEVATED_ACCESS_GROUPS


def collect_branch_tool_links(
    workers: list[dict],
    *,
    line_user_id: str,
    display_name: str | None,
    secret: str,
    ttl_seconds: int,
    path: str,
    lan_url_key: str,
    tailscale_url_key: str,
    include_tailscale: bool,
    mint_app: str | None = None,
    mint_kwargs: dict[str, Any] | None = None,
) -> list[BranchLink]:
    """
    Build Flex link rows from worker heartbeats.

    Regular users get LAN links only. admin/exec also get Tailscale links when
    the worker advertised a Tailscale base URL.
    """
    workers = sorted(
        workers,
        key=lambda w: hq_worker_sort_key(str(w.get("worker_name") or "")),
    )
    links: list[BranchLink] = []
    seen_branch: set[str] = set()
    extra = dict(mint_kwargs or {})
    if mint_app:
        extra["app"] = mint_app

    for w in workers:
        branch = branch_for_worker(str(w.get("worker_name") or ""))
        if not branch or branch in seen_branch:
            continue
        online = w.get("online_status") == "online"
        lan_base = (w.get(lan_url_key) or "").strip().rstrip("/")
        if not lan_base:
            continue

        def _mint(base: str, *, branch_code: str = branch) -> str:
            try:
                token = mint_access_token(
                    secret=secret,
                    line_user_id=line_user_id,
                    display_name=display_name or line_user_id,
                    branch=branch_code,
                    ttl_seconds=ttl_seconds,
                    **extra,
                )
                return build_entry_url(base, token, path=path)
            except Exception:  # noqa: BLE001
                prefix = path if path.startswith("/") else f"/{path}"
                if not prefix.endswith("/"):
                    prefix += "/"
                return base + prefix

        status = "online" if online else "offline"
        links.append((branch, _mint(lan_base) if online else "", status))

        if include_tailscale:
            ts_base = (w.get(tailscale_url_key) or "").strip().rstrip("/")
            if ts_base and ts_base != lan_base and online:
                label = TAILSCALE_BUTTON_LABEL.get(branch, f"{branch} · Tailscale")
                links.append((branch, _mint(ts_base), "online", label))

        seen_branch.add(branch)

    return links


def elevated_wifi_hint(include_tailscale: bool, *, allow_tailscale_copy: bool = False) -> str:
    if include_tailscale:
        return "กดชื่อสาขาเพื่อเปิด — Wi‑Fi สาขา หรือ Tailscale"
    if allow_tailscale_copy:
        return "กดชื่อสาขาเพื่อเปิด — ต้องอยู่ Wi‑Fi สาขา (หรือ Tailscale)"
    return "กดชื่อสาขาเพื่อเปิด — ต้องอยู่ Wi‑Fi สาขานั้น"

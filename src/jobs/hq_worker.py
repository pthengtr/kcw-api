"""HQ worker preference: Linux box first when its heartbeat is live."""

from __future__ import annotations

from src.jobs.heartbeat import get_all_worker_status

HQ_WORKER_CANDIDATES = ("HQ-UBUNTU-SERVER", "HQ-PC")
SYP_WORKER_NAME = "SYP-PC"


def online_worker_names(engine, *, offline_after_seconds: int = 30) -> set[str]:
    rows = get_all_worker_status(engine, offline_after_seconds=offline_after_seconds)
    return {str(r["worker_name"]) for r in rows if r.get("online_status") == "online"}


def pick_hq_worker(
    engine,
    allowed_workers: set[str] | None = None,
    *,
    offline_after_seconds: int = 30,
) -> str | None:
    """Return the preferred live HQ worker, or None if none are online."""
    online = online_worker_names(engine, offline_after_seconds=offline_after_seconds)
    if allowed_workers is not None:
        online &= allowed_workers
    for name in HQ_WORKER_CANDIDATES:
        if name in online:
            return name
    return None


def hq_worker_sort_key(worker_name: str) -> tuple[int, str]:
    """Lower is better. Unknown HQ* names sort after known candidates."""
    name = worker_name or ""
    try:
        return (HQ_WORKER_CANDIDATES.index(name), name)
    except ValueError:
        return (len(HQ_WORKER_CANDIDATES), name)

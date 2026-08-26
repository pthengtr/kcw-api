"""Site worker preference: Linux boxes first when their heartbeats are live."""

from __future__ import annotations

from src.jobs.heartbeat import get_all_worker_status

HQ_WORKER_CANDIDATES = ("HQ-UBUNTU-SERVER", "HQ-PC")
SYP_WORKER_CANDIDATES = ("SYP-UBUNTU-SERVER", "SYP-PC")
# Retired Windows boxes — hide from operator-facing worker status in LINE.
LEGACY_WORKER_NAMES = frozenset({"HQ-PC", "SYP-PC"})
# Back-compat alias — prefer pick_syp_worker() instead of hard-coding.
SYP_WORKER_NAME = SYP_WORKER_CANDIDATES[-1]


def filter_worker_status_rows(rows: list[dict]) -> list[dict]:
    """Drop retired Windows workers from chatbot status lists."""
    return [r for r in rows if r.get("worker_name") not in LEGACY_WORKER_NAMES]


def online_worker_names(engine, *, offline_after_seconds: int = 30) -> set[str]:
    rows = get_all_worker_status(engine, offline_after_seconds=offline_after_seconds)
    return {str(r["worker_name"]) for r in rows if r.get("online_status") == "online"}


def _pick_worker(
    candidates: tuple[str, ...],
    engine,
    allowed_workers: set[str] | None = None,
    *,
    offline_after_seconds: int = 30,
) -> str | None:
    online = online_worker_names(engine, offline_after_seconds=offline_after_seconds)
    if allowed_workers is not None:
        online &= allowed_workers
    for name in candidates:
        if name in online:
            return name
    return None


def pick_hq_worker(
    engine,
    allowed_workers: set[str] | None = None,
    *,
    offline_after_seconds: int = 30,
) -> str | None:
    """Return the preferred live HQ worker, or None if none are online."""
    return _pick_worker(
        HQ_WORKER_CANDIDATES,
        engine,
        allowed_workers=allowed_workers,
        offline_after_seconds=offline_after_seconds,
    )


def pick_syp_worker(
    engine,
    allowed_workers: set[str] | None = None,
    *,
    offline_after_seconds: int = 30,
) -> str | None:
    """Return the preferred live SYP worker, or None if none are online."""
    return _pick_worker(
        SYP_WORKER_CANDIDATES,
        engine,
        allowed_workers=allowed_workers,
        offline_after_seconds=offline_after_seconds,
    )


def worker_sort_key(worker_name: str) -> tuple[int, int, str]:
    """Lower is better. Ubuntu Linux boxes beat Windows PCs within each site."""
    name = worker_name or ""
    upper = name.upper()
    if upper.startswith("HQ"):
        site_rank = 0
        candidates = HQ_WORKER_CANDIDATES
    elif upper.startswith("SYP"):
        site_rank = 1
        candidates = SYP_WORKER_CANDIDATES
    else:
        return (2, 99, name)
    try:
        return (site_rank, candidates.index(name), name)
    except ValueError:
        return (site_rank, len(candidates), name)


def hq_worker_sort_key(worker_name: str) -> tuple[int, str]:
    """Lower is better. Unknown HQ* names sort after known candidates."""
    site, rank, name = worker_sort_key(worker_name)
    if site == 0:
        return (rank, name)
    return (len(HQ_WORKER_CANDIDATES), name)

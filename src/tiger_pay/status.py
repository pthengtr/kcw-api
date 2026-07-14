ACTIVE_STATUSES = frozenset(
    {"sending", "pending", "paying", "changing", "cancelling"}
)
TERMINAL_STATUSES = frozenset({"success", "cancelled", "failed"})
KNOWN_STATUSES = frozenset(
    {
        "ready",
        "sending",
        "pending",
        "paying",
        "changing",
        "cancelling",
        "cancelled",
        "success",
        "failed",
        "unknown",
    }
)

_RAW_STATUS_ALIASES = {
    "paid": "success",
    "complete": "success",
    "completed": "success",
    "cancel": "cancelled",
    "canceled": "cancelled",
    "fail": "failed",
    "error": "failed",
}


def normalize_status(raw_status: str | None) -> str:
    if raw_status is None:
        return "unknown"

    cleaned = raw_status.strip().lower()
    if not cleaned:
        return "unknown"

    mapped = _RAW_STATUS_ALIASES.get(cleaned, cleaned)
    if mapped in KNOWN_STATUSES:
        return mapped
    return "unknown"


def is_active_status(status: str) -> bool:
    return status in ACTIVE_STATUSES


def is_terminal_status(status: str) -> bool:
    return status in TERMINAL_STATUSES

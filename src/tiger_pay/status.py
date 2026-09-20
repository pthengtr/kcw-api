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
    # Device uses "change" while dispensing overpayment change; keep polling.
    "change": "changing",
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


def can_replace_status(current: str | None, incoming: str | None) -> bool:
    """Terminal companion statuses are sticky.

    Late poll/webhook rows must not move ``success`` / ``cancelled`` / ``failed``
    back to an active state (that unlocked a second payment on the same bill).
    Same-status refresh is allowed so ids / timestamps can still update.
    """
    current_n = normalize_status(current)
    incoming_n = normalize_status(incoming)
    if current_n not in TERMINAL_STATUSES:
        return True
    return incoming_n == current_n

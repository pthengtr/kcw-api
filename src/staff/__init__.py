"""Shared staff legal-name registry (LINE user id → full name + nickname)."""

from src.staff.profiles import (
    SYSTEM_LINE_USER_IDS,
    format_issuer_label,
    get_staff_profile,
    issuer_label_for_actor,
    require_staff_mapping,
)

__all__ = [
    "SYSTEM_LINE_USER_IDS",
    "format_issuer_label",
    "get_staff_profile",
    "issuer_label_for_actor",
    "require_staff_mapping",
]

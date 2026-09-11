from __future__ import annotations

from typing import Any, TypedDict


class SubstituteError(Exception):
    """Base error for substitute catalog operations."""


class BcodeConflictError(SubstituteError):
    """BCODE is already a member of another group (v1: one group per SKU)."""

    def __init__(self, bcode: str, existing_group_id: str):
        self.bcode = bcode
        self.existing_group_id = existing_group_id
        super().__init__(
            f"bcode {bcode} already in group {existing_group_id}"
        )


class NotFoundError(SubstituteError):
    def __init__(self, what: str):
        self.what = what
        super().__init__(what)


class UnknownBcodeError(SubstituteError):
    """BCODE not found in ICMAS on HQ or SYP."""

    def __init__(self, bcode: str):
        self.bcode = bcode
        super().__init__(f"bcode {bcode} not found in ICMAS (HQ/SYP)")


class MemberDict(TypedDict, total=False):
    group_id: str
    bcode: str
    sort_rank: int
    note: str | None


class GroupDict(TypedDict, total=False):
    group_id: str
    name: str | None
    note: str | None
    created_at: str | None
    updated_at: str | None
    created_by: str | None
    members: list[MemberDict]


def member_payload(
    bcode: str,
    *,
    sort_rank: int = 0,
    note: str | None = None,
) -> dict[str, Any]:
    return {
        "bcode": (bcode or "").strip(),
        "sort_rank": int(sort_rank or 0),
        "note": note,
    }

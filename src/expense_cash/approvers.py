"""Expense-cash approver roster.

Named roster users keep their existing access_group for other ops commands.
Expense approval is a separate gate: either their LINE user id is on this
roster, or ops.line_access.access_group = cash_approver.
"""

from __future__ import annotations

from typing import Any

# nick → LINE user id (ops.staff_profiles / ops.line_access)
PEUNG_LINE_USER_ID = "U7ad4da99b4438917dbe13684f2d9aafb"
PHU_LINE_USER_ID = "U3357ce0387b5355980d710e3f9feed0e"
ICE_LINE_USER_ID = "Ua994bb2f6f93dd003276d6b17196b6c1"
MAY_LINE_USER_ID = "U88f0e18f1d4bf865eb360db0e5f7c839"
CARTOON_LINE_USER_ID = "Ua542a4e8651997f5d051cbe60b80ad63"
JEAB_LINE_USER_ID = "U7fa69960556c92b529db58541ed7b1e2"

CASH_APPROVER_GROUP = "cash_approver"

CASH_APPROVER_LINE_USER_IDS = frozenset(
    {
        PEUNG_LINE_USER_ID,
        PHU_LINE_USER_ID,
        ICE_LINE_USER_ID,
        MAY_LINE_USER_ID,
        CARTOON_LINE_USER_ID,
        JEAB_LINE_USER_ID,
    }
)


def is_cash_approver(access: dict[str, Any] | None) -> bool:
    access = access or {}
    if access.get("is_allowed") is False:
        return False
    uid = str(access.get("line_user_id") or "").strip()
    if uid and uid in CASH_APPROVER_LINE_USER_IDS:
        return True
    group = str(access.get("access_group") or "").strip().lower()
    return group == CASH_APPROVER_GROUP

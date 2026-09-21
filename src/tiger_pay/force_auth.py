"""Admin / Tailscale gate for Companion force-complete."""

from __future__ import annotations

from typing import Any

from sqlalchemy.engine import Engine

from src.access.helper import get_line_access
from src.handlers.branch_tool_links import is_elevated_access
from src.tiger_pay.submitter import TAILSCALE_USER_ID


def can_force_complete(engine: Engine, identity: Any | None) -> bool:
    """True for Tailscale sessions or elevated LINE users (admin/exec)."""
    if identity is None:
        return False
    uid = str(getattr(identity, "line_user_id", None) or "").strip()
    if not uid:
        return False
    if uid == TAILSCALE_USER_ID:
        return True
    access = get_line_access(engine, uid)
    return is_elevated_access(access)

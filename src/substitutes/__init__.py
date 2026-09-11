"""Product substitutes — live suggestions + confirmed catalog groups."""

from src.substitutes.enrich import enrich_group, enrich_member_rows, fetch_dual_stock
from src.substitutes.models import BcodeConflictError, SubstituteError, UnknownBcodeError
from src.substitutes.peers import (
    attach_live_suggestions,
    attach_substitute_hints,
    needs_substitute_hint,
)
from src.substitutes.suggest import suggest_for_bcode, suggest_for_bcodes

__all__ = [
    "BcodeConflictError",
    "SubstituteError",
    "UnknownBcodeError",
    "attach_live_suggestions",
    "attach_substitute_hints",
    "enrich_group",
    "enrich_member_rows",
    "fetch_dual_stock",
    "needs_substitute_hint",
    "suggest_for_bcode",
    "suggest_for_bcodes",
]
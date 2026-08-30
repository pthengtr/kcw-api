from __future__ import annotations

from typing import Literal

Branch = Literal["HQ", "SYP"]
Direction = Literal["to_syp", "to_hq"]


def branches_for_direction(direction: str) -> tuple[Branch, Branch]:
    """Requester is always to_branch (needs stock)."""
    d = (direction or "to_syp").strip().lower()
    if d == "to_hq":
        return "SYP", "HQ"
    return "HQ", "SYP"


def ship_billno_prefix(*, from_branch: str) -> str:
    return "3TF" if (from_branch or "").upper() == "SYP" else "TF"


def receive_billno_prefix(*, from_branch: str, to_branch: str) -> str:
    fb = (from_branch or "").upper()
    tb = (to_branch or "").upper()
    if fb == "SYP" and tb == "HQ":
        return "3TF"
    return "TF"


def site_matches_branch(site: str, branch: str) -> bool:
    return (site or "").upper() == (branch or "").upper()


def can_submit_at_site(site: str, to_branch: str) -> bool:
    return site_matches_branch(site, to_branch)


def can_prepare_at_site(site: str, from_branch: str) -> bool:
    return site_matches_branch(site, from_branch)


def can_receive_at_site(site: str, to_branch: str) -> bool:
    return site_matches_branch(site, to_branch)


def direction_label(from_branch: str, to_branch: str) -> str:
    return f"{(from_branch or '').upper()} → {(to_branch or '').upper()}"

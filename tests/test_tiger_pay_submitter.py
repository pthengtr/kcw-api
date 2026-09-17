from __future__ import annotations

from types import SimpleNamespace

from src.tiger_pay.submitter import (
    TAILSCALE_DISPLAY_NAME,
    TAILSCALE_USER_ID,
    normalize_submitter,
    submitter_from_identity,
    submitter_payload,
)


def test_normalize_submitter_line_user():
    by, name = normalize_submitter(line_user_id="U123", display_name="Ann")
    assert by == "U123"
    assert name == "Ann"


def test_normalize_submitter_tailscale_account():
    by, name = normalize_submitter(line_user_id="tailscale", display_name="tailnet")
    assert by == TAILSCALE_USER_ID
    assert name == TAILSCALE_DISPLAY_NAME


def test_normalize_submitter_empty():
    assert normalize_submitter(line_user_id=None, display_name="x") == (None, None)
    assert normalize_submitter(line_user_id="  ", display_name="x") == (None, None)


def test_submitter_from_identity_and_payload():
    ident = SimpleNamespace(line_user_id="tailscale", display_name="tailnet")
    by, name = submitter_from_identity(ident)
    assert submitter_payload(submitted_by=by, submitted_by_name=name) == {
        "submitted_by": "tailscale",
        "submitted_by_name": "Tailscale account",
    }

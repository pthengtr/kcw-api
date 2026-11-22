from __future__ import annotations

from typing import Any


def build_agent_prompt(
    ticket: dict[str, Any],
    *,
    attachment_paths: list[str],
    reopen_comment: str | None = None,
) -> str:
    meta = ticket.get("target_meta") or {}
    if isinstance(meta, str):
        import json

        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}

    code_roots = meta.get("codeRoots") or meta.get("code_roots") or []
    notes = meta.get("notes") or ""
    repo = meta.get("repo") or ticket.get("target_source") or "unknown"
    prior_pr = ticket.get("pr_url") or ""

    attach_block = "(none)"
    if attachment_paths:
        lines = "\n".join(f"- {p}" for p in attachment_paths)
        attach_block = (
            "Open and analyze these local files before coding "
            "(screenshots, design refs, example output docs):\n"
            f"{lines}"
        )

    reopen_block = "(none)"
    if reopen_comment or prior_pr:
        reopen_block = (
            f"Prior PR: {prior_pr or '(none)'}\n"
            f"User reopen reason: {reopen_comment or '(none)'}\n"
            "Fix what was still wrong; keep the smallest correct change."
        )

    roots = ", ".join(code_roots) if code_roots else "(use target label to locate code)"

    return f"""You are fixing a support ticket in repo {repo} only.
Do not modify other repositories. Work only in this git working tree.

Target: {ticket.get('target_label')} ({ticket.get('target_source')}/{ticket.get('target_id')})
Kind: {ticket.get('kind')}
Primary code areas (start here): {roots}
Notes: {notes or '(none)'}

User request:
{ticket.get('title') or ''}
{ticket.get('body') or ''}

Attachments (local files — open and analyze before coding):
{attach_block}

Reopen context (if any):
{reopen_block}

Constraints:
- Stay inside this target's code areas unless a tiny shared dependency is required.
- Smallest correct change; match attached design/example output when provided.
- Leave a clear commit message describing the fix.
- Prefer editing existing files over large refactors.
"""

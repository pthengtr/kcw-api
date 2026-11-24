from __future__ import annotations

from typing import Any


def _ticket_meta(ticket: dict[str, Any]) -> dict[str, Any]:
    meta = ticket.get("target_meta") or {}
    if isinstance(meta, str):
        import json

        try:
            meta = json.loads(meta)
        except Exception:
            meta = {}
    return meta if isinstance(meta, dict) else {}


def _attach_block(attachment_paths: list[str], *, for_coding: bool) -> str:
    if not attachment_paths:
        return "(none)"
    lines = "\n".join(f"- {p}" for p in attachment_paths)
    if for_coding:
        return (
            "Open and analyze these local files before coding "
            "(screenshots, design refs, example output docs):\n"
            f"{lines}"
        )
    return (
        "Open and analyze these local files if they help answer the question:\n"
        f"{lines}"
    )


def build_data_query_prompt(
    ticket: dict[str, Any],
    *,
    attachment_paths: list[str],
    reopen_comment: str | None = None,
) -> str:
    meta = _ticket_meta(ticket)
    notes = meta.get("notes") or ""
    roots = meta.get("codeRoots") or meta.get("code_roots") or []
    roots_txt = ", ".join(roots) if roots else "(use domain notes)"
    reopen_block = reopen_comment or "(none)"
    target_id = str(ticket.get("target_id") or "all")

    domain_hints = {
        "all": (
            "Use any of: Supabase (kcw), HQ KSS PARTS9, SYP kss-pc PARTS9, "
            "and kcw-analytic Google Drive outputs."
        ),
        "supabase": "Prefer Supabase Postgres / Storage / RPCs for project kcw.",
        "kss": "Prefer HQ SQL Server PARTS9 via KSS (PARTS9_HQ_* / python_reader).",
        "kss-pc": "Prefer SYP SQL Server PARTS9 via kss-pc (PARTS9_SYP_*).",
        "analytics-gdrive": (
            "Prefer mounted analytic tree under "
            "/home/hqadmin/mnt/gdrive/KCW-Data/kcw_analytics "
            "(01_raw, 03_curated, 04_outputs) and ~/projects/kcw-analytic."
        ),
    }
    domain = domain_hints.get(target_id, domain_hints["all"])

    return f"""You are the HQ data agent on hq-ubuntu-server answering a staff data question.
This is NOT a code-fix ticket. Do not open PRs or edit application repos unless
a tiny throwaway script in /tmp is required to query data.

Domain focus: {ticket.get('target_label')} ({ticket.get('target_source')}/{target_id})
Domain guidance: {domain}
Path hints: {roots_txt}
Notes: {notes or '(none)'}

Available data on this machine (use what is needed):
- Supabase project kcw (credentials in ~/projects/kcw-api/.env and ~/projects/kcw-analytic/.env)
- HQ KSS PARTS9 SQL Server (PARTS9_HQ_*)
- SYP kss-pc PARTS9 SQL Server (PARTS9_SYP_*)
- kcw-analytic results on Google Drive mount:
  /home/hqadmin/mnt/gdrive/KCW-Data/kcw_analytics
- Helper code / notebooks: ~/projects/kcw-analytic

User question:
{ticket.get('title') or ''}
{ticket.get('body') or ''}

Attachments:
{_attach_block(attachment_paths, for_coding=False)}

Follow-up / reopen context:
{reopen_block}

Response rules:
- Investigate with shell/SQL/files as needed; prefer read-only queries.
- Answer clearly with numbers, tables, or file paths the user can verify.
- Cite which source you used (Supabase / KSS / kss-pc / GDrive path).
- If something is inaccessible, say exactly what failed.
- Do not invent data. Do not modify production tables unless the user explicitly asked
  for a write and it is safe/reversible.
- Put the final answer in plain text at the end (this becomes the ticket reply).

Filesystem safety (mandatory — rclone FUSE under ~/mnt hangs process trees):
- NEVER run find/fd/locate/rg starting at /, /home, /home/hqadmin, or /home/hqadmin/mnt.
- Scope file searches to a concrete subdirectory you need
  (e.g. /home/hqadmin/mnt/gdrive/KCW-Data/kcw_analytics/04_outputs or ~/projects/kcw-analytic).
- Prefer known paths and SQL over recursive filesystem crawls.
"""


def build_agent_prompt(
    ticket: dict[str, Any],
    *,
    attachment_paths: list[str],
    reopen_comment: str | None = None,
) -> str:
    if ticket.get("kind") == "data_query":
        return build_data_query_prompt(
            ticket,
            attachment_paths=attachment_paths,
            reopen_comment=reopen_comment,
        )

    meta = _ticket_meta(ticket)

    code_roots = meta.get("codeRoots") or meta.get("code_roots") or []
    notes = meta.get("notes") or ""
    repo = meta.get("repo") or ticket.get("target_source") or "unknown"
    prior_pr = ticket.get("pr_url") or ""

    attach_block = _attach_block(attachment_paths, for_coding=True)

    reopen_block = "(none)"
    if reopen_comment or prior_pr:
        reopen_block = (
            f"Prior PR: {prior_pr or '(none)'}\n"
            f"User reopen reason: {reopen_comment or '(none)'}\n"
            "Fix what was still wrong; keep the smallest correct change."
        )

    roots = ", ".join(code_roots) if code_roots else "(use target label to locate code)"

    pytest_hint = {
        "kcw-api": (
            "Tests: /home/hqadmin/projects/kcw-api/.venv/bin/python -m pytest "
            "<path> -q   (worktree has no local .venv — do NOT search for pytest)."
        ),
        "kcw-v2": (
            "Tests: from this worktree run  npm test  /  npx vitest  / project scripts "
            "as documented; do NOT find binaries under /home/hqadmin."
        ),
    }.get(str(repo), "Use project-local test runners only; never search $HOME for binaries.")

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
- Never add/commit `.tools/`, `.venv/`, `node_modules/`, binaries, or any file near GitHub's 100MB limit.
- {pytest_hint}

Filesystem safety (mandatory — rclone FUSE under ~/mnt hangs process trees):
- NEVER run find/fd/locate starting at /, /home, /home/hqadmin, or /home/hqadmin/mnt.
- NEVER recursively scan /home/hqadmin/mnt (gdrive/kss mounts).
- Stay inside this worktree (+ listed attachment paths). Do not explore sibling repos.
"""

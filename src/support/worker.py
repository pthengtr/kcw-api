"""Poll support_tickets and run a local Cursor agent on hq-ubuntu-server."""

from __future__ import annotations

import json
import os
import time
import traceback

from dotenv import load_dotenv
from sqlalchemy import text

from src.db import get_engine
from src.support.attachments import (
    cleanup_attachments,
    download_attachments,
    get_supabase_client,
)
from src.support.git_pr import (
    base_branch,
    commit_all,
    data_query_cwd,
    has_changes,
    prepare_worktree,
    push_and_pr_merge,
    remove_worktree,
    run_local_agent,
)
from src.support.prompt import build_agent_prompt

load_dotenv()

WORKER_NAME = os.getenv("SUPPORT_WORKER_NAME", "hq-ubuntu-server")
POLL_SECONDS = float(os.getenv("SUPPORT_POLL_SECONDS", "8"))
IDLE_SECONDS = float(os.getenv("SUPPORT_IDLE_SECONDS", "15"))


def _row_to_dict(row) -> dict | None:
    if row is None:
        return None
    data = dict(row)
    meta = data.get("target_meta")
    if isinstance(meta, str):
        try:
            data["target_meta"] = json.loads(meta)
        except Exception:
            data["target_meta"] = {}
    return data


def claim_next_ticket(engine) -> dict | None:
    sql = text(
        """
        with next_ticket as (
            select id
            from public.support_tickets
            where status = 'pending'
            order by created_at
            for update skip locked
            limit 1
        )
        update public.support_tickets t
        set
            status = 'running',
            claimed_at = now(),
            error_message = null,
            finished_at = null
        from next_ticket n
        where t.id = n.id
        returning t.*
        """
    )
    with engine.begin() as conn:
        row = conn.execute(sql).mappings().first()
        ticket = _row_to_dict(row)
        if not ticket or not ticket.get("id"):
            return None
        conn.execute(
            text(
                """
                insert into public.support_ticket_events
                  (ticket_id, event_type, comment, meta)
                values (
                  cast(:id as uuid),
                  'claimed',
                  null,
                  cast(:meta as jsonb)
                )
                """
            ),
            {
                "id": str(ticket["id"]),
                "meta": json.dumps({"worker": WORKER_NAME}),
            },
        )
    return ticket


def latest_reopen_comment(engine, ticket_id: str) -> str | None:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                select comment
                from public.support_ticket_events
                where ticket_id = cast(:id as uuid)
                  and event_type = 'reopened'
                order by created_at desc
                limit 1
                """
            ),
            {"id": ticket_id},
        ).mappings().first()
    if not row:
        return None
    return row.get("comment")


def mark_waiting(
    engine,
    ticket_id: str,
    *,
    pr_url: str | None,
    merge_sha: str | None,
    agent_session_id: str | None,
    event_comment: str | None = None,
    event_meta: dict | None = None,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                update public.support_tickets
                set status = 'waiting',
                    pr_url = :pr_url,
                    merge_sha = :merge_sha,
                    agent_session_id = :agent_session_id,
                    finished_at = now(),
                    error_message = null
                where id = cast(:id as uuid)
                """
            ),
            {
                "id": ticket_id,
                "pr_url": pr_url,
                "merge_sha": merge_sha,
                "agent_session_id": agent_session_id,
            },
        )
        meta = {
            "pr_url": pr_url,
            "merge_sha": merge_sha,
            "worker": WORKER_NAME,
            **(event_meta or {}),
        }
        conn.execute(
            text(
                """
                insert into public.support_ticket_events
                  (ticket_id, event_type, comment, meta)
                values (
                  cast(:id as uuid),
                  'waiting',
                  :comment,
                  cast(:meta as jsonb)
                )
                """
            ),
            {
                "id": ticket_id,
                "comment": event_comment,
                "meta": json.dumps(meta),
            },
        )


def mark_failed(engine, ticket_id: str, error_message: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                update public.support_tickets
                set status = 'failed',
                    error_message = :error_message,
                    finished_at = now()
                where id = cast(:id as uuid)
                """
            ),
            {"id": ticket_id, "error_message": error_message[:4000]},
        )
        conn.execute(
            text(
                """
                insert into public.support_ticket_events
                  (ticket_id, event_type, comment, meta)
                values (
                  cast(:id as uuid),
                  'failed',
                  :comment,
                  cast(:meta as jsonb)
                )
                """
            ),
            {
                "id": ticket_id,
                "comment": error_message[:2000],
                "meta": json.dumps({"worker": WORKER_NAME}),
            },
        )


def add_event(
    engine,
    ticket_id: str,
    event_type: str,
    *,
    comment: str | None = None,
    meta: dict | None = None,
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                insert into public.support_ticket_events
                  (ticket_id, event_type, comment, meta)
                values (
                  cast(:id as uuid),
                  :event_type,
                  :comment,
                  cast(:meta as jsonb)
                )
                """
            ),
            {
                "id": ticket_id,
                "event_type": event_type,
                "comment": comment,
                "meta": json.dumps(meta or {}),
            },
        )


def process_data_query(engine, ticket: dict, *, local_files: list[str]) -> None:
    """Answer-only path: no git worktree / PR."""
    ticket_id = str(ticket["id"])
    reopen_comment = latest_reopen_comment(engine, ticket_id)
    prompt = build_agent_prompt(
        ticket,
        attachment_paths=local_files,
        reopen_comment=reopen_comment,
    )
    cwd = data_query_cwd()
    add_event(
        engine,
        ticket_id,
        "agent_started",
        meta={
            "mode": "data_query",
            "cwd": str(cwd),
            "worker": WORKER_NAME,
            "target_id": ticket.get("target_id"),
        },
    )

    agent_out = run_local_agent(cwd=cwd, prompt=prompt)
    answer = (agent_out or "").strip()
    if not answer:
        raise RuntimeError("Data-query agent finished with empty answer")

    add_event(
        engine,
        ticket_id,
        "answered",
        comment=answer[:8000],
        meta={"worker": WORKER_NAME, "mode": "data_query"},
    )
    mark_waiting(
        engine,
        ticket_id,
        pr_url=None,
        merge_sha=None,
        agent_session_id=None,
        event_comment=None,
        event_meta={"mode": "data_query"},
    )
    print(f"[support] data_query waiting {ticket_id} answer_chars={len(answer)}")


def process_code_ticket(engine, ticket: dict, *, local_files: list[str]) -> None:
    ticket_id = str(ticket["id"])
    target_source = ticket["target_source"]
    if target_source not in ("kcw-api", "kcw-v2"):
        raise RuntimeError(
            f"Code tickets require kcw-api/kcw-v2 target, got {target_source}"
        )

    reopen_comment = latest_reopen_comment(engine, ticket_id)
    prompt = build_agent_prompt(
        ticket,
        attachment_paths=local_files,
        reopen_comment=reopen_comment,
    )

    worktree, branch = prepare_worktree(ticket_id, target_source)
    add_event(
        engine,
        ticket_id,
        "agent_started",
        meta={"branch": branch, "cwd": str(worktree), "worker": WORKER_NAME},
    )

    agent_out = run_local_agent(cwd=worktree, prompt=prompt)
    add_event(
        engine,
        ticket_id,
        "agent_finished",
        comment=agent_out[-1500:] if agent_out else None,
    )

    if has_changes(worktree):
        commit_all(
            worktree,
            f"support: {ticket.get('title') or ticket_id}".strip()[:200],
        )

    from src.support.git_pr import _run

    base = base_branch()
    log = _run(
        ["git", "rev-list", "--count", f"origin/{base}..HEAD"],
        cwd=worktree,
        check=False,
    )
    try:
        ahead = int((log.stdout or "0").strip() or "0") > 0
    except ValueError:
        ahead = False
    if not ahead:
        raise RuntimeError(
            "Agent finished with no code changes to commit/push"
        )

    pr_title = f"support: {ticket.get('title') or ticket_id}"
    pr_body = (
        f"Automated support ticket `{ticket_id}`\n\n"
        f"- Target: {ticket.get('target_label')} "
        f"({ticket.get('target_source')}/{ticket.get('target_id')})\n"
        f"- Kind: {ticket.get('kind')}\n\n"
        f"{ticket.get('body') or ''}\n"
    )
    pr_url, merge_sha = push_and_pr_merge(
        worktree, branch=branch, title=pr_title, body=pr_body
    )
    add_event(
        engine,
        ticket_id,
        "merged",
        meta={"pr_url": pr_url, "merge_sha": merge_sha},
    )
    mark_waiting(
        engine,
        ticket_id,
        pr_url=pr_url,
        merge_sha=merge_sha,
        agent_session_id=None,
    )
    print(f"[support] waiting verify {ticket_id} pr={pr_url}")


def process_ticket(engine, ticket: dict) -> None:
    ticket_id = str(ticket["id"])
    target_source = ticket["target_source"]
    kind = ticket.get("kind") or ""
    local_files: list[str] = []

    print(
        f"[support] processing {ticket_id} kind={kind} "
        f"target={target_source}/{ticket['target_id']}"
    )

    try:
        sb = get_supabase_client()
        paths = list(ticket.get("attachment_paths") or [])
        downloaded = download_attachments(
            sb, ticket_id=ticket_id, storage_paths=paths
        )
        local_files = [str(p) for p in downloaded]

        if kind == "data_query":
            process_data_query(engine, ticket, local_files=local_files)
        else:
            process_code_ticket(engine, ticket, local_files=local_files)
    except Exception as exc:
        print(f"[support] failed {ticket_id}: {exc}\n{traceback.format_exc()}")
        mark_failed(engine, ticket_id, str(exc))
    finally:
        cleanup_attachments(ticket_id)
        if kind != "data_query" and target_source in ("kcw-api", "kcw-v2"):
            try:
                remove_worktree(ticket_id, target_source)
            except Exception as cleanup_err:
                print(f"[support] worktree cleanup warning: {cleanup_err}")


def main() -> None:
    print(f"[support] worker starting as {WORKER_NAME}")
    engine = get_engine()
    while True:
        try:
            ticket = claim_next_ticket(engine)
            if not ticket or not ticket.get("id"):
                time.sleep(IDLE_SECONDS)
                continue
            try:
                process_ticket(engine, ticket)
            except Exception:
                # Already marked failed inside process_ticket when possible.
                pass
            time.sleep(POLL_SECONDS)
        except KeyboardInterrupt:
            print("[support] shutting down")
            break
        except Exception as loop_err:
            print(f"[support] loop error: {loop_err}")
            time.sleep(IDLE_SECONDS)


if __name__ == "__main__":
    main()

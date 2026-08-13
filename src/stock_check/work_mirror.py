from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from src.db import get_engine
from src.stock_check.db_local import LocalStore

logger = logging.getLogger("kcw.stock_check.work_mirror")


def flush_work_outbox(store: LocalStore, *, branch: str) -> int:
    """Push local work-event rows into stock.work_event via Supabase SQL."""
    items = store.list_unsent_work_outbox()
    if not items:
        return 0
    try:
        engine = get_engine()
    except Exception as exc:  # noqa: BLE001
        logger.warning("work mirror engine unavailable: %s", exc)
        return 0

    sent = 0
    for item in items:
        try:
            payload: dict[str, Any] = json.loads(item["payload_json"])
            _write_supabase_work_event(engine, payload, branch=branch)
            store.mark_work_outbox_sent(item["id"])
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("work mirror failed for %s", item["id"])
            store.mark_work_outbox_error(item["id"], str(exc))
    return sent


def _write_supabase_work_event(engine, payload: dict[str, Any], *, branch: str) -> None:
    sql = text(
        """
        insert into stock.work_event (
          id, branch, line_user_id, display_name, event_type,
          bcode, draft_id, variance, source, created_at
        ) values (
          :id, :branch, :line_user_id, :display_name, :event_type,
          :bcode, :draft_id, :variance, :source, to_timestamp(:created_at)
        )
        on conflict (id) do nothing
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql,
            {
                "id": str(payload.get("id") or ""),
                "branch": branch.upper(),
                "line_user_id": str(payload.get("line_user_id") or ""),
                "display_name": str(payload.get("display_name") or "")[:200],
                "event_type": str(payload.get("event_type") or ""),
                "bcode": payload.get("bcode"),
                "draft_id": payload.get("draft_id"),
                "variance": payload.get("variance"),
                "source": payload.get("source"),
                "created_at": float(payload.get("created_at") or 0),
            },
        )

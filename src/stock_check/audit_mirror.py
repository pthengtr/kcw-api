from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from src.db import get_engine
from src.stock_check.db_local import LocalStore

logger = logging.getLogger("kcw.stock_check.audit_mirror")


def flush_audit_outbox(store: LocalStore, *, branch: str) -> int:
    """Push local outbox rows into stock.audit_event / audit_status via Supabase SQL."""
    items = store.list_unsent_outbox()
    if not items:
        return 0
    try:
        engine = get_engine()
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit mirror engine unavailable: %s", exc)
        return 0

    sent = 0
    for item in items:
        try:
            payload: dict[str, Any] = json.loads(item["payload_json"])
            _write_supabase_audit(engine, payload)
            store.mark_outbox_sent(item["id"])
            sent += 1
        except Exception as exc:  # noqa: BLE001
            logger.exception("audit mirror failed for %s", item["id"])
            store.mark_outbox_error(item["id"], str(exc))
    return sent


def _write_supabase_audit(engine, payload: dict[str, Any]) -> None:
    branch = str(payload.get("branch") or "").upper()
    bcode = str(payload.get("bcode") or "").strip()
    operator_name = str(payload.get("operator_name") or "unknown")
    operator_id = str(payload.get("operator_id") or "")
    outcome = str(payload.get("outcome") or "correct")
    variance = payload.get("variance")
    billno = payload.get("billno")
    source_raw = str(payload.get("source") or "ondemand")
    source = source_raw if source_raw in {"batch", "ondemand", "manual"} else "manual"
    audited_by = f"{operator_name}|{operator_id}" if operator_id else operator_name
    notes_parts = [f"outcome={outcome}"]
    if variance is not None:
        notes_parts.append(f"variance={variance}")
    if billno:
        notes_parts.append(f"billno={billno}")
    if payload.get("approver_name"):
        notes_parts.append(
            f"approver={payload.get('approver_name')}|{payload.get('approver_id') or ''}"
        )
    notes = "; ".join(notes_parts)[:500]

    sql_event = text(
        """
        insert into stock.audit_event (
          branch, bcode, audited_by, source, notes
        ) values (
          :branch, :bcode, :audited_by, :source, :notes
        )
        """
    )
    sql_status = text(
        """
        insert into stock.audit_status (
          branch, bcode, last_audited_at, last_audited_by, audit_count, notes, updated_at
        ) values (
          :branch, :bcode, now(), :audited_by, 1, :notes, now()
        )
        on conflict (branch, bcode) do update set
          last_audited_at = now(),
          last_audited_by = excluded.last_audited_by,
          audit_count = stock.audit_status.audit_count + 1,
          notes = excluded.notes,
          updated_at = now()
        """
    )
    with engine.begin() as conn:
        conn.execute(
            sql_event,
            {
                "branch": branch,
                "bcode": bcode,
                "audited_by": audited_by[:200],
                "source": source,
                "notes": notes,
            },
        )
        conn.execute(
            sql_status,
            {
                "branch": branch,
                "bcode": bcode,
                "audited_by": audited_by[:200],
                "notes": notes,
            },
        )

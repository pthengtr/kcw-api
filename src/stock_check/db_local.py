from __future__ import annotations

import json
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  line_user_id TEXT NOT NULL,
  display_name TEXT NOT NULL,
  is_approver INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL,
  last_seen_at REAL NOT NULL,
  ended_at REAL
);

CREATE TABLE IF NOT EXISTS leases (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL REFERENCES sessions(id),
  bcode TEXT NOT NULL,
  leased_at REAL NOT NULL,
  expires_at REAL NOT NULL,
  status TEXT NOT NULL DEFAULT 'leased',
  pick_priority INTEGER,
  pick_reasons TEXT,
  abc_class TEXT,
  sales_days_90 INTEGER,
  UNIQUE(session_id, bcode)
);

CREATE INDEX IF NOT EXISTS leases_active_bcode_idx
  ON leases(bcode) WHERE status = 'leased';

CREATE TABLE IF NOT EXISTS drafts (
  id TEXT PRIMARY KEY,
  bcode TEXT NOT NULL,
  descr TEXT,
  location1 TEXT,
  location2 TEXT,
  system_qty REAL NOT NULL,
  counted_qty REAL NOT NULL,
  variance REAL NOT NULL,
  entry_mode TEXT NOT NULL,
  source TEXT NOT NULL,
  status TEXT NOT NULL,
  operator_line_user_id TEXT NOT NULL,
  operator_name TEXT NOT NULL,
  approver_line_user_id TEXT,
  approver_name TEXT,
  posted_billno TEXT,
  post_error TEXT,
  notes TEXT,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL,
  completed_at REAL
);

CREATE INDEX IF NOT EXISTS drafts_status_idx ON drafts(status, created_at DESC);

CREATE TABLE IF NOT EXISTS local_audit_status (
  bcode TEXT PRIMARY KEY,
  last_audited_at REAL NOT NULL,
  last_audited_by TEXT NOT NULL,
  last_outcome TEXT NOT NULL,
  audit_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_outbox (
  id TEXT PRIMARY KEY,
  payload_json TEXT NOT NULL,
  created_at REAL NOT NULL,
  sent_at REAL,
  last_error TEXT,
  attempts INTEGER NOT NULL DEFAULT 0
);
"""


class LocalStore:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.executescript(SCHEMA)
            self._migrate(conn)

    @staticmethod
    def _migrate(conn: sqlite3.Connection) -> None:
        cols = {str(r[1]) for r in conn.execute("PRAGMA table_info(leases)").fetchall()}
        alterations = {
            "pick_priority": "ALTER TABLE leases ADD COLUMN pick_priority INTEGER",
            "pick_reasons": "ALTER TABLE leases ADD COLUMN pick_reasons TEXT",
            "abc_class": "ALTER TABLE leases ADD COLUMN abc_class TEXT",
            "sales_days_90": "ALTER TABLE leases ADD COLUMN sales_days_90 INTEGER",
        }
        for name, sql in alterations.items():
            if name not in cols:
                conn.execute(sql)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def create_session(
        self,
        *,
        line_user_id: str,
        display_name: str,
        is_approver: bool,
        now: float | None = None,
    ) -> str:
        ts = now if now is not None else time.time()
        session_id = str(uuid.uuid4())
        with self.connect() as conn:
            # End any prior open session for this user (releases leases).
            prior = conn.execute(
                """
                SELECT id FROM sessions
                WHERE line_user_id = ? AND ended_at IS NULL
                ORDER BY created_at DESC
                """,
                (line_user_id,),
            ).fetchall()
            for row in prior:
                self._end_session_conn(conn, row["id"], ts)
            conn.execute(
                """
                INSERT INTO sessions (id, line_user_id, display_name, is_approver, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, line_user_id, display_name, 1 if is_approver else 0, ts, ts),
            )
        return session_id

    def touch_session(self, session_id: str, *, now: float | None = None) -> None:
        """Bump session last_seen only — does not extend leases."""
        ts = now if now is not None else time.time()
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE id = ? AND ended_at IS NULL",
                (ts, session_id),
            )

    def extend_leases(
        self,
        session_id: str,
        *,
        lease_ttl: int,
        now: float | None = None,
    ) -> int:
        """Refresh expires_at for this session's active leases (activity / heartbeat)."""
        ts = now if now is not None else time.time()
        with self.connect() as conn:
            conn.execute(
                "UPDATE sessions SET last_seen_at = ? WHERE id = ? AND ended_at IS NULL",
                (ts, session_id),
            )
            cur = conn.execute(
                """
                UPDATE leases SET expires_at = ?
                WHERE session_id = ? AND status = 'leased'
                """,
                (ts + int(lease_ttl), session_id),
            )
            return cur.rowcount

    def end_session(self, session_id: str, *, now: float | None = None) -> int:
        ts = now if now is not None else time.time()
        with self.connect() as conn:
            return self._end_session_conn(conn, session_id, ts)

    def _end_session_conn(self, conn: sqlite3.Connection, session_id: str, ts: float) -> int:
        cur = conn.execute(
            """
            UPDATE leases SET status = 'released'
            WHERE session_id = ? AND status = 'leased'
            """,
            (session_id,),
        )
        conn.execute(
            "UPDATE sessions SET ended_at = ?, last_seen_at = ? WHERE id = ? AND ended_at IS NULL",
            (ts, ts, session_id),
        )
        return cur.rowcount

    def expire_stale_leases(self, *, now: float | None = None) -> int:
        ts = now if now is not None else time.time()
        with self.connect() as conn:
            cur = conn.execute(
                """
                UPDATE leases SET status = 'released'
                WHERE status = 'leased' AND expires_at < ?
                """,
                (ts,),
            )
            return cur.rowcount

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM sessions WHERE id = ? AND ended_at IS NULL",
                (session_id,),
            ).fetchone()
            return dict(row) if row else None

    def active_leased_bcodes(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT bcode FROM leases WHERE status = 'leased'"
            ).fetchall()
            return {r["bcode"] for r in rows}

    def list_leases_for_session(self, session_id: str) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM leases
                WHERE session_id = ? AND status = 'leased'
                ORDER BY leased_at
                """,
                (session_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def claim_leases(
        self,
        *,
        session_id: str,
        bcodes: list[str] | None = None,
        lease_items: list[dict[str, Any]] | None = None,
        lease_ttl: int,
        now: float | None = None,
    ) -> list[str]:
        ts = now if now is not None else time.time()
        expires = ts + int(lease_ttl)
        if lease_items is not None:
            items = lease_items
        else:
            items = [{"bcode": b} for b in (bcodes or [])]
        claimed: list[str] = []
        with self.connect() as conn:
            held = {
                r["bcode"]
                for r in conn.execute(
                    "SELECT bcode FROM leases WHERE status = 'leased'"
                ).fetchall()
            }
            for item in items:
                bcode = str(item.get("bcode") or "").strip()
                if not bcode or bcode in held:
                    continue
                lease_id = str(uuid.uuid4())
                reasons = item.get("pick_reasons") or []
                if isinstance(reasons, str):
                    reasons_json = reasons
                else:
                    reasons_json = json.dumps(list(reasons), ensure_ascii=False)
                try:
                    conn.execute(
                        """
                        INSERT INTO leases (
                          id, session_id, bcode, leased_at, expires_at, status,
                          pick_priority, pick_reasons, abc_class, sales_days_90
                        )
                        VALUES (?, ?, ?, ?, ?, 'leased', ?, ?, ?, ?)
                        """,
                        (
                            lease_id,
                            session_id,
                            bcode,
                            ts,
                            expires,
                            item.get("pick_priority"),
                            reasons_json,
                            item.get("abc_class"),
                            item.get("sales_days_90"),
                        ),
                    )
                except sqlite3.IntegrityError:
                    continue
                claimed.append(bcode)
                held.add(bcode)
        return claimed

    def mark_lease_done(self, session_id: str, bcode: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE leases SET status = 'done'
                WHERE session_id = ? AND bcode = ? AND status = 'leased'
                """,
                (session_id, bcode),
            )

    def release_one_lease(self, session_id: str, bcode: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE leases SET status = 'released'
                WHERE session_id = ? AND bcode = ? AND status = 'leased'
                """,
                (session_id, bcode),
            )

    def upsert_local_audit(
        self,
        *,
        bcode: str,
        audited_by: str,
        outcome: str,
        now: float | None = None,
    ) -> None:
        ts = now if now is not None else time.time()
        with self.connect() as conn:
            row = conn.execute(
                "SELECT audit_count FROM local_audit_status WHERE bcode = ?",
                (bcode,),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE local_audit_status
                    SET last_audited_at = ?, last_audited_by = ?, last_outcome = ?,
                        audit_count = audit_count + 1
                    WHERE bcode = ?
                    """,
                    (ts, audited_by, outcome, bcode),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO local_audit_status
                      (bcode, last_audited_at, last_audited_by, last_outcome, audit_count)
                    VALUES (?, ?, ?, ?, 1)
                    """,
                    (bcode, ts, audited_by, outcome),
                )

    def get_local_audits(self, bcodes: list[str] | None = None) -> dict[str, dict[str, Any]]:
        with self.connect() as conn:
            if bcodes is None:
                rows = conn.execute("SELECT * FROM local_audit_status").fetchall()
            elif not bcodes:
                return {}
            else:
                placeholders = ",".join("?" for _ in bcodes)
                rows = conn.execute(
                    f"SELECT * FROM local_audit_status WHERE bcode IN ({placeholders})",
                    bcodes,
                ).fetchall()
            return {r["bcode"]: dict(r) for r in rows}

    def create_draft(self, data: dict[str, Any]) -> str:
        draft_id = str(uuid.uuid4())
        ts = time.time()
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO drafts (
                  id, bcode, descr, location1, location2, system_qty, counted_qty, variance,
                  entry_mode, source, status, operator_line_user_id, operator_name,
                  notes, created_at, updated_at, completed_at
                ) VALUES (
                  ?, ?, ?, ?, ?, ?, ?, ?,
                  ?, ?, ?, ?, ?,
                  ?, ?, ?, ?
                )
                """,
                (
                    draft_id,
                    data["bcode"],
                    data.get("descr"),
                    data.get("location1"),
                    data.get("location2"),
                    data["system_qty"],
                    data["counted_qty"],
                    data["variance"],
                    data["entry_mode"],
                    data["source"],
                    data["status"],
                    data["operator_line_user_id"],
                    data["operator_name"],
                    data.get("notes"),
                    ts,
                    ts,
                    data.get("completed_at"),
                ),
            )
        return draft_id

    def pending_bcodes(self) -> set[str]:
        with self.connect() as conn:
            rows = conn.execute(
                "SELECT bcode FROM drafts WHERE status = 'pending'"
            ).fetchall()
            return {r["bcode"] for r in rows}

    def get_pending_draft_for_bcode(self, bcode: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM drafts
                WHERE bcode = ? AND status = 'pending'
                ORDER BY created_at
                LIMIT 1
                """,
                (bcode,),
            ).fetchone()
            return dict(row) if row else None

    def get_active_lease_for_bcode(self, bcode: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM leases
                WHERE bcode = ? AND status = 'leased'
                LIMIT 1
                """,
                (bcode,),
            ).fetchone()
            return dict(row) if row else None

    def list_pending_drafts(self) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM drafts
                WHERE status = 'pending'
                ORDER BY created_at
                """
            ).fetchall()
            return [dict(r) for r in rows]

    def get_draft(self, draft_id: str) -> dict[str, Any] | None:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM drafts WHERE id = ?", (draft_id,)).fetchone()
            return dict(row) if row else None

    def update_draft(self, draft_id: str, **fields: Any) -> None:
        if not fields:
            return
        fields = {**fields, "updated_at": time.time()}
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values()) + [draft_id]
        with self.connect() as conn:
            conn.execute(f"UPDATE drafts SET {cols} WHERE id = ?", values)

    def enqueue_audit_outbox(self, payload_json: str) -> str:
        item_id = str(uuid.uuid4())
        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_outbox (id, payload_json, created_at)
                VALUES (?, ?, ?)
                """,
                (item_id, payload_json, time.time()),
            )
        return item_id

    def list_unsent_outbox(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM audit_outbox
                WHERE sent_at IS NULL
                ORDER BY created_at
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
            return [dict(r) for r in rows]

    def mark_outbox_sent(self, item_id: str) -> None:
        with self.connect() as conn:
            conn.execute(
                "UPDATE audit_outbox SET sent_at = ?, last_error = NULL WHERE id = ?",
                (time.time(), item_id),
            )

    def mark_outbox_error(self, item_id: str, error: str) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                UPDATE audit_outbox
                SET attempts = attempts + 1, last_error = ?
                WHERE id = ?
                """,
                (error[:500], item_id),
            )

"""Read local product insight SQLite for parts9 Explorer."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def _db_path() -> Path | None:
    env = (os.getenv("PRODUCT_INSIGHTS_DB") or "").strip()
    if env:
        return Path(env).expanduser()
    default = Path.home() / "kcw-data" / "product_insights" / "insights.sqlite"
    return default if default.is_file() else None


def lookup_insight(site: str, bcode: str) -> dict[str, Any]:
    """
    Return Explorer panel payload:
      status: ready | working | no_movement
      insight fields when ready
    """
    site_l = (site or "hq").lower()
    code = (bcode or "").strip()
    path = _db_path()
    empty = {
        "status": "no_movement",
        "site": site_l,
        "bcode": code,
        "summary": None,
        "generated_at": None,
        "facts_as_of": None,
        "insight": None,
    }
    if not path or not path.is_file() or not code:
        return empty

    import sqlite3

    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return empty

    try:
        row = conn.execute(
            """
            SELECT site, bcode, generated_at, facts_as_of, prompt_version,
                   model_id, summary, insight_json
            FROM product_insights
            WHERE site = ? AND bcode = ?
            """,
            (site_l, code),
        ).fetchone()
        if row:
            insight = None
            try:
                insight = json.loads(row["insight_json"] or "{}")
            except Exception:
                insight = {"raw": row["insight_json"]}
            return {
                "status": "ready",
                "site": row["site"],
                "bcode": row["bcode"],
                "generated_at": row["generated_at"],
                "facts_as_of": row["facts_as_of"],
                "prompt_version": row["prompt_version"],
                "model_id": row["model_id"],
                "summary": row["summary"],
                "insight": insight,
            }

        q = conn.execute(
            """
            SELECT status, snap_id, window, movement_score, facts_as_of, updated_at
            FROM insight_queue
            WHERE site = ? AND bcode = ?
            ORDER BY
              CASE status
                WHEN 'running' THEN 0
                WHEN 'pending' THEN 1
                WHEN 'done' THEN 2
                ELSE 3
              END,
              updated_at DESC
            LIMIT 1
            """,
            (site_l, code),
        ).fetchone()
        if q and (q["status"] or "") in ("pending", "running"):
            return {
                "status": "working",
                "site": site_l,
                "bcode": code,
                "summary": None,
                "generated_at": None,
                "facts_as_of": q["facts_as_of"],
                "insight": None,
                "queue": dict(q),
            }
        return empty
    except sqlite3.Error:
        return empty
    finally:
        conn.close()

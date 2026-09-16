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
        "policy": None,
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
        cols = {r[1] for r in conn.execute("PRAGMA table_info(product_insights)")}
        select_cols = [
            "site",
            "bcode",
            "generated_at",
            "facts_as_of",
            "prompt_version",
            "model_id",
            "summary",
            "insight_json",
        ]
        policy_cols = [
            "typical_monthly_qty",
            "suggested_cover_weeks",
            "safe_holding_qty",
            "safe_holding_reason",
            "order_ok",
            "order_ok_reason",
            "dead_stock",
            "dead_stock_reason",
            "suggested_order_qty",
            "suggested_order_qty_large",
            "order_unit",
            "order_unit_large",
            "last_supplier",
            "last_buy_price",
            "last_buy_date",
            "rec_qtymin",
            "rec_qtymin_reason",
            "check_stock",
            "stock_anomaly",
            "qtyoh_hq",
            "qtyoh_syp",
            "qtymin_hq",
            "qtymin_syp",
            "rec_transfer_qty_to_syp",
            "rec_transfer_reason",
            "sales_qty_30d",
            "sales_qty_90d",
            "sales_qty_12m",
            "trend_30d",
            "trend_90d",
            "trend_12m",
            "trend_label",
            "margin_pct_list",
            "margin_pct_12m",
            "margin_pct_prior_12m",
            "margin_delta_pp",
            "margin_flag",
            "cost_change_pct_12m",
            "price_change_pct_12m",
        ]
        for c in policy_cols:
            if c in cols:
                select_cols.append(c)
        row = conn.execute(
            f"""
            SELECT {", ".join(select_cols)}
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
            policy = {c: row[c] for c in policy_cols if c in row.keys()}
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
                "policy": policy,
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
                "policy": None,
                "queue": dict(q),
            }
        return empty
    except sqlite3.Error:
        return empty
    finally:
        conn.close()

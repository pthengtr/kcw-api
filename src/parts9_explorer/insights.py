"""Read local product insight SQLite for parts9 Explorer."""

from __future__ import annotations

import json
import os
from collections import defaultdict
from pathlib import Path
from typing import Any


def _db_path() -> Path | None:
    env = (os.getenv("PRODUCT_INSIGHTS_DB") or "").strip()
    if env:
        return Path(env).expanduser()
    default = Path.home() / "kcw-data" / "product_insights" / "insights.sqlite"
    return default if default.is_file() else None


def _snap_dir() -> Path:
    env = (os.getenv("PRODUCT_INSIGHTS_SNAP_DIR") or "").strip()
    if env:
        return Path(env).expanduser()
    db = _db_path()
    if db:
        return db.parent / "snaps"
    return Path.home() / "kcw-data" / "product_insights" / "snaps"


def _latest_snap_db() -> Path | None:
    root = _snap_dir()
    if not root.is_dir():
        return None
    best: Path | None = None
    best_mtime = -1.0
    for child in root.iterdir():
        if not child.is_dir():
            continue
        snap = child / "snapshot.sqlite"
        if not snap.is_file():
            continue
        try:
            mtime = snap.stat().st_mtime
        except OSError:
            continue
        if mtime > best_mtime:
            best_mtime = mtime
            best = snap
    return best


def _customer_channel(billno: str | None, jourmode: str | None, src_site: str | None) -> str:
    """Mirror kcw-analytic channel_of — customer demand only (no transfer/excluded)."""
    b = (billno or "").strip().upper()
    j = str(jourmode).strip() if jourmode is not None else ""
    src = (src_site or "").strip().lower()
    if j == "0":
        return "excluded"
    if b.startswith("CNTAD") or b.startswith("3CNTAD") or b.startswith("TAD"):
        return "online"
    if (
        b.startswith("TFV")
        or b.startswith("3TFV")
        or b.startswith("TF")
        or b.startswith("3TF")
        or b.startswith("CNTF")
        or b.startswith("3CNTF")
    ):
        return "transfer"
    if src == "syp" or b.startswith("3"):
        return "syp_store"
    return "hq_store"


def monthly_customer_sales(bcode: str, *, n_months: int = 11) -> list[dict[str, Any]]:
    """Last N calendar months of customer SI qty from the latest insight snap."""
    code = (bcode or "").strip()
    snap = _latest_snap_db()
    if not code or not snap:
        return []

    import sqlite3

    try:
        conn = sqlite3.connect(f"file:{snap}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error:
        return []

    try:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(sidet)")}
        if "bcode" not in cols or "billdate" not in cols or "qty" not in cols:
            return []
        select = ["billdate", "qty"]
        if "billno" in cols:
            select.append("billno")
        if "jourmode" in cols:
            select.append("jourmode")
        if "src_site" in cols:
            select.append("src_site")
        rows = conn.execute(
            f"SELECT {', '.join(select)} FROM sidet WHERE trim(bcode) = ?",
            (code,),
        ).fetchall()
    except sqlite3.Error:
        return []
    finally:
        conn.close()

    by_ym: dict[str, float] = defaultdict(float)
    for row in rows:
        keys = row.keys()
        ch = _customer_channel(
            row["billno"] if "billno" in keys else None,
            row["jourmode"] if "jourmode" in keys else None,
            row["src_site"] if "src_site" in keys else None,
        )
        if ch not in ("hq_store", "syp_store", "online"):
            continue
        ym = str(row["billdate"] or "")[:7]
        if len(ym) != 7 or ym[4] != "-":
            continue
        try:
            q = float(row["qty"] or 0)
        except (TypeError, ValueError):
            continue
        by_ym[ym] += q

    if not by_ym:
        return []

    end = sorted(by_ym.keys())[-1]
    try:
        y, m = int(end[:4]), int(end[5:7])
    except ValueError:
        return []

    # Contiguous last n_months ending at latest month with data.
    out: list[dict[str, Any]] = []
    cy, cm = y, m
    for _ in range(n_months):
        key = f"{cy:04d}-{cm:02d}"
        out.append({"ym": key, "qty": round(by_ym.get(key, 0.0), 2)})
        cm -= 1
        if cm < 1:
            cm = 12
            cy -= 1
    out.reverse()
    return out


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
        "monthly_sales": [],
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
            "last_supplier_acct",
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
                "monthly_sales": monthly_customer_sales(code),
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
                "monthly_sales": [],
                "queue": dict(q),
            }
        return empty
    except sqlite3.Error:
        return empty
    finally:
        conn.close()

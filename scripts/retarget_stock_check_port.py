from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import text

from scripts.setup_stock_check_hq import STOCK_KEYS, upsert_env

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / ".env"

from dotenv import dotenv_values

existing = dotenv_values(ENV)
updates = dict(STOCK_KEYS)
updates["STOCK_CHECK_TOKEN_SECRET"] = existing.get("STOCK_CHECK_TOKEN_SECRET") or ""
updates["STOCK_CHECK_APPROVER_LINE_USER_IDS"] = (
    existing.get("STOCK_CHECK_APPROVER_LINE_USER_IDS") or ""
)
pub = (existing.get("PUBLIC_BASE_URL") or "").strip()
if pub in {"http://192.168.1.19:8000", "http://192.168.1.19:8787"}:
    updates["PUBLIC_BASE_URL"] = ""

upsert_env(ENV, updates)
print("env ->", updates["STOCK_CHECK_PUBLIC_BASE_URL"])

load_dotenv(ENV, override=True)
from src.stock_check.config import clear_stock_check_settings_cache
from src.db import get_engine

clear_stock_check_settings_cache()
engine = get_engine()
with engine.begin() as conn:
    conn.execute(
        text(
            """
            update ops.worker_heartbeat
            set public_base_url = :u, last_seen = now(), updated_at = now()
            where worker_name = 'HQ-PC'
            """
        ),
        {"u": updates["STOCK_CHECK_PUBLIC_BASE_URL"]},
    )
print("heartbeat updated")

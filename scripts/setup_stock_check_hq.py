"""One-shot HQ setup: patch .env, apply heartbeat migration, print status."""
from __future__ import annotations

import secrets
import sys
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
ENV_PATH = ROOT / ".env"

STOCK_KEYS = {
    "STOCK_CHECK_ENABLED": "true",
    "STOCK_CHECK_BRANCH": "HQ",
    "STOCK_CHECK_LISTEN_PORT": "8787",
    # Empty = auto-detect LAN IP on each worker heartbeat
    "STOCK_CHECK_PUBLIC_BASE_URL": "",
    "STOCK_CHECK_TOKEN_TTL_SECONDS": "900",
    "STOCK_CHECK_LEASE_TTL_SECONDS": "1200",
    "STOCK_CHECK_DATA_DIR": ".stock_check",
}


def upsert_env(path: Path, updates: dict[str, str]) -> None:
    raw = path.read_text(encoding="utf-8") if path.exists() else ""
    lines = raw.splitlines()
    seen: set[str] = set()
    out: list[str] = []
    for line in lines:
        if not line.strip() or line.lstrip().startswith("#") or "=" not in line:
            out.append(line)
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            out.append(line)
    missing = [k for k in updates if k not in seen]
    if missing:
        if out and out[-1].strip():
            out.append("")
        out.append("# --- stock-check (HQ local) ---")
        for key in missing:
            out.append(f"{key}={updates[key]}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    existing = dotenv_values(ENV_PATH) if ENV_PATH.exists() else {}
    updates = dict(STOCK_KEYS)
    secret = (existing.get("STOCK_CHECK_TOKEN_SECRET") or "").strip()
    if not secret:
        secret = secrets.token_urlsafe(32)
    updates["STOCK_CHECK_TOKEN_SECRET"] = secret

    # Keep approver list if already set; otherwise leave empty placeholder key
    approvers = (existing.get("STOCK_CHECK_APPROVER_LINE_USER_IDS") or "").strip()
    updates["STOCK_CHECK_APPROVER_LINE_USER_IDS"] = approvers

    upsert_env(ENV_PATH, updates)
    print("env_updated", ENV_PATH)

    # Load after write
    sys.path.insert(0, str(ROOT))
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH, override=True)
    from src.db import get_engine

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                alter table ops.worker_heartbeat
                  add column if not exists public_base_url text
                """
            )
        )
        cols = conn.execute(
            text(
                """
                select column_name
                from information_schema.columns
                where table_schema = 'ops' and table_name = 'worker_heartbeat'
                order by ordinal_position
                """
            )
        ).fetchall()
        print("heartbeat_cols", [c[0] for c in cols])

        # Register HQ URL immediately so LINE can find it even before worker loop
        conn.execute(
            text(
                """
                insert into ops.worker_heartbeat (
                  worker_name, last_seen, hostname, status, public_base_url, updated_at
                ) values (
                  'HQ-PC', now(), :host, 'idle', :url, now()
                )
                on conflict (worker_name) do update set
                  last_seen = now(),
                  public_base_url = excluded.public_base_url,
                  status = excluded.status,
                  updated_at = now()
                """
            ),
            {"host": "HQ-PC", "url": updates["STOCK_CHECK_PUBLIC_BASE_URL"]},
        )

        try:
            rows = conn.execute(
                text(
                    """
                    select line_user_id, display_name, access_group
                    from ops.line_access
                    where coalesce(is_allowed, true) = true
                    order by access_group, display_name
                    limit 40
                    """
                )
            ).mappings().fetchall()
            print("line_access_count", len(rows))
            for r in rows:
                print(
                    f"  {r['access_group']}: {r['display_name'] or '-'} | {r['line_user_id']}"
                )
        except Exception as exc:  # noqa: BLE001
            print("line_access_err", exc)

    print("STOCK_CHECK_PUBLIC_BASE_URL", updates["STOCK_CHECK_PUBLIC_BASE_URL"])
    print("STOCK_CHECK_TOKEN_SECRET_SET", bool(secret))
    print("STOCK_CHECK_APPROVER_LINE_USER_IDS", approvers or "(empty — set LINE user ids)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

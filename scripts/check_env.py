"""Validate required companion/.env keys for local Windows/Linux dev."""

from __future__ import annotations

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import dotenv_values

REQUIRED = (
    "TIGER_PAY_CLIENT_SECRET",
    "SUPABASE_URL",
    "SUPABASE_SERVICE_ROLE_KEY",
)


def _source_label(key: str, file_vals: dict[str, str | None]) -> str:
    file_set = bool((file_vals.get(key) or "").strip())
    if key not in os.environ:
        env_state = "unset"
    elif not (os.environ.get(key) or "").strip():
        env_state = "empty"
    else:
        env_state = "set"
    return f"file={'set' if file_set else 'MISSING'}, process_env={env_state}"


def main() -> int:
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        print(f".env not found at {env_path}")
        return 1

    file_vals = dotenv_values(env_path)
    print(f"Loaded .env from {env_path}")
    print(f"File size: {env_path.stat().st_size} bytes")

    missing: list[str] = []
    for key in REQUIRED:
        print(f"  {key}: {_source_label(key, file_vals)}")
        if not (file_vals.get(key) or "").strip():
            missing.append(key)

    if missing:
        print("Missing or empty in .env file:")
        for key in missing:
            print(f"  - {key}")
        print("Tips:")
        print("  - Put .env in the repo root next to run_dev.bat")
        print("  - SUPABASE_URL=https://xxxx.supabase.co  (no spaces around =)")
        print("  - Save as UTF-8 (not UTF-16)")
        print("  - SUPABASE_DB_URL is different from SUPABASE_URL")
        print("  - If process_env=empty, clear that Windows environment variable")
        return 1

    # Also prove pydantic settings can load the same values.
    try:
        from src.tiger_pay.config import get_tiger_pay_settings

        get_tiger_pay_settings.cache_clear()
        settings = get_tiger_pay_settings()
        print(
            "Pydantic load OK "
            f"(supabase_url starts with {settings.supabase_url[:28]}...)"
        )
    except Exception as exc:
        print(f"Pydantic settings failed to load: {exc}")
        print(
            "If process_env shows empty for a key, remove/clear that "
            "Windows environment variable."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Push yesterday's TAR net to Narumon at 10:00 Asia/Bangkok.

Recipient: TAR_TRANSFER_PUSH_LINE_USER_ID if set, otherwise an allowed
ops.line_access row whose display name matches TAR_TRANSFER_PUSH_NAMES
(default narumonwit).
"""

from __future__ import annotations

import argparse
import os
from datetime import date, timedelta
from pathlib import Path

from sqlalchemy import text

from src.bot.line_bot import push_line_message
from src.db import get_engine
from src.tar_transfer.summary import (
    bangkok_today,
    format_tar_transfer_message,
    load_tar_transfer,
)

DEFAULT_PUSH_NAMES = "narumonwit"


def push_names() -> list[str]:
    raw = os.getenv("TAR_TRANSFER_PUSH_NAMES", DEFAULT_PUSH_NAMES)
    names = []
    for part in raw.split(","):
        name = "".join(part.split()).casefold()
        if name:
            names.append(name)
    return names


def explicit_push_user_ids() -> list[str]:
    raw = os.getenv("TAR_TRANSFER_PUSH_LINE_USER_ID", "")
    return [part.strip() for part in raw.split(",") if part.strip()]


def name_tokens(display_name: str) -> set[str]:
    """Compact form plus each word, so 'phu' matches 'PHU Nattapon W.'."""
    raw = display_name or ""
    compact = "".join(raw.split()).casefold()
    tokens = {compact} if compact else set()
    for word in raw.replace(".", " ").split():
        cleaned = "".join(ch for ch in word.casefold() if ch.isalnum())
        if cleaned:
            tokens.add(cleaned)
    return tokens


def line_user_ids_for_names(engine, names: list[str]) -> list[str]:
    wanted = []
    for part in names:
        token = "".join(part.split()).casefold()
        if token and token not in wanted:
            wanted.append(token)
    if not wanted:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                select line_user_id, display_name
                from ops.line_access
                where is_allowed
                """
            )
        ).fetchall()
    found = []
    for line_user_id, display_name in rows:
        tokens = name_tokens(display_name or "")
        if any(token in tokens for token in wanted) and line_user_id not in found:
            found.append(line_user_id)
    return found


def push_recipient_ids(engine) -> list[str]:
    explicit = explicit_push_user_ids()
    if explicit:
        return explicit
    return line_user_ids_for_names(engine, push_names())


def state_path() -> Path:
    raw = (os.getenv("TAR_TRANSFER_PUSH_STATE") or "").strip()
    if raw:
        return Path(raw)
    return Path.home() / ".local/state/kcw-api/tar-transfer-push-date"


def already_sent(day: date, path: Path | None = None) -> bool:
    file = path or state_path()
    try:
        return file.read_text(encoding="utf-8").strip() == day.isoformat()
    except OSError:
        return False


def mark_sent(day: date, path: Path | None = None) -> None:
    file = path or state_path()
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_text(day.isoformat() + "\n", encoding="utf-8")


def push_yesterday(*, force: bool = False, today: date | None = None) -> str:
    send_day = today or bangkok_today()
    if not force and already_sent(send_day):
        return f"already sent {send_day.isoformat()}"

    engine = get_engine()
    recipients = push_recipient_ids(engine)
    if not recipients:
        names = ", ".join(push_names()) or "(none)"
        raise SystemExit(
            "No LINE recipient. Set TAR_TRANSFER_PUSH_LINE_USER_ID "
            f"or match an allowed display name ({names})."
        )

    report_day = send_day - timedelta(days=1)
    message = format_tar_transfer_message(load_tar_transfer(engine, report_day))
    for line_user_id in recipients:
        push_line_message(line_user_id, message)
    mark_sent(send_day)
    return f"pushed {report_day.isoformat()} to {len(recipients)} user(s)"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Push yesterday's TAR net to LINE")
    parser.add_argument("--force", action="store_true", help="Send again even if today already pushed")
    args = parser.parse_args(argv)
    print(push_yesterday(force=args.force))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""LINE notice when the HQ daily pipeline finishes.

Success sends the same text as the ยอดขาย command to peung, phu, and ice.
Failure sends the failed step to peung and turbo.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from src.bot.line_bot import push_line_message
from src.db import get_engine
from src.handlers.sales import handle_sales_query
from src.tar_transfer.push import line_user_ids_for_names

DEFAULT_OK_NAMES = "peung,phu,ice"
DEFAULT_FAIL_NAMES = "peung,turbo"


def _names(env_name: str, default: str) -> list[str]:
    raw = os.getenv(env_name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


def ok_names() -> list[str]:
    return _names("HQ_DAILY_PUSH_NAMES", DEFAULT_OK_NAMES)


def fail_names() -> list[str]:
    return _names("HQ_DAILY_PUSH_FAIL_NAMES", DEFAULT_FAIL_NAMES)


def log_excerpt(path: str, *, max_lines: int = 8) -> str:
    file = Path(path) if path else None
    if file is None or not file.is_file():
        return ""
    try:
        lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    kept = [line.rstrip() for line in lines if line.strip()]
    return "\n".join(kept[-max_lines:])


def format_hq_failure(step: str, code: int, excerpt: str = "") -> str:
    lines = [
        "HQ ประจำวันรันไม่สำเร็จ",
        f"ขั้นตอน: {step.strip() or 'ไม่ทราบ'}",
        f"exit {code}",
    ]
    body = (excerpt or "").strip()
    if body:
        lines.append(body[-800:])
    return "\n".join(lines)[:5000]


def push_to(engine, names: list[str], message: str) -> str:
    recipients = line_user_ids_for_names(engine, names)
    if not recipients:
        raise SystemExit(f"No LINE recipient for {', '.join(names) or '(none)'}")
    for line_user_id in recipients:
        push_line_message(line_user_id, message)
    return f"pushed to {len(recipients)} user(s)"


def push_ok() -> str:
    engine = get_engine()
    message = handle_sales_query(engine, "ยอดขาย")
    return push_to(engine, ok_names(), message)


def push_fail(step: str, code: int, log_path: str = "") -> str:
    engine = get_engine()
    message = format_hq_failure(step, code, log_excerpt(log_path))
    return push_to(engine, fail_names(), message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Push the HQ daily run result to LINE")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("ok", help="Send ยอดขาย to peung, phu, and ice")
    fail = sub.add_parser("fail", help="Send the failure to peung and turbo")
    fail.add_argument("--code", type=int, default=1)
    fail.add_argument("--step", default="")
    fail.add_argument("--log", default="")
    args = parser.parse_args(argv)
    if args.mode == "ok":
        print(push_ok())
    else:
        print(push_fail(args.step, args.code, args.log))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

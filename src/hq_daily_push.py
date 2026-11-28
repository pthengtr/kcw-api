"""LINE notice when the HQ daily pipeline finishes.

Success sends today's ยอดขาย (Bangkok date) to peung, phu, and ice.
A bare ยอดขาย command uses yesterday before 19:00, so the daily push
always passes today's date.
Failure sends the failed step to peung and turbo.

Channel: prefers the outbound/"new" OA (bot v2) when dual channels are
configured — HQ_DAILY_LINE_CHANNEL or LINE_OUTBOUND_CHANNEL, else "new".
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

load_dotenv()

from src.bot.line_bot import (  # noqa: E402
    outbound_line_channel,
    push_line_message,
)
from src.db import get_engine  # noqa: E402
from src.handlers.sales import handle_sales_query  # noqa: E402
from src.tar_transfer.push import line_user_ids_for_names  # noqa: E402

DEFAULT_OK_NAMES = "peung,phu,ice"
DEFAULT_FAIL_NAMES = "peung,turbo"
BANGKOK = ZoneInfo("Asia/Bangkok")


def _names(env_name: str, default: str) -> list[str]:
    raw = os.getenv(env_name, default)
    return [part.strip() for part in raw.split(",") if part.strip()]


def ok_names() -> list[str]:
    return _names("HQ_DAILY_PUSH_NAMES", DEFAULT_OK_NAMES)


def fail_names() -> list[str]:
    return _names("HQ_DAILY_PUSH_FAIL_NAMES", DEFAULT_FAIL_NAMES)


def outbound_preference() -> str:
    return (
        os.getenv("HQ_DAILY_LINE_CHANNEL")
        or os.getenv("LINE_OUTBOUND_CHANNEL")
        or "new"
    ).strip() or "new"


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

    # Prefer bot v2 / "new" without exclusive bind so a 429 on one OA can
    # fall through to the other (see _access_tokens_to_try + 429 retry).
    pref = outbound_preference()
    previous_outbound = os.environ.get("LINE_OUTBOUND_CHANNEL")
    os.environ["LINE_OUTBOUND_CHANNEL"] = pref
    try:
        try:
            for line_user_id in recipients:
                push_line_message(line_user_id, message)
        except requests.HTTPError as exc:
            resp = getattr(exc, "response", None)
            if resp is not None and resp.status_code == 429:
                return (
                    "quota 429 for ยอดขาย; "
                    "set LINE_CHANNEL_SECRET_2 + LINE_CHANNEL_ACCESS_TOKEN_2 "
                    "for bot v2 (or wait for monthly reset)"
                )
            raise
    finally:
        if previous_outbound is None:
            os.environ.pop("LINE_OUTBOUND_CHANNEL", None)
        else:
            os.environ["LINE_OUTBOUND_CHANNEL"] = previous_outbound

    channel = outbound_line_channel(pref)
    channel_name = channel.name if channel else "default"
    return f"pushed to {len(recipients)} user(s) via {channel_name}"


def bangkok_today() -> str:
    return datetime.now(BANGKOK).date().isoformat()


def push_ok() -> str:
    engine = get_engine()
    message = handle_sales_query(engine, f"ยอดขาย {bangkok_today()}")
    return push_to(engine, ok_names(), message)


def push_fail(step: str, code: int, log_path: str = "") -> str:
    engine = get_engine()
    message = format_hq_failure(step, code, log_excerpt(log_path))
    return push_to(engine, fail_names(), message)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Push the HQ daily run result to LINE")
    sub = parser.add_subparsers(dest="mode", required=True)
    sub.add_parser("ok", help="Send today's ยอดขาย to peung, phu, and ice")
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

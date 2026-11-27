"""Till-side worker: speak Thai when a cloud QR payment is confirmed.

Runs on a PC with speakers near the Tiger cashbox (not on HQ — no soundcard,
and Tiger Open API has no TTS). Claims ``tiger_pay.cloud_qr_payment`` rows
with ``status='C'`` and ``announced_at is null``, then speaks:

  ชำระเงินผ่าน QR สำเร็จ จำนวน {amount} บาท

Env:
  ANNOUNCE_POLL_INTERVAL_SECONDS  default 1.0
  ANNOUNCE_LOOKBACK_HOURS         default 24
  ANNOUNCE_WORKER_ID              default hostname
  ANNOUNCE_DRY_RUN                1 = print phrase, do not speak
  SUPABASE_DB_*                   same DB env as companion (via src.db)
"""

from __future__ import annotations

import logging
import os
import signal
import socket
import sys
import time

from dotenv import load_dotenv

from src.db import get_engine
from src.tiger_pay import cloud_qr_repos
from src.tiger_pay.announce_tts import (
    cloud_qr_success_phrase,
    env_flag,
    env_float,
    speak_thai,
)

load_dotenv()

logger = logging.getLogger("kcw.tiger_pay.announce_worker")


def _worker_id() -> str:
    raw = os.getenv("ANNOUNCE_WORKER_ID")
    if raw and str(raw).strip():
        return str(raw).strip()[:120]
    try:
        return socket.gethostname()[:120] or "announce"
    except Exception:
        return "announce"


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def run_once(engine, *, worker_id: str, lookback_hours: float, dry_run: bool) -> bool:
    """Claim and announce at most one payment. Returns True if work was done."""
    row = cloud_qr_repos.claim_next_cloud_qr_announce(
        engine,
        worker_id=worker_id,
        lookback_hours=lookback_hours,
    )
    if row is None:
        return False
    phrase = cloud_qr_success_phrase(row)
    logger.info(
        "announcing cloud QR id=%s bill=%s amount=%s",
        row.get("id"),
        row.get("pos_bill_number"),
        row.get("paid_amount") if row.get("paid_amount") is not None else row.get("amount"),
    )
    try:
        speak_thai(phrase, dry_run=dry_run)
    except Exception:
        logger.exception(
            "TTS failed after claim id=%s; row stays announced to avoid loops",
            row.get("id"),
        )
    return True


def main() -> int:
    _configure_logging()
    interval = max(0.2, env_float("ANNOUNCE_POLL_INTERVAL_SECONDS", 1.0))
    lookback = max(0.1, env_float("ANNOUNCE_LOOKBACK_HOURS", 24.0))
    dry_run = env_flag("ANNOUNCE_DRY_RUN", False)
    worker_id = _worker_id()

    stop = False

    def _handle_signal(signum, _frame) -> None:
        nonlocal stop
        logger.info("received signal %s; stopping", signum)
        stop = True

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            signal.signal(sig, _handle_signal)
        except Exception:
            pass

    engine = get_engine()
    logger.info(
        "cloud QR announce worker starting id=%s interval=%.2fs lookback=%.1fh dry_run=%s",
        worker_id,
        interval,
        lookback,
        dry_run,
    )

    while not stop:
        try:
            did = run_once(
                engine,
                worker_id=worker_id,
                lookback_hours=lookback,
                dry_run=dry_run,
            )
            if did:
                continue
        except Exception:
            logger.exception("announce cycle failed; backing off")
            time.sleep(min(30.0, max(2.0, interval * 4)))
            continue
        time.sleep(interval)

    logger.info("cloud QR announce worker stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())

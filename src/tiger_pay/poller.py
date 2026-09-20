from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

from src.db import get_engine
from src.tiger_pay.config import get_tiger_pay_settings
from src.tiger_pay.payment_service import (
    poll_attempt_once,
    recover_active_attempts,
    recover_sending_attempts,
)
from src.tiger_pay import repos
from src.tiger_pay.status import is_active_status

logger = logging.getLogger("kcw.tiger_pay.poller")

_WEBHOOK_WARN_INTERVAL_SECONDS = 15 * 60
_leader_lock_fh: IO[str] | None = None


def _default_poller_lock_path() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR") or "/tmp"
    return Path(runtime) / "kcw-tiger-pay-poller.lock"


def try_acquire_poller_leadership(*, lock_path: str | Path | None = None) -> bool:
    """First worker to lock the file runs the device poller. No-op lock on Windows."""
    global _leader_lock_fh
    if os.name == "nt":
        return True
    import fcntl

    path = Path(lock_path) if lock_path is not None else _default_poller_lock_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = open(path, "a+", encoding="utf-8")
    try:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        return False
    fh.seek(0)
    fh.truncate()
    fh.write(str(os.getpid()))
    fh.flush()
    _leader_lock_fh = fh
    return True


def release_poller_leadership() -> None:
    global _leader_lock_fh
    if _leader_lock_fh is None:
        return
    try:
        _leader_lock_fh.close()
    except Exception:
        logger.debug("poller lock close failed", exc_info=True)
    _leader_lock_fh = None


def webhook_received_recently(
    last_received_at: datetime | None,
    *,
    quiet_seconds: float,
    now: datetime | None = None,
) -> bool:
    """True when a webhook landed inside ``quiet_seconds`` (skip device GETs)."""
    if quiet_seconds <= 0 or last_received_at is None:
        return False
    now_utc = now or datetime.now(timezone.utc)
    last_utc = (
        last_received_at
        if last_received_at.tzinfo
        else last_received_at.replace(tzinfo=timezone.utc)
    )
    age_seconds = (now_utc - last_utc.astimezone(timezone.utc)).total_seconds()
    return age_seconds < quiet_seconds


class PaymentStatusPoller:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._failure_backoff_seconds = 0.0
        self._last_webhook_warn_at = 0.0

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop.clear()
        self._task = asyncio.create_task(self._run(), name="tiger-pay-payment-poller")

    async def stop(self) -> None:
        self._stop.set()
        if self._task is None:
            return
        try:
            await asyncio.wait_for(self._task, timeout=5)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            self._task.cancel()
        self._task = None

    async def _run(self) -> None:
        settings = get_tiger_pay_settings()
        interval = settings.tiger_pay_poll_interval_seconds
        # One shared engine for the poller process lifetime.
        engine = get_engine()

        try:
            await asyncio.to_thread(recover_active_attempts, engine)
            logger.info("Tiger Pay startup recovery complete")
        except Exception:
            logger.exception("Tiger Pay startup recovery failed")
            self._failure_backoff_seconds = max(5.0, interval)

        while not self._stop.is_set():
            try:
                await self._poll_active_once(engine)
                self._failure_backoff_seconds = 0.0
            except Exception:
                # Avoid log/conn spam every 1.5s when DB pooler is full.
                self._failure_backoff_seconds = min(
                    60.0,
                    max(5.0, (self._failure_backoff_seconds or interval) * 2),
                )
                logger.exception(
                    "Tiger Pay poller cycle failed; backing off %.1fs",
                    self._failure_backoff_seconds,
                )

            sleep_for = self._failure_backoff_seconds or interval
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=sleep_for)
            except asyncio.TimeoutError:
                continue

    async def _poll_active_once(self, engine) -> None:
        skip_device = await asyncio.to_thread(self._webhook_quiet_for_device_poll, engine)
        if skip_device:
            logger.debug("Tiger Pay skip device poll; webhook is fresh")
        else:
            active = await asyncio.to_thread(repos.list_active_payment_attempts, engine)
            for attempt in active:
                if not is_active_status(str(attempt.get("status") or "")):
                    continue
                await asyncio.to_thread(poll_attempt_once, engine, attempt)
        await asyncio.to_thread(recover_sending_attempts, engine)
        await asyncio.to_thread(self._warn_if_webhooks_stale, engine)

    def _webhook_quiet_for_device_poll(self, engine) -> bool:
        settings = get_tiger_pay_settings()
        quiet_seconds = float(settings.tiger_pay_poll_webhook_quiet_seconds)
        if quiet_seconds <= 0:
            return False
        try:
            last = repos.latest_webhook_received_at(engine)
        except Exception:
            logger.debug("webhook_event table not readable for poll skip", exc_info=True)
            return False
        return webhook_received_recently(last, quiet_seconds=quiet_seconds)

    def _warn_if_webhooks_stale(self, engine) -> None:
        settings = get_tiger_pay_settings()
        stale_hours = float(settings.tiger_pay_webhook_stale_hours)
        now_mono = time.monotonic()
        if now_mono - self._last_webhook_warn_at < _WEBHOOK_WARN_INTERVAL_SECONDS:
            return
        try:
            last = repos.latest_webhook_received_at(engine)
        except Exception:
            logger.debug("webhook_event table not readable", exc_info=True)
            return

        age_hours: float | None
        if last is None:
            age_hours = None
        else:
            last_utc = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
            age_hours = (
                datetime.now(timezone.utc) - last_utc.astimezone(timezone.utc)
            ).total_seconds() / 3600
            if age_hours < stale_hours:
                return
        self._last_webhook_warn_at = now_mono
        logger.warning(
            "Tiger Pay webhooks look stale last_received_at=%s stale_after_hours=%s "
            "(companion is poller-only until the device posts /webhooks/tiger-pay)",
            last.isoformat() if last is not None else None,
            stale_hours,
        )


payment_status_poller = PaymentStatusPoller()

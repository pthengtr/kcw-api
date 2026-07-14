from __future__ import annotations

import asyncio
import logging

from src.db import get_engine
from src.tiger_pay.config import get_tiger_pay_settings
from src.tiger_pay.payment_service import poll_attempt_once, recover_active_attempts
from src.tiger_pay import repos
from src.tiger_pay.status import is_active_status

logger = logging.getLogger("kcw.tiger_pay.poller")


class PaymentStatusPoller:
    def __init__(self) -> None:
        self._task: asyncio.Task[None] | None = None
        self._stop = asyncio.Event()
        self._failure_backoff_seconds = 0.0

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
        active = await asyncio.to_thread(repos.list_active_payment_attempts, engine)
        for attempt in active:
            if not is_active_status(str(attempt.get("status") or "")):
                continue
            await asyncio.to_thread(poll_attempt_once, engine, attempt)


payment_status_poller = PaymentStatusPoller()

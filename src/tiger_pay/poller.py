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

        try:
            await asyncio.to_thread(recover_active_attempts, get_engine())
            logger.info("Tiger Pay startup recovery complete")
        except Exception:
            logger.exception("Tiger Pay startup recovery failed")

        while not self._stop.is_set():
            try:
                await self._poll_active_once()
            except Exception:
                logger.exception("Tiger Pay poller cycle failed")

            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval)
            except asyncio.TimeoutError:
                continue

    async def _poll_active_once(self) -> None:
        engine = get_engine()
        active = await asyncio.to_thread(repos.list_active_payment_attempts, engine)
        for attempt in active:
            if not is_active_status(str(attempt.get("status") or "")):
                continue
            await asyncio.to_thread(poll_attempt_once, engine, attempt)


payment_status_poller = PaymentStatusPoller()

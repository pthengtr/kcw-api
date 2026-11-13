from __future__ import annotations

import threading
import time
from unittest.mock import MagicMock

from src.jobs.queue import reclaim_stale_running_jobs
from src.jobs.worker import (
    _heartbeat_stale_after_seconds,
    _start_heartbeat_thread,
)


def test_heartbeat_stale_after_scales_with_interval():
    assert _heartbeat_stale_after_seconds(10) == 30.0
    assert _heartbeat_stale_after_seconds(5) == 30.0
    assert _heartbeat_stale_after_seconds(20) == 60.0


def test_reclaim_stale_running_jobs_returns_ids(monkeypatch):
    executed = {}

    class _Result:
        def mappings(self):
            return self

        def all(self):
            return [{"id": 11}, {"id": 12}]

    class _Conn:
        def execute(self, sql, params):
            executed["params"] = params
            return _Result()

    class _Engine:
        def begin(self):
            return self

        def __enter__(self):
            return _Conn()

        def __exit__(self, *args):
            return False

    ids = reclaim_stale_running_jobs(_Engine(), "HQ-UBUNTU-SERVER")
    assert ids == [11, 12]
    assert executed["params"]["worker_name"] == "HQ-UBUNTU-SERVER"
    assert "restart" in executed["params"]["error_message"]


def test_heartbeat_thread_keeps_beating_while_main_blocks(monkeypatch):
    calls: list[str] = []
    lock = threading.Lock()

    def _fake_send(engine, worker_name, status):
        with lock:
            calls.append(status)

    monkeypatch.setattr("src.jobs.worker._send_heartbeat", _fake_send)

    status_holder = {"status": "running", "lock": threading.Lock()}
    stop = _start_heartbeat_thread(
        engine=MagicMock(),
        worker_name="HQ-UBUNTU-SERVER",
        interval_seconds=1,
        status_holder=status_holder,
    )

    # Simulate a long blocking job on the "main" thread.
    time.sleep(2.5)
    stop.set()
    time.sleep(0.2)

    with lock:
        assert len(calls) >= 2
        assert all(status == "running" for status in calls)

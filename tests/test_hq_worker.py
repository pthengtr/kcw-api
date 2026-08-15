from __future__ import annotations

from src.jobs.hq_worker import hq_worker_sort_key, pick_hq_worker
from src.handlers.companion_entry import is_companion_command


class _FakeEngine:
    pass


def test_pick_hq_worker_prefers_ubuntu(monkeypatch):
    monkeypatch.setattr(
        "src.jobs.hq_worker.get_all_worker_status",
        lambda engine, offline_after_seconds=30: [
            {"worker_name": "HQ-PC", "online_status": "online"},
            {"worker_name": "HQ-UBUNTU-SERVER", "online_status": "online"},
            {"worker_name": "SYP-PC", "online_status": "online"},
        ],
    )
    assert pick_hq_worker(_FakeEngine()) == "HQ-UBUNTU-SERVER"


def test_pick_hq_worker_falls_back_to_hq_pc(monkeypatch):
    monkeypatch.setattr(
        "src.jobs.hq_worker.get_all_worker_status",
        lambda engine, offline_after_seconds=30: [
            {"worker_name": "HQ-PC", "online_status": "online"},
            {"worker_name": "HQ-UBUNTU-SERVER", "online_status": "offline"},
        ],
    )
    assert pick_hq_worker(_FakeEngine()) == "HQ-PC"


def test_hq_worker_sort_key_ubuntu_first():
    names = ["SYP-PC", "HQ-PC", "HQ-UBUNTU-SERVER"]
    ordered = sorted(names, key=hq_worker_sort_key)
    assert ordered[0] == "HQ-UBUNTU-SERVER"
    assert ordered[1] == "HQ-PC"


def test_companion_command_variants():
    assert is_companion_command("ไทเกอร์")
    assert is_companion_command("tiger pay")
    assert is_companion_command("เก็บเงิน")
    assert not is_companion_command("เช็คสต็อก")

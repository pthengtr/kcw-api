from __future__ import annotations

from src.jobs.hq_worker import pick_syp_worker, worker_sort_key


class _FakeEngine:
    pass


def test_pick_syp_worker_prefers_ubuntu(monkeypatch):
    monkeypatch.setattr(
        "src.jobs.hq_worker.get_all_worker_status",
        lambda engine, offline_after_seconds=30: [
            {"worker_name": "SYP-PC", "online_status": "online"},
            {"worker_name": "SYP-UBUNTU-SERVER", "online_status": "online"},
        ],
    )
    assert pick_syp_worker(_FakeEngine()) == "SYP-UBUNTU-SERVER"


def test_pick_syp_worker_falls_back_to_syp_pc(monkeypatch):
    monkeypatch.setattr(
        "src.jobs.hq_worker.get_all_worker_status",
        lambda engine, offline_after_seconds=30: [
            {"worker_name": "SYP-PC", "online_status": "online"},
            {"worker_name": "SYP-UBUNTU-SERVER", "online_status": "offline"},
        ],
    )
    assert pick_syp_worker(_FakeEngine()) == "SYP-PC"


def test_worker_sort_key_ubuntu_before_pc_within_site():
    names = ["SYP-PC", "HQ-PC", "SYP-UBUNTU-SERVER", "HQ-UBUNTU-SERVER"]
    ordered = sorted(names, key=worker_sort_key)
    assert ordered == [
        "HQ-UBUNTU-SERVER",
        "HQ-PC",
        "SYP-UBUNTU-SERVER",
        "SYP-PC",
    ]

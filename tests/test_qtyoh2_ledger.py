"""Unit tests for QTYOH2 ledger sync (no live PARTS9)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from src.db.qtyoh2_ledger import (
    Qtyoh2SyncResult,
    qtyoh2_sync_on_read_enabled,
    sync_qtyoh2_from_ledger,
    sync_qtyoh2_from_ledger_many,
)


def test_flag_defaults_on(monkeypatch):
    monkeypatch.delenv("QTYOH2_SYNC_ON_READ", raising=False)
    assert qtyoh2_sync_on_read_enabled() is True


def test_flag_off(monkeypatch):
    monkeypatch.setenv("QTYOH2_SYNC_ON_READ", "0")
    assert qtyoh2_sync_on_read_enabled() is False
    result = sync_qtyoh2_from_ledger("12051563", engine=MagicMock())
    assert result.skipped and result.reason == "flag_off"


def test_sync_updates_when_ledger_differs(monkeypatch):
    monkeypatch.setenv("QTYOH2_SYNC_ON_READ", "1")

    read_row = {
        "icmas_id": 42,
        "beg": 183.0,
        "old_qtyoh2": 200.0,
        "pi_units": 22277.0,
        "si_units": 22245.0,  # → new 215
    }

    conn = MagicMock()
    conn.execute.side_effect = [
        MagicMock(mappings=lambda: MagicMock(first=lambda: read_row)),
        SimpleNamespace(rowcount=1),
    ]
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None

    result = sync_qtyoh2_from_ledger("12051563", engine=engine)
    assert result == Qtyoh2SyncResult(
        bcode="12051563",
        old_qtyoh2=200.0,
        new_qtyoh2=215.0,
        updated=True,
        skipped=False,
        reason="updated",
    )
    assert conn.execute.call_count == 2


def test_sync_unchanged_skips_update(monkeypatch):
    monkeypatch.setenv("QTYOH2_SYNC_ON_READ", "1")
    read_row = {
        "icmas_id": 1,
        "beg": 10.0,
        "old_qtyoh2": 15.0,
        "pi_units": 20.0,
        "si_units": 15.0,
    }
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = read_row
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None

    result = sync_qtyoh2_from_ledger("x", engine=engine)
    assert result.updated is False
    assert result.new_qtyoh2 == 15.0
    assert conn.execute.call_count == 1


def test_batch_dedupes(monkeypatch):
    monkeypatch.setenv("QTYOH2_SYNC_ON_READ", "1")
    read_row = {
        "icmas_id": 1,
        "beg": 0.0,
        "old_qtyoh2": 0.0,
        "pi_units": 0.0,
        "si_units": 0.0,
    }
    conn = MagicMock()
    conn.execute.return_value.mappings.return_value.first.return_value = read_row
    engine = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None

    results = sync_qtyoh2_from_ledger_many(["a", "a", "b"], engine=engine)
    assert [r.bcode for r in results] == ["a", "b"]

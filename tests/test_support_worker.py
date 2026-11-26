"""Unit tests for support worker reclaim helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from src.support import worker


def test_stale_running_minutes_above_agent_timeout():
    assert worker.STALE_RUNNING_MINUTES >= 45.0


def test_requeue_running_ticket_updates_and_logs_event():
    conn = MagicMock()
    result = MagicMock()
    result.mappings.return_value.first.return_value = {"id": "t1"}
    conn.execute.return_value = result
    begin = MagicMock()
    begin.__enter__.return_value = conn
    begin.__exit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin

    assert worker.requeue_running_ticket(engine, "t1", reason="sigterm") is True
    assert conn.execute.call_count == 2
    first_sql = str(conn.execute.call_args_list[0].args[0])
    assert "status = 'pending'" in first_sql
    assert "status = 'running'" in first_sql
    second_params = conn.execute.call_args_list[1].args[1]
    assert second_params["id"] == "t1"
    event_sql = str(conn.execute.call_args_list[1].args[0])
    assert "requeued" in event_sql


def test_requeue_running_ticket_noop_when_not_running():
    conn = MagicMock()
    result = MagicMock()
    result.mappings.return_value.first.return_value = None
    conn.execute.return_value = result
    begin = MagicMock()
    begin.__enter__.return_value = conn
    begin.__exit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin

    assert worker.requeue_running_ticket(engine, "t1", reason="sigterm") is False
    assert conn.execute.call_count == 1


def test_reclaim_stale_running_startup_has_no_age_filter():
    conn = MagicMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = [{"id": "a"}, {"id": "b"}]
    conn.execute.return_value = result
    begin = MagicMock()
    begin.__enter__.return_value = conn
    begin.__exit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin

    ids = worker.reclaim_stale_running(engine, all_running=True)
    assert ids == ["a", "b"]
    select_sql = str(conn.execute.call_args_list[0].args[0])
    assert "make_interval" not in select_sql
    assert "status = 'running'" in select_sql
    # one update returning + one event insert per id
    assert conn.execute.call_count == 1 + 2


def test_reclaim_stale_running_age_filter():
    conn = MagicMock()
    result = MagicMock()
    result.mappings.return_value.all.return_value = []
    conn.execute.return_value = result
    begin = MagicMock()
    begin.__enter__.return_value = conn
    begin.__exit__.return_value = None
    engine = MagicMock()
    engine.begin.return_value = begin

    assert worker.reclaim_stale_running(engine, max_age_minutes=12) == []
    select_sql = str(conn.execute.call_args_list[0].args[0])
    assert "interval '1 minute'" in select_sql
    assert "make_interval" not in select_sql
    params = conn.execute.call_args_list[0].args[1]
    assert params["mins"] == 12.0

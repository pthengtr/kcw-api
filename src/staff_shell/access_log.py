"""Durable audit of who opened / switched / left staff services."""

from __future__ import annotations

from typing import Any


def log_service_access(
    *,
    line_user_id: str,
    display_name: str = "",
    branch: str = "",
    service_id: str,
    source: str,
    action: str,
    path: str | None = None,
) -> None:
    """Best-effort insert into ops.service_access_log. Never raises to callers."""
    uid = (line_user_id or "").strip()
    sid = (service_id or "").strip()
    if not uid or not sid:
        return
    try:
        from src.db.engine import get_engine

        engine = get_engine()
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                insert into ops.service_access_log (
                    line_user_id,
                    display_name,
                    branch,
                    service_id,
                    source,
                    action,
                    path
                )
                values (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uid,
                    (display_name or "").strip() or None,
                    (branch or "").strip().upper() or None,
                    sid,
                    (source or "direct").strip() or "direct",
                    (action or "open").strip() or "open",
                    (path or "").strip() or None,
                ),
            )
    except Exception as exc:  # noqa: BLE001
        print(f"service_access_log write failed: {exc}")


def record_service_menu_usage(
    *,
    line_user_id: str,
    service_id: str,
) -> None:
    """Upsert per-user per-service tap counts for Phase 2 personalized menus.

    Best-effort; never raises to callers. Counts both Flex menu taps and the
    same primary LINE commands when typed.
    """
    uid = (line_user_id or "").strip()
    sid = (service_id or "").strip()
    if not uid or not sid:
        return
    try:
        from src.db.engine import get_engine

        engine = get_engine()
        with engine.begin() as conn:
            conn.exec_driver_sql(
                """
                insert into ops.service_menu_usage (
                    line_user_id,
                    service_id,
                    click_count,
                    last_clicked_at
                )
                values (%s, %s, 1, now())
                on conflict (line_user_id, service_id) do update
                set
                    click_count = ops.service_menu_usage.click_count + 1,
                    last_clicked_at = now()
                """,
                (uid, sid),
            )
    except Exception as exc:  # noqa: BLE001
        print(f"service_menu_usage write failed: {exc}")


def log_rows_for_tests(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Helper for unit tests that stub the DB."""
    return list(rows)

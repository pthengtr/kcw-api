"""Shared staff shell: service catalog, session, launcher chrome."""

from src.staff_shell.catalog import (
    SERVICE_PERMISSIONS,
    WEB_SERVICES,
    filter_web_services,
    get_service,
    line_menu_entries,
)
from src.staff_shell.ui import inject_shell, render_shell_html

__all__ = [
    "SERVICE_PERMISSIONS",
    "WEB_SERVICES",
    "filter_web_services",
    "get_service",
    "inject_shell",
    "line_menu_entries",
    "render_shell_html",
]

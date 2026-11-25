from __future__ import annotations

import os
import re

from src.handlers.companion_entry import is_companion_command
from src.handlers.explorer_entry import is_explorer_command
from src.handlers.image import is_image_command
from src.handlers.pay_notes_entry import is_pay_notes_command
from src.handlers.receive_notes_entry import is_receive_notes_command
from src.handlers.stock_check_entry import is_stock_check_command
from src.handlers.hq_po_entry import is_hq_po_command
from src.handlers.hq_receive_entry import is_hq_receive_command
from src.handlers.online_sale_entry import is_online_sale_command
from src.handlers.transfer_entry import is_transfer_command
from src.staff_shell.catalog import (
    ServiceDef,
    all_line_menu_services,
    line_menu_entries,
    line_menu_help_service,
    line_menu_sections,
)

SERVICES_MENU_COMMANDS = {
    "menu",
    "เมนู",
    "services",
    "service",
}

# Minimal classic palette
_BTN_BG = "#F5F6F8"
_TITLE_COLOR = "#111111"
_CATEGORY_COLOR = "#64748B"
_LABEL_COLOR = "#1F2937"
_HELP_COLOR = "#64748B"

_DEFAULT_ICON_BASE = (
    "https://raw.githubusercontent.com/pthengtr/kcw-api/master/static/line_menu_icons"
)


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_SERVICES_MENU_NORM = {_normalize_cmd(c) for c in SERVICES_MENU_COMMANDS}


def is_services_menu_request(text: str) -> bool:
    return _normalize_cmd(text) in _SERVICES_MENU_NORM


def _icon_base_url() -> str:
    return (os.getenv("LINE_MENU_ICON_BASE_URL") or _DEFAULT_ICON_BASE).rstrip("/")


def _icon_url(icon_key: str) -> str:
    key = (icon_key or "app").strip() or "app"
    return f"{_icon_base_url()}/{key}.png"


def _category_header(title: str, *, first: bool) -> dict:
    return {
        "type": "text",
        "text": title,
        "size": "xs",
        "weight": "bold",
        "color": _CATEGORY_COLOR,
        "margin": "md" if not first else "sm",
    }


def _service_cell(svc: ServiceDef) -> dict:
    """Left-aligned outline icon + label on a light gray tap target.

    Icons are only valid inside baseline boxes (LINE Flex schema).
    """
    return {
        "type": "box",
        "layout": "baseline",
        "flex": 1,
        "backgroundColor": _BTN_BG,
        "cornerRadius": "8px",
        "paddingAll": "10px",
        "spacing": "sm",
        "action": {
            "type": "message",
            "label": svc.label[:40],
            "text": svc.line_command,
        },
        "contents": [
            {
                "type": "icon",
                "url": _icon_url(svc.icon),
                "size": "xxs",  # 16px — closest LINE size to 14–16px
                "aspectRatio": "1:1",
            },
            {
                "type": "text",
                "text": svc.label,
                "size": "sm",
                "color": _LABEL_COLOR,
                "wrap": True,
                "flex": 1,
                "align": "start",
            },
        ],
    }


def _button_rows(services: list[ServiceDef]) -> list[dict]:
    """Pack service cells into horizontal pairs (2 columns)."""
    rows: list[dict] = []
    for i in range(0, len(services), 2):
        pair = services[i : i + 2]
        contents = [_service_cell(svc) for svc in pair]
        if len(contents) == 1:
            contents.append({"type": "filler", "flex": 1})
        rows.append(
            {
                "type": "box",
                "layout": "horizontal",
                "spacing": "sm",
                "margin": "sm",
                "contents": contents,
            }
        )
    return rows


def _help_footer(svc: ServiceDef) -> dict:
    return {
        "type": "box",
        "layout": "baseline",
        "margin": "lg",
        "spacing": "sm",
        "action": {
            "type": "message",
            "label": svc.label[:40],
            "text": svc.line_command,
        },
        "contents": [
            {
                "type": "icon",
                "url": _icon_url(svc.icon),
                "size": "xxs",
                "aspectRatio": "1:1",
            },
            {
                "type": "text",
                "text": svc.label,
                "size": "sm",
                "color": _HELP_COLOR,
                "flex": 1,
                "align": "start",
            },
        ],
    }


def handle_services_menu() -> dict:
    """Compact categorized Flex card; each cell sends the service command directly."""
    body_contents: list[dict] = [
        {
            "type": "text",
            "text": "KCW Services",
            "weight": "bold",
            "size": "lg",
            "color": _TITLE_COLOR,
        },
        {"type": "separator", "margin": "md"},
    ]

    for idx, (title, services) in enumerate(line_menu_sections()):
        body_contents.append(_category_header(title, first=idx == 0))
        body_contents.extend(_button_rows(services))

    help_svc = line_menu_help_service()
    if help_svc is not None:
        body_contents.append({"type": "separator", "margin": "lg"})
        body_contents.append(_help_footer(help_svc))

    return {
        "type": "flex",
        "altText": "KCW Services — กดเลือก",
        "contents": {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "none",
                "paddingAll": "16px",
                "contents": body_contents,
            },
        },
    }


def iter_services_menu_buttons(msg: dict | None = None) -> list[dict]:
    """Flatten message-action nodes from a Flex menu (nested 2-column cells)."""
    root = msg if msg is not None else handle_services_menu()
    body = (((root or {}).get("contents") or {}).get("body") or {}).get("contents") or []
    out: list[dict] = []

    def walk(nodes: list) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            action = node.get("action")
            if isinstance(action, dict) and action.get("type") == "message":
                # Normalize so callers can treat cells like legacy button nodes.
                out.append(
                    {
                        "type": "button",
                        "action": action,
                        "flex": node.get("flex", 1),
                    }
                )
                continue
            nested = node.get("contents")
            if isinstance(nested, list):
                walk(nested)

    walk(body)
    return out


def services_menu_button_messages() -> list[str]:
    return [message for _label, message in line_menu_entries()]


def services_menu_handlers_match() -> dict[str, bool]:
    by_id = {svc.id: svc.line_command for svc in all_line_menu_services()}
    return {
        "stock_check": is_stock_check_command(by_id["stock-check"]),
        "companion": is_companion_command(by_id["companion"]),
        "explorer": is_explorer_command(by_id["parts9-explorer"]),
        "transfer": is_transfer_command(by_id["transfer"]),
        "hq_po": is_hq_po_command(by_id["hq-po"]),
        "hq_receive": is_hq_receive_command(by_id["hq-receive"]),
        "online_sale": is_online_sale_command(by_id["online-sale"]),
        "pay_notes": is_pay_notes_command(by_id["pay-notes"]),
        "receive_notes": is_receive_notes_command(by_id["receive-notes"]),
        "image": is_image_command(by_id["product-image"]),
    }

from __future__ import annotations

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
    line_menu_entries,
    line_menu_sections,
)

SERVICES_MENU_COMMANDS = {
    "menu",
    "เมนู",
    "services",
    "service",
}


def _normalize_cmd(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


_SERVICES_MENU_NORM = {_normalize_cmd(c) for c in SERVICES_MENU_COMMANDS}


def is_services_menu_request(text: str) -> bool:
    return _normalize_cmd(text) in _SERVICES_MENU_NORM


def _msg_button(label: str, message: str) -> dict:
    return {
        "type": "button",
        "style": "secondary",
        "height": "sm",
        "flex": 1,
        "action": {"type": "message", "label": label[:40], "text": message},
    }


def _category_header(title: str, *, first: bool) -> dict:
    return {
        "type": "text",
        "text": title,
        "size": "xs",
        "weight": "bold",
        "color": "#64748B",
        "margin": "md" if not first else "sm",
    }


def _button_rows(services: list[ServiceDef]) -> list[dict]:
    """Pack service buttons into horizontal pairs (2 columns)."""
    rows: list[dict] = []
    for i in range(0, len(services), 2):
        pair = services[i : i + 2]
        contents = [_msg_button(svc.label, svc.line_command) for svc in pair]
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


def handle_services_menu() -> dict:
    """Compact categorized Flex card; each button sends the service command directly."""
    body_contents: list[dict] = [
        {
            "type": "text",
            "text": "เมนูบริการ",
            "weight": "bold",
            "size": "lg",
            "color": "#111111",
        },
        {
            "type": "text",
            "text": "กดเลือกบริการที่ต้องการใช้",
            "size": "sm",
            "color": "#888888",
            "wrap": True,
            "margin": "sm",
        },
        {"type": "separator", "margin": "md"},
    ]

    for idx, (title, services) in enumerate(line_menu_sections()):
        body_contents.append(_category_header(title, first=idx == 0))
        body_contents.extend(_button_rows(services))

    return {
        "type": "flex",
        "altText": "เมนูบริการ KCW — กดเลือก",
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
    """Flatten button nodes from a Flex menu (nested 2-column rows)."""
    root = msg if msg is not None else handle_services_menu()
    body = (((root or {}).get("contents") or {}).get("body") or {}).get("contents") or []
    out: list[dict] = []

    def walk(nodes: list) -> None:
        for node in nodes:
            if not isinstance(node, dict):
                continue
            if node.get("type") == "button":
                out.append(node)
            nested = node.get("contents")
            if isinstance(nested, list):
                walk(nested)

    walk(body)
    return out


def services_menu_button_messages() -> list[str]:
    return [message for _label, message in line_menu_entries()]


def services_menu_handlers_match() -> dict[str, bool]:
    checks = services_menu_button_messages()
    # Order matches all_line_menu_services(): web services then รูป, help.
    return {
        "stock_check": is_stock_check_command(checks[0]),
        "companion": is_companion_command(checks[1]),
        "explorer": is_explorer_command(checks[2]),
        "transfer": is_transfer_command(checks[3]),
        "hq_po": is_hq_po_command(checks[4]),
        "hq_receive": is_hq_receive_command(checks[5]),
        "online_sale": is_online_sale_command(checks[6]),
        "pay_notes": is_pay_notes_command(checks[7]),
        "receive_notes": is_receive_notes_command(checks[8]),
        "image": is_image_command(checks[9]),
    }

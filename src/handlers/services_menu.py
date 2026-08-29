from __future__ import annotations

import re

from src.handlers.companion_entry import is_companion_command
from src.handlers.explorer_entry import is_explorer_command
from src.handlers.image import is_image_command
from src.handlers.ops_entry import is_ops_command
from src.handlers.pay_notes_entry import is_pay_notes_command
from src.handlers.stock_check_entry import is_stock_check_command
from src.handlers.transfer_entry import is_transfer_command

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
        "margin": "sm",
        "action": {"type": "message", "label": label[:40], "text": message},
    }


def handle_services_menu() -> dict:
    """Flex card listing all KCW tool entry commands (tap sends message to bot)."""
    buttons = [
        _msg_button("เช็คสต็อก", "เช็คสต็อก"),
        _msg_button("ไทเกอร์เพย์", "ไทเกอร์"),
        _msg_button("ค้นหา PARTS9", "ค้นหา"),
        _msg_button("โอนสินค้า", "โอนสินค้า"),
        _msg_button("จัดการรูปสินค้า", "รูป"),
        _msg_button("ชำระเจ้าหนี้", "ชำระเจ้าหนี้"),
        _msg_button("สถานะใบสั่งซื้อ", "สถานะใบสั่งซื้อ"),
        _msg_button("วิธีใช้ทั้งหมด", "help"),
    ]
    return {
        "type": "flex",
        "altText": "เมนูบริการ KCW — กดเลือก",
        "contents": {
            "type": "bubble",
            "size": "mega",
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
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
                    *buttons,
                ],
            },
        },
    }


def services_menu_button_messages() -> list[str]:
    return [btn["action"]["text"] for btn in [
        _msg_button("เช็คสต็อก", "เช็คสต็อก"),
        _msg_button("ไทเกอร์เพย์", "ไทเกอร์"),
        _msg_button("ค้นหา PARTS9", "ค้นหา"),
        _msg_button("โอนสินค้า", "โอนสินค้า"),
        _msg_button("จัดการรูปสินค้า", "รูป"),
        _msg_button("ชำระเจ้าหนี้", "ชำระเจ้าหนี้"),
        _msg_button("สถานะใบสั่งซื้อ", "สถานะใบสั่งซื้อ"),
        _msg_button("วิธีใช้ทั้งหมด", "help"),
    ]]


def services_menu_handlers_match() -> dict[str, bool]:
    checks = services_menu_button_messages()
    return {
        "stock_check": is_stock_check_command(checks[0]),
        "companion": is_companion_command(checks[1]),
        "explorer": is_explorer_command(checks[2]),
        "transfer": is_transfer_command(checks[3]),
        "image": is_image_command(checks[4]),
        "pay_notes": is_pay_notes_command(checks[5]),
        "ops": is_ops_command(checks[6]),
    }

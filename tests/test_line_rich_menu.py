"""Rich menu message actions must match existing LINE command handlers."""

from __future__ import annotations

import json
from pathlib import Path

from src.handlers.companion_entry import is_companion_command
from src.handlers.explorer_entry import is_explorer_command
from src.handlers.image import is_image_command
from src.handlers.transfer_entry import is_transfer_command
from src.handlers.pay_notes_entry import is_pay_notes_command
from src.handlers.stock_check_entry import is_stock_check_command

SPEC = Path(__file__).resolve().parents[1] / "scripts" / "line_rich_menu" / "menu_spec.json"

EXPECTED_TEXTS = ["เช็คสต็อก", "ไทเกอร์", "ค้นหา", "โอนสินค้า", "รูป", "ชำระเจ้าหนี้"]


def test_rich_menu_message_actions_match_handlers():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    areas = spec["areas"]
    assert len(areas) == 6

    texts = [a["action"]["text"] for a in areas]
    assert texts == EXPECTED_TEXTS
    assert is_stock_check_command(texts[0])
    assert is_companion_command(texts[1])
    assert is_explorer_command(texts[2])
    assert is_transfer_command(texts[3])
    assert is_image_command(texts[4])
    assert is_pay_notes_command(texts[5])
    for area in areas:
        assert area["action"]["type"] == "message"


def test_rich_menu_geometry_is_line_full_size_3x2():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["size"] == {"width": 2500, "height": 1686}
    assert spec["chatBarText"] == "เมนู"

    areas = spec["areas"]
    assert [(a["bounds"]["x"], a["bounds"]["y"]) for a in areas] == [
        (0, 0),
        (833, 0),
        (1667, 0),
        (0, 749),
        (833, 749),
        (1667, 749),
    ]
    assert [a["bounds"]["width"] for a in areas] == [833, 834, 833, 833, 834, 833]
    assert [a["bounds"]["height"] for a in areas] == [749, 749, 749, 937, 937, 937]
    covered = sum(a["bounds"]["width"] * a["bounds"]["height"] for a in areas)
    assert covered == 2500 * 1686

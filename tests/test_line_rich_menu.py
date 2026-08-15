"""Rich menu message actions must match existing LINE command handlers."""

from __future__ import annotations

import json
from pathlib import Path

from src.handlers.companion_entry import is_companion_command
from src.handlers.explorer_entry import is_explorer_command
from src.handlers.stock_check_entry import is_stock_check_command

SPEC = Path(__file__).resolve().parents[1] / "scripts" / "line_rich_menu" / "menu_spec.json"


def test_rich_menu_message_actions_match_handlers():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    areas = spec["areas"]
    assert len(areas) == 3

    texts = [a["action"]["text"] for a in areas]
    assert texts == ["เช็คสต็อก", "ไทเกอร์", "ค้นหา"]
    assert is_stock_check_command(texts[0])
    assert is_companion_command(texts[1])
    assert is_explorer_command(texts[2])


def test_rich_menu_geometry_is_line_half_size():
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    assert spec["size"] == {"width": 2500, "height": 843}
    total_w = sum(a["bounds"]["width"] for a in spec["areas"])
    assert total_w == 2500
    for area in spec["areas"]:
        assert area["bounds"]["height"] == 843
        assert area["action"]["type"] == "message"

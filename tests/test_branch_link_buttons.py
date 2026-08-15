"""Short URI button replies hide long entry tokens in chat."""

from __future__ import annotations

from src.bot.branch_link_buttons import branch_uri_buttons


def test_branch_uri_buttons_hides_urls_behind_labels():
    long_url = "http://192.168.1.10:8787/stock-check/?t=" + ("x" * 200)
    msg = branch_uri_buttons(
        title="ตรวจนับสต็อก",
        alt_text="ตรวจนับสต็อก",
        links=[
            ("HQ", long_url, "online"),
            ("SYP", "", "offline"),
        ],
    )
    assert msg["type"] == "template"
    assert msg["template"]["type"] == "buttons"
    assert long_url not in msg["template"]["text"]
    assert "ออฟไลน์" in msg["template"]["text"]
    actions = msg["template"]["actions"]
    assert len(actions) == 1
    assert actions[0] == {"type": "uri", "label": "สำนักงานใหญ่", "uri": long_url}


def test_branch_uri_buttons_all_offline_falls_back_to_text():
    msg = branch_uri_buttons(
        title="ไทเกอร์เพย์",
        alt_text="ไทเกอร์เพย์",
        links=[("HQ", "", "offline"), ("SYP", "", "offline")],
    )
    assert msg["type"] == "text"
    assert "ยังไม่มีสาขาออนไลน์" in msg["text"]

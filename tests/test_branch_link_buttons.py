"""Short URI word-links hide long entry tokens in chat."""

from __future__ import annotations

from src.bot.branch_link_buttons import branch_uri_buttons


def test_branch_uri_buttons_hides_urls_behind_thai_words():
    long_url = "http://192.168.1.10:8787/stock-check/?t=" + ("x" * 200)
    msg = branch_uri_buttons(
        title="ตรวจนับสต็อก",
        alt_text="ตรวจนับสต็อก",
        links=[
            ("HQ", long_url, "online"),
            ("SYP", "", "offline"),
        ],
    )
    assert msg["type"] == "flex"
    assert long_url not in str(msg.get("altText"))
    body = msg["contents"]["body"]["contents"]
    texts = [c.get("text") for c in body if c.get("type") == "text"]
    assert "ตรวจนับสต็อก" in texts
    assert all(long_url not in (t or "") for t in texts)

    buttons = [c for c in body if c.get("type") == "button"]
    assert len(buttons) == 1
    assert buttons[0]["style"] == "link"
    assert buttons[0]["action"] == {
        "type": "uri",
        "label": "สำนักงานใหญ่",
        "uri": long_url,
    }
    assert any("ออฟไลน์" in (t or "") for t in texts)


def test_branch_uri_buttons_both_branches():
    long_url = "http://192.168.1.10:8787/stock-check/?t=abc"
    msg = branch_uri_buttons(
        title="ไทเกอร์เพย์",
        alt_text="ไทเกอร์เพย์",
        links=[
            ("HQ", long_url, "online"),
            ("SYP", long_url.replace("8787", "8000"), "online"),
        ],
    )
    buttons = [c for c in msg["contents"]["body"]["contents"] if c.get("type") == "button"]
    assert [b["action"]["label"] for b in buttons] == [
        "สำนักงานใหญ่",
        "สาขาสี่แยกพัฒนา",
    ]


def test_branch_uri_buttons_all_offline_falls_back_to_text():
    msg = branch_uri_buttons(
        title="ไทเกอร์เพย์",
        alt_text="ไทเกอร์เพย์",
        links=[("HQ", "", "offline"), ("SYP", "", "offline")],
    )
    assert msg["type"] == "text"
    assert "ยังไม่มีสาขาออนไลน์" in msg["text"]

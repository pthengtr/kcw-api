"""Build short LINE button replies that hide long entry URLs behind URI actions."""

from __future__ import annotations

BRANCH_LABEL = {
    "HQ": "สำนักงานใหญ่",
    "SYP": "สาขาสี่แยกพัฒนา",
}

# LINE buttons label max 20 characters
BRANCH_BUTTON = {
    "HQ": "สำนักงานใหญ่",
    "SYP": "สาขาสี่แยกพัฒนา",
}


def branch_uri_buttons(
    *,
    title: str,
    alt_text: str,
    links: list[tuple[str, str, str]],
    wifi_hint: str = "กดปุ่มสาขา — ต้องอยู่ Wi‑Fi สาขานั้น",
) -> dict:
    """
    links: (branch, url, status) where status is online|offline|local.

    Returns a LINE buttons template so the long token URL is not shown in chat.
    Falls back to plain text when every branch is offline.
    """
    actions: list[dict] = []
    offline_names: list[str] = []

    for branch, url, status in links:
        name = BRANCH_LABEL.get(branch, branch)
        if status == "offline" or not url:
            offline_names.append(name)
            continue
        label = BRANCH_BUTTON.get(branch, name)[:20]
        actions.append({"type": "uri", "label": label, "uri": url})

    if not actions:
        lines = [title, "", "ยังไม่มีสาขาออนไลน์ครับ"]
        if offline_names:
            lines.append("ออฟไลน์: " + ", ".join(offline_names))
        return {"type": "text", "text": "\n".join(lines)}

    text_parts = [title, wifi_hint]
    if offline_names:
        text_parts.append("ออฟไลน์: " + ", ".join(offline_names))
    text = "\n".join(text_parts)
    if len(text) > 160:
        text = text[:157] + "…"

    return {
        "type": "template",
        "altText": alt_text[:400],
        "template": {
            "type": "buttons",
            "text": text,
            "actions": actions[:4],
        },
    }

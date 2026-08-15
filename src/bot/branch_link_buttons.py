"""Build short LINE replies that hide long entry URLs behind Thai word-links."""

from __future__ import annotations

BRANCH_LABEL = {
    "HQ": "สำนักงานใหญ่",
    "SYP": "สาขาสี่แยกพัฒนา",
}


def branch_uri_buttons(
    *,
    title: str,
    alt_text: str,
    links: list[tuple],
    wifi_hint: str = "กดชื่อสาขาเพื่อเปิด — ต้องอยู่ Wi‑Fi สาขานั้น",
) -> dict:
    """
    links: (branch, url, status) or (branch, url, status, label).

    Returns a Flex message: Thai branch names are tappable word-links; the
    long token URL is only inside the URI action (never shown as chat text).
    Falls back to plain text when every branch is offline.
    """
    link_rows: list[dict] = []
    offline_names: list[str] = []
    seen_offline: set[str] = set()

    for item in links:
        if len(item) >= 4:
            branch, url, status, label = item[0], item[1], item[2], item[3]
        else:
            branch, url, status = item[0], item[1], item[2]
            label = None
        name = BRANCH_LABEL.get(branch, branch)
        if status == "offline" or not url:
            if name not in seen_offline:
                offline_names.append(name)
                seen_offline.add(name)
            continue
        button_label = (label or name)[:40]
        link_rows.append(
            {
                "type": "button",
                "style": "link",
                "height": "sm",
                "action": {
                    "type": "uri",
                    "label": button_label,
                    "uri": url,
                },
            }
        )

    if not link_rows:
        lines = [title, "", "ยังไม่มีสาขาออนไลน์ครับ"]
        if offline_names:
            lines.append("ออฟไลน์: " + ", ".join(offline_names))
        return {"type": "text", "text": "\n".join(lines)}

    body_contents: list[dict] = [
        {
            "type": "text",
            "text": title,
            "weight": "bold",
            "size": "lg",
            "color": "#111111",
        },
        {
            "type": "text",
            "text": wifi_hint,
            "size": "sm",
            "color": "#888888",
            "wrap": True,
        },
        {"type": "separator", "margin": "md"},
    ]
    body_contents.extend(link_rows)

    if offline_names:
        body_contents.append(
            {
                "type": "text",
                "text": "ออฟไลน์: " + ", ".join(offline_names),
                "size": "xs",
                "color": "#AAAAAA",
                "wrap": True,
                "margin": "md",
            }
        )

    return {
        "type": "flex",
        "altText": alt_text[:400],
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "16px",
                "contents": body_contents,
            },
        },
    }

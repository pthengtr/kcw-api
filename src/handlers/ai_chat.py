import re


AI_TRIGGER = ["เฮียช้า", "จ๋า"]
AI_PATTERN = re.compile(r"^(?:เฮียช้า|จ๋า)[\s,:-]*", re.IGNORECASE)


def is_ai_chat_request(text: str) -> bool:
    t = (text or "").strip()
    return bool(AI_PATTERN.match(t))


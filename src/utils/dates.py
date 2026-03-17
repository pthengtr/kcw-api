from datetime import datetime
from zoneinfo import ZoneInfo
import re


SG_TZ = ZoneInfo("Asia/Singapore")


def today_sg_str() -> str:
    return datetime.now(SG_TZ).strftime("%Y-%m-%d")


def parse_sales_date_or_today(user_text: str) -> str:
    text = (user_text or "").strip()

    m = re.match(r"^ยอดขาย(?:\s+(\d{4}-\d{2}-\d{2}))?$", text)
    if m:
        return m.group(1) or today_sg_str()

    return today_sg_str()
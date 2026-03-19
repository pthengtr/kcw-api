
GREETING_MESSAGE = """เฮียช้าเวอร์ชันบอทครับ 🤖

ตัวจริงอาจเดินอยู่หน้าร้าน
แต่ตัวนี้ช่วยตอบเรื่องสินค้าให้ได้ครับ 😄

ลองพิมพ์แบบนี้:

🔎 ค้นหาสินค้า
• ลูกปืน 6207
• นมฮ ptt
• 22010585

📊 ดูยอดขาย
• ยอดขาย
• ยอดขาย 2026-03-17

📦 ดูประวัติสินค้า
• ประวัติซื้อ 22010585
• ประวัติขาย 22010585
• ซื้อ 22010585
• ขาย 22010585
• ซื้อ 22010585 10
• ขาย 22010585 10

*ระบบทดลองใช้งาน เฮียกำลังฝึกอยู่ครับ 😄*"""


def is_greeting(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {
        "hi",
        "hello",
        "hey",
        "สวัสดี",
        "หวัดดี",
        "ดี",
        "/start",
        "start",
        "เฮียช้า",
        "help",
        "ช่วยด้วย",
        "เมนู",
    }


def is_help_request(text: str) -> bool:
    t = (text or "").strip().lower()

    if t in {
        "hi",
        "hello",
        "hey",
        "สวัสดี",
        "หวัดดี",
        "/start",
        "help",
        "menu",
        "เมนู",
        "ช่วยด้วย",
        "เฮียช้า",
    }:
        return True

    if "?" in t:
        return True

    return False

def is_greeting(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {
        "hi", "hello", "hey",
        "สวัสดี", "หวัดดี", "ดี", "/start", "start",
        "เฮียช้า", "help", "ช่วยด้วย", "เมนู"
    }

def is_help_request(text: str) -> bool:
    t = (text or "").strip().lower()

    # ⭐ explicit greeting / help keywords
    if t in {
        "hi", "hello", "hey",
        "สวัสดี", "หวัดดี", "/start",
        "help", "menu", "เมนู", "ช่วยด้วย",
        "เฮียช้า"
    }:
        return True

    # ⭐ contains question mark
    if "?" in t:
        return True

    return False

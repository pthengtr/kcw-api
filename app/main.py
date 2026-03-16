from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.db import get_engine
from src.search.service import search_products
from src.ai import format_product_answer_ai
from src.telegram_bot import send_telegram_message

app = FastAPI(title="KCW API")

engine = get_engine()


class AskRequest(BaseModel):
    message: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ask")
def ask(req: AskRequest):
    bcode = req.message.strip()

    df = search_products(engine, bcode, limit=5)

    rows = df.fillna("").to_dict(orient="records")

    formatted = format_product_answer_ai(bcode, rows)

    return {
        "status": "ok",
        "reply": formatted
    }


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    update = await request.json()

    message = update.get("message") or {}
    chat = message.get("chat") or {}
    text = message.get("text", "").strip()
    chat_id = chat.get("id")

    if not chat_id:
        return {"ok": True}

    # ⭐ greeting when user press START
    if text.lower() == "/start":
        greeting = (
            "สวัสดีครับ 👋\n"
            "นี่คือระบบค้นหาสินค้า KCW (เวอร์ชันทดลอง)\n\n"
            "คุณสามารถพิมพ์ BCODE เพื่อค้นหาสินค้าได้ทันที\n"
            "ระบบยังอยู่ระหว่างพัฒนา อาจมีข้อผิดพลาดได้ 🙏"
        )
        send_telegram_message(chat_id, greeting)
        return {"ok": True}

    if not text:
        send_telegram_message(chat_id, "ส่ง BCODE มาได้เลย")
        return {"ok": True}

    # ⭐ query DB
    df = search_products(engine, text, limit=5)
    rows = df.fillna("").to_dict(orient="records")

    # ⭐ use AI formatter
    reply = format_product_answer_ai(text, rows)

    # ⭐ send back
    send_telegram_message(chat_id, reply)

    return {"ok": True}
from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.db import get_engine
from src.search.service import search_products
from src.ai import format_product_answer_ai
from src.bot.telegram import send_telegram_message
from src.bot.telegram import to_telegram_message
from src.bot.telegram import answer_callback_query
from src.bot.engine import handle_callback
from src.bot.engine import handle_user_text


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

    # ⭐ CALLBACK MODE (button click)
    callback = update.get("callback_query")
    if callback:
        chat_id = callback["message"]["chat"]["id"]
        data = callback.get("data", "")

        # remove loading spinner
        answer_callback_query(callback["id"])

        resp = handle_callback(data)
        text, markup = to_telegram_message(resp)

        send_telegram_message(chat_id, text, markup)

        return {"ok": True}

    # ⭐ NORMAL MESSAGE MODE
    message = update.get("message") or {}
    chat = message.get("chat") or {}
    text = (message.get("text") or "").strip()
    chat_id = chat.get("id")

    if not chat_id:
        return {"ok": True}

    # ⭐ greeting
    if text.lower() == "/start":
        greeting = (
            "สวัสดีครับ 👋\n"
            "นี่คือระบบค้นหาสินค้า KCW (เวอร์ชันทดลอง)\n\n"
            "พิมพ์ชื่อสินค้า / รหัส / รุ่น เพื่อค้นหาได้เลย"
        )
        send_telegram_message(chat_id, greeting)
        return {"ok": True}

    if not text:
        send_telegram_message(chat_id, "พิมพ์คำค้นหาได้เลย")
        return {"ok": True}

    # ⭐ use conversation engine (NOT direct search anymore)
    resp = handle_user_text(engine, text)

    text, markup = to_telegram_message(resp)

    send_telegram_message(chat_id, text, markup)

    return {"ok": True}
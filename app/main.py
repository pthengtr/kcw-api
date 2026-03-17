import os
import hmac
import base64
import hashlib
import json

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

from src.db import get_engine
from src.search.service import simple_and_search_sql
from src.search.formatters import format_product_answer
from src.bot.telegram_bot import telegram_send_message

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

    df = simple_and_search_sql(engine, bcode, limit=5)

    rows = df.fillna("").to_dict(orient="records")

    formatted = format_product_answer(bcode, rows)

    return {
        "status": "ok",
        "reply": formatted
    }


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):

    update = await request.json()

    message = update.get("message") or {}
    chat = message.get("chat") or {}

    chat_id = chat.get("id")
    user_text = (message.get("text") or "").strip()

    if not chat_id:
        return {"ok": True}

    # ⭐ GREETING
    if user_text.lower() == "/start":

        msg = (
            "👋 สวัสดีครับ\n"
            "ระบบค้นหาสินค้า KCW (ทดลอง)\n\n"
            "ตัวอย่างการค้นหา:\n"
            "• 22010585\n"
            "• ลูกปืน 6207\n"
            "• 220105 นมฮ\n\n"
            "พิมพ์คำค้นหาได้เลย"
        )

        telegram_send_message(chat_id, msg)
        return {"ok": True}

    # ⭐ EMPTY
    if not user_text:
        telegram_send_message(chat_id, "พิมพ์คำค้นหาได้เลย")
        return {"ok": True}

    # ⭐ SIMPLE SEARCH
    df = simple_and_search_sql(
        engine=engine,
        query=user_text,
        limit=10
    )

    if df.empty:
        telegram_send_message(chat_id, "❌ ไม่พบสินค้า")
        return {"ok": True}

    msg = format_product_answer(df)

    telegram_send_message(chat_id, msg)

    return {"ok": True}

LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET", "")
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")

def verify_line_signature(body: bytes, signature: str, channel_secret: str) -> bool:
    digest = hmac.new(
        channel_secret.encode("utf-8"),
        body,
        hashlib.sha256
    ).digest()
    expected_signature = base64.b64encode(digest).decode("utf-8")
    return hmac.compare_digest(expected_signature, signature)

@app.post("/line/webhook")
async def line_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if not verify_line_signature(body, signature, LINE_CHANNEL_SECRET):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(body.decode("utf-8"))
    events = payload.get("events", [])

    # Important: LINE verification can send events=[]
    if not events:
        return {"ok": True}

    for event in events:
        print("LINE EVENT:", event)

        # later you can handle:
        # - follow
        # - message
        # - postback
        # - unfollow

    return {"ok": True}
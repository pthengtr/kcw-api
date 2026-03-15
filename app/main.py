from fastapi import FastAPI, Request
from pydantic import BaseModel

from src.db import get_engine
from src.queries import query_product_by_bcode
from src.ai import format_product_answer
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

    df = query_product_by_bcode(engine, bcode)

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
    text = message.get("text", "").strip()
    chat_id = chat.get("id")

    if not chat_id:
        return {"ok": True}

    if not text:
        send_telegram_message(chat_id, "ส่ง BCODE มาได้เลย")
        return {"ok": True}

    # ⭐ query DB
    df = query_product_by_bcode(engine, text)
    rows = df.fillna("").to_dict(orient="records")

    # ⭐ use AI formatter
    reply = format_product_answer(text, rows)

    # ⭐ send back
    send_telegram_message(chat_id, reply)

    return {"ok": True}
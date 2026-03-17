import json

from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel

from src.db import get_engine
from src.search.service import simple_and_search_sql
from src.search.formatters import format_product_answer
from src.bot.line_bot import verify_line_signature
from src.bot.line_bot import reply_line_message

app = FastAPI(title="KCW API")

engine = get_engine()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/line-webhook")
async def line_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if not verify_line_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(body.decode("utf-8"))
    events = payload.get("events", [])

    engine = get_engine()
    # Important: LINE verification can send events=[]
    if not events:
        return {"ok": True}

    for event in events:
        print("LINE EVENT:", event)

        event_type = event.get("type")

        if event_type != "message":
            continue

        message = event.get("message", {})
        if message.get("type") != "text":
            continue

        user_text = (message.get("text") or "").strip()
        reply_token = event.get("replyToken")

        try:
            results = simple_and_search_sql(engine, user_text)
            reply_text = format_product_answer(results)
        except Exception as e:
            print("SEARCH ERROR:", e)
            reply_text = "ระบบค้นหามีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้ง"

        try:
            reply_line_message(reply_token, reply_text)
        except Exception as e:
            print("LINE REPLY ERROR:", e)


    return {"ok": True}
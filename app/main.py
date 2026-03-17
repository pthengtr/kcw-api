from fastapi import FastAPI, Request, HTTPException
import json

from src.db import get_engine
from src.bot.line_bot import verify_line_signature, reply_line_message
from src.handlers.router import route_user_text

app = FastAPI()


@app.post("/line-webhook")
async def line_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("x-line-signature", "")

    if not verify_line_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = json.loads(body.decode("utf-8"))
    events = payload.get("events", [])

    if not events:
        return {"ok": True}

    engine = get_engine()

    for event in events:
        print("LINE EVENT:", event)

        if event.get("type") != "message":
            continue

        message = event.get("message", {})
        if message.get("type") != "text":
            continue

        user_text = (message.get("text") or "").strip()
        reply_token = event.get("replyToken")

        try:
            reply_text = route_user_text(engine, user_text)
        except Exception as e:
            print("ROUTE ERROR:", e)
            reply_text = "ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้ง"

        try:
            reply_line_message(reply_token, reply_text)
        except Exception as e:
            print("LINE REPLY ERROR:", e)

    return {"ok": True}
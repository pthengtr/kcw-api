from fastapi import FastAPI, Request, HTTPException
import json

from src.db import get_engine
from src.bot.line_bot import (
    verify_line_signature,
    reply_line_message,
    reply_line_image,
)
from src.handlers.router import route_user_text
from src.access.helper import get_line_user_id
from src.access.helper import get_or_create_line_access
from src.access.helper import build_access_denied_message

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

        # =========================
        # ACCESS CHECK
        # =========================
        try:
            line_user_id = get_line_user_id(event)
            access = get_or_create_line_access(engine, line_user_id)

            if not access["is_allowed"]:
                reply_text = build_access_denied_message(access)
                reply_line_message(reply_token, reply_text)
                continue

        except Exception as e:
            print("ACCESS CHECK ERROR:", e)
            try:
                reply_line_message(
                    reply_token,
                    "ระบบตรวจสอบสิทธิ์มีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้ง"
                )
            except Exception as reply_err:
                print("LINE REPLY ERROR:", reply_err)
            continue

        # =========================
        # NORMAL ROUTING
        # =========================
        try:
            reply_payload = route_user_text(engine, user_text, access=access)

            # backward compatibility:
            if isinstance(reply_payload, str):
                reply_payload = {"type": "text", "text": reply_payload}

            if not isinstance(reply_payload, dict):
                raise ValueError(f"Unexpected reply_payload type: {type(reply_payload)}")

        except Exception as e:
            print("ROUTE ERROR:", e)
            reply_payload = {
                "type": "text",
                "text": "ระบบมีปัญหาชั่วคราว กรุณาลองใหม่อีกครั้ง"
            }

        try:
            print("DEBUG reply_payload:", reply_payload)

            if reply_payload.get("type") == "image":
                reply_line_image(
                    reply_token,
                    image_url=reply_payload["originalContentUrl"],
                    preview_url=reply_payload.get("previewImageUrl"),
                )
            else:
                reply_line_message(reply_token, reply_payload.get("text", "ไม่มีข้อความตอบกลับ"))
        except Exception as e:
            print("LINE REPLY ERROR:", e)

    return {"ok": True}
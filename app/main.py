from fastapi import FastAPI, Request, HTTPException
import json
import time
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

from src.db import get_engine
from src.bot.line_bot import (
    verify_line_signature,
    reply_line_message,
    reply_line_response,
)
from src.handlers.router import route_user_text
from src.access.helper import get_line_user_id
from src.access.helper import get_or_create_line_access
from src.access.helper import build_access_denied_message

# add this import
from src.ai.openai_kb import handle_kb_select_postback

app = FastAPI()


@app.post("/kcw-peak/sync")
async def kcw_peak_sync(request: Request):
    try:
        body = await request.json()
        print("========== KCW PEAK ==========")
        print("payload:", body)
        print("==============================")
        return {
            "status": "ok",
            "received": True,
        }
    except Exception as e:
        print("KCW PEAK ERROR:", e)
        raise HTTPException(status_code=400, detail="Invalid payload")


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

        reply_token = event.get("replyToken")
        event_type = event.get("type")

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
        # ROUTING
        # =========================
        try:
            t_route_0 = time.perf_counter()

            if event_type == "postback":
                postback = event.get("postback", {}) or {}
                data = (postback.get("data") or "").strip()

                if data.startswith("kb_select:"):
                    reply_payload = handle_kb_select_postback(data)
                else:
                    # ignore unknown postback for now
                    continue

            elif event_type == "message":
                message = event.get("message", {}) or {}

                if message.get("type") != "text":
                    continue

                user_text = (message.get("text") or "").strip()
                reply_payload = route_user_text(engine, user_text, access=access)

            else:
                continue

            t_route_1 = time.perf_counter()

            print(
                f"LATENCY route_ms={(t_route_1 - t_route_0)*1000:.1f}"
            )

            # backward compatibility
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
            t_reply_0 = time.perf_counter()
            reply_line_response(reply_token, reply_payload)
            t_reply_1 = time.perf_counter()
            print(f"LATENCY line_reply_ms={(t_reply_1 - t_reply_0)*1000:.1f}")

        except Exception as e:
            print("LINE REPLY ERROR:", e)

    return {"ok": True}
from src.handlers.sales import handle_sales_query
from src.handlers.product import handle_product_query_response
from src.handlers.job import handle_job_query, is_job_request
from src.handlers.history import handle_history_query, is_history_request
from src.handlers.ai_chat import is_ai_chat_request
from src.ai.openai_kb import build_kb_quick_reply_result
from src.handlers.message import GREETING_MESSAGE, is_help_request
from src.handlers.image import (
    is_image_command,
    handle_image_command,
    handle_image_session_text,
)
from src.handlers.product_snapshot import is_product_snapshot_request
from src.access.helper import can_execute
from src.handlers.location import is_location_request, handle_location_query
from src.handlers.check import is_check_request, handle_check_response


def route_user_text(
    engine,
    user_text: str,
    access: dict,
    line_user_id: str | None = None,
) -> dict:
    text = (user_text or "").strip()

    # Image upload/delete session should block normal text routing until user types "เสร็จ".
    image_session_reply = handle_image_session_text(line_user_id, text)
    if image_session_reply is not None:
        return image_session_reply

    if is_help_request(user_text):
        return {"type": "text", "text": GREETING_MESSAGE}

    if is_image_command(text):
        return handle_image_command(text, line_user_id=line_user_id)

    if is_job_request(text):
        return handle_job_query(engine, text, access=access)

    if text.startswith("ยอดขาย"):
        cmd = "ยอดขาย"
        if not can_execute(access["access_group"], cmd):
            return {"type": "text", "text": "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"}

        return {
            "type": "text",
            "text": handle_sales_query(engine, text),
        }

    if is_history_request(text):
        cmd = "ประวัติสินค้า"
        if not can_execute(access["access_group"], cmd):
            return {"type": "text", "text": "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"}

        return {
            "type": "text",
            "text": handle_history_query(engine, text),
        }

    if is_ai_chat_request(text):
        return build_kb_quick_reply_result(text)

    if is_product_snapshot_request(text):
        # Backward-compatible alias:
        # "สินค้า {bcode}" now returns the merged เช็ค response.
        return handle_check_response(engine, text)

    if is_location_request(text):
        cmd = "ที่เก็บ"
        if not can_execute(access["access_group"], cmd):
            return {"type": "text", "text": "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"}

        return {
            "type": "text",
            "text": handle_location_query(engine, text),
        }

    if is_check_request(text):
        return handle_check_response(engine, text)

    return handle_product_query_response(engine, text, access=access)
from src.handlers.sales import handle_sales_query
from src.handlers.product import handle_product_query
from src.handlers.product_snapshot import handle_product_snapshot_query, is_product_snapshot_request
from src.handlers.job import handle_job_query, is_job_request
from src.handlers.history import handle_history_query, is_history_request
from src.handlers.ai_chat import handle_ai_chat_query, is_ai_chat_request
from src.handlers.message import GREETING_MESSAGE, is_help_request
from src.access.helper import can_execute
from src.ai.gemini_kb import ask_gemini_file_search
from src.handlers.image import is_image_command, handle_image_command


def route_user_text(engine, user_text: str, access: dict) -> str:
    text = (user_text or "").strip()

    # 1) greeting / help
    if is_help_request(user_text):
        return GREETING_MESSAGE

    # 2) job queue
    if is_job_request(text):
        return handle_job_query(engine, text, access=access)

    # 3) sales summary
    if text.startswith("ยอดขาย"):
        cmd = "ยอดขาย"
        if not can_execute(access["access_group"], cmd):
            return "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"
        return handle_sales_query(engine, text)

    # 4) product snapshot
    if is_product_snapshot_request(text):
        cmd = "สินค้า"
        if not can_execute(access["access_group"], cmd):
            return "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"
        return handle_product_snapshot_query(engine, text)

    # 5) purchase / sales history
    if is_history_request(text):
        cmd = "ประวัติสินค้า"
        if not can_execute(access["access_group"], cmd):
            return "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"
        return handle_history_query(engine, text)

    # 6) AI chat
    if is_ai_chat_request(text):
        # return handle_ai_chat_query
        return ask_gemini_file_search(text)
    
    if is_image_command(text):
        return handle_image_command(text)


    # 7) default product search
    return handle_product_query(engine, text)
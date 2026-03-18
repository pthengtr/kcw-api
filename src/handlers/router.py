from src.handlers.sales import handle_sales_query
from src.handlers.product import handle_product_query
from src.handlers.job import handle_job_query, is_job_request
from src.handlers.message import GREETING_MESSAGE, is_help_request
from src.access.helper import can_execute


def route_user_text(engine, user_text: str, access: dict) -> str:
    text = (user_text or "").strip()

    # 1) greeting / help
    if is_help_request(user_text):
        return GREETING_MESSAGE

    # 2) job queue
    if is_job_request(text):
        return handle_job_query(engine, text, access=access)

    # 3) sales
    if text.startswith("ยอดขาย"):
        cmd = "ยอดขาย"
        if not can_execute(access["access_group"], cmd):
            return "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"

        return handle_sales_query(engine, text)

    # 4) default product search
    return handle_product_query(engine, text)
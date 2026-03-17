from src.handlers.sales import handle_sales_query
from src.handlers.product import handle_product_query
from src.handlers.message import GREETING_MESSAGE, is_help_request


def route_user_text(engine, user_text: str) -> str:
    text = (user_text or "").strip()

    # 1) greeting / help
    if is_help_request(user_text):
       return GREETING_MESSAGE

    if text.startswith("ยอดขาย"):
        return handle_sales_query(engine, text)

    return handle_product_query(engine, text)
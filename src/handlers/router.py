from src.handlers.sales import handle_sales_query
from src.handlers.product import handle_product_query


def route_user_text(engine, user_text: str) -> str:
    text = (user_text or "").strip()

    if text.startswith("ยอดขาย"):
        return handle_sales_query(engine, text)

    return handle_product_query(engine, text)
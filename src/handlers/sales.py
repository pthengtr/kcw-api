from src.queries import get_daily_sales_summary
from src.utils.dates import parse_sales_date_or_today


def format_daily_sales_message(sales: dict) -> str:
    return (
        f"ยอดขายวันที่ {sales['date']}\n"
        f"HQ: {sales['HQ']:,.2f}\n"
        f"SYP: {sales['SYP']:,.2f}\n"
        f"รวม: {sales['BOTH']:,.2f}"
    )


def handle_sales_query(engine, user_text: str) -> str:
    target_date = parse_sales_date_or_today(user_text)
    sales = get_daily_sales_summary(engine, target_date)
    return format_daily_sales_message(sales)
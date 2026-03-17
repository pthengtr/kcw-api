from src.queries import get_daily_sales_summary

def format_daily_sales_message(sales: dict) -> str:
    return (
        f"ยอดขายวันที่ {sales['date']}\n"
        f"HQ: {sales['HQ']:,.0f}\n"
        f"SYP: {sales['SYP']:,.0f}\n"
        f"รวม: {sales['BOTH']:,.0f}"
    )


def handle_sales_query(engine, user_text: str) -> str:
    parts = user_text.split()

    if len(parts) >= 2:
        date = parts[1]
    else:
        date = None

    sales = get_daily_sales_summary(engine, date)

    return format_daily_sales_message(sales)
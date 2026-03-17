from src.search import simple_and_search_sql, format_product_answer


def handle_product_query(engine, user_text: str) -> str:
    results = simple_and_search_sql(engine, user_text)
    return format_product_answer(results)
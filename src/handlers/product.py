from src.search import simple_and_search_sql, format_product_answer


def handle_product_query(engine, user_text: str, access: dict | None = None) -> str:
    results = simple_and_search_sql(engine, user_text, limit=5)

    access_group = (access or {}).get("access_group", "")
    can_see_cost = access_group in {"admin", "exec"}

    return format_product_answer(results, can_see_cost=can_see_cost)
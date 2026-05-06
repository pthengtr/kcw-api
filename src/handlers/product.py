from src.search import simple_and_search_sql, format_product_answer


def _safe_text(value, default: str = "") -> str:
    if value is None:
        return default

    s = str(value).strip()
    if not s or s.lower() == "nan":
        return default

    return s


def _extract_single_bcode(search_result: dict) -> str | None:
    """
    Return BCODE only when search result is confidently one product.

    We use total == 1, not just len(df) == 1, because search limit may return
    one displayed row while total could still be larger.
    """
    total = int(search_result.get("total", 0) or 0)
    if total != 1:
        return None

    df = search_result.get("items")
    if df is None or df.empty:
        return None

    bcode = _safe_text(df.iloc[0].get("BCODE"))
    return bcode or None


def build_product_quick_reply(bcode: str) -> dict:
    return {
        "items": [
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "ซื้อ-ขาย ล่าสุด",
                    "text": f"เช็ค {bcode}",
                },
            },
            {
                "type": "action",
                "action": {
                    "type": "message",
                    "label": "จัดการรูป",
                    "text": f"รูป {bcode}",
                },
            },
        ]
    }


def _qr_pick_bcode_action(bcode: str) -> dict:
    """
    Option B: quick reply sends *only* BCODE so user can pick,
    then the next response can show follow-up actions for that BCODE.
    """
    safe_bcode = _safe_text(bcode, "")
    label = safe_bcode[:20] if safe_bcode else "เลือกสินค้า"
    return {
        "type": "action",
        "action": {
            "type": "message",
            "label": label,
            "text": safe_bcode,
        },
    }


def build_product_search_quick_reply(search_result: dict, max_items: int = 13) -> dict | None:
    df = search_result.get("items")
    if df is None or getattr(df, "empty", True):
        return None

    items: list[dict] = []
    seen: set[str] = set()

    for _, row in df.iterrows():
        bcode = _safe_text(row.get("BCODE"), "")
        if not bcode or bcode in seen:
            continue
        seen.add(bcode)

        items.append(_qr_pick_bcode_action(bcode))
        if len(items) >= max_items:
            break

    return {"items": items} if items else None


def handle_product_query(engine, user_text: str, access: dict | None = None) -> str:
    results = simple_and_search_sql(engine, user_text, limit=5)

    access_group = (access or {}).get("access_group", "")
    can_see_cost = access_group in {"admin", "exec"}

    return format_product_answer(results, can_see_cost=can_see_cost)


def handle_product_query_response(engine, user_text: str, access: dict | None = None) -> dict:
    results = simple_and_search_sql(engine, user_text, limit=5)

    access_group = (access or {}).get("access_group", "")
    can_see_cost = access_group in {"admin", "exec"}

    text = format_product_answer(results, can_see_cost=can_see_cost)
    bcode = _extract_single_bcode(results)

    response = {
        "type": "text",
        "text": text,
    }

    if bcode:
        response["quickReply"] = build_product_quick_reply(bcode)
    else:
        quick_reply = build_product_search_quick_reply(results)
        if quick_reply:
            response["quickReply"] = quick_reply

    return response
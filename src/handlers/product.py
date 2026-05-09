import base64
import json

from src.search import simple_and_search_sql, format_product_answer


PRODUCT_SEARCH_PAGE_SIZE = 5
PRODUCT_SEARCH_NEXT_PREFIX = "product_search_next:"
LINE_POSTBACK_DATA_MAX_LENGTH = 300


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


def _encode_next_search_data(query: str, next_offset: int, limit: int) -> str | None:
    payload = {
        "q": str(query or "").strip(),
        "o": max(int(next_offset or 0), 0),
        "l": max(int(limit or 0), 1),
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii").rstrip("=")
    data = f"{PRODUCT_SEARCH_NEXT_PREFIX}{encoded}"

    if len(data) > LINE_POSTBACK_DATA_MAX_LENGTH:
        return None

    return data


def _decode_next_search_data(data: str) -> tuple[str, int, int] | None:
    raw = (data or "").strip()
    if not raw.startswith(PRODUCT_SEARCH_NEXT_PREFIX):
        return None

    encoded = raw.replace(PRODUCT_SEARCH_NEXT_PREFIX, "", 1).strip()
    if not encoded:
        return None

    try:
        padded = encoded + ("=" * (-len(encoded) % 4))
        payload = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8"))
        query = str(payload.get("q") or "").strip()
        offset = max(int(payload.get("o") or 0), 0)
        limit = max(int(payload.get("l") or PRODUCT_SEARCH_PAGE_SIZE), 1)
    except Exception:
        return None

    if not query:
        return None

    return query, offset, limit


def is_product_search_next_postback(data: str) -> bool:
    return (data or "").strip().startswith(PRODUCT_SEARCH_NEXT_PREFIX)


def _qr_next_search_action(query: str, next_offset: int, limit: int) -> dict | None:
    data = _encode_next_search_data(query, next_offset, limit)
    if not data:
        return None

    return {
        "type": "action",
        "action": {
            "type": "postback",
            "label": f"ถัดไป {limit}",
            "data": data,
            "displayText": f"ดูผลลัพธ์ถัดไป {limit} รายการ",
        },
    }


def _qr_previous_search_action(query: str, previous_offset: int, limit: int) -> dict | None:
    data = _encode_next_search_data(query, previous_offset, limit)
    if not data:
        return None

    return {
        "type": "action",
        "action": {
            "type": "postback",
            "label": f"ก่อนหน้า {limit}",
            "data": data,
            "displayText": f"ดูผลลัพธ์ก่อนหน้า {limit} รายการ",
        },
    }


def build_product_search_quick_reply(
    search_result: dict,
    query: str,
    max_items: int = 13,
) -> dict | None:
    df = search_result.get("items")
    if df is None or getattr(df, "empty", True):
        return None

    items: list[dict] = []
    seen: set[str] = set()
    total = int(search_result.get("total", 0) or 0)
    offset = max(int(search_result.get("offset", 0) or 0), 0)
    limit = max(int(search_result.get("limit", PRODUCT_SEARCH_PAGE_SIZE) or 0), 1)

    if offset > 0:
        previous_action = _qr_previous_search_action(
            query,
            max(offset - limit, 0),
            limit,
        )
        if previous_action:
            items.append(previous_action)

    for _, row in df.iterrows():
        bcode = _safe_text(row.get("BCODE"), "")
        if not bcode or bcode in seen:
            continue
        seen.add(bcode)

        items.append(_qr_pick_bcode_action(bcode))
        if len(items) >= max_items:
            break

    next_offset = offset + len(df)

    if total > next_offset and len(items) < max_items:
        next_action = _qr_next_search_action(query, next_offset, limit)
        if next_action:
            items.append(next_action)

    return {"items": items} if items else None


def handle_product_query(
    engine,
    user_text: str,
    access: dict | None = None,
    limit: int = PRODUCT_SEARCH_PAGE_SIZE,
    offset: int = 0,
) -> str:
    results = simple_and_search_sql(engine, user_text, limit=limit, offset=offset)

    access_group = (access or {}).get("access_group", "")
    can_see_cost = access_group in {"admin", "exec"}

    return format_product_answer(results, can_see_cost=can_see_cost)


def handle_product_query_response(
    engine,
    user_text: str,
    access: dict | None = None,
    limit: int = PRODUCT_SEARCH_PAGE_SIZE,
    offset: int = 0,
) -> dict:
    results = simple_and_search_sql(engine, user_text, limit=limit, offset=offset)

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
        quick_reply = build_product_search_quick_reply(results, user_text)
        if quick_reply:
            response["quickReply"] = quick_reply

    return response


def handle_product_search_next_postback(
    engine,
    data: str,
    access: dict | None = None,
) -> dict:
    decoded = _decode_next_search_data(data)
    if not decoded:
        return {
            "type": "text",
            "text": "ไม่พบข้อมูลค้นหาต่อ กรุณาค้นหาสินค้าใหม่อีกครั้ง",
        }

    query, offset, limit = decoded
    return handle_product_query_response(
        engine,
        query,
        access=access,
        limit=limit,
        offset=offset,
    )
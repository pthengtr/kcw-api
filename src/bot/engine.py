from src.search.service import search_products
from .models import BotResponse, Action


def handle_user_text(engine, text: str) -> BotResponse:
    df = search_products(engine, text, limit=5)

    if df.empty:
        return BotResponse(text="ไม่พบสินค้า")

    actions = []

    for _, row in df.iterrows():
        bcode = row["BCODE"]
        descr = str(row["DESCR"])[:25]

        actions.append(
            Action(
                type="select_product",
                value=bcode,
                label=f"{bcode} {descr}"
            )
        )

    return BotResponse(
        text="พบสินค้าที่ใกล้เคียง เลือกได้เลย:",
        actions=actions
    )


def handle_callback(data: str) -> BotResponse:
    """
    data example:
    select_product:2201048
    """

    try:
        action_type, value = data.split(":", 1)
    except Exception:
        return BotResponse(text="คำสั่งไม่ถูกต้อง")

    if action_type == "select_product":
        return BotResponse(
            text=f"คุณเลือกสินค้า {value}"
        )

    return BotResponse(text="ไม่รู้จัก action นี้")
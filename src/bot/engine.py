from src.search.service import search_products, get_product_detail_by_bcode
from src.ai import format_product_answer_ai
from .models import BotResponse, Action


def build_product_menu(bcode: str) -> list[Action]:
    return [
        Action(type="product_info", value=bcode, label="ข้อมูลสินค้า"),
        Action(type="purchase_history", value=bcode, label="ประวัติซื้อ"),
        Action(type="sales_history", value=bcode, label="ประวัติขาย"),
    ]


def handle_user_text(engine, text: str) -> BotResponse:
    df = search_products(engine, text, limit=5)

    if df.empty:
        return BotResponse(text="ไม่พบสินค้า")

    actions = []
    for _, row in df.iterrows():
        bcode = str(row["BCODE"]).strip()
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


def handle_callback(engine, data: str) -> BotResponse:
    try:
        action_type, value = data.split(":", 1)
    except Exception:
        return BotResponse(text="คำสั่งไม่ถูกต้อง")

    if action_type == "select_product":
        return BotResponse(
            text=f"เลือกสินค้า {value} แล้ว\nต้องการดูอะไรต่อ?",
            actions=build_product_menu(value)
        )

    if action_type == "product_info":
        df = get_product_detail_by_bcode(engine, value)

        if df.empty:
            return BotResponse(
                text=f"ไม่พบข้อมูลสินค้า {value}",
                actions=build_product_menu(value)
            )

        row = df.iloc[0]

        formated_text = format_product_answer_ai(row.get('BCODE'), row)

        return BotResponse(
            text=formated_text,
            actions=build_product_menu(value)
        )

    if action_type == "purchase_history":
        return BotResponse(
            text=f"ประวัติซื้อของ {value}\n\nอยู่ระหว่างพัฒนา",
            actions=build_product_menu(value)
        )

    if action_type == "sales_history":
        return BotResponse(
            text=f"ประวัติขายของ {value}\n\nอยู่ระหว่างพัฒนา",
            actions=build_product_menu(value)
        )

    return BotResponse(text="ไม่รู้จัก action นี้")


def safe_val(v):
    if v is None:
        return "-"
    s = str(v).strip()
    return s if s else "-"
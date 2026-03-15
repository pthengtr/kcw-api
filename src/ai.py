import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_product_answer(bcode: str, rows: list[dict]) -> str:
    if not rows:
        return f"ไม่พบสินค้า BCODE {bcode}"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "คุณเป็นผู้ช่วยค้นหาสินค้าของร้าน ตอบเป็นภาษาไทยเสมอ แบบสั้น กระชับ และอ่านง่ายสำหรับแชต"
            },
            {
                "role": "user",
                "content": f"""
                            ผู้ใช้ค้นหา BCODE: {bcode}

                            ข้อมูลสินค้า:
                            {rows}

                            ช่วยสรุปผลเป็นภาษาไทย
                            แสดง:
                            - BCODE
                            - รายละเอียดสินค้า
                            - ยี่ห้อ
                            - รุ่น
                            - ราคา
                            """
            }
        ],
    )

    return res.choices[0].message.content
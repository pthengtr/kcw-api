import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_product_answer_ai(bcode: str, rows: list[dict]) -> str:

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
                            คุณคือผู้ช่วยร้านค้าของ KCW

                            ด้านล่างคือข้อมูลสินค้า โดยชื่อคอลัมน์มีความหมายดังนี้

                            - BCODE = รหัสสินค้า
                            - ACODE = ชื่อย่อ
                            - DESCR = ชื่อสินค้า
                            - BRAND = ยี่ห้อ
                            - MODEL = รุ่น
                            - PRICE1 = ราคาขายหน่วยย่อย
                            - VENDOR = ซื้อมาจาก
                            - MAIN = หมวดสินค้า
                            - UI1 = หน่วยย่อย
                            - UI2 = หน่วยใหญ่
                            - PRICEM1 = ราคาขายหน่วยใหญ่
                            - MTP2 = จำนวนต่อหน่วยใหญ่
                            - LOCATION1 = สถานที่เก็บ
                            - LOCATION2 = สถานที่เก็บเพิ่มเติม
                            - QTYOH2 = จำนวนคงเหลือ
                            - REMARK = หมายเหตุ
                            - SIZE1-3 = ขนาด ใน / นอก / หนา

                            กรุณาสรุปข้อมูลสินค้าเป็นภาษาไทยให้เข้าใจง่าย โดย:

                            - ใช้ประโยคธรรมดา ไม่ต้องเขียนรูปแบบ field = value
                            - แสดงข้อมูลสำคัญเป็นรายการ bullet
                            - ถ้าข้อมูลไหนว่าง ให้ข้ามไม่ต้องแสดง
                            - ใช้คำอ่านง่าย เช่น “ราคาขาย”, “คงเหลือในสต็อก”
                            - ตอบสั้น กระชับ

                            ข้อมูลสินค้า:
                            {rows}
                            """
            }
        ],
    )

    return res.choices[0].message.content
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def format_product_answer_ai(bcode: str) -> str:

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

                            ช่วยสรุปผลเป็นภาษาไทย
                            แสดง:
                            - BCODE คือ รหัสสินค้า
                            - ACODE คือ ชื่อย่อ
                            - DESCR ชื่อสินค้า
                            - BRAND ยี่ห้อ
                            - MODEL รุ่น
                            - PRICE1 ราคาหน่วยย่อย
                            - VENDOR ซื้อมาจาก
                            - MAIN หมวด
                            - UI1 หน่วยย่อย
                            - UI2 หน่วยใหญ่
                            - PRICEM1 ราคาหน่วยใหญ่
                            - MTP2 จำนวนต่อหน่วยใหญ่
                            - LOCATION1 (ถ้าไม่มีไม่ต้องแสดง)
                            - LOCATION2 (ถ้าไม่มีไม่ต้องแสดง)
                            - QTYOH2 จำนวนในสตอก
                            - REMARK หมายเหตุ
                            - SIZE1-3 ใน นอก หนา
                            """
            }
        ],
    )

    return res.choices[0].message.content
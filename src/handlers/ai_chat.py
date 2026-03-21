from src.ai.openai_client import get_openai_client


AI_TRIGGER = ["เฮียช้า", "จ๋า"]


def is_ai_chat_request(text: str) -> bool:
    t = (text or "").strip()

    return any(
        t.startswith(trg)
        for trg in AI_TRIGGER
    )


def extract_ai_question(text: str) -> str:
    t = (text or "").strip()
    if t.startswith(AI_TRIGGER):
        return t.replace(AI_TRIGGER, "", 1).strip()
    return t


def _extract_text_from_response(resp) -> str:
    """
    Works with Responses API text output.
    Tries output_text first, then falls back to parsing output items.
    """
    output_text = getattr(resp, "output_text", None)
    if output_text:
        return output_text.strip()

    output = getattr(resp, "output", None) or []
    chunks = []

    for item in output:
        content = getattr(item, "content", None) or []
        for part in content:
            if getattr(part, "type", None) == "output_text":
                chunks.append(getattr(part, "text", ""))

    text = "".join(chunks).strip()
    return text or "เฮียช้างงนิดหน่อยครับ ลองถามใหม่อีกครั้งได้เลย 😅"


def handle_ai_chat_query(user_text: str) -> str:

    try: 
            question = extract_ai_question(user_text)

            if not question:
                return (
                    "เฮียช้าพร้อมครับ 😄\n"
                    "ลองพิมพ์แบบนี้:\n"
                    "• เฮียช้า ปีนี้ตรุษจีนวันไหน\n"
                    "• เฮียช้า ลูกปืนคืออะไร\n"
                    "• เฮียช้า ช่วยสรุปความต่างระหว่างน้ำมันเกียร์กับไฮดรอลิก"
                )

            client = get_openai_client()

            system_prompt = """
        คุณคือ "เฮียช้า" ผู้ช่วยแชทร้านอะไหล่

        แนวทางตอบ:
        - ตอบเป็นภาษาไทย
        - สั้น กระชับ อ่านง่าย เหมาะกับ LINE chat
        - โทนเป็นกันเอง สุภาพ แบบคนในร้าน
        - ถ้าเป็นคำถามทั่วไป ตอบได้ตามปกติ
        - ถ้าเป็นคำถามด้านเทคนิคที่เสี่ยงต่อการเดามั่ว เช่น การใส่แทนกัน ความเข้ากันได้ อะแดปเตอร์
        และยังไม่มีข้อมูลยืนยัน ให้ตอบแบบระวังตัวว่า "ยังไม่แน่ใจ ต้องเช็กเพิ่ม"
        - อย่าตอบยาวเกินจำเป็น
        - ไม่ต้องใส่ markdown พิเศษ
        - ไม่ต้องใส่คำนำยืดยาวทุกครั้ง
        """

            resp = client.responses.create(
                model="gpt-4.1-mini",
                input=[
                    {
                        "role": "system",
                        "content": [{"type": "input_text", "text": system_prompt.strip()}],
                    },
                    {
                        "role": "user",
                        "content": [{"type": "input_text", "text": question}],
                    },
                ],
            )

            return _extract_text_from_response(resp)
    
    except Exception:
        return (
            "เฮียช้าตอบไม่ทันครับ 😅\n"
            "ลองถามใหม่อีกครั้งได้เลย"
        )    

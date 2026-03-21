import json

from src.ai.openai_client import get_openai_client
from src.handlers.ai_chat import (
    is_ai_chat_request,
    extract_ai_question,
    _extract_text_from_response,
)
from src.repos.media_assets import search_measurement_guides


def is_ai_guide_request(text: str) -> bool:
    return is_ai_chat_request(text)


def _safe_route_json(raw_text: str) -> dict:
    try:
        data = json.loads(raw_text)
        return {
            "should_send_guide_images": bool(data.get("should_send_guide_images", False)),
            "guide_intent": str(data.get("guide_intent", "none") or "none"),
            "object_name": str(data.get("object_name", "unknown") or "unknown"),
            "search_terms": [
                str(x).strip()
                for x in (data.get("search_terms", []) or [])
                if str(x).strip()
            ],
        }
    except Exception:
        return {
            "should_send_guide_images": False,
            "guide_intent": "none",
            "object_name": "unknown",
            "search_terms": [],
        }


def _route_guide_need(question: str) -> dict:
    client = get_openai_client()

    system_prompt = """
คุณเป็นตัวช่วยจัดเส้นทางให้แชทร้านอะไหล่

ตอบเป็น JSON เท่านั้น:
{
  "should_send_guide_images": boolean,
  "guide_intent": "measurement" | "identification" | "rotation" | "none",
  "object_name": string,
  "search_terms": [string]
}

หลักการ:
- ถ้าผู้ใช้ถามว่าต้องวัดยังไง วัดอะไร ขนาดอะไร เกลียวเท่าไร เทเปอร์ยังไง หรือทิศทางหมุน ให้ should_send_guide_images=true
- object_name ให้เป็นชื่อ normalized ถ้าเดาได้ เช่น:
  piston
  water_pump
  universal_joint
  tie_rod_end
  truck_tie_rod_end
  pitman_arm
  ball_joint
  hydraulic_pump_rotation
  thread
- ถ้าไม่ชัด ให้ object_name = "unknown"
- search_terms ให้เป็นคำสั้น ๆ ไทย/อังกฤษที่ใช้ค้น metadata รูป
- ถ้าไม่ควรส่งรูป ให้ guide_intent="none"
""".strip()

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": question}],
            },
        ],
    )
    return _safe_route_json(_extract_text_from_response(resp))


def _answer_ai_text(question: str) -> str:
    client = get_openai_client()

    system_prompt = """
คุณคือ "เฮียช้า" ผู้ช่วยแชทร้านอะไหล่
แนวทางตอบ:
- ตอบเป็นภาษาไทย
- สั้น กระชับ อ่านง่าย เหมาะกับ LINE
- โทนสุภาพ แบบคนในร้าน
- ถ้าเป็นเรื่องการวัดหรือเทียบอะไหล่ ให้บอกให้ส่งขนาดหรือรูปกลับมาเพิ่มได้
- ถ้ายังไม่แน่ใจ ให้ตอบแบบระวังว่า ยังไม่ชัวร์ ต้องเช็กเพิ่ม
""".strip()

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}],
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": question}],
            },
        ],
    )
    return _extract_text_from_response(resp)


def handle_ai_guide_query(engine, user_text: str) -> dict:
    question = extract_ai_question(user_text)

    if not question:
        return {
            "type": "text",
            "text": (
                "เฮียช้าพร้อมครับ\n"
                "ลองพิมพ์แบบนี้:\n"
                "• เฮียช้า วัดลูกหมากคันชักยังไง\n"
                "• จ๋า ปั๊มไฮดูทิศทางหมุนยังไง\n"
                "• เฮียช้า ลูกสูบต้องวัดอะไรบ้าง"
            ),
        }

    route = _route_guide_need(question)

    messages: list[dict] = []

    if route["should_send_guide_images"]:
        guides = search_measurement_guides(
            engine=engine,
            search_terms=route["search_terms"],
            object_name=route["object_name"],
            guide_intent=route["guide_intent"],
            limit=3,
        )

        if guides:
            messages.append({
                "type": "text",
                "text": "ผมส่งรูปอ้างอิงที่น่าจะช่วยก่อนครับ",
            })

            for g in guides[:3]:
                if g.get("public_url"):
                    messages.append({
                        "type": "image",
                        "originalContentUrl": g["public_url"],
                        "previewImageUrl": g["public_url"],
                    })

    answer_text = _answer_ai_text(question)
    messages.append({
        "type": "text",
        "text": answer_text,
    })

    return {
        "type": "messages",
        "messages": messages,
    }
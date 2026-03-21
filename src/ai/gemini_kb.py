import os
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_FILE_SEARCH_STORE = os.getenv("GEMINI_FILE_SEARCH_STORE", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

client = genai.Client(api_key=GEMINI_API_KEY)


def _extract_reference_text(resp, max_refs: int = 3) -> str:
    """
    Try to build a short reference line from Gemini grounding metadata.
    Falls back silently if metadata is missing.
    """
    try:
        candidates = getattr(resp, "candidates", None) or []
        if not candidates:
            return ""

        gm = getattr(candidates[0], "grounding_metadata", None)
        if gm is None:
            return ""

        refs = []

        # Different SDK / response shapes may expose different fields
        chunks = getattr(gm, "grounding_chunks", None) or []
        supports = getattr(gm, "grounding_supports", None) or []

        # 1) Try chunk-level titles first
        for ch in chunks:
            title = None

            for attr in ("retrieved_context", "chunk", "web"):
                obj = getattr(ch, attr, None)
                if obj is not None:
                    maybe_title = getattr(obj, "title", None)
                    if maybe_title:
                        title = str(maybe_title).strip()
                        break

            if title and title not in refs:
                refs.append(title)

            if len(refs) >= max_refs:
                break

        # 2) Fallback: some responses only expose segment text or partial info
        if not refs:
            for s in supports:
                seg = getattr(s, "segment", None)
                if seg is not None:
                    maybe_text = getattr(seg, "text", None)
                    if maybe_text:
                        text = str(maybe_text).strip().replace("\n", " ")
                        if text and text not in refs:
                            refs.append(text[:60] + ("..." if len(text) > 60 else ""))

                if len(refs) >= max_refs:
                    break

        if not refs:
            return ""

        return "อ้างอิง: " + " | ".join(refs[:max_refs])

    except Exception:
        return ""


def ask_gemini_file_search(question: str) -> str:
    q = (question or "").strip()
    if not q:
        return "กรุณาพิมพ์คำถามก่อนครับ"

    if not GEMINI_FILE_SEARCH_STORE:
        return "ยังไม่ได้ตั้งค่า Gemini File Search store ครับ"

    prompt = f"""
ตอบคำถามนี้โดยใช้ข้อมูลจากเอกสารที่ค้นเจอเท่านั้น

คำถามผู้ใช้:
{q}

รูปแบบคำตอบ:
- ตอบเป็นภาษาไทย แบบสั้น กระชับ อ่านง่าย เหมาะกับแชต LINE
- บรรทัดแรก: สรุปคำตอบตรง ๆ ไม่เกิน 2 ประโยค
- จากนั้นสรุปเป็นหัวข้อสั้น ๆ 2-4 ข้อ
- ถ้ามีเงื่อนไขหรือข้อควรระวังสำคัญ ให้ใส่สั้น ๆ
- ถ้าข้อมูลไม่ชัดเจนหรือหาไม่เจอ ให้บอกตามตรง
- ห้ามเดาข้อมูลเพิ่ม
- ถ้าคำตอบยาวเกินไป ให้เลือกเฉพาะสาระที่ผู้ใช้ควรรู้ก่อน
- ยังไม่ต้องพิมพ์บรรทัดอ้างอิงเอง
"""

    try:
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[GEMINI_FILE_SEARCH_STORE]
                        )
                    )
                ]
            ),
        )

        answer = (getattr(resp, "text", "") or "").strip()
        if not answer:
            return "ผมหาคำตอบจากคลังเอกสารไม่เจอครับ ลองถามให้เฉพาะเจาะจงขึ้นอีกนิด"

        ref_line = _extract_reference_text(resp)

        final_text = answer
        if ref_line:
            final_text += f"\n\n{ref_line}"

        return final_text

    except Exception as e:
        print("Gemini file search error:", e)
        return "ระบบค้นหาคู่มือขัดข้องชั่วคราวครับ"
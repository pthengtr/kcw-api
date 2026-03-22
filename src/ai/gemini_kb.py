import os
import re
from google import genai
from google.genai import types

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_FILE_SEARCH_STORE = os.getenv("GEMINI_FILE_SEARCH_STORE", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()

client = genai.Client(api_key=GEMINI_API_KEY)


def _strip_trigger(text: str) -> str:
    t = (text or "").strip()

    triggers = [
        "เฮียช้า",
        "เฮียช้า ",
        "เฮียช้า:",
        "เฮียช้า,",
        "จ๋า"
    ]

    for trg in triggers:
        if t.lower().startswith(trg):
            t = t[len(trg):].strip()
            break

    return t


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

        chunks = getattr(gm, "grounding_chunks", None) or []
        supports = getattr(gm, "grounding_supports", None) or []

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


def _looks_like_image_url(url: str) -> bool:
    u = (url or "").lower()
    return any(ext in u for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]) or "/storage/v1/object/public/" in u


def _extract_images_from_text(text: str, max_images: int = 3) -> tuple[str, list[dict]]:
    """
    Supports:
    1) ![alt](url)
    2) [alt](url)  -> if url looks like image
    3) bare image urls
    """
    if not text:
        return "", []

    images = []
    seen = set()
    cleaned = text

    # 1) markdown images
    md_image_pattern = re.compile(r'!\[(.*?)\]\((https?://[^\s<>"\)]+(?:\?[^\s<>"\)]*)?)\)')
    for m in md_image_pattern.finditer(text):
        alt = (m.group(1) or "").strip()
        url = (m.group(2) or "").strip()
        if url and url not in seen and _looks_like_image_url(url):
            images.append({"alt": alt, "url": url})
            seen.add(url)
        if len(images) >= max_images:
            break

    cleaned = md_image_pattern.sub("", cleaned)

    # 2) normal markdown links that are actually images
    if len(images) < max_images:
        md_link_pattern = re.compile(r'(?<!!)\[(.*?)\]\((https?://[^\s<>"\)]+(?:\?[^\s<>"\)]*)?)\)')
        for m in md_link_pattern.finditer(text):
            alt = (m.group(1) or "").strip()
            url = (m.group(2) or "").strip()
            if url and url not in seen and _looks_like_image_url(url):
                images.append({"alt": alt, "url": url})
                seen.add(url)
            if len(images) >= max_images:
                break

        cleaned = md_link_pattern.sub("", cleaned)

    # 3) bare urls
    if len(images) < max_images:
        bare_url_pattern = re.compile(r'https?://[^\s<>"\]]+')
        for m in bare_url_pattern.finditer(text):
            url = (m.group(0) or "").rstrip(".,);:").strip()
            if url and url not in seen and _looks_like_image_url(url):
                images.append({"alt": "", "url": url})
                seen.add(url)
            if len(images) >= max_images:
                break

        for url in list(seen):
            cleaned = cleaned.replace(url, "")

    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned, images

def ask_gemini_file_search(question: str) -> dict:
    q = (_strip_trigger(question) or "").strip()
    if not q:
        return {
            "text": "ถามอะไรเฮียหน่อยสิครับ 😄",
            "images": [],
            "raw_answer": "",
        }

    if not GEMINI_FILE_SEARCH_STORE:
        return {
            "text": "ยังไม่ได้ตั้งค่า Gemini File Search store ครับ",
            "images": [],
            "raw_answer": "",
        }

    prompt = f"""
---

### System Instruction (ฉบับรวมสมบูรณ์)

**บทบาท:**
คุณคือผู้เชี่ยวชาญด้านเทคนิคอะไหล่ยนต์และเครื่องจักร (Technical Parts Specialist) ตอบคำถามโดยใช้ข้อมูลจากเอกสารที่อัปโหลดไว้ใน File Search เท่านั้น

**กฎการตอบคำถาม (LINE Format):**
1. **สรุปเนื้อหา:** ตอบเป็นภาษาไทย แบบสั้น กระชับ อ่านง่าย
   - **บรรทัดแรก:** สรุปคำตอบตรงๆ ไม่เกิน 2 ประโยค
   - **เนื้อหา:** สรุปเป็นหัวข้อสั้นๆ 2-4 ข้อ
   - **คำเตือน:** ถ้ามีเงื่อนไขหรือข้อควรระวังสำคัญ ให้ใส่สั้นๆ ท้ายคำตอบ
2. **การจัดการรูปภาพ (สำคัญมาก):**
   - หากในเอกสารมีลิงก์รูปภาพ Markdown (เช่น `![alt](https://...)`) **คุณต้องแสดงลิงก์นั้นในคำตอบเสมอ**
   - วางลิงก์รูปภาพไว้ต่อจากหัวข้อหรือคำอธิบายที่เกี่ยวข้องทันที
   - ห้ามแก้ไขหรือย่อ URL จาก Supabase โดยเด็ดขาด ต้องคัดลอกรูปแบบ `![alt text](url)` มาทั้งหมด
3. **ข้อจำกัดข้อมูล:**
   - หากข้อมูลไม่ชัดเจน ให้บอกว่า "ข้อมูลในคลังไม่ชัดเจน"
   - หากหาไม่เจอ ให้บอกว่า "ไม่มีข้อมูลในคลังข้อมูล"
   - **ห้ามเดาข้อมูลเพิ่มเองเด็ดขาด** ให้ตอบตามเอกสารเท่านั้น
4. **Tone & General Questions:**
   - หากเป็นคำถามทั่วไปที่ไม่เกี่ยวกับเรื่องงาน/อะไหล่ ให้ตอบติดตลกว่า "ตอนนี้เวลางานนะ ตั้งใจทำงานก่อน อย่าเพิ่งอู้ครับ!" หรือแนวๆ นี้
   - ไม่ต้องพิมพ์บรรทัดอ้างอิง (Citations) เอง

---

### ตัวอย่างรูปแบบการตอบที่ AI จะแสดงผล:

**ผู้ใช้ถาม:** วัดลูกหมากยังไง
**AI ตอบ:**
การวัดลูกหมากให้เน้นที่ขนาดแกนเตเปอร์และฐานบอดี้ครับ เพื่อความแม่นยำในการหาอะไหล่ทดแทน

• วัดขนาดแกนเตเปอร์ (Taper) ส่วนบนและล่าง
• วัดขนาดความโตของฐาน/บอดี้ลูกหมาก
![วิธีวัดขนาดลูกหมาก](https://xyz.supabase.co/storage/v1/object/public/bucket/ball-joint-01.png)

**ข้อควรระวัง:** ควรใช้เวอร์เนียร์ดิจิทัลเพื่อให้ได้ค่าที่ละเอียดที่สุดครับ

---

คำถามผู้ใช้:
{q}

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
            return {
                "text": "ผมหาคำตอบจากคลังเอกสารไม่เจอครับ ลองถามให้เฉพาะเจาะจงขึ้นอีกนิด",
                "images": [],
                "raw_answer": "",
            }

        ref_line = _extract_reference_text(resp)

        raw_answer = answer
        if ref_line:
            raw_answer += f"\n\n{ref_line}"

        cleaned_text, images = _extract_images_from_text(raw_answer, max_images=3)

        return {
            "text": cleaned_text,
            "images": images,
            "raw_answer": raw_answer,
        }

    except Exception as e:
        print("Gemini file search error:", e)
        print("RAW ANSWER:", raw_answer)
        print("IMAGES:", images)
        return {
            "text": "ระบบค้นหาคู่มือขัดข้องชั่วคราวครับ",
            "images": [],
            "raw_answer": "",
        }
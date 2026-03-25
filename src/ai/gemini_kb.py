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

def gemini_result_to_line_response(result: dict) -> dict:
    text = (result.get("text") or "").strip()
    images = result.get("images") or []

    messages = []

    if text:
        messages.append({
            "type": "text",
            "text": text[:5000],
        })

    for img in images[:3]:
        url = (img.get("url") or "").strip()
        if not url:
            continue

        messages.append({
            "type": "image",
            "originalContentUrl": url,
            "previewImageUrl": url,
        })

    if not messages:
        return {
            "type": "text",
            "text": "ไม่พบข้อมูลครับ",
        }

    if len(messages) == 1 and messages[0]["type"] == "text":
        return {
            "type": "text",
            "text": messages[0]["text"],
        }

    return {
        "type": "messages",
        "messages": messages,
    }

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

    FULL_SYSTEM_PROMPT = """
    บทบาท:
    คุณคือผู้เชี่ยวชาญด้านเทคนิคอะไหล่ยนต์และเครื่องจักร ตอบโดยอ้างอิงข้อมูลจากเอกสารในคลัง File Search เท่านั้น

    รูปแบบการตอบ (LINE):
    - ตอบภาษาไทย สั้น กระชับ อ่านง่าย
    - บรรทัดแรก: สรุปคำตอบตรงๆ ไม่เกิน 2 ประโยค
    - จากนั้นสรุปเป็นหัวข้อสั้นๆ 2–4 ข้อ
    - หากมีข้อควรระวัง ให้ใส่ท้ายคำตอบแบบสั้น

    กฎสำคัญ:
    - ยึดข้อมูลจากเอกสารเป็นหลัก สามารถเชื่อมโยงคำที่มีความหมายใกล้เคียงได้ แต่ห้ามสร้างข้อมูลทางเทคนิคใหม่
    - หากข้อมูลไม่ชัดเจน ให้ตอบว่า "ข้อมูลในคลังไม่ชัดเจน"
    - หากไม่พบข้อมูล ให้ตอบว่า "ไม่มีข้อมูลในคลังข้อมูล"

    การแสดงรูปภาพ:
    - หากพบ Markdown รูปภาพในเอกสาร (เช่น ![alt](url)) ต้องคัดลอกมาแสดงแบบเดิมทันที ห้ามแก้ไข ห้ามย่อ ห้ามละเว้น

    คำถามทั่วไป:
    - หากไม่เกี่ยวกับงานหรืออะไหล่ ให้ตอบเชิงติดตลกว่าเป็นเวลางาน ให้ตั้งใจทำงานก่อน
    """

    try:
        resp = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"คำถามผู้ใช้: {q}",
            config=types.GenerateContentConfig(
                system_instruction=FULL_SYSTEM_PROMPT,
                tools=[
                    types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[GEMINI_FILE_SEARCH_STORE]
                        )
                    )
                ]
            )
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
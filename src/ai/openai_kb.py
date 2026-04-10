import os
import re
import time
from typing import Dict, List, Optional, Tuple

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

client = OpenAI(api_key=OPENAI_API_KEY)


def _clean_image_url(url: str) -> str:
    if not url:
        return ""

    url = url.strip()

    # remove trailing markdown leftovers
    url = url.split(")")[0]
    url = url.split("\n")[0]

    return url.strip()

def _strip_trigger(text: str) -> str:
    t = (text or "").strip()
    triggers = ["เฮียช้า", "เฮียช้า ", "เฮียช้า:", "เฮียช้า,", "จ๋า"]
    for trg in triggers:
        if t.lower().startswith(trg):
            t = t[len(trg):].strip()
            break
    return t


def _looks_like_image_url(url: str) -> bool:
    u = (url or "").lower()
    return any(ext in u for ext in [".png", ".jpg", ".jpeg", ".webp", ".gif"]) or "/storage/v1/object/public/" in u


def _extract_images_from_text(text: str, max_images: int = 3) -> tuple[str, list[dict]]:
    if not text:
        return "", []

    images = []
    seen = set()
    cleaned = text

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

    if len(images) < max_images:
        md_link_pattern = re.compile(r'\[(.*?)\]\((https?://[^\s<>"\)]+(?:\?[^\s<>"\)]*)?)\)')
        for m in md_link_pattern.finditer(text):
            alt = (m.group(1) or "").strip()
            url = (m.group(2) or "").strip()
            if url and url not in seen and _looks_like_image_url(url):
                images.append({"alt": alt, "url": url})
                seen.add(url)
                if len(images) >= max_images:
                    break

        cleaned = md_link_pattern.sub("", cleaned)

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


def _extract_reference_text(resp, max_refs: int = 3) -> str:
    """
    Reads file_search tool results if present and builds a short reference line.
    """
    refs = []
    try:
        output = getattr(resp, "output", None) or []
        for item in output:
            if getattr(item, "type", None) != "file_search_call":
                continue

            results = getattr(item, "results", None) or []
            for r in results:
                name = getattr(r, "file_name", None) or getattr(r, "filename", None)
                if name:
                    name = str(name).strip()
                    if name and name not in refs:
                        refs.append(name)
                if len(refs) >= max_refs:
                    break

            if len(refs) >= max_refs:
                break
    except Exception:
        return ""

    if not refs:
        return ""

    return "อ้างอิง: " + " | ".join(refs[:max_refs])


def openai_result_to_line_response(result: dict) -> dict:
    text = (result.get("text") or "").strip()
    images = result.get("images") or []

    messages = []
    if text:
        messages.append({
            "type": "text",
            "text": text[:5000],
        })

    for img in images[:3]:
        url = _clean_image_url(img.get("url"))

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


MAX_RETRIES = 2
INITIAL_BACKOFF_SECONDS = 1.2


def ask_openai_file_search(question: str) -> dict:
    q = (_strip_trigger(question) or "").strip()
    if not q:
        return {
            "text": "ถามอะไรเฮียหน่อยสิครับ 😄",
            "images": [],
            "raw_answer": "",
        }

    if not OPENAI_VECTOR_STORE_ID:
        return {
            "text": "ยังไม่ได้ตั้งค่า OpenAI Vector Store ครับ",
            "images": [],
            "raw_answer": "",
        }

    system_prompt = """
บทบาท:
คุณคือผู้เชี่ยวชาญด้านเทคนิคอะไหล่ยนต์และเครื่องจักร ตอบโดยอ้างอิงข้อมูลจากเอกสารในคลัง File Search

รูปแบบการตอบ (LINE):
- ตอบภาษาไทย สั้น กระชับ อ่านง่าย
- บรรทัดแรก: สรุปคำตอบตรงๆ ไม่เกิน 2 ประโยค

- จากนั้น:
  • หากเป็นคำอธิบายทั่วไป → สรุปเป็นหัวข้อสั้นๆ 2–4 ข้อ
  • หากข้อมูลเป็น "รายการ", "list", "ตาราง", หรือมีหลายรายการในเอกสาร → ต้องแสดงรายการทั้งหมดตามเอกสาร (ไม่จำกัดจำนวน)

กฎการแสดงรายการ (สำคัญมาก):
- หากพบรายการในเอกสาร:
  • ต้องแสดงครบทั้งหมด ห้ามตัด ห้ามเลือกบางส่วน
  • ห้ามสรุปแทนรายการ
  • ต้องคงลำดับเดิมจากเอกสาร
  • ต้องคงชื่อสินค้า / รหัส / รุ่น ตามต้นฉบับ
  • สามารถจัดรูปแบบให้อ่านง่ายขึ้นได้ แต่ห้ามเปลี่ยนความหมาย

กฎสำคัญ:
- ตอบโดยอ้างอิงเฉพาะข้อมูลที่ค้นพบจาก File Search ในรอบนี้เท่านั้น
- ยึดข้อมูลจากเอกสารเป็นหลัก สามารถเชื่อมโยงคำที่มีความหมายใกล้เคียงได้ แต่ห้ามสร้างข้อมูลทางเทคนิคใหม่
- หากข้อมูลไม่ชัดเจน ให้ตอบว่า "ข้อมูลในคลังไม่ชัดเจน"
- หากไม่พบข้อมูล ให้ตอบว่า "ไม่มีข้อมูลในคลังข้อมูล"
- หากคำตอบมีหลายความเป็นไปได้ ให้เลือกเฉพาะที่เอกสารระบุชัด
- ห้ามใช้ความรู้ทั่วไปนอกเอกสาร แม้จะดูเหมือนถูกต้อง

ข้อห้ามเพิ่มเติม:
- ห้ามสร้างรายการสินค้าใหม่ที่ไม่มีในเอกสาร
- ห้ามแนะนำสินค้าอื่นนอกเหนือจากที่ปรากฏในเอกสาร
- ห้ามขยายไปยังรุ่นหรือหมวดอื่นที่ไม่ได้อยู่ในข้อมูลที่ค้นพบ

การแสดงรูปภาพ:
- หากพบ Markdown รูปภาพในเอกสาร (เช่น ![alt](url)) ต้องคัดลอกมาแสดงแบบเดิมทันที ห้ามแก้ไข ห้ามย่อ ห้ามละเว้น

คำถามทั่วไป:
- หากไม่เกี่ยวกับงานหรืออะไหล่ ให้ตอบเชิงติดตลกว่าเป็นเวลางาน ให้ตั้งใจทำงานก่อน

การตรวจสอบก่อนตอบ:
- หากมีรายการมากกว่า 4 รายการ → ต้องแสดงครบ ห้ามสรุป
- ตรวจสอบว่าไม่มีการตัดรายการออก
- ตรวจสอบว่าไม่มีข้อมูลที่ไม่ได้มาจากเอกสาร
""".strip()

    raw_answer = ""
    images: List[dict] = []

    def _call_once() -> dict:
        resp = client.responses.create(
            model=OPENAI_MODEL,
            instructions=system_prompt,
            input=f"คำถามผู้ใช้: {q}",
            tools=[
                {
                    "type": "file_search",
                    "vector_store_ids": [OPENAI_VECTOR_STORE_ID],
                    "max_num_results": 8,
                }
            ],
            include=["file_search_call.results"],
        )

        answer = (getattr(resp, "output_text", "") or "").strip()
        if not answer:
            return {
                "text": "",
                "images": [],
                "raw_answer": "",
            }

        ref_line = _extract_reference_text(resp)
        combined_answer = answer
        if ref_line:
            combined_answer += f"\\n\\n{ref_line}"

        cleaned_text, extracted_images = _extract_images_from_text(combined_answer, max_images=3)

        return {
            "text": cleaned_text,
            "images": extracted_images,
            "raw_answer": combined_answer,
        }

    last_error = None
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(MAX_RETRIES + 1):
        try:
            result = _call_once()
            if (result.get("text") or "").strip():
                return result
            last_error = RuntimeError("Empty response")
        except Exception as e:
            last_error = e
            print(f"OpenAI file search error attempt {attempt + 1}: {e}")

        if attempt < MAX_RETRIES:
            time.sleep(backoff)
            backoff *= 2

    print("OpenAI file search failed:", last_error)
    return {
        "text": "ระบบค้นหาคู่มือขัดข้องชั่วคราวครับ",
        "images": [],
        "raw_answer": raw_answer,
    }
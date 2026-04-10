import os
import re
import time
import uuid
import logging
from typing import List

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_VECTOR_STORE_ID = os.getenv("OPENAI_VECTOR_STORE_ID", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()

# request timeout in seconds for each OpenAI call
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "8").strip())

# retry settings
MAX_RETRIES = int(os.getenv("OPENAI_MAX_RETRIES", "2").strip())
INITIAL_BACKOFF_SECONDS = float(os.getenv("OPENAI_INITIAL_BACKOFF_SECONDS", "1.2").strip())

client = OpenAI(
    api_key=OPENAI_API_KEY,
    max_retries=0,
)

logger = logging.getLogger("kcw.openai_kb")


def _clean_image_url(url: str) -> str:
    if not url:
        return ""
    url = url.strip()
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

    md_image_pattern = re.compile(
        r'!\[(.*?)\]\((https?://[^\s<>"\)]+(?:\?[^\s<>"\)]*)?)\)'
    )
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
        md_link_pattern = re.compile(
            r'\[(.*?)\]\((https?://[^\s<>"\)]+(?:\?[^\s<>"\)]*)?)\)'
        )
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


def ask_openai_file_search(question: str) -> dict:
    trace_id = str(uuid.uuid4())[:8]
    t_total_0 = time.perf_counter()

    q = (_strip_trigger(question) or "").strip()
    if not q:
        return {
            "text": "ถามอะไรเฮียหน่อยสิครับ ",
            "images": [],
            "raw_answer": "",
        }

    if not OPENAI_VECTOR_STORE_ID:
        logger.warning("trace=%s vector_store_missing", trace_id)
        return {
            "text": "ยังไม่ได้ตั้งค่า OpenAI Vector Store ครับ",
            "images": [],
            "raw_answer": "",
        }

    system_prompt = """
บทบาท:
คุณคือผู้เชี่ยวชาญด้านอะไหล่ยนต์และเครื่องจักร
ตอบโดยอ้างอิงข้อมูลจาก File Search เท่านั้น

ภาษาที่ใช้:

ภาษาไทย
สั้น กระชับ อ่านง่าย (เหมาะกับ LINE)

โครงสร้างคำตอบ:

บรรทัดแรก: สรุปคำตอบตรงๆ ไม่เกิน 2 ประโยค
จากนั้น:
หากเป็นคำอธิบายทั่วไป → สรุปเป็นหัวข้อสั้นๆ 2–4 ข้อ
หากเป็นข้อมูลแบบรายการ / list / ตาราง → แสดงรายการทั้งหมด

กฎการแสดงรายการ (สำคัญ):

ต้องแสดงครบทั้งหมด ห้ามตัด ห้ามเลือกบางส่วน
ห้ามสรุปแทนรายการ
ต้องคงลำดับเดิม
ต้องคงชื่อสินค้า / รุ่น / รหัส ตามเอกสาร
จัดรูปแบบให้อ่านง่ายได้ แต่ห้ามเปลี่ยนความหมาย

กฎการอ้างอิง:

ใช้เฉพาะข้อมูลที่พบจาก File Search ในรอบนี้เท่านั้น
ห้ามใช้ความรู้ภายนอก
สามารถตีความคำใกล้เคียงได้ แต่ห้ามสร้างข้อมูลใหม่

กรณีข้อมูล:

ไม่พบข้อมูล → "ไม่มีข้อมูลในคลังข้อมูล"
ข้อมูลไม่ชัดเจน → "ข้อมูลในคลังไม่ชัดเจน"
มีหลายความเป็นไปได้ → เลือกเฉพาะที่เอกสารระบุชัด

ข้อห้าม:

ห้ามสร้างรายการสินค้าใหม่
ห้ามแนะนำสินค้านอกเอกสาร
ห้ามขยายไปหมวดหรือรุ่นอื่น

รูปภาพ:
- หากพบ Markdown รูปภาพ (![]()) ต้องแสดงตามต้นฉบับทุกตัวอักษร ห้ามแก้ไข ห้ามย่อ ห้ามละเว้น

คำถามทั่วไป:

หากไม่เกี่ยวกับอะไหล่ → ตอบเชิงติดตลกว่าเป็นเวลางาน ให้ตั้งใจทำงานก่อน

ลำดับการตัดสินใจ:

ค้นข้อมูลจาก File Search
ถ้าไม่พบ → ตอบ "ไม่มีข้อมูลในคลังข้อมูล"
ถ้าพบเป็นรายการ → แสดงครบทั้งหมด
ถ้าเป็นคำอธิบาย → สรุป 2–4 ข้อ
ตรวจสอบว่าทุกข้อมูลมาจากเอกสารเท่านั้น
""".strip()

    raw_answer = ""

    def _call_once() -> dict:
        t_req_0 = time.perf_counter()

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
            max_output_tokens=700,
            timeout=OPENAI_TIMEOUT_SECONDS,
        )

        t_req_1 = time.perf_counter()

        answer = (getattr(resp, "output_text", "") or "").strip()

        ref_line = _extract_reference_text(resp)
        combined_answer = answer
        if ref_line:
            combined_answer = f"{combined_answer}\n\n{ref_line}" if combined_answer else ref_line

        cleaned_text, extracted_images = _extract_images_from_text(combined_answer, max_images=3)

        logger.info(
            "trace=%s stage=openai_call model=%s qlen=%d openai_ms=%.1f output_chars=%d images=%d",
            trace_id,
            OPENAI_MODEL,
            len(q),
            (t_req_1 - t_req_0) * 1000,
            len(cleaned_text or ""),
            len(extracted_images),
        )

        return {
            "text": cleaned_text,
            "images": extracted_images,
            "raw_answer": combined_answer,
        }

    last_error = None
    backoff = INITIAL_BACKOFF_SECONDS

    for attempt in range(MAX_RETRIES + 1):
        attempt_t0 = time.perf_counter()

        try:
            logger.info(
                "trace=%s attempt=%d/%d stage=start q=%r",
                trace_id,
                attempt + 1,
                MAX_RETRIES + 1,
                q[:200],
            )

            result = _call_once()
            raw_answer = result.get("raw_answer", "") or ""

            if (result.get("text") or "").strip() or (result.get("images") or []):
                logger.info(
                    "trace=%s attempt=%d/%d stage=success attempt_ms=%.1f total_ms=%.1f",
                    trace_id,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    (time.perf_counter() - attempt_t0) * 1000,
                    (time.perf_counter() - t_total_0) * 1000,
                )
                return result

            last_error = RuntimeError("Empty response")
            logger.warning(
                "trace=%s attempt=%d/%d stage=empty_response attempt_ms=%.1f",
                trace_id,
                attempt + 1,
                MAX_RETRIES + 1,
                (time.perf_counter() - attempt_t0) * 1000,
            )

        except Exception as e:
            last_error = e
            logger.exception(
                "trace=%s attempt=%d/%d stage=error attempt_ms=%.1f err=%s",
                trace_id,
                attempt + 1,
                MAX_RETRIES + 1,
                (time.perf_counter() - attempt_t0) * 1000,
                e,
            )

        if attempt < MAX_RETRIES:
            logger.info(
                "trace=%s attempt=%d/%d stage=backoff sleep_s=%.2f total_ms=%.1f",
                trace_id,
                attempt + 1,
                MAX_RETRIES + 1,
                backoff,
                (time.perf_counter() - t_total_0) * 1000,
            )
            time.sleep(backoff)
            backoff *= 2

    logger.error(
        "trace=%s stage=failed total_ms=%.1f last_error=%r",
        trace_id,
        (time.perf_counter() - t_total_0) * 1000,
        last_error,
    )

    return {
        "text": "ระบบค้นหาคู่มือขัดข้องชั่วคราวครับ",
        "images": [],
        "raw_answer": raw_answer,
    }
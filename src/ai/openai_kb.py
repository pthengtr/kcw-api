import os
import re
import time
import uuid
import json
import logging
from typing import List

from openai import OpenAI

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small").strip()

# request timeout in seconds for each OpenAI call
OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12").strip())

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
    """
    Kept old function name for compatibility with router.py.
    Actual behavior is now: embed the stripped query and return the vector.
    """
    trace_id = str(uuid.uuid4())[:8]
    t_total_0 = time.perf_counter()
    q = (_strip_trigger(question) or "").strip()

    if not q:
        return {
            "text": "ถามอะไรเฮียหน่อยสิครับ ",
            "images": [],
            "raw_answer": "",
            "embedding": [],
            "query": "",
            "model": OPENAI_EMBEDDING_MODEL,
            "dimensions": 0,
        }

    if not OPENAI_API_KEY:
        logger.warning("trace=%s openai_api_key_missing", trace_id)
        return {
            "text": "ยังไม่ได้ตั้งค่า OpenAI API Key ครับ",
            "images": [],
            "raw_answer": "",
            "embedding": [],
            "query": q,
            "model": OPENAI_EMBEDDING_MODEL,
            "dimensions": 0,
        }

    raw_answer = ""

    def _call_once() -> dict:
        t_req_0 = time.perf_counter()

        resp = client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=q,
            timeout=OPENAI_TIMEOUT_SECONDS,
        )

        t_req_1 = time.perf_counter()
        vector = resp.data[0].embedding if resp.data else []

        preview = {
            "query": q,
            "model": OPENAI_EMBEDDING_MODEL,
            "dimensions": len(vector),
            "first_8": vector[:8],
        }
        answer_text = json.dumps(preview, ensure_ascii=False)

        logger.info(
            "trace=%s stage=openai_embedding model=%s qlen=%d openai_ms=%.1f dims=%d",
            trace_id,
            OPENAI_EMBEDDING_MODEL,
            len(q),
            (t_req_1 - t_req_0) * 1000,
            len(vector),
        )

        usage = getattr(resp, "usage", None)
        if usage:
            try:
                logger.info(
                    "tokens input=%s total=%s",
                    getattr(usage, "prompt_tokens", None) or getattr(usage, "input_tokens", None),
                    getattr(usage, "total_tokens", None),
                )
            except Exception:
                pass

        return {
            "text": answer_text,
            "images": [],
            "raw_answer": answer_text,
            "embedding": vector,
            "query": q,
            "model": OPENAI_EMBEDDING_MODEL,
            "dimensions": len(vector),
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

            if result.get("embedding"):
                logger.info(
                    "trace=%s attempt=%d/%d stage=success attempt_ms=%.1f total_ms=%.1f",
                    trace_id,
                    attempt + 1,
                    MAX_RETRIES + 1,
                    (time.perf_counter() - attempt_t0) * 1000,
                    (time.perf_counter() - t_total_0) * 1000,
                )
                return result

            last_error = RuntimeError("Empty embedding response")
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
        "text": "ระบบ embedding ขัดข้องชั่วคราวครับ",
        "images": [],
        "raw_answer": raw_answer,
        "embedding": [],
        "query": q,
        "model": OPENAI_EMBEDDING_MODEL,
        "dimensions": 0,
    }
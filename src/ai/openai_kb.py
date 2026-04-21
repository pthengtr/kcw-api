import os
import re
import logging
from typing import Any

from openai import OpenAI
from supabase import create_client, Client

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "").strip()
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip()
OPENAI_EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small").strip()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").strip()
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()
SUPABASE_KB_SCHEMA = os.getenv("SUPABASE_KB_SCHEMA", "kb").strip()
SUPABASE_KB_RPC = os.getenv("SUPABASE_KB_RPC", "match_kb_parts").strip()

# table used for direct fetch by id after quick-reply selection
SUPABASE_KB_TABLE = os.getenv("SUPABASE_KB_TABLE", "kb_parts").strip()

KB_MATCH_COUNT = int(os.getenv("KB_MATCH_COUNT", "3").strip())
KB_AUTO_THRESHOLD = float(os.getenv("KB_AUTO_THRESHOLD", "0.90").strip())
KB_MIN_GAP = float(os.getenv("KB_MIN_GAP", "0.06").strip())

OPENAI_TIMEOUT_SECONDS = float(os.getenv("OPENAI_TIMEOUT_SECONDS", "12").strip())

# new flags
AI_FORMAT_KB_ENABLED = os.getenv("AI_FORMAT_KB_ENABLED", "false").strip().lower() in {
    "1", "true", "yes", "on"
}
AI_FORMAT_KB_MODEL = os.getenv("AI_FORMAT_KB_MODEL", "gpt-4o-mini").strip()

SUPABASE_KB_TABLE = os.getenv("SUPABASE_KB_TABLE", "kb_parts").strip()
SUPABASE_KB_IMAGE_BUCKET = os.getenv("SUPABASE_KB_IMAGE_BUCKET", "kb-parts").strip()
KB_MAX_IMAGES = min(int(os.getenv("KB_MAX_IMAGES", "3").strip()), 4)

client = OpenAI(
    api_key=OPENAI_API_KEY,
    max_retries=0,
)

supabase: Client | None = None
if SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

logger = logging.getLogger("kcw.openai_kb")

def _kb_table():
    if supabase is None:
        raise RuntimeError("Supabase client is not configured")
    return supabase.schema(SUPABASE_KB_SCHEMA).table(SUPABASE_KB_TABLE)

def _list_kb_images(kb_id: str, max_images: int = KB_MAX_IMAGES) -> list[dict[str, str]]:
    if supabase is None:
        raise RuntimeError("Supabase client is not configured")

    folder = str(kb_id).strip()
    if not folder:
        return []

    files = (
        supabase.storage
        .from_(SUPABASE_KB_IMAGE_BUCKET)
        .list(
            folder,
            {
                "limit": max(max_images, 1),
                "offset": 0,
                "sortBy": {"column": "name", "order": "asc"},
            },
        )
    ) or []

    images: list[dict[str, str]] = []

    for item in files:
        name = str((item or {}).get("name") or "").strip()
        if not name or name.endswith("/"):
            continue

        path = f"{folder}/{name}"
        public_url = supabase.storage.from_(SUPABASE_KB_IMAGE_BUCKET).get_public_url(path)
        url = str(public_url or "").strip()
        if not url:
            continue

        images.append({"alt": name, "url": url})

        if len(images) >= max_images:
            break

    return images

def _strip_trigger(text: str) -> str:
    t = (text or "").strip()
    triggers = ["เฮียช้า", "เฮียช้า ", "เฮียช้า:", "เฮียช้า,", "จ๋า"]
    for trg in triggers:
        if t.lower().startswith(trg):
            t = t[len(trg):].strip()
            break
    return t

def _extract_images_from_text(text: str, max_images: int = 3) -> tuple[str, list[dict[str, str]]]:
    if not text:
        return "", []

    images: list[dict[str, str]] = []
    seen = set()
    cleaned = text

    md_image_pattern = re.compile(
        r'!\[(.*?)\]\((https?://[^\s<>"\)]+(?:\?[^\s<>"\)]*)?)\)'
    )

    for m in md_image_pattern.finditer(text):
        alt = (m.group(1) or "").strip()
        url = (m.group(2) or "").strip()
        if url and url not in seen:
            images.append({"alt": alt, "url": url})
            seen.add(url)
        if len(images) >= max_images:
            break

    cleaned = md_image_pattern.sub("", cleaned)
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
        url = (img.get("url") or "").strip()
        if not url:
            continue
        messages.append({
            "type": "image",
            "originalContentUrl": url,
            "previewImageUrl": url,
        })

    if not messages:
        return {"type": "text", "text": "ไม่พบข้อมูลครับ"}

    if len(messages) == 1 and messages[0]["type"] == "text":
        return {"type": "text", "text": messages[0]["text"]}

    return {"type": "messages", "messages": messages}

def _embed_query(question: str) -> list[float]:
    resp = client.embeddings.create(
        model=OPENAI_EMBED_MODEL,
        input=question,
        timeout=OPENAI_TIMEOUT_SECONDS,
    )
    return resp.data[0].embedding

def _search_kb(query_embedding: list[float], match_count: int) -> list[dict[str, Any]]:
    if supabase is None:
        raise RuntimeError("Supabase client is not configured")

    rpc = supabase.rpc(
        SUPABASE_KB_RPC,
        {
            "query_embedding": query_embedding,
            "match_count": match_count,
        },
    ).execute()

    return rpc.data or []

def get_kb_by_id(kb_id: str) -> dict[str, Any] | None:
    if supabase is None:
        raise RuntimeError("Supabase client is not configured")

    resp = (
        _kb_table()
        .select("id,title,content,related")
        .eq("id", kb_id)
        .limit(1)
        .execute()
    )

    data = resp.data or []
    return data[0] if data else None

def _build_direct_answer(row: dict[str, Any]) -> str:
    title = str(row.get("title") or "").strip()
    content = str(row.get("content") or "").strip()
    related = str(row.get("related") or "").strip()

    lines = []
    if title:
        lines.append(title)
    if content:
        lines.append(content)
    if related:
        lines.append("")
        lines.append("อะไหล่เกี่ยวข้อง:")
        lines.append(related)

    return "\n".join(lines).strip() or "ไม่มีข้อมูลในคลังข้อมูล"

def _format_with_ai(question: str, raw_answer: str) -> str:
    """
    Use GPT-4o-mini to make deterministic final answer cleaner for LINE.
    Must preserve facts exactly.
    """
    try:
        resp = client.chat.completions.create(
            model=AI_FORMAT_KB_MODEL,
            temperature=0.0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You format Thai auto-parts knowledge answers for LINE.\n"
                        "Rules:\n"
                        "- Use ONLY the provided source text\n"
                        "- Keep ALL part codes, quantities, model names, and facts EXACTLY the same\n"
                        "- Do NOT add, infer, explain, summarize beyond the source, or remove lines\n"
                        "- Improve readability only\n"
                        "- Keep it concise and easy to read in LINE\n"
                        "- Plain text only\n"
                        "- No markdown table\n"
                        "- No bold\n"
                        "- Bullets are allowed only as '-'"
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question}\n\n"
                        f"Source text:\n{raw_answer}\n\n"
                        "Format this for LINE."
                    ),
                },
            ],
            timeout=OPENAI_TIMEOUT_SECONDS,
        )
        return (resp.choices[0].message.content or "").strip() or raw_answer
    except Exception as e:
        logger.exception("AI format failed: %s", e)
        return raw_answer

def _maybe_format_with_ai(question: str, raw_answer: str) -> str:
    if not raw_answer:
        return raw_answer

    if not AI_FORMAT_KB_ENABLED:
        return raw_answer

    return _format_with_ai(question, raw_answer)

def handle_kb_select_postback(data: str) -> dict:
    kb_id = (data or "").replace("kb_select:", "", 1).strip()
    if not kb_id:
        return {
            "text": "ไม่พบรายการที่เลือกครับ",
            "images": [],
            "raw_answer": "",
        }

    try:
        row = get_kb_by_id(kb_id)
        if not row:
            return {
                "text": "ไม่พบข้อมูลรายการที่เลือกครับ",
                "images": [],
                "raw_answer": "",
            }

        raw_answer_text = _build_direct_answer(row)
        final_answer_text = _maybe_format_with_ai(
            str(row.get("title") or "").strip(),
            raw_answer_text,
        )

        images = _list_kb_images(kb_id, KB_MAX_IMAGES)

        return {
            "text": final_answer_text,
            "images": images,
            "raw_answer": raw_answer_text,
        }

    except Exception as e:
        logger.exception("kb_select_error=%s", e)
        return {
            "text": "ระบบค้นหาคลังข้อมูลขัดข้องชั่วคราวครับ",
            "images": [],
            "raw_answer": "",
        }
    
def build_kb_quick_reply_result(question: str) -> dict:
    q = (_strip_trigger(question) or "").strip()
    if not q:
        return {"type": "text", "text": "ถามอะไรเฮียหน่อยสิครับ"}

    emb = _embed_query(q)
    rows = _search_kb(emb, KB_MATCH_COUNT)

    if not rows:
        return {"type": "text", "text": "ไม่มีข้อมูลในคลังข้อมูล"}

    items = []
    lines = ["เจอหัวข้อใกล้เคียงครับ เลือกได้เลย:"]

    for idx, row in enumerate(rows[:10], start=1):
        kb_id = str(row.get("id") or "").strip()
        title = str(row.get("title") or f"หัวข้อ {idx}").strip()

        lines.append(f"{idx}. {title}")

        items.append({
            "type": "action",
            "action": {
                "type": "postback",
                "label": title[:20],
                "data": f"kb_select:{kb_id}",
                "displayText": title[:300],
            }
        })

    return {
        "type": "messages",
        "messages": [
            {
                "type": "text",
                "text": "\n".join(lines)[:5000],
                "quickReply": {"items": items},
            }
        ],
    }



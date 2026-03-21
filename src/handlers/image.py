import os
from supabase import create_client, Client

SUPABASE_URL = os.getenv("SUPABASE_DB_URL", "").rstrip("/")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_IMAGE_BUCKET = os.getenv("SUPABASE_IMAGE_BUCKET", "pictures")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)


def build_public_storage_url(bucket: str, path: str) -> str:
    path = path.lstrip("/")
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def is_image_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return (
        t == "img" or t.startswith("img ")
        or t == "รูป" or t.startswith("รูป ")
        or t == "ภาพ" or t.startswith("ภาพ ")
    )


def extract_image_key(text: str) -> str | None:
    parts = (text or "").strip().split(maxsplit=1)
    if len(parts) < 2:
        return None
    return parts[1].strip()


def list_product_images(bcode: str, max_images: int = 3) -> list[str]:
    folder = f"product/{bcode}".strip("/")

    items = supabase.storage.from_(SUPABASE_IMAGE_BUCKET).list(folder)

    if not items:
        return []

    image_exts = {".jpg", ".jpeg", ".png", ".webp"}
    paths = []

    for item in items:
        name = item.get("name", "")
        lower = name.lower()

        if "." not in lower:
            continue

        ext = "." + lower.rsplit(".", 1)[-1]
        if ext not in image_exts:
            continue

        paths.append(f"{folder}/{name}")

    paths.sort()
    return paths[:max_images]


def handle_image_command(text: str) -> dict:
    bcode = extract_image_key(text)

    if not bcode:
        return {
            "type": "text",
            "text": "กรุณาระบุรหัสสินค้า เช่น รูป 22010585"
        }

    image_paths = list_product_images(bcode, max_images=3)

    if not image_paths:
        return {
            "type": "text",
            "text": f"ไม่พบรูปสินค้าสำหรับ {bcode} ครับ"
        }

    messages = [
        {
            "type": "text",
            "text": f"รูปสินค้า {bcode} ({len(image_paths)} รูป)"
        }
    ]

    for path in image_paths:
        url = build_public_storage_url(SUPABASE_IMAGE_BUCKET, path)
        messages.append({
            "type": "image",
            "originalContentUrl": url,
            "previewImageUrl": url,
        })

    return {
        "type": "messages",
        "messages": messages,
    }
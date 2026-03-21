import os


SUPABASE_URL = os.getenv("SUPABASE_DB_URL", "").rstrip("/")
SUPABASE_IMAGE_BUCKET = os.getenv("SUPABASE_IMAGE_BUCKET", "pictures")


def build_public_storage_url(bucket: str, path: str) -> str:
    path = path.lstrip("/")
    return f"{SUPABASE_URL}/storage/v1/object/public/{bucket}/{path}"


def is_image_command(text: str) -> bool:
    t = (text or "").strip().lower()
    return t == "img" or t.startswith("img ")


def handle_image_command(text: str) -> dict:
    t = (text or "").strip()
    parts = t.split(maxsplit=1)
    key = parts[1].strip().lower() if len(parts) > 1 else "test"

    image_map = {
        "test": "public/knowledge/how_to_measure_screw.jpg",
    }

    path = image_map.get(key)
    if not path:
        return {
            "type": "text",
            "text": "ไม่พบรูปครับ ลองใช้: img test"
        }

    image_url = build_public_storage_url(SUPABASE_IMAGE_BUCKET, path)

    print("DEBUG image_url:", image_url)

    return {
        "type": "image",
        "originalContentUrl": image_url,
        "previewImageUrl": image_url,
    }
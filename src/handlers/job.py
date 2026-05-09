from src.jobs.queue import (
    get_job_by_id,
    get_jobs_by_batch_id,
    get_recent_jobs_for_requester,
)
from src.jobs.tasks import (
    enqueue_sync_inventory_jobs,
    enqueue_sync_product_images_jobs,
    enqueue_sync_online_sales_jobs,
)
from src.jobs.heartbeat import get_all_worker_status
from src.access.helper import can_execute


def _qr_message(label: str, text: str) -> dict:
    return {
        "type": "action",
        "action": {
            "type": "message",
            "label": label,
            "text": text,
        },
    }

def is_update_menu_request(text: str) -> bool:
    t = (text or "").strip().lower()
    compact = "".join(t.split())

    return compact in {
        "update",
        "sync",
        "อัปเดต",
        "อัพเดต",
        "อัปเดท",
        "อัพเดท",
    }

def build_update_menu_quick_reply() -> dict:
    return {
        "items": [
            _qr_message("อัปเดตสต็อก", "อัปเดตสต็อก"),
            _qr_message("อัปเดตรูปสินค้า", "อัปเดตรูปสินค้า"),
            _qr_message("อัปเดตออนไลน์", "อัปเดตออนไลน์"),
            _qr_message("สถานะเครื่อง", "worker status"),
        ]
    }

def _job_quick_reply_label(job: dict, current_job_id: int | None = None) -> str:
    job_id = int(job["id"])

    if current_job_id is not None and job_id == current_job_id:
        return f"รีเฟรช {job_id}"

    payload = job.get("payload") or {}
    site = payload.get("site")

    if site:
        return f"{site} {job_id}"

    return f"job {job_id}"


def _job_quick_reply_jobs(job: dict, extra_jobs: list[dict]) -> list[dict]:
    job_id = int(job["id"])
    jobs_by_id = {job_id: job}

    for extra_job in extra_jobs:
        jobs_by_id.setdefault(int(extra_job["id"]), extra_job)

    current = jobs_by_id.pop(job_id)
    return [current, *jobs_by_id.values()]


def build_job_status_quick_reply(
    jobs: list[dict],
    current_job_id: int | None = None,
) -> dict:
    items = []

    for job in jobs[:12]:
        items.append(
            _qr_message(
                label=_job_quick_reply_label(job, current_job_id=current_job_id),
                text=f"job status {job['id']}",
            )
        )

    items.append(_qr_message("สถานะเครื่อง", "worker status"))

    return {"items": items}


def get_job_status_quick_reply_jobs(engine, job: dict) -> list[dict]:
    job_id = int(job["id"])
    batch_id = job.get("batch_id")

    related_jobs = []

    if batch_id:
        related_jobs = get_jobs_by_batch_id(engine, str(batch_id))

    if len(related_jobs) <= 1 and job.get("requested_by") and job.get("job_type"):
        related_jobs.extend(
            get_recent_jobs_for_requester(
                engine=engine,
                requested_by=job["requested_by"],
                job_type=job["job_type"],
                exclude_job_id=job_id,
                limit=3,
            )
        )

    return _job_quick_reply_jobs(job, related_jobs)

def text_response(text: str, quick_reply: dict | None = None) -> dict:
    response = {
        "type": "text",
        "text": text,
    }

    if quick_reply:
        response["quickReply"] = quick_reply

    return response

def is_sync_online_sales_request(text: str) -> bool:
    t = (text or "").strip().lower()
    compact = "".join(t.split())

    return (
        compact
        in {
            "อัปเดตออนไลน์",
            "อัพเดตออนไลน์",
            "อัปเดทออนไลน์",
            "อัพเดทออนไลน์",
            "อัปเดตonline",
            "อัพเดตonline",
            "อัปเดทonline",
            "อัพเดทonline",
            "updateonline",
            "synconline",
            "synconlinesales",
            "syncmarketplace",
        }
        or t
        in {
            "sync online",
            "sync online sales",
            "sync marketplace",
            "update online",
            "update online sales",
            "online sync",
            "online sales sync",
        }
    )

def is_sync_product_images_request(text: str) -> bool:
    t = (text or "").strip().lower()

    return t in {
        "sync รูป",
        "sync image",
        "sync images",
        "sync product images",
        "อัปเดตรูป",
        "อัพเดตรูป",
        "อัปเดตรูปสินค้า",
        "อัพเดตรูปสินค้า",
        "ซิงค์รูป",
        "ซิงค์รูปสินค้า",
    }

def is_sync_inventory_request(text: str) -> bool:
    t = (text or "").strip().lower()
    compact = "".join(t.split())

    return (
        compact
        in {
            "อัปเดตสต็อก",
            "อัพเดตสต็อก",
            "อัปเดทสต็อก",
            "อัพเดทสต็อก",
            "อัปเดตstock",
            "อัพเดตstock",
            "อัปเดทstock",
            "อัพเดทstock",
            "อัปเดตสินค้า",
            "อัพเดตสินค้า",
            "อัปเดทสินค้า",
            "อัพเดทสินค้า",
            "syncstock",
            "syncinventory",
        }
        or t
        in {
            "sync stock",
            "sync inventory",
            "update stock",
            "update inventory",
        }
    )

def is_worker_status_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"worker status", "สถานะเครื่อง"}

def is_job_request(text: str) -> bool:
    t = (text or "").strip().lower()

    return (
        t.startswith("job status")
        or is_worker_status_request(t)
        or is_update_menu_request(t)
        or is_sync_product_images_request(t)
        or is_sync_online_sales_request(t)
        or is_sync_inventory_request(t)
    )

def handle_job_query(engine, user_text: str, access: dict) -> dict:
    cmd = "job"

    if not can_execute(access["access_group"], cmd):
        return text_response("บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ")

    text = (user_text or "").strip()
    text_lower = text.lower()

    # job status
    if text_lower.startswith("job status "):
        raw_id = text_lower.replace("job status ", "", 1).strip()

        if not raw_id.isdigit():
            return text_response("รูปแบบไม่ถูกต้องครับ\nลองใช้: job status 123")

        job = get_job_by_id(engine, int(raw_id))

        if not job:
            return text_response(f"ไม่พบ job_id {raw_id}")

        job_id = int(job["id"])

        return text_response(
            format_job_status(job),
            quick_reply=build_job_status_quick_reply(
                get_job_status_quick_reply_jobs(engine, job),
                current_job_id=job_id,
            ),
        )

    # worker status
    if is_worker_status_request(text_lower):
        rows = get_all_worker_status(engine, offline_after_seconds=30)

        if not rows:
            return "ยังไม่พบ worker heartbeat"

        lines = ["สถานะ worker"]

        for r in rows:
            icon = "🟢" if r["online_status"] == "online" else "🔴"
            worker_state = r.get("worker_state") or "-"
            seconds_ago = r.get("seconds_ago")

            if seconds_ago is None:
                lines.append(f"{icon} {r['worker_name']} ({worker_state})")
            else:
                lines.append(
                    f"{icon} {r['worker_name']} ({worker_state}, {seconds_ago}s ago)"
                )

        return text_response(
            "\n".join(lines),
            quick_reply={"items": [_qr_message("รีเฟรชสถานะเครื่อง", "worker status")]},
        )

    # generic update menu
    if is_update_menu_request(text_lower):
        return text_response(
            "อยากอัปเดตอะไรครับ?",
            quick_reply=build_update_menu_quick_reply(),
        )
    
    # sync product images
    # Must be checked before inventory sync because old inventory trigger accepts "sync ..."
    if is_sync_product_images_request(text_lower):
        rows = get_all_worker_status(engine, offline_after_seconds=30)
        online_workers = {
            r["worker_name"]
            for r in rows
            if r["online_status"] == "online"
        }

        jobs = enqueue_sync_product_images_jobs(
            engine=engine,
            requested_by=access.get("line_user_id"),
            source="line",
            allowed_workers=online_workers,
        )

        if not jobs:
            return (
                "ยังสั่งซิงค์รูปไม่ได้ครับ\n"
                "ไม่พบ worker ที่ออนไลน์สำหรับงานนี้"
            )

        lines = ["ได้เลย เดี๋ยวจ๋าไปก๊อบรูปสินค้าลงเครื่องเซิฟเวอร์ให้นะ ✅"]

        for job in jobs:
            lines.append(
                f"- {job['payload'].get('site')}: "
                f"job_id {job['id']} -> {job.get('worker_name', '-')}"
            )

        lines.append("")
        lines.append("กดปุ่มด้านล่างเพื่อเช็คสถานะต่อได้เลย")

        return text_response(
            "\n".join(lines),
            quick_reply=build_job_status_quick_reply(jobs),
        )

    # sync inventory
    if is_sync_inventory_request(text_lower):
        rows = get_all_worker_status(engine, offline_after_seconds=30)
        online_workers = {
            r["worker_name"]
            for r in rows
            if r["online_status"] == "online"
        }

        jobs = enqueue_sync_inventory_jobs(
            engine=engine,
            requested_by=access.get("line_user_id"),
            source="line",
            allowed_workers=online_workers,
        )

        if not jobs:
            return "ไว้ลองใหม่อีกรอบนะครับ ตอนนี้ไม่มีใครว่างไปเช็คของให้"

        lines = ["โอเคครับ เดี๋ยวเฮียเดินไปเช็กสต็อกหลังร้านให้ครับ"]

        for job in jobs:
            lines.append(
                f"- {job['payload'].get('site')}: "
                f"job_id {job['id']} -> {job.get('worker_name', '-')}"
            )

        lines.append("")
        lines.append("กดปุ่มด้านล่างเพื่อเช็คสถานะต่อได้เลย")

        return text_response(
            "\n".join(lines),
            quick_reply=build_job_status_quick_reply(jobs),
        )

    # sync online sales
    # Must be checked before inventory sync because old inventory trigger accepts "sync ..." and "อัปเดต..."
    if is_sync_online_sales_request(text_lower):
        rows = get_all_worker_status(engine, offline_after_seconds=30)
        online_workers = {
            r["worker_name"]
            for r in rows
            if r["online_status"] == "online"
        }

        jobs = enqueue_sync_online_sales_jobs(
            engine=engine,
            requested_by=access.get("line_user_id"),
            source="line",
            allowed_workers=online_workers,
        )

        if not jobs:
            return text_response(
                "ยังอัปเดตออนไลน์ไม่ได้ครับ\n"
                "ไม่พบ HQ-PC ออนไลน์สำหรับงานนี้"
            )

        lines = ["ได้เลย เดี๋ยวจ๋าไปอัปเดตยอดขายออนไลน์ที่ HQ ให้นะ ✅"]

        for job in jobs:
            lines.append(
                f"- {job['payload'].get('site')}: "
                f"job_id {job['id']} -> {job.get('worker_name', '-')}"
            )

        lines.append("")
        lines.append("กดปุ่มด้านล่างเพื่อเช็คสถานะต่อได้เลย")

        return text_response(
            "\n".join(lines),
            quick_reply=build_job_status_quick_reply(jobs),
        )

    return "คำสั่งไม่ถูกต้อง"

def format_job_status(job: dict) -> str:
    parts = [
        f"job_id: {job.get('id')}",
        f"type: {job.get('job_type')}",
        f"status: {job.get('status')}",
        f"worker: {job.get('worker_name') or '-'}",
    ]

    payload = job.get("payload") or {}

    if payload.get("site"):
        parts.append(f"site: {payload['site']}")

    if payload.get("task"):
        parts.append(f"task: {payload['task']}")

    if job.get("result_message"):
        parts.append(f"result: {job['result_message']}")

    if job.get("error_message"):
        parts.append(f"error: {job['error_message']}")

    return "\n".join(parts)
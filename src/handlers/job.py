from src.jobs.queue import get_job_by_id
from src.jobs.tasks import enqueue_sync_inventory_jobs
from src.jobs.heartbeat import get_all_worker_status
from src.access.helper import can_execute


def is_sync_inventory_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return (
        t.startswith("sync")
        or t.startswith("อัปเดต")
        or t.startswith("อัพเดต")
    )


def is_worker_status_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {"worker status", "สถานะเครื่อง"}


def is_job_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return (
        t.startswith("job status")
        or is_worker_status_request(t)
        or is_sync_inventory_request(t)
    )


def handle_job_query(engine, user_text: str, access: dict) -> str:
    cmd = "job"

    if not can_execute(access["access_group"], cmd):
        return "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"

    text = (user_text or "").strip()
    text_lower = text.lower()

    # job status
    if text_lower.startswith("job status "):
        raw_id = text_lower.replace("job status ", "", 1).strip()
        if not raw_id.isdigit():
            return "รูปแบบไม่ถูกต้องครับ\nลองใช้: job status 123"

        job = get_job_by_id(engine, int(raw_id))
        if not job:
            return f"ไม่พบ job_id {raw_id}"

        return format_job_status(job)

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
                lines.append(f"{icon} {r['worker_name']} ({worker_state}, {seconds_ago}s ago)")

        return "\n".join(lines)

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

        lines = ["โอเคครับ 👍 เดี๋ยวเฮียเดินไปเช็กสต็อกหลังร้านให้ครับ 📦"]
        for job in jobs:
            lines.append(
                f"- {job['payload'].get('site')}: job_id {job['id']} -> {job.get('worker_name', '-')}"
            )

        return "\n".join(lines)

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

    if job.get("result_message"):
        parts.append(f"result: {job['result_message']}")

    if job.get("error_message"):
        parts.append(f"error: {job['error_message']}")

    return "\n".join(parts)
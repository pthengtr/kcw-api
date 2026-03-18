from src.jobs.queue import enqueue_job, get_job_by_id
from src.jobs.tasks import enqueue_sync_inventory_jobs
from src.access.helper import can_execute


def is_job_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return (
        t in {"test job", "queue test", "run test", "ทดสอบคิว", "ทดสอบงาน"}
        or t.startswith("job ")
        or t == "sync inventory"
    )


def handle_job_query(engine, user_text: str, access: dict) -> str:
    cmd = "job"

    if not can_execute(access["access_group"], cmd):
        return "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"

    text = (user_text or "").strip()
    text_lower = text.lower()

    if text_lower.startswith("job status "):
        raw_id = text_lower.replace("job status ", "", 1).strip()
        if not raw_id.isdigit():
            return "รูปแบบไม่ถูกต้องครับ\nลองใช้: job status 123"

        job = get_job_by_id(engine, int(raw_id))
        if not job:
            return f"ไม่พบ job_id {raw_id}"

        return format_job_status(job)

    if text_lower == "sync inventory":
        jobs = enqueue_sync_inventory_jobs(
            engine=engine,
            requested_by=access.get("line_user_id"),
            source="line",
        )

        lines = ["รับงาน sync inventory แล้วครับ ✅"]
        for job in jobs:
            lines.append(
                f"- {job['payload'].get('site')}: job_id {job['id']} -> {job['worker_name']}"
            )

        return "\n".join(lines)

    job = enqueue_job(
        engine=engine,
        job_type="echo_test",
        payload={"text": text},
        worker_name=None,
        requested_by=access.get("line_user_id"),
        source="line",
    )

    return (
        "รับงานแล้วครับ ✅\n"
        f"job_id: {job['id']}\n"
        "ลองเช็กสถานะด้วย:\n"
        f"job status {job['id']}"
    )


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
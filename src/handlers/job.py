from src.jobs.queue import enqueue_job, get_job_by_id
from src.access.helper import can_execute


JOB_TRIGGER_KEYWORDS = {
    "test job",
    "queue test",
    "run test",
    "ทดสอบคิว",
    "ทดสอบงาน",
}


def is_job_request(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in JOB_TRIGGER_KEYWORDS or t.startswith("job ")


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

    job = enqueue_job(
        engine=engine,
        job_type="echo_test",
        payload={"text": text},
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
    status = job.get("status") or "-"
    job_id = job.get("id")
    job_type = job.get("job_type") or "-"
    result_message = job.get("result_message")
    error_message = job.get("error_message")

    parts = [
        f"job_id: {job_id}",
        f"type: {job_type}",
        f"status: {status}",
    ]

    if result_message:
        parts.append(f"result: {result_message}")

    if error_message:
        parts.append(f"error: {error_message}")

    return "\n".join(parts)
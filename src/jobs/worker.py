import os
import time
import traceback

from src.db import get_engine
from src.jobs.queue import (
    claim_next_job,
    finish_job_success,
    finish_job_failed,
)


def process_job(job: dict) -> str:
    job_type = job["job_type"]
    payload = job.get("payload") or {}

    if job_type == "echo_test":
        text_value = payload.get("text", "")
        time.sleep(2)
        return f"echo ok: {text_value}"

    raise ValueError(f"Unsupported job_type: {job_type}")


def run_worker_forever():
    engine = get_engine()
    worker_name = os.getenv("WORKER_NAME", "unknown-worker")
    poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "3"))

    print(f"[START] worker={worker_name}")

    while True:
        try:
            job = claim_next_job(engine, worker_name=worker_name)

            if not job:
                time.sleep(poll_seconds)
                continue

            job_id = job["id"]
            print(f"[JOB START] id={job_id} type={job['job_type']}")

            try:
                result_message = process_job(job)
                finish_job_success(engine, job_id, result_message=result_message)
                print(f"[JOB DONE] id={job_id} result={result_message}")
            except Exception as job_error:
                err_text = "".join(
                    traceback.format_exception_only(type(job_error), job_error)
                ).strip()
                finish_job_failed(engine, job_id, error_message=err_text)
                print(f"[JOB FAILED] id={job_id} error={err_text}")

        except Exception as loop_error:
            print(f"[LOOP ERROR] {loop_error}")
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker_forever()
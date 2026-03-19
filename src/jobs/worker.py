import os
import time
import traceback
import subprocess

from src.db import get_engine
from src.jobs.queue import (
    claim_next_job,
    finish_job_success,
    finish_job_failed,
)
from src.jobs.heartbeat import upsert_worker_heartbeat


def run_sync_inventory(job: dict) -> str:
    bat_path = os.getenv("SYNC_INVENTORY_BAT")
    if not bat_path:
        raise ValueError("SYNC_INVENTORY_BAT is not configured")

    result = subprocess.run(
        [bat_path],
        capture_output=True,
        text=True,
        shell=True,
        timeout=60 * 30,
    )

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        raise RuntimeError(
            f"bat failed rc={result.returncode}; stderr={stderr[:500]}"
        )

    return stdout[:1000] or "sync_inventory completed"


def process_job(job: dict) -> str:
    job_type = job["job_type"]

    if job_type == "sync_inventory":
        return run_sync_inventory(job)

    raise ValueError(f"Unsupported job_type: {job_type}")


def run_worker_forever():
    engine = get_engine()
    worker_name = os.getenv("WORKER_NAME", "unknown-worker")
    poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "3"))
    heartbeat_interval_seconds = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "10"))

    print(f"[START] worker={worker_name}")

    last_heartbeat_at = 0.0

    while True:
        try:
            now_ts = time.time()

            if now_ts - last_heartbeat_at >= heartbeat_interval_seconds:
                upsert_worker_heartbeat(
                    engine=engine,
                    worker_name=worker_name,
                    status="idle",
                )
                last_heartbeat_at = now_ts

            job = claim_next_job(engine, worker_name=worker_name)

            if not job:
                time.sleep(poll_seconds)
                continue

            job_id = job["id"]
            print(f"[JOB START] id={job_id} type={job['job_type']}")

            upsert_worker_heartbeat(
                engine=engine,
                worker_name=worker_name,
                status="running",
            )

            try:
                result_message = process_job(job)

                finish_job_success(
                    engine=engine,
                    job_id=job_id,
                    result_message=result_message,
                )

                upsert_worker_heartbeat(
                    engine=engine,
                    worker_name=worker_name,
                    status="idle",
                )

                print(f"[JOB DONE] id={job_id} result={result_message}")

            except Exception as job_error:
                err_text = "".join(
                    traceback.format_exception_only(type(job_error), job_error)
                ).strip()

                finish_job_failed(
                    engine=engine,
                    job_id=job_id,
                    error_message=err_text,
                )

                upsert_worker_heartbeat(
                    engine=engine,
                    worker_name=worker_name,
                    status="idle",
                )

                print(f"[JOB FAILED] id={job_id} error={err_text}")

        except Exception as loop_error:
            print(f"[LOOP ERROR] {loop_error}")
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker_forever()
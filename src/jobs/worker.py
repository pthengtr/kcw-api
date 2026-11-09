import os
import threading
import time
import traceback

from dotenv import load_dotenv

from src.db import get_engine
from src.jobs.command_runner import run_configured_command
from src.jobs.queue import (
    claim_next_job,
    finish_job_failed,
    finish_job_success,
)
from src.jobs.heartbeat import upsert_worker_heartbeat
from src.stock_check.net import (
    resolve_companion_public_base_url,
    resolve_companion_tailscale_base_url,
    resolve_stock_check_public_base_url,
    resolve_stock_check_tailscale_base_url,
)
from src.parts9_explorer.net import (
    resolve_explorer_public_base_url,
    resolve_explorer_tailscale_base_url,
)
from src.pay_notes.net import (
    resolve_pay_notes_public_base_url,
    resolve_pay_notes_tailscale_base_url,
)
from src.transfer.net import (
    resolve_transfer_public_base_url,
    resolve_transfer_tailscale_base_url,
)


load_dotenv()


def process_job(job: dict) -> str:
    return run_configured_command(job)


def _resolve_service_urls() -> dict:
    return {
        "public_base_url": resolve_stock_check_public_base_url(),
        "companion_public_base_url": resolve_companion_public_base_url(),
        "explorer_public_base_url": resolve_explorer_public_base_url(),
        "tailscale_public_base_url": resolve_stock_check_tailscale_base_url(),
        "companion_tailscale_base_url": resolve_companion_tailscale_base_url(),
        "explorer_tailscale_base_url": resolve_explorer_tailscale_base_url(),
        "pay_notes_public_base_url": resolve_pay_notes_public_base_url(),
        "pay_notes_tailscale_base_url": resolve_pay_notes_tailscale_base_url(),
        "transfer_public_base_url": resolve_transfer_public_base_url(),
        "transfer_tailscale_base_url": resolve_transfer_tailscale_base_url(),
    }


def _send_heartbeat(engine, worker_name: str, status: str) -> None:
    upsert_worker_heartbeat(
        engine=engine,
        worker_name=worker_name,
        status=status,
        update_urls=True,
        **_resolve_service_urls(),
    )


def _start_heartbeat_thread(
    engine,
    worker_name: str,
    interval_seconds: int,
    status_holder: dict,
) -> threading.Event:
    """Keep last_seen fresh even while process_job() blocks on long commands."""
    stop_event = threading.Event()

    def _loop() -> None:
        while not stop_event.is_set():
            try:
                with status_holder["lock"]:
                    status = status_holder["status"]
                _send_heartbeat(engine, worker_name, status)
            except Exception as heartbeat_error:
                print(f"[HEARTBEAT ERROR] {heartbeat_error}")
            stop_event.wait(interval_seconds)

    thread = threading.Thread(
        target=_loop,
        name="kcw-worker-heartbeat",
        daemon=True,
    )
    thread.start()
    return stop_event


def run_worker_forever():
    engine = get_engine()

    worker_name = os.getenv("WORKER_NAME", "unknown-worker")
    poll_seconds = int(os.getenv("WORKER_POLL_SECONDS", "3"))
    heartbeat_interval_seconds = int(os.getenv("HEARTBEAT_INTERVAL_SECONDS", "10"))

    print(f"[START] worker={worker_name}")
    print(f"[START] poll_seconds={poll_seconds}")
    print(f"[START] heartbeat_interval_seconds={heartbeat_interval_seconds}")
    print(
        f"[START] public_base_url={resolve_stock_check_public_base_url() or '- (auto-detect pending)'}"
    )
    print(
        f"[START] explorer_public_base_url={resolve_explorer_public_base_url() or '- (auto-detect pending)'}"
    )
    print(
        f"[START] tailscale_public_base_url="
        f"{resolve_stock_check_tailscale_base_url() or '- (auto-detect pending)'}"
    )
    print("[START] command source=.env WORKER_JOB_<JOB_TYPE>_COMMAND")

    status_holder = {"status": "idle", "lock": threading.Lock()}
    _start_heartbeat_thread(
        engine=engine,
        worker_name=worker_name,
        interval_seconds=heartbeat_interval_seconds,
        status_holder=status_holder,
    )

    def set_status(status: str) -> None:
        with status_holder["lock"]:
            status_holder["status"] = status
        try:
            _send_heartbeat(engine, worker_name, status)
        except Exception as heartbeat_error:
            print(f"[HEARTBEAT ERROR] {heartbeat_error}")

    while True:
        try:
            job = claim_next_job(engine, worker_name=worker_name)

            if not job:
                time.sleep(poll_seconds)
                continue

            job_id = job["id"]
            job_type = job["job_type"]

            print(f"[JOB START] id={job_id} type={job_type}")
            set_status("running")

            try:
                result_message = process_job(job)

                finish_job_success(
                    engine=engine,
                    job_id=job_id,
                    result_message=result_message,
                )

                set_status("idle")
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

                set_status("idle")
                print(f"[JOB FAILED] id={job_id} error={err_text}")

        except Exception as loop_error:
            print(f"[LOOP ERROR] {loop_error}")
            time.sleep(poll_seconds)


if __name__ == "__main__":
    run_worker_forever()

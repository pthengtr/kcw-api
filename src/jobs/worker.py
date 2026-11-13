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
    reclaim_stale_running_jobs,
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


def _heartbeat_stale_after_seconds(interval_seconds: int) -> float:
    """How long without a successful beat before the watchdog respawns the thread."""
    return max(float(interval_seconds) * 3.0, 30.0)


def _start_heartbeat_thread(
    engine,
    worker_name: str,
    interval_seconds: int,
    status_holder: dict,
) -> threading.Event:
    """Keep last_seen fresh even while process_job() blocks on long commands.

    A supervisor respawns the beat loop if the thread dies or stops succeeding
    (so a hung DB call cannot permanently silence LINE/ops online status).
    """
    stop_event = threading.Event()
    stale_after = _heartbeat_stale_after_seconds(interval_seconds)

    def _beat_once() -> None:
        with status_holder["lock"]:
            status = status_holder["status"]
        _send_heartbeat(engine, worker_name, status)
        with status_holder["lock"]:
            status_holder["last_ok_monotonic"] = time.monotonic()

    def _beat_loop(generation: int) -> None:
        while not stop_event.is_set():
            with status_holder["lock"]:
                if status_holder.get("generation") != generation:
                    return
            try:
                _beat_once()
            except Exception as heartbeat_error:
                print(f"[HEARTBEAT ERROR] {heartbeat_error}", flush=True)
            stop_event.wait(interval_seconds)

    def _spawn_beat_thread() -> threading.Thread:
        with status_holder["lock"]:
            status_holder["generation"] = int(status_holder.get("generation") or 0) + 1
            generation = status_holder["generation"]
            # Grace so the supervisor does not immediately treat a fresh spawn as stale.
            status_holder["last_ok_monotonic"] = time.monotonic()
        thread = threading.Thread(
            target=_beat_loop,
            kwargs={"generation": generation},
            name="kcw-worker-heartbeat",
            daemon=True,
        )
        thread.start()
        with status_holder["lock"]:
            status_holder["thread"] = thread
        print(f"[HEARTBEAT] thread started generation={generation}", flush=True)
        return thread

    def _supervisor() -> None:
        _spawn_beat_thread()
        while not stop_event.is_set():
            stop_event.wait(max(interval_seconds, 5))
            if stop_event.is_set():
                break
            with status_holder["lock"]:
                thread = status_holder.get("thread")
                last_ok = float(status_holder.get("last_ok_monotonic") or 0.0)
            alive = thread is not None and thread.is_alive()
            stale = (time.monotonic() - last_ok) > stale_after
            if alive and not stale:
                continue
            reason = "dead" if not alive else f"stale>{stale_after:.0f}s"
            print(f"[HEARTBEAT] respawning ({reason})", flush=True)
            _spawn_beat_thread()

    supervisor = threading.Thread(
        target=_supervisor,
        name="kcw-worker-heartbeat-supervisor",
        daemon=True,
    )
    with status_holder["lock"]:
        status_holder["generation"] = 0
        status_holder["last_ok_monotonic"] = time.monotonic()
        status_holder["thread"] = None
    supervisor.start()
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

    reclaimed = reclaim_stale_running_jobs(engine, worker_name)
    if reclaimed:
        print(f"[START] reclaimed stale running jobs={reclaimed}", flush=True)

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
            with status_holder["lock"]:
                status_holder["last_ok_monotonic"] = time.monotonic()
        except Exception as heartbeat_error:
            print(f"[HEARTBEAT ERROR] {heartbeat_error}", flush=True)

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

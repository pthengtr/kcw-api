import json
import os
import re
import subprocess
from typing import Any

from dotenv import load_dotenv


load_dotenv()


DEFAULT_TIMEOUT_SECONDS = int(os.getenv("WORKER_COMMAND_TIMEOUT_SECONDS", "1800"))
MAX_RESULT_CHARS = int(os.getenv("WORKER_RESULT_MAX_CHARS", "1200"))


def _job_type_to_env_key(job_type: str) -> str:
    """
    sync_inventory      -> SYNC_INVENTORY
    sync-product-images -> SYNC_PRODUCT_IMAGES
    """
    key = re.sub(r"[^A-Za-z0-9]+", "_", job_type.strip()).strip("_")
    return key.upper()


def _env_bool(value: str | None, default: bool = True) -> bool:
    if value is None:
        return default

    return value.strip().lower() not in {"0", "false", "no", "off", "disabled"}


def _expand(value: str | None) -> str | None:
    if value is None:
        return None

    return os.path.expandvars(os.path.expanduser(value))


def _truncate(value: str, max_chars: int) -> str:
    value = value or ""

    if len(value) <= max_chars:
        return value

    return value[:max_chars] + "\n...<truncated>"


def _get_command_config(job_type: str) -> dict[str, Any]:
    env_key = _job_type_to_env_key(job_type)

    enabled = _env_bool(os.getenv(f"WORKER_JOB_{env_key}_ENABLED"), default=True)
    if not enabled:
        raise ValueError(f"job_type is disabled by env: {job_type}")

    command = os.getenv(f"WORKER_JOB_{env_key}_COMMAND")
    if not command:
        raise ValueError(
            f"Unsupported job_type: {job_type}. "
            f"Missing env WORKER_JOB_{env_key}_COMMAND"
        )

    cwd = os.getenv(f"WORKER_JOB_{env_key}_CWD")
    timeout_seconds = int(
        os.getenv(f"WORKER_JOB_{env_key}_TIMEOUT_SECONDS")
        or DEFAULT_TIMEOUT_SECONDS
    )

    # For .bat files and Windows paths, shell=True is the practical default.
    shell = _env_bool(os.getenv(f"WORKER_JOB_{env_key}_SHELL"), default=True)

    return {
        "env_key": env_key,
        "command": _expand(command),
        "cwd": _expand(cwd),
        "timeout_seconds": timeout_seconds,
        "shell": shell,
    }


def _build_child_env(job: dict) -> dict[str, str]:
    env = os.environ.copy()

    payload = job.get("payload") or {}
    if not isinstance(payload, dict):
        payload = {}

    env.update(
        {
            "WORKER_JOB_ID": str(job.get("id", "")),
            "WORKER_JOB_TYPE": str(job.get("job_type", "")),
            "WORKER_JOB_PAYLOAD_JSON": json.dumps(payload, ensure_ascii=False),
            "WORKER_JOB_REQUESTED_BY": str(job.get("requested_by") or ""),
            "WORKER_JOB_SOURCE": str(job.get("source") or ""),
            "WORKER_NAME": str(os.getenv("WORKER_NAME", "")),
        }
    )

    return env


def run_configured_command(job: dict) -> str:
    job_type = str(job.get("job_type") or "").strip()
    if not job_type:
        raise ValueError("Missing job_type")

    config = _get_command_config(job_type)

    print(
        "[COMMAND START]",
        {
            "job_id": job.get("id"),
            "job_type": job_type,
            "env_key": config["env_key"],
            "command": config["command"],
            "cwd": config["cwd"],
            "timeout_seconds": config["timeout_seconds"],
            "shell": config["shell"],
        },
    )

    result = subprocess.run(
        config["command"],
        cwd=config["cwd"],
        env=_build_child_env(job),
        shell=config["shell"],
        capture_output=True,
        text=True,
        timeout=config["timeout_seconds"],
    )

    stdout = (result.stdout or "").strip()
    stderr = (result.stderr or "").strip()

    if result.returncode != 0:
        raise RuntimeError(
            "command failed "
            f"rc={result.returncode}; "
            f"stdout={_truncate(stdout, 700)}; "
            f"stderr={_truncate(stderr, 1200)}"
        )

    if stdout:
        return _truncate(stdout, MAX_RESULT_CHARS)

    if stderr:
        return _truncate(stderr, MAX_RESULT_CHARS)

    return f"{job_type} completed"
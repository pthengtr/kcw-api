from datetime import datetime, timezone

from fastapi import APIRouter

from src.tiger_pay import repos
from src.tiger_pay.config import get_tiger_pay_settings
from src.db import get_engine

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
async def ready() -> dict[str, object]:
    """Companion readiness: DB plus webhook recency. Does not ping the LAN device."""
    payload: dict[str, object] = {"status": "ok", "db": "ok"}
    try:
        engine = get_engine()
        last = repos.latest_webhook_received_at(engine)
    except Exception as exc:
        payload["status"] = "degraded"
        payload["db"] = "error"
        payload["db_error"] = str(exc)
        return payload

    settings = get_tiger_pay_settings()
    stale_hours = float(settings.tiger_pay_webhook_stale_hours)
    payload["webhook_last_received_at"] = last.isoformat() if last is not None else None
    if last is None:
        payload["webhook_stale"] = True
        payload["status"] = "degraded"
        return payload

    last_utc = last if last.tzinfo else last.replace(tzinfo=timezone.utc)
    age_hours = (
        datetime.now(timezone.utc) - last_utc.astimezone(timezone.utc)
    ).total_seconds() / 3600
    payload["webhook_age_hours"] = round(age_hours, 2)
    payload["webhook_stale"] = age_hours >= stale_hours
    if payload["webhook_stale"]:
        payload["status"] = "degraded"
    return payload

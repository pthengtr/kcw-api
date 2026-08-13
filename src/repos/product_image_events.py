from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text

from src.db import get_engine

logger = logging.getLogger("kcw.product_image_events")

EVENT_UPLOAD = "image_upload"
EVENT_REPLACE = "image_replace"
EVENT_DELETE = "image_delete"


def record_product_image_event(
    *,
    line_user_id: str | None,
    display_name: str | None = None,
    event_type: str,
    bcode: str,
    storage_path: str | None = None,
    bucket: str | None = None,
    source: str = "line_bot",
) -> bool:
    """
    Insert one product-image KPI event.

    Returns True on success. Failures are logged and swallowed so Storage
    mutations that already succeeded are not rolled back from the LINE reply.
    """
    line_user_id = (line_user_id or "").strip()
    bcode = (bcode or "").strip()
    event_type = (event_type or "").strip()

    if not line_user_id or not bcode or not event_type:
        logger.warning(
            "skip product_image_event: missing fields line_user_id=%r bcode=%r event_type=%r",
            line_user_id,
            bcode,
            event_type,
        )
        return False

    params: dict[str, Any] = {
        "line_user_id": line_user_id,
        "display_name": (display_name or "")[:200],
        "event_type": event_type,
        "bcode": bcode,
        "storage_path": storage_path,
        "bucket": (bucket or "pictures").strip() or "pictures",
        "source": (source or "line_bot").strip() or "line_bot",
    }

    sql = text(
        """
        insert into ops.product_image_event (
          line_user_id, display_name, event_type, bcode,
          storage_path, bucket, source
        ) values (
          :line_user_id, :display_name, :event_type, :bcode,
          :storage_path, :bucket, :source
        )
        """
    )

    try:
        engine = get_engine()
        with engine.begin() as conn:
            conn.execute(sql, params)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.exception("product_image_event insert failed: %s", exc)
        return False


def event_type_for_upload(*, replaced: bool) -> str:
    return EVENT_REPLACE if replaced else EVENT_UPLOAD

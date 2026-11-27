from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy.engine import Engine

from src.bot.line_bot import (
    LineChannel,
    configured_line_channels,
    multicast_line_messages,
    outbound_line_channel,
    push_line_messages,
    use_line_channel,
)
from src.expense_cash import copy, repos

logger = logging.getLogger("kcw.expense_cash.notify")


def _expense_line_channels() -> list[LineChannel]:
    """Channels that should receive expense-cash pushes.

    Default ``all`` fans out to every configured OA so approvers who only
    added v1 still get Flex, and dual users see it on both chats.

    Set ``EXPENSE_CASH_LINE_CHANNEL`` to ``new`` / ``secondary`` / ``primary``
    (or a ``LINE_CHANNEL_NAME``) to pin a single OA.
    """
    pref = (
        os.getenv("EXPENSE_CASH_LINE_CHANNEL")
        or os.getenv("LINE_OUTBOUND_CHANNEL")
        or "all"
    ).strip().lower()
    channels = configured_line_channels()
    if not channels:
        return []
    if pref in {"all", "both", "*"}:
        return channels
    chosen = outbound_line_channel(pref)
    return [chosen] if chosen else channels


def _deliver_messages(ids: list[str], messages: list[dict]) -> int:
    """Deliver to each recipient on each expense channel. Returns success count."""
    if not ids or not messages:
        return 0

    channels = _expense_line_channels()
    if not channels:
        # No channel objects (misconfig) — last-resort unbound push.
        delivered = 0
        try:
            multicast_line_messages(ids, messages)
            return len(ids)
        except Exception:
            logger.exception("Unbound multicast expense notify failed; per-user push")
        for uid in ids:
            try:
                push_line_messages(uid, messages)
                delivered += 1
            except Exception:
                logger.exception("Failed expense push to %s", uid)
        return delivered

    delivered = 0
    for channel in channels:
        logger.info("expense-cash LINE channel=%s recipients=%s", channel.name, len(ids))
        with use_line_channel(channel):
            # Multicast only when a single OA is targeted — mixed friendship on
            # a second OA makes multicast fail the whole batch.
            if len(channels) == 1:
                try:
                    multicast_line_messages(ids, messages)
                    delivered += len(ids)
                    continue
                except Exception:
                    logger.exception(
                        "Multicast expense notify failed on %s; per-user push",
                        channel.name,
                    )
            for uid in ids:
                try:
                    push_line_messages(uid, messages)
                    delivered += 1
                except Exception:
                    logger.exception(
                        "Failed expense push on %s to %s", channel.name, uid
                    )
    return delivered


def _amount_int(row: dict[str, Any]) -> int:
    try:
        return int(float(row.get("amount") or 0))
    except (TypeError, ValueError):
        return 0


def _meta_row(label: str, value: str) -> dict:
    """Label + value row for Minimal Classic body sections."""
    return {
        "type": "box",
        "layout": "baseline",
        "spacing": "sm",
        "contents": [
            {
                "type": "text",
                "text": label,
                "size": "xs",
                "color": "#64748B",
                "flex": 2,
            },
            {
                "type": "text",
                "text": value[:500] or "-",
                "size": "sm",
                "color": "#1F2937",
                "wrap": True,
                "flex": 5,
            },
        ],
    }


def admin_flex_card(row: dict[str, Any]) -> dict:
    """Approver Flex card — Minimal Classic: amount-first, compact actions."""
    short = int(row.get("short_code") or 0)
    rid = str(row.get("id") or "")
    name = (row.get("requester_name") or "ไม่ระบุ").strip()
    reason = (row.get("reason") or "").strip()
    extra = (row.get("extra_reason") or "").strip()
    body_reason = reason
    if extra:
        body_reason = f"{reason}\n(+ {extra})"
    amount = _amount_int(row)
    status = copy.STATUS_TH.get(str(row.get("status")), str(row.get("status")))

    return {
        "type": "flex",
        "altText": f"คำขอเบิก #{short} {amount:,} บาท",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "16px",
                "contents": [
                    {
                        "type": "text",
                        "text": f"คำขอเบิก #{short}",
                        "size": "xs",
                        "weight": "bold",
                        "color": "#64748B",
                    },
                    {
                        "type": "text",
                        "text": f"{amount:,} บาท",
                        "weight": "bold",
                        "size": "xxl",
                        "color": "#111111",
                    },
                    {"type": "separator", "margin": "md"},
                    _meta_row("ผู้ขอ", name),
                    _meta_row("รายการ", body_reason or "-"),
                    _meta_row("สถานะ", status),
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "spacing": "sm",
                "paddingAll": "12px",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "height": "sm",
                        "color": "#166534",
                        "action": {
                            "type": "postback",
                            "label": "อนุมัติ",
                            "data": f"expense_cash:approve:{rid}",
                            "displayText": f"อนุมัติ {short}",
                        },
                    },
                    {
                        "type": "box",
                        "layout": "horizontal",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "button",
                                "style": "link",
                                "height": "sm",
                                "flex": 1,
                                "color": "#64748B",
                                "action": {
                                    "type": "postback",
                                    "label": "ขอข้อมูลเพิ่ม",
                                    "data": f"expense_cash:needs_info:{rid}",
                                    "displayText": f"ส่งกลับ {short}",
                                },
                            },
                            {
                                "type": "button",
                                "style": "link",
                                "height": "sm",
                                "flex": 1,
                                "color": "#B91C1C",
                                "action": {
                                    "type": "postback",
                                    "label": "ปฏิเสธ",
                                    "data": f"expense_cash:reject:{rid}",
                                    "displayText": f"ปฏิเสธ {short}",
                                },
                            },
                        ],
                    },
                ],
            },
        },
    }


def _approver_recipient_ids(
    engine: Engine, *, exclude_line_user_id: str | None = None
) -> list[str]:
    skip = (exclude_line_user_id or "").strip()
    return [
        uid
        for uid in repos.list_approver_line_ids(engine)
        if uid and uid != skip
    ]


def notify_admins_new_request(
    engine: Engine,
    row: dict[str, Any],
    *,
    exclude_line_user_id: str | None = None,
) -> bool:
    """Push Flex to cash approvers. Returns True if at least one delivery succeeded.

    Skips the requester (they already got the reply ack). Uses multicast so one
    exhausted-quota failure does not burn N serial push attempts.
    """
    ids = _approver_recipient_ids(
        engine,
        exclude_line_user_id=exclude_line_user_id
        or str(row.get("requester_line_user_id") or ""),
    )
    if not ids:
        logger.warning(
            "No expense-cash approvers to notify for #%s",
            row.get("short_code"),
        )
        return False

    msg = admin_flex_card(row)
    delivered = _deliver_messages(ids, [msg])
    if delivered == 0:
        logger.warning(
            "No expense-cash admin notify delivered for #%s",
            row.get("short_code"),
        )
    return delivered > 0


def notify_requester_text(line_user_id: str, text: str) -> None:
    if not line_user_id:
        return
    if _deliver_messages([line_user_id], [{"type": "text", "text": text[:5000]}]) == 0:
        logger.warning("Failed to push requester text to %s", line_user_id)


def notify_requester_approved(
    *,
    line_user_id: str,
    short_code: int,
    amount: int,
    voucher_num: str | None,
    qr_image_url: str | None,
) -> None:
    messages: list[dict] = [
        {
            "type": "text",
            "text": copy.approved_text(
                short_code=short_code,
                amount=amount,
                voucher_num=voucher_num,
            ),
        }
    ]
    if qr_image_url:
        messages.append(
            {
                "type": "image",
                "originalContentUrl": qr_image_url,
                "previewImageUrl": qr_image_url,
            }
        )
    if _deliver_messages([line_user_id], messages) == 0:
        logger.warning("Failed to push approved QR to %s", line_user_id)


def _peer_notify_enabled() -> bool:
    """Peer-approve pushes are off by default — they burn monthly LINE quota fast."""
    raw = (os.getenv("EXPENSE_CASH_PEER_NOTIFY") or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def notify_other_approvers_approved(
    engine: Engine,
    row: dict[str, Any],
    *,
    reviewer_line_user_id: str | None,
    reviewer_name: str | None,
) -> None:
    """Tell peer approvers that someone already approved (skip the actor)."""
    if not _peer_notify_enabled():
        return
    actor = (reviewer_line_user_id or "").strip()
    ids = _approver_recipient_ids(engine, exclude_line_user_id=actor)
    if not ids:
        return
    short = int(row.get("short_code") or 0)
    amount = _amount_int(row)
    text = copy.approved_peer_notice(
        short_code=short,
        amount=amount,
        reviewer_name=reviewer_name,
        requester_name=(row.get("requester_name") or None),
    )
    msg = {"type": "text", "text": text[:5000]}
    if _deliver_messages(ids, [msg]) == 0:
        logger.warning("No peer-approve notify delivered for #%s", short)

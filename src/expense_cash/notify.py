from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.engine import Engine

from src.bot.line_bot import push_line_messages
from src.expense_cash import copy, repos

logger = logging.getLogger("kcw.expense_cash.notify")


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


def notify_admins_new_request(engine: Engine, row: dict[str, Any]) -> None:
    ids = repos.list_approver_line_ids(engine)
    msg = admin_flex_card(row)
    for uid in ids:
        try:
            push_line_messages(uid, [msg])
        except Exception:
            logger.exception("Failed to push admin notify to %s", uid)


def notify_requester_text(line_user_id: str, text: str) -> None:
    if not line_user_id:
        return
    try:
        push_line_messages(line_user_id, [{"type": "text", "text": text[:5000]}])
    except Exception:
        logger.exception("Failed to push requester text")


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
    try:
        push_line_messages(line_user_id, messages)
    except Exception:
        logger.exception("Failed to push approved QR")


def notify_other_approvers_approved(
    engine: Engine,
    row: dict[str, Any],
    *,
    reviewer_line_user_id: str | None,
    reviewer_name: str | None,
) -> None:
    """Tell peer approvers that someone already approved (skip the actor)."""
    actor = (reviewer_line_user_id or "").strip()
    ids = [
        uid
        for uid in repos.list_approver_line_ids(engine)
        if uid and uid != actor
    ]
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
    for uid in ids:
        try:
            push_line_messages(uid, [msg])
        except Exception:
            logger.exception("Failed to push peer-approve notify to %s", uid)

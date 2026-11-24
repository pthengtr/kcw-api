from __future__ import annotations

import re
from typing import Any

from src.expense_cash import copy, repos, sessions
from src.expense_cash.approvers import is_cash_approver
from src.expense_cash.service import (
    ExpenseCashError,
    approve_request,
    cancel_request_voucher,
    create_pending,
    format_open_list,
    parse_amount,
    refresh_request_voucher,
    reject_request,
    resubmit_extra_reason,
    send_back_for_info,
)

INTENT_ALIASES = {
    "เบิกเงิน",
    "เบิกค่าใช้จ่าย",
    "เบิกค่าใช้",
    "ถอนเงิน",
    "ขอเบิก",
    "expensewithdraw",
    "withdrawexpense",
    "cashrequest",
}

LIST_ALIASES = {"รายการเบิก", "listเบิก", "เบิกรอ"}

APPROVE_RE = re.compile(
    r"^\s*อนุมัติ\s*#?\s*(\d+)\s*$",
    re.IGNORECASE,
)
SEND_BACK_RE = re.compile(
    r"^\s*ส่งกลับ\s*#?\s*(\d+)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
REJECT_RE = re.compile(
    r"^\s*ปฏิเสธ\s*#?\s*(\d+)\s+(.+)$",
    re.IGNORECASE | re.DOTALL,
)
STATUS_RE = re.compile(
    r"^\s*สถานะเบิก\s*#?\s*(\d+)\s*$",
    re.IGNORECASE,
)
CANCEL_RE = re.compile(
    r"^\s*ยกเลิกเบิก\s*#?\s*(\d+)\s*$",
    re.IGNORECASE,
)

POSTBACK_PREFIX = "expense_cash:"


def _norm(text: str) -> str:
    t = (text or "").strip().lower()
    return re.sub(r"\s+", "", t)


def is_expense_cash_intent(text: str) -> bool:
    return _norm(text) in INTENT_ALIASES


def is_expense_cash_list(text: str) -> bool:
    return _norm(text) in LIST_ALIASES


def is_expense_cash_admin_command(text: str) -> bool:
    if is_expense_cash_list(text):
        return True
    if APPROVE_RE.match(text or ""):
        return True
    if SEND_BACK_RE.match(text or ""):
        return True
    if REJECT_RE.match(text or ""):
        return True
    if STATUS_RE.match(text or ""):
        return True
    if CANCEL_RE.match(text or ""):
        return True
    return False


def is_expense_cash_postback(data: str) -> bool:
    return (data or "").startswith(POSTBACK_PREFIX)


def _display_name(access: dict | None, line_user_id: str | None) -> str | None:
    access = access or {}
    return (
        access.get("display_name")
        or access.get("line_display_name")
        or line_user_id
    )


def _is_approver(access: dict | None) -> bool:
    return is_cash_approver(access)


def handle_expense_cash_session_text(
    engine,
    line_user_id: str | None,
    text: str,
    *,
    access: dict | None = None,
) -> dict | None:
    """Return reply if user has an active cash-request session; else None."""
    if not line_user_id:
        return None

    session = sessions.get_session(line_user_id)
    raw = (text or "").strip()

    # Open needs_info without explicit session: treat free text as extra reason
    # only when not an intent/admin command and no other session.
    if session is None:
        if is_expense_cash_intent(raw) or is_expense_cash_admin_command(raw):
            return None
        if sessions.END_WORDS & {_norm(raw)}:
            return None
        needs = repos.get_open_needs_info_for_user(engine, line_user_id)
        if needs and raw and not raw.startswith("/"):
            # Avoid hijacking product searches: only short-ish replies or
            # when user explicitly continues. Require they are not looking
            # like a product barcode (all digits 6+).
            if raw.isdigit() and len(raw) >= 6:
                return None
            try:
                updated = resubmit_extra_reason(
                    engine,
                    request_id=str(needs["id"]),
                    extra_reason=raw,
                )
            except ExpenseCashError:
                return None
            return {
                "type": "text",
                "text": copy.resubmitted_ack(
                    short_code=int(updated["short_code"])
                ),
            }
        return None

    if _norm(raw) in sessions.END_WORDS:
        sessions.clear_session(line_user_id)
        return {"type": "text", "text": copy.cancelled()}

    kind = session.get("kind")

    if kind == "request":
        return _handle_request_steps(
            engine, line_user_id, raw, session, access=access
        )

    if kind == "admin_note":
        return _handle_admin_note(engine, line_user_id, raw, session, access=access)

    if kind == "extra_reason":
        try:
            updated = resubmit_extra_reason(
                engine,
                request_id=str(session.get("request_id")),
                extra_reason=raw,
            )
        except ExpenseCashError as exc:
            sessions.clear_session(line_user_id)
            return {"type": "text", "text": exc.message}
        sessions.clear_session(line_user_id)
        return {
            "type": "text",
            "text": copy.resubmitted_ack(short_code=int(updated["short_code"])),
        }

    sessions.clear_session(line_user_id)
    return None


def _handle_request_steps(
    engine,
    line_user_id: str,
    raw: str,
    session: dict[str, Any],
    *,
    access: dict | None,
) -> dict:
    step = session.get("step")
    if step == "await_reason":
        if len(raw.strip()) < 3:
            return {"type": "text", "text": copy.reason_too_short()}
        session["reason"] = raw.strip()
        session["step"] = "await_amount"
        sessions.touch(session)
        return {"type": "text", "text": copy.ask_amount()}

    if step == "await_amount":
        amount = parse_amount(raw)
        if amount is None:
            return {"type": "text", "text": copy.amount_invalid()}
        reason = str(session.get("reason") or "").strip()
        row = create_pending(
            engine,
            line_user_id=line_user_id,
            display_name=_display_name(access, line_user_id),
            reason=reason,
            amount=amount,
        )
        sessions.clear_session(line_user_id)
        return {
            "type": "text",
            "text": copy.pending_ack(
                short_code=int(row["short_code"]),
                amount=amount,
                reason=reason,
            ),
        }

    sessions.clear_session(line_user_id)
    return {"type": "text", "text": copy.cancelled()}


def _handle_admin_note(
    engine,
    line_user_id: str,
    raw: str,
    session: dict[str, Any],
    *,
    access: dict | None,
) -> dict:
    if not _is_approver(access):
        sessions.clear_session(line_user_id)
        return {"type": "text", "text": copy.no_permission()}

    action = session.get("action")
    request_id = str(session.get("request_id") or "")
    short = int(session.get("short_code") or 0)
    name = _display_name(access, line_user_id)
    try:
        if action == "reject":
            reject_request(
                engine,
                request_id=request_id,
                admin_note=raw,
                reviewer_line_user_id=line_user_id,
                reviewer_name=name,
            )
            sessions.clear_session(line_user_id)
            return {"type": "text", "text": copy.reject_ok(short_code=short)}
        send_back_for_info(
            engine,
            request_id=request_id,
            admin_note=raw,
            reviewer_line_user_id=line_user_id,
            reviewer_name=name,
        )
        sessions.clear_session(line_user_id)
        return {"type": "text", "text": copy.needs_info_ok(short_code=short)}
    except ExpenseCashError as exc:
        sessions.clear_session(line_user_id)
        if exc.code == "not_found":
            return {"type": "text", "text": copy.not_found(code=str(short))}
        if exc.code == "bad_state":
            return {
                "type": "text",
                "text": copy.bad_state(short_code=short, status=exc.message),
            }
        return {"type": "text", "text": exc.message}


def handle_expense_cash_intent(
    engine,
    *,
    line_user_id: str,
    access: dict | None = None,
) -> dict:
    existing = sessions.get_session(line_user_id)
    if existing and existing.get("kind") == "request":
        return {"type": "text", "text": copy.session_busy_other()}
    sessions.start_request_session(line_user_id)
    return {"type": "text", "text": copy.ask_reason()}


def handle_expense_cash_admin_command(
    engine,
    text: str,
    *,
    line_user_id: str,
    access: dict | None = None,
) -> dict:
    if not _is_approver(access):
        return {"type": "text", "text": copy.no_permission()}

    name = _display_name(access, line_user_id)

    if is_expense_cash_list(text):
        rows = repos.list_open(engine)
        return {"type": "text", "text": format_open_list(rows)}

    m = APPROVE_RE.match(text or "")
    if m:
        code = int(m.group(1))
        try:
            row = approve_request(
                engine,
                short_code=code,
                reviewer_line_user_id=line_user_id,
                reviewer_name=name,
            )
            return {
                "type": "text",
                "text": copy.approve_ok(short_code=int(row["short_code"])),
            }
        except ExpenseCashError as exc:
            return _admin_err(exc, code)

    m = SEND_BACK_RE.match(text or "")
    if m:
        code = int(m.group(1))
        note = m.group(2).strip()
        try:
            row = send_back_for_info(
                engine,
                short_code=code,
                admin_note=note,
                reviewer_line_user_id=line_user_id,
                reviewer_name=name,
            )
            return {
                "type": "text",
                "text": copy.needs_info_ok(short_code=int(row["short_code"])),
            }
        except ExpenseCashError as exc:
            return _admin_err(exc, code)

    m = REJECT_RE.match(text or "")
    if m:
        code = int(m.group(1))
        note = m.group(2).strip()
        try:
            row = reject_request(
                engine,
                short_code=code,
                admin_note=note,
                reviewer_line_user_id=line_user_id,
                reviewer_name=name,
            )
            return {
                "type": "text",
                "text": copy.reject_ok(short_code=int(row["short_code"])),
            }
        except ExpenseCashError as exc:
            return _admin_err(exc, code)

    m = STATUS_RE.match(text or "")
    if m:
        code = int(m.group(1))
        try:
            detail = refresh_request_voucher(engine, short_code=code)
            row = detail["request"]
            voucher = detail.get("voucher") or {}
            return {
                "type": "text",
                "text": copy.status_detail(
                    short_code=int(row["short_code"]),
                    request_status=str(row.get("status") or ""),
                    amount=int(float(row.get("amount") or 0)),
                    voucher_status=(voucher.get("status") if voucher else None),
                    voucher_num=(voucher.get("voucher_num") if voucher else None),
                ),
            }
        except ExpenseCashError as exc:
            return _admin_err(exc, code)

    m = CANCEL_RE.match(text or "")
    if m:
        code = int(m.group(1))
        try:
            row = cancel_request_voucher(
                engine,
                short_code=code,
                reviewer_line_user_id=line_user_id,
                reviewer_name=name,
            )
            return {
                "type": "text",
                "text": copy.cancel_ok(short_code=int(row["short_code"])),
            }
        except ExpenseCashError as exc:
            return _admin_err(exc, code)

    return {"type": "text", "text": "ไม่เข้าใจคำสั่งเบิกครับ"}


def _admin_err(exc: ExpenseCashError, code: int) -> dict:
    if exc.code == "not_found":
        return {"type": "text", "text": copy.not_found(code=str(code))}
    if exc.code in {"bad_state", "already_used", "no_voucher"}:
        return {
            "type": "text",
            "text": copy.bad_state(short_code=code, status=exc.message),
        }
    if exc.code in {
        "tiger_create_failed",
        "qr_upload_failed",
        "supabase_missing",
        "tiger_cancel_failed",
        "tiger_cancel_unconfirmed",
        "not_active",
        "missing_voucher_num",
    }:
        return {
            "type": "text",
            "text": copy.voucher_failed(short_code=code, err=exc.message),
        }
    return {"type": "text", "text": exc.message}


def handle_expense_cash_postback(
    engine,
    data: str,
    *,
    line_user_id: str,
    access: dict | None = None,
) -> dict:
    if not _is_approver(access):
        return {"type": "text", "text": copy.no_permission()}

    parts = (data or "").split(":")
    # expense_cash:approve:uuid
    if len(parts) < 3:
        return {"type": "text", "text": "โพสต์แบ็กไม่ถูกต้องครับ"}
    action = parts[1]
    request_id = parts[2]
    row = repos.get_by_id(engine, request_id)
    if not row:
        return {"type": "text", "text": copy.not_found(code="?")}
    short = int(row["short_code"])
    name = _display_name(access, line_user_id)

    if action == "approve":
        try:
            approve_request(
                engine,
                request_id=request_id,
                reviewer_line_user_id=line_user_id,
                reviewer_name=name,
            )
            return {"type": "text", "text": copy.approve_ok(short_code=short)}
        except ExpenseCashError as exc:
            return _admin_err(exc, short)

    if action in {"needs_info", "reject"}:
        sessions.start_admin_note_session(
            line_user_id,
            action=action,
            request_id=request_id,
            short_code=short,
        )
        return {
            "type": "text",
            "text": copy.ask_admin_note(action=action, short_code=short),
        }

    return {"type": "text", "text": "โพสต์แบ็กไม่รู้จักครับ"}

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy.engine import Engine

from src.expense_cash import copy, notify, repos
from src.expense_cash.tiger import ExpenseCashTigerError, start_expense_cash_voucher


class ExpenseCashError(Exception):
    def __init__(self, message: str, *, code: str = "error") -> None:
        self.message = message
        self.code = code
        super().__init__(message)


def parse_amount(text: str) -> int | None:
    raw = (text or "").strip().replace(",", "").replace(" ", "")
    if not raw.isdigit():
        return None
    value = int(raw)
    if value <= 0:
        return None
    return value


def create_pending(
    engine: Engine,
    *,
    line_user_id: str,
    display_name: str | None,
    reason: str,
    amount: int,
) -> dict[str, Any]:
    row = repos.create_request(
        engine,
        requester_line_user_id=line_user_id,
        requester_name=display_name,
        reason=reason.strip(),
        amount=amount,
    )
    notify.notify_admins_new_request(engine, row)
    return row


def resubmit_extra_reason(
    engine: Engine,
    *,
    request_id: str,
    extra_reason: str,
) -> dict[str, Any]:
    row = repos.get_by_id(engine, request_id)
    if not row:
        raise ExpenseCashError("not found", code="not_found")
    if row.get("status") != "needs_info":
        raise ExpenseCashError("bad state", code="bad_state")
    prev = (row.get("extra_reason") or "").strip()
    chunk = extra_reason.strip()
    merged = f"{prev}\n{chunk}".strip() if prev else chunk
    updated = repos.update_request(
        engine,
        request_id,
        extra_reason=merged,
        status="pending",
        admin_note=None,
    )
    if not updated:
        raise ExpenseCashError("update failed", code="update_failed")
    notify.notify_admins_new_request(engine, updated)
    return updated


def approve_request(
    engine: Engine,
    *,
    request_id: str | None = None,
    short_code: int | None = None,
    reviewer_line_user_id: str | None = None,
    reviewer_name: str | None = None,
) -> dict[str, Any]:
    row = (
        repos.get_by_id(engine, request_id)
        if request_id
        else repos.get_by_short_code(engine, int(short_code or 0))
    )
    if not row:
        raise ExpenseCashError("not found", code="not_found")
    if row.get("status") not in repos.APPROVABLE_STATUSES:
        raise ExpenseCashError(
            f"status {row.get('status')}",
            code="bad_state",
        )

    rid = str(row["id"])
    short = int(row["short_code"])
    amount = int(float(row["amount"]))
    reason_bits = [row.get("reason") or ""]
    if row.get("extra_reason"):
        reason_bits.append(str(row["extra_reason"]))
    reason = " | ".join(b.strip() for b in reason_bits if b and str(b).strip())

    try:
        voucher = start_expense_cash_voucher(
            engine,
            request_id=rid,
            short_code=short,
            amount=amount,
            reason=reason,
            submitted_by=reviewer_line_user_id,
            submitted_by_name=reviewer_name,
        )
    except ExpenseCashTigerError as exc:
        raise ExpenseCashError(exc.message, code=exc.code) from exc

    attempt = voucher.get("attempt") or {}
    qr_url = voucher.get("qr_image_url")
    updated = repos.update_request(
        engine,
        rid,
        status="approved",
        reviewed_by=reviewer_line_user_id,
        reviewed_by_name=reviewer_name,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
        voucher_attempt_id=str(attempt.get("id") or "") or None,
        qr_image_url=qr_url,
        admin_note=None,
    )
    if not updated:
        raise ExpenseCashError("update failed", code="update_failed")

    notify.notify_requester_approved(
        line_user_id=str(row.get("requester_line_user_id") or ""),
        short_code=short,
        amount=amount,
        voucher_num=str(attempt.get("voucher_num") or "") or None,
        qr_image_url=qr_url,
    )
    return updated


def send_back_for_info(
    engine: Engine,
    *,
    request_id: str | None = None,
    short_code: int | None = None,
    admin_note: str,
    reviewer_line_user_id: str | None = None,
    reviewer_name: str | None = None,
) -> dict[str, Any]:
    row = (
        repos.get_by_id(engine, request_id)
        if request_id
        else repos.get_by_short_code(engine, int(short_code or 0))
    )
    if not row:
        raise ExpenseCashError("not found", code="not_found")
    if row.get("status") not in ("pending", "needs_info"):
        raise ExpenseCashError(f"status {row.get('status')}", code="bad_state")

    note = (admin_note or "").strip()
    if len(note) < 2:
        raise ExpenseCashError("note required", code="note_required")

    rid = str(row["id"])
    updated = repos.update_request(
        engine,
        rid,
        status="needs_info",
        admin_note=note,
        reviewed_by=reviewer_line_user_id,
        reviewed_by_name=reviewer_name,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )
    if not updated:
        raise ExpenseCashError("update failed", code="update_failed")

    notify.notify_requester_text(
        str(row.get("requester_line_user_id") or ""),
        copy.needs_info_prompt(
            short_code=int(row["short_code"]),
            admin_note=note,
        ),
    )
    # Put requester into extra_reason session from handler side when LINE;
    # for API, they reply freely and handler picks needs_info row.
    return updated


def reject_request(
    engine: Engine,
    *,
    request_id: str | None = None,
    short_code: int | None = None,
    admin_note: str,
    reviewer_line_user_id: str | None = None,
    reviewer_name: str | None = None,
) -> dict[str, Any]:
    row = (
        repos.get_by_id(engine, request_id)
        if request_id
        else repos.get_by_short_code(engine, int(short_code or 0))
    )
    if not row:
        raise ExpenseCashError("not found", code="not_found")
    if row.get("status") not in ("pending", "needs_info"):
        raise ExpenseCashError(f"status {row.get('status')}", code="bad_state")

    note = (admin_note or "").strip() or "ปฏิเสธ"
    rid = str(row["id"])
    updated = repos.update_request(
        engine,
        rid,
        status="rejected",
        admin_note=note,
        reviewed_by=reviewer_line_user_id,
        reviewed_by_name=reviewer_name,
        reviewed_at=datetime.now(timezone.utc).isoformat(),
    )
    if not updated:
        raise ExpenseCashError("update failed", code="update_failed")

    notify.notify_requester_text(
        str(row.get("requester_line_user_id") or ""),
        copy.rejected_text(short_code=int(row["short_code"]), admin_note=note),
    )
    return updated


def format_open_list(rows: list[dict[str, Any]]) -> str:
    if not rows:
        return copy.list_empty()
    lines = [copy.list_header()]
    for row in rows:
        short = int(row.get("short_code") or 0)
        amount = int(float(row.get("amount") or 0))
        name = (row.get("requester_name") or "-").strip()
        status = copy.STATUS_TH.get(str(row.get("status")), str(row.get("status")))
        reason = (row.get("reason") or "").strip()[:40]
        lines.append(
            f"#{short} {amount:,}฿ · {name} · {status}\n  {reason}"
        )
    lines.append(
        "\nพิมพ์ อนุมัติ {เลข} / ส่งกลับ {เลข} เหตุผล… / ปฏิเสธ {เลข} เหตุผล…"
    )
    return "\n".join(lines)

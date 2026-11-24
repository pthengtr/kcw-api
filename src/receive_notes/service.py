from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.receive_notes.company_banks import (
    brdet_line_from_payment,
    receive_bank_key_from_bankname,
    receive_bank_key_from_gl,
    resolve_company_receive_account,
)
from src.receive_notes.config import ReceiveNotesSettings, get_receive_notes_settings
from src.receive_notes.db import (
    confirmed_refund_total,
    get_note,
    get_pending_tiger_receipt_for_note,
    get_receipt,
    get_receipt_by_voucno,
    get_receive_notes_supabase_client,
    insert_note,
    insert_receipt,
    insert_receipt_bills,
    insert_receipt_channels,
    insert_receipt_edit_audit,
    list_receipt_edit_audits,
    list_receipts_for_note,
    patch_note,
    patch_receipt,
    patch_receipt_channel,
    prior_allocations_for_bills,
)
from src.receive_notes.parts9 import (
    assess_receive_edit_gate,
    fetch_bills_for_receive,
    get_note_header,
    infer_settle_method,
    list_brdet,
)
from src.receive_notes.tiger import (
    ReceiveTigerError,
    get_ar_attempt,
    get_ar_refund_attempt,
    is_ar_pos_bill_id,
    receipt_id_from_pos_bill_id,
    refresh_ar_refund_attempt,
    start_ar_cash_attempt,
    start_ar_refund_voucher_attempt,
)
from src.receive_notes.writer import (
    ReceiveNoteWriteError,
    create_receive_note,
    create_receipt_voucher,
    update_voucher_receive_meta,
)

_BKK = ZoneInfo("Asia/Bangkok")


class ReceiveServiceError(RuntimeError):
    def __init__(self, message: str, *, code: str = "service_error"):
        super().__init__(message)
        self.code = code


def _split_by_jourmode(bills: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for b in bills:
        mode = str(b.get("JOURMODE") or "1").strip() or "1"
        groups.setdefault(mode, []).append(b)
    return groups


def _channel_amounts(channels: list[dict[str, Any]]) -> tuple[float, float, float]:
    cash = transfer = cheque = 0.0
    for ch in channels:
        method = str(ch.get("settle_method") or "").lower()
        amt = float(ch.get("amount") or ch.get("chkamt") or 0)
        if method == "cash":
            cash += amt
        elif method == "transfer":
            transfer += amt
        elif method in ("cheque", "check"):
            cheque += amt
    return round(cash, 2), round(transfer, 2), round(cheque, 2)


def _build_brdet_lines(channels: list[dict[str, Any]], *, tiger_payment_no: str | None = None):
    lines = []
    for ch in channels:
        method = str(ch.get("settle_method") or "transfer").lower()
        tiger_ref = ch.get("tiger_payment_no") or tiger_payment_no
        lines.append(
            brdet_line_from_payment(
                settle_method=method,
                chkno=str(ch.get("chkno") or ""),
                chkamt=float(ch.get("amount") or ch.get("chkamt") or 0),
                chkdate=str(ch.get("chkdate") or date.today().isoformat()),
                receive_bank_key=ch.get("receive_bank_key") or ch.get("bankname"),
                tiger_payment_no=tiger_ref if method == "cash" else None,
            )
        )
    return lines


def create_note(
    *,
    acctno: str,
    acctname: str,
    billnos: list[str],
    due_date: str | None = None,
    remark: str | None = None,
    discount_mode: str = "amount",
    discount_input: float = 0.0,
    discount_amount: float = 0.0,
    settle_method: str = "transfer",
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Legacy helper — prefer router POST /api/notes for full AP-shaped create."""
    settings = settings or get_receive_notes_settings()
    result = create_receive_note(
        settings=settings,
        acctno=acctno,
        acctname=acctname,
        billnos=billnos,
        operator=operator,
    )
    client = get_receive_notes_supabase_client()
    try:
        insert_note(
            client,
            {
                "acctno": result["acctno"],
                "noteno": result["noteno"],
                "jourmode": result["jourmode"],
                "due_date": due_date,
                "remark": remark,
                "discount_mode": discount_mode or "amount",
                "discount_input": discount_input,
                "discount_amount": discount_amount,
                "settle_method": settle_method or "transfer",
                "status": "open",
                "created_by": operator,
            },
        )
    except Exception:
        # KSS note already exists; overlay best-effort
        pass
    return result


def prepare_receive(
    *,
    acctno: str,
    acctname: str,
    allocations: list[dict[str, Any]],
    channels: list[dict[str, Any]],
    discount: float = 0.0,
    noteno: str | None = None,
    remark: str | None = None,
    money_confirmed: bool = False,
    cash_mode: str | None = None,
    cash_manual_reason: str | None = None,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Validate + create overlay receipt(s). Writes KSS immediately unless Tiger cash pending."""
    settings = settings or get_receive_notes_settings()
    site = settings.site
    acct = (acctno or "").strip()
    name = (acctname or "").strip()
    note = (noteno or "").strip() or None
    if not acct or not allocations or not channels:
        raise ReceiveServiceError("acctno, allocations, and channels required", code="validation")

    billnos = [str(a.get("billno") or "").strip() for a in allocations]
    bills = fetch_bills_for_receive(site, acct, billnos, noteno=note)
    by_no = {str(b.get("BILLNO") or "").strip(): b for b in bills}
    if len(by_no) != len(set(billnos)):
        raise ReceiveServiceError("one or more bills unavailable", code="bill_invalid")

    client = get_receive_notes_supabase_client()
    prior = prior_allocations_for_bills(client, billnos)

    # Attach JOURMODE + remaining
    enriched: list[dict[str, Any]] = []
    for alloc in allocations:
        bno = str(alloc.get("billno") or "").strip()
        bill = by_no[bno]
        aftertax = round(float(bill.get("AFTERTAX") or 0), 2)
        prior_amt = float(prior.get(bno, 0.0))
        remaining = round(aftertax - prior_amt, 2)
        amount = round(float(alloc.get("allocate_amt") or remaining), 2)
        # Sale: remaining > 0. Credit note (ใบลดหนี้): remaining < 0 is still open.
        if aftertax >= 0:
            if remaining <= 0:
                raise ReceiveServiceError(
                    f"bill {bno} already fully allocated", code="already_paid"
                )
            if amount <= 0 or amount - remaining > 1e-6:
                raise ReceiveServiceError(f"invalid allocate for {bno}", code="validation")
            fully = amount + prior_amt + 1e-6 >= aftertax
        else:
            if remaining >= 0:
                raise ReceiveServiceError(
                    f"bill {bno} already fully allocated", code="already_paid"
                )
            if amount >= 0 or amount < remaining - 1e-6:
                raise ReceiveServiceError(f"invalid allocate for {bno}", code="validation")
            fully = amount + prior_amt - 1e-6 <= aftertax
        enriched.append(
            {
                "billno": bno,
                "aftertax": aftertax,
                "allocate_amt": amount,
                "JOURMODE": str(bill.get("JOURMODE") or "1").strip() or "1",
                "fully_paid": fully,
            }
        )

    cash_amt, transfer_amt, cheque_amt = _channel_amounts(channels)
    has_tiger_cash = cash_amt > 0 and (cash_mode or "tiger") == "tiger"
    if cash_amt > 0 and (cash_mode or "tiger") == "manual" and not (cash_manual_reason or "").strip():
        raise ReceiveServiceError("manual cash requires a reason", code="validation")

    groups = _split_by_jourmode(enriched)
    # Channel amounts apply to the combined receive; if VAT split, require single jourmode
    # or split channels proportionally — for safety, reject multi-mode with shared channels
    # unless caller already split. Auto-split by creating one receipt per jourmode with
    # proportional channel split by billamt share.
    results: list[dict[str, Any]] = []
    total_alloc = sum(float(a["allocate_amt"]) for a in enriched) or 1.0

    for jourmode, group in groups.items():
        share = sum(float(a["allocate_amt"]) for a in group) / total_alloc
        group_channels = []
        for ch in channels:
            amt = round(float(ch.get("amount") or ch.get("chkamt") or 0) * share, 2)
            if amt <= 0:
                continue
            item = dict(ch)
            item["amount"] = amt
            group_channels.append(item)
        # Fix rounding on last channel of largest method
        ch_sum = round(sum(float(c["amount"]) for c in group_channels), 2)
        billamt = round(sum(float(a["allocate_amt"]) for a in group), 2)
        disc = round(float(discount or 0) * share, 2)
        netamt = round(billamt - disc, 2)
        if group_channels and abs(ch_sum - netamt) > 0.05:
            # nudge first channel
            delta = round(netamt - ch_sum, 2)
            group_channels[0]["amount"] = round(float(group_channels[0]["amount"]) + delta, 2)

        g_cash, g_transfer, g_cheque = _channel_amounts(group_channels)
        needs_tiger = g_cash > 0 and (cash_mode or "tiger") == "tiger"
        proof_needed = (g_transfer > 0 or g_cheque > 0 or ((cash_mode or "") == "manual" and g_cash > 0))

        workflow = "pending"
        proof_status = "none"
        if needs_tiger:
            workflow = "awaiting_tiger"
        elif money_confirmed and proof_needed:
            workflow = "awaiting_proof"
            proof_status = "awaiting"
        elif money_confirmed:
            workflow = "done"
            proof_status = "none"
        else:
            workflow = "review"

        receipt = insert_receipt(
            client,
            {
                "acctno": acct,
                "acctname": name,
                "noteno": note,
                "jourmode": jourmode,
                "received_at": date.today().isoformat(),
                "received_by": operator,
                "remark": remark,
                "billamt": billamt,
                "discount": disc,
                "netamt": netamt,
                "cash_amt": g_cash,
                "transfer_amt": g_transfer,
                "cheque_amt": g_cheque,
                "workflow_status": workflow,
                "proof_status": proof_status,
                "kss_sync_status": "pending",
                "cash_mode": (cash_mode if g_cash > 0 else None),
                "cash_manual_reason": cash_manual_reason if (cash_mode == "manual" and g_cash > 0) else None,
                "money_confirmed": bool(money_confirmed) and not needs_tiger,
            },
        )
        receipt_id = receipt["id"]
        insert_receipt_bills(
            client,
            [
                {
                    "receipt_id": receipt_id,
                    "billno": a["billno"],
                    "aftertax": a["aftertax"],
                    "allocate_amt": a["allocate_amt"],
                    "fully_paid": bool(a["fully_paid"]),
                }
                for a in group
            ],
        )
        insert_receipt_channels(
            client,
            [
                {
                    "receipt_id": receipt_id,
                    "settle_method": str(c.get("settle_method") or "transfer").lower(),
                    "amount": float(c.get("amount") or 0),
                    "chkno": c.get("chkno"),
                    "chkdate": c.get("chkdate") or date.today().isoformat(),
                    "receive_bank_key": c.get("receive_bank_key"),
                    "bankname": c.get("bankname"),
                    "bank_gl": c.get("bank_gl"),
                }
                for c in group_channels
            ],
        )

        out: dict[str, Any] = {"receipt": get_receipt(client, receipt_id)}

        if needs_tiger:
            try:
                attempt = start_ar_cash_attempt(
                    receipt_id=receipt_id,
                    amount=g_cash,
                    noteno=note,
                    submitted_by=operator,
                    submitted_by_name=operator,
                    note=f"AR {note or acct} {receipt_id}",
                )
                patch_receipt(
                    client,
                    receipt_id,
                    {
                        "tiger_attempt_id": attempt.get("id"),
                        "tiger_payment_id": attempt.get("tiger_payment_id"),
                        "tiger_payment_no": attempt.get("tiger_payment_no"),
                    },
                )
                out["tiger_attempt"] = attempt
                out["receipt"] = get_receipt(client, receipt_id)
            except ReceiveTigerError as exc:
                patch_receipt(
                    client,
                    receipt_id,
                    {
                        "workflow_status": "failed",
                        "kss_sync_error": str(exc),
                    },
                )
                out["tiger_error"] = {"message": str(exc), "code": exc.code}
                out["receipt"] = get_receipt(client, receipt_id)
        elif money_confirmed:
            out["kss"] = finalize_kss_for_receipt(
                receipt_id=receipt_id,
                settings=settings,
                operator=operator,
            )
            out["receipt"] = get_receipt(client, receipt_id)

        results.append(out)

    return {"receipts": results, "count": len(results)}


def finalize_kss_for_receipt(
    *,
    receipt_id: str,
    settings: ReceiveNotesSettings | None = None,
    operator: str | None = None,
    tiger_payment_no: str | None = None,
) -> dict[str, Any]:
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    receipt = get_receipt(client, receipt_id)
    if not receipt:
        raise ReceiveServiceError("receipt not found", code="not_found")

    if receipt.get("voucno") and receipt.get("kss_sync_status") == "synced":
        # idempotent
        return create_receipt_voucher(
            settings=settings,
            acctno=receipt["acctno"],
            acctname=receipt.get("acctname") or "",
            bill_allocations=receipt.get("receipt_bill") or [],
            brdet_lines=[],
            discount=float(receipt.get("discount") or 0),
            noteno=receipt.get("noteno"),
            existing_voucno=receipt["voucno"],
            operator=operator,
        )

    bills = receipt.get("receipt_bill") or []
    channels = receipt.get("receipt_channel") or []
    allocs = [
        {
            "billno": b["billno"],
            "allocate_amt": float(b["allocate_amt"]),
        }
        for b in bills
    ]
    brdet_lines = _build_brdet_lines(
        [
            {
                "settle_method": c.get("settle_method"),
                "amount": c.get("amount"),
                "chkno": c.get("chkno"),
                "chkdate": c.get("chkdate"),
                "receive_bank_key": c.get("receive_bank_key"),
                "bankname": c.get("bankname"),
            }
            for c in channels
        ],
        tiger_payment_no=tiger_payment_no or receipt.get("tiger_payment_no"),
    )

    try:
        result = create_receipt_voucher(
            settings=settings,
            acctno=receipt["acctno"],
            acctname=receipt.get("acctname") or "",
            bill_allocations=allocs,
            brdet_lines=brdet_lines,
            discount=float(receipt.get("discount") or 0),
            noteno=receipt.get("noteno"),
            existing_voucno=receipt.get("voucno"),
            operator=operator,
        )
    except ReceiveNoteWriteError as exc:
        patch_receipt(
            client,
            receipt_id,
            {
                "kss_sync_status": "failed",
                "kss_sync_error": str(exc),
                "workflow_status": "review",
            },
        )
        raise ReceiveServiceError(str(exc), code=exc.code) from exc

    proof = receipt.get("proof_status") or "none"
    workflow = "done"
    if proof == "awaiting":
        workflow = "awaiting_proof"
    if receipt.get("cash_mode") == "tiger" and float(receipt.get("cash_amt") or 0) > 0:
        proof = "tiger_auto"

    patch_receipt(
        client,
        receipt_id,
        {
            "voucno": result["voucno"],
            "kss_sync_status": "synced",
            "kss_sync_error": None,
            "workflow_status": workflow,
            "proof_status": proof,
            "money_confirmed": True,
        },
    )
    if receipt.get("noteno"):
        try:
            patch_note(
                client,
                receipt["acctno"],
                receipt["noteno"],
                {"status": "received"},
            )
        except Exception:
            pass
    return result


def complete_tiger_receipt(
    *,
    receipt_id: str,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    receipt = get_receipt(client, receipt_id)
    if not receipt:
        raise ReceiveServiceError("receipt not found", code="not_found")

    attempt = get_ar_attempt(receipt_id)
    if not attempt:
        raise ReceiveServiceError("no Tiger attempt for receipt", code="tiger_missing")
    status = str(attempt.get("status") or "").lower()
    if status != "success":
        if status in ("failed", "cancelled", "canceled"):
            patch_receipt(
                client,
                receipt_id,
                {"workflow_status": "failed", "kss_sync_error": f"tiger_{status}"},
            )
            raise ReceiveServiceError(f"Tiger status={status}", code="tiger_failed")
        raise ReceiveServiceError(f"Tiger still {status}", code="tiger_pending")

    patch_receipt(
        client,
        receipt_id,
        {
            "tiger_attempt_id": attempt.get("id"),
            "tiger_payment_id": attempt.get("tiger_payment_id"),
            "tiger_payment_no": attempt.get("tiger_payment_no"),
            "money_confirmed": True,
        },
    )
    kss = finalize_kss_for_receipt(
        receipt_id=receipt_id,
        settings=settings,
        operator=operator,
        tiger_payment_no=attempt.get("tiger_payment_no"),
    )
    return {"attempt": attempt, "kss": kss, "receipt": get_receipt(client, receipt_id)}


def start_note_cash_via_tiger(
    *,
    acctno: str,
    acctname: str,
    noteno: str,
    bill_allocations: list[dict[str, Any]],
    chkamt: float,
    discount: float = 0.0,
    chkdate: str | None = None,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Note-first cash receive: start Tiger with BN/BNN ref; do not write KSS yet.

    Reuses an in-flight ``awaiting_tiger`` overlay for the same note (dedupe).
    Each overlay receipt keeps its own Tiger attempt id for multi-pay / retry.
    """
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        raise ReceiveServiceError("acctno and noteno required", code="validation")

    existing = get_pending_tiger_receipt_for_note(client, acct, note)
    if existing:
        receipt_id = str(existing.get("id") or "")
        attempt = get_ar_attempt(receipt_id) if receipt_id else None
        status = str((attempt or {}).get("status") or "").lower()
        if attempt and status == "success":
            return complete_tiger_receipt(
                receipt_id=receipt_id,
                operator=operator,
                settings=settings,
            )
        if attempt and status not in ("failed", "cancelled", "canceled"):
            return {
                "awaiting_tiger": True,
                "receipt": existing,
                "tiger_attempt": attempt,
            }
        # Prior attempt died — close the stale awaiting_tiger row so a retry
        # can allocate bills again, then fall through to a fresh overlay send.
        if receipt_id:
            patch_receipt(
                client,
                receipt_id,
                {
                    "workflow_status": "failed",
                    "kss_sync_error": f"tiger_{status or 'missing'}",
                },
            )

    billamt = round(sum(float(a.get("allocate_amt") or 0) for a in bill_allocations), 2)
    disc = round(float(discount or 0), 2)
    net = round(billamt - disc, 2)
    cash = round(float(chkamt), 2)
    if abs(cash - net) > 0.05:
        raise ReceiveServiceError(
            f"cash amount ({cash}) must match note net ({net}) for Tiger",
            code="validation",
        )

    channels = [
        {
            "settle_method": "cash",
            "amount": net,
            "chkdate": (chkdate or date.today().isoformat()),
        }
    ]
    prepared = prepare_receive(
        acctno=acct,
        acctname=acctname,
        allocations=bill_allocations,
        channels=channels,
        discount=disc,
        noteno=note,
        money_confirmed=True,
        cash_mode="tiger",
        operator=operator,
        settings=settings,
    )
    rows = prepared.get("receipts") or []
    if not rows:
        raise ReceiveServiceError("failed to create cash receipt", code="service_error")
    row = rows[0]
    if row.get("tiger_error"):
        err = row["tiger_error"]
        raise ReceiveServiceError(
            str(err.get("message") or "Tiger error"),
            code=str(err.get("code") or "tiger_error"),
        )
    receipt = row.get("receipt") or {}
    return {
        "awaiting_tiger": True,
        "receipt": receipt,
        "tiger_attempt": row.get("tiger_attempt"),
    }


def sync_tiger_receipt(
    *,
    receipt_id: str,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Poll Tiger attempt for an overlay receipt; finalize KSS only on success."""
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    receipt = get_receipt(client, receipt_id)
    if not receipt:
        raise ReceiveServiceError("receipt not found", code="not_found")

    if receipt.get("voucno") and receipt.get("kss_sync_status") == "synced":
        return {
            "awaiting_tiger": False,
            "done": True,
            "receipt": receipt,
            "kss": {
                "voucno": receipt.get("voucno"),
                "noteno": receipt.get("noteno"),
            },
        }

    attempt = get_ar_attempt(receipt_id)
    if not attempt:
        raise ReceiveServiceError("no Tiger attempt for receipt", code="tiger_missing")

    status = str(attempt.get("status") or "").lower()
    if status == "success":
        done = complete_tiger_receipt(
            receipt_id=receipt_id,
            operator=operator,
            settings=settings,
        )
        return {
            "awaiting_tiger": False,
            "done": True,
            "receipt": done.get("receipt"),
            "tiger_attempt": done.get("attempt"),
            "kss": done.get("kss"),
        }
    if status in ("failed", "cancelled", "canceled"):
        patch_receipt(
            client,
            receipt_id,
            {"workflow_status": "failed", "kss_sync_error": f"tiger_{status}"},
        )
        return {
            "awaiting_tiger": False,
            "done": False,
            "failed": True,
            "tiger_status": status,
            "receipt": get_receipt(client, receipt_id),
            "tiger_attempt": attempt,
        }
    return {
        "awaiting_tiger": True,
        "done": False,
        "tiger_status": status,
        "receipt": receipt,
        "tiger_attempt": attempt,
    }


def complete_tiger_receipt_for_pos_bill(
    *,
    pos_bill_id: str,
    operator: str | None = None,
) -> dict[str, Any] | None:
    """Webhook/poller hook: finalize AR overlay when Tiger marks ar: attempt success."""
    if not is_ar_pos_bill_id(pos_bill_id):
        return None
    receipt_id = receipt_id_from_pos_bill_id(pos_bill_id)
    if not receipt_id:
        return None
    try:
        return complete_tiger_receipt(receipt_id=receipt_id, operator=operator)
    except ReceiveServiceError as exc:
        if exc.code == "tiger_pending":
            return None
        if exc.code in ("tiger_failed", "tiger_missing", "not_found"):
            return {"error": str(exc), "code": exc.code, "receipt_id": receipt_id}
        raise


def resync_receipt(
    *,
    receipt_id: str,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Idempotent KSS resync — reuses VOUCNO when already synced."""
    return {
        "kss": finalize_kss_for_receipt(
            receipt_id=receipt_id,
            settings=settings,
            operator=operator,
        ),
        "receipt": get_receipt(get_receive_notes_supabase_client(), receipt_id),
    }


def note_refund_snapshot(
    *,
    acctno: str,
    noteno: str,
    note_net: float,
    client=None,
) -> dict[str, Any]:
    """Remaining customer-credit refund for a negative BN/BNN note."""
    client = client or get_receive_notes_supabase_client()
    net = round(float(note_net or 0), 2)
    credit = round(abs(net), 2) if net < -1e-9 else 0.0
    refunded = confirmed_refund_total(client, acctno, noteno) if credit else 0.0
    remaining = round(max(credit - refunded, 0.0), 2)
    return {
        "is_refund": credit > 0,
        "note_net": net,
        "credit_amt": credit,
        "refunded_amt": refunded,
        "remaining_refund": remaining,
    }


def _allocate_refund_bills(
    bills: list[dict[str, Any]],
    *,
    refund_amt: float,
    prior: dict[str, float],
) -> list[dict[str, Any]]:
    """Greedy negative allocate across credit bills up to refund_amt (positive)."""
    target = -round(abs(float(refund_amt)), 2)
    if target >= 0:
        raise ReceiveServiceError("refund amount must be > 0", code="validation")
    remaining_target = target
    enriched: list[dict[str, Any]] = []
    for bill in bills:
        if remaining_target >= -1e-9:
            break
        bno = str(bill.get("BILLNO") or "").strip()
        aftertax = round(float(bill.get("AFTERTAX") or 0), 2)
        if aftertax >= 0:
            continue
        prior_amt = float(prior.get(bno, 0.0))
        bill_remaining = round(aftertax - prior_amt, 2)  # still negative when open
        if bill_remaining >= -1e-9:
            continue
        # Allocate as much negative as min(|remaining_target|, |bill_remaining|)
        take = round(max(remaining_target, bill_remaining), 2)
        fully = take + prior_amt - 1e-6 <= aftertax
        enriched.append(
            {
                "billno": bno,
                "aftertax": aftertax,
                "allocate_amt": take,
                "JOURMODE": str(bill.get("JOURMODE") or "1").strip() or "1",
                "fully_paid": fully,
            }
        )
        remaining_target = round(remaining_target - take, 2)
    if abs(remaining_target) > 0.05:
        raise ReceiveServiceError(
            "refund exceeds remaining credit on note bills",
            code="validation",
        )
    if not enriched:
        raise ReceiveServiceError("no open credit bills to refund", code="already_paid")
    return enriched


def finalize_refund_kss_for_receipt(
    *,
    receipt_id: str,
    settings: ReceiveNotesSettings | None = None,
    operator: str | None = None,
    tiger_voucher_num: str | None = None,
) -> dict[str, Any]:
    """Write PVN to KSS only when this refund closes the note credit (no remaining)."""
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    receipt = get_receipt(client, receipt_id)
    if not receipt:
        raise ReceiveServiceError("receipt not found", code="not_found")

    if receipt.get("voucno") and receipt.get("kss_sync_status") == "synced":
        return {
            "voucno": receipt.get("voucno"),
            "noteno": receipt.get("noteno"),
            "acctno": receipt.get("acctno"),
            "idempotent": True,
            "is_refund": True,
        }

    tiger_ref = (
        tiger_voucher_num
        or receipt.get("tiger_payment_no")
        or ""
    ).strip() or None

    acct = str(receipt.get("acctno") or "").strip()
    note = str(receipt.get("noteno") or "").strip()

    # Credit snapshot stashed as "credit:{amt}" in cash_manual_reason (no schema change).
    credit = 0.0
    reason = str(receipt.get("cash_manual_reason") or "")
    if reason.startswith("credit:"):
        try:
            credit = abs(float(reason.split(":", 1)[1]))
        except (TypeError, ValueError):
            credit = 0.0
    if credit <= 0:
        credit = abs(float(receipt.get("billamt") or 0))

    channels = receipt.get("receipt_channel") or []
    bills = receipt.get("receipt_bill") or []
    method = (
        str((channels[0] or {}).get("settle_method") or "transfer").lower()
        if channels
        else "transfer"
    )
    proof_needed = method in ("transfer", "cheque")

    # Leave awaiting_tiger so confirmed_refund_total can include this row.
    patch_receipt(
        client,
        receipt_id,
        {
            "money_confirmed": True,
            "tiger_payment_no": tiger_ref or receipt.get("tiger_payment_no"),
            "workflow_status": "review",
        },
    )

    refunded = confirmed_refund_total(client, acct, note)
    remaining = round(max(credit - refunded, 0.0), 2)

    if remaining > 0.05:
        # Partial refund: keep overlay PVN placeholder for history/print; defer KSS clear.
        overlay_vouc = str(receipt.get("voucno") or "").strip()
        patch_receipt(
            client,
            receipt_id,
            {
                "workflow_status": "awaiting_proof" if proof_needed else "done",
                "proof_status": "awaiting" if proof_needed else "none",
                "kss_sync_status": "pending",
                "kss_sync_error": None,
            },
        )
        return {
            "voucno": overlay_vouc or None,
            "noteno": note,
            "acctno": acct,
            "is_refund": True,
            "partial": True,
            "remaining_refund": remaining,
            "refunded_amt": refunded,
            "kss_deferred": True,
            "settle_method": method,
        }

    # Full credit cleared — write PVN + stamp SIMAS / RVMAS.
    # Rebuild full allocations for all note bills from confirmed overlay receipts.
    alloc_by_bill: dict[str, float] = {}
    for row in list_receipts_for_note(client, acct, note):
        status = str(row.get("workflow_status") or "")
        if status in ("failed", "awaiting_tiger"):
            continue
        if status == "review" and not row.get("money_confirmed"):
            continue
        for b in row.get("receipt_bill") or []:
            bno = str(b.get("billno") or "").strip()
            if not bno:
                continue
            alloc_by_bill[bno] = round(
                alloc_by_bill.get(bno, 0.0) + float(b.get("allocate_amt") or 0), 2
            )
    if not alloc_by_bill and bills:
        for b in bills:
            bno = str(b.get("billno") or "").strip()
            if bno:
                alloc_by_bill[bno] = float(b.get("allocate_amt") or 0)

    allocs = [{"billno": bno, "allocate_amt": amt} for bno, amt in alloc_by_bill.items()]
    # BRDET: one line per confirmed refund channel across receipts (positive chkamt).
    brdet_lines: list[dict[str, Any]] = []
    for row in list_receipts_for_note(client, acct, note):
        status = str(row.get("workflow_status") or "")
        if status in ("failed", "awaiting_tiger"):
            continue
        if status == "review" and not row.get("money_confirmed"):
            continue
        row_tiger = str(row.get("tiger_payment_no") or "").strip() or None
        for c in row.get("receipt_channel") or []:
            brdet_lines.append(
                {
                    "settle_method": c.get("settle_method"),
                    "amount": c.get("amount"),
                    "chkamt": c.get("amount") or c.get("chkamt"),
                    "chkno": c.get("chkno"),
                    "chkdate": c.get("chkdate"),
                    "receive_bank_key": c.get("receive_bank_key"),
                    "bankname": c.get("bankname"),
                    "tiger_payment_no": row_tiger if str(c.get("settle_method") or "") == "cash" else None,
                }
            )
    brdet_built = _build_brdet_lines(brdet_lines, tiger_payment_no=tiger_ref)

    try:
        result = create_receipt_voucher(
            settings=settings,
            acctno=acct,
            acctname=receipt.get("acctname") or "",
            bill_allocations=allocs,
            brdet_lines=brdet_built,
            discount=0.0,
            noteno=note,
            existing_voucno=receipt.get("voucno"),
            operator=operator,
            refund=True,
        )
    except ReceiveNoteWriteError as exc:
        patch_receipt(
            client,
            receipt_id,
            {
                "kss_sync_status": "failed",
                "kss_sync_error": str(exc),
                "workflow_status": "review",
            },
        )
        raise ReceiveServiceError(str(exc), code=exc.code) from exc

    voucno = result.get("voucno")
    proof = "tiger_auto" if method == "cash" else ("awaiting" if proof_needed else "none")
    workflow = "awaiting_proof" if proof == "awaiting" else "done"
    patch_receipt(
        client,
        receipt_id,
        {
            "voucno": voucno,
            "kss_sync_status": "synced",
            "kss_sync_error": None,
            "workflow_status": workflow,
            "proof_status": proof,
            "money_confirmed": True,
            "tiger_payment_no": tiger_ref or receipt.get("tiger_payment_no"),
        },
    )
    # Stamp sibling overlay refunds with same PVN for history.
    for row in list_receipts_for_note(client, acct, note):
        rid = str(row.get("id") or "")
        if not rid or rid == receipt_id:
            continue
        status = str(row.get("workflow_status") or "")
        if status in ("failed", "awaiting_tiger"):
            continue
        if row.get("voucno") and row.get("kss_sync_status") == "synced":
            continue
        patch_receipt(
            client,
            rid,
            {
                "voucno": voucno,
                "kss_sync_status": "synced",
                "workflow_status": "done" if status != "awaiting_proof" else status,
                "money_confirmed": True,
            },
        )
    if note:
        try:
            patch_note(client, acct, note, {"status": "received", "settle_method": method})
        except Exception:
            pass
    return {**result, "is_refund": True, "partial": False, "remaining_refund": 0.0}


def start_note_refund(
    *,
    acctno: str,
    acctname: str,
    noteno: str,
    bills: list[dict[str, Any]],
    refund_amt: float,
    note_net: float,
    settle_method: str,
    chkno: str = "",
    chkdate: str | None = None,
    receive_bank_key: str | None = None,
    discount: float = 0.0,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Customer credit refund for a negative BN/BNN.

    Cash → Tiger voucher (KCN pattern); KSS PVN only after machine confirms used.
    Transfer/cheque → finalize immediately when remaining hits zero.
    Closing the dialog before Tiger success leaves the note open (รอคืนเงิน).
    """
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    method = (settle_method or "transfer").strip().lower()
    if method not in ("transfer", "cheque", "cash"):
        method = "transfer"
    if not acct or not note:
        raise ReceiveServiceError("acctno and noteno required", code="validation")

    snap = note_refund_snapshot(acctno=acct, noteno=note, note_net=note_net, client=client)
    if not snap["is_refund"]:
        raise ReceiveServiceError("note is not a credit refund", code="validation")
    remaining = float(snap["remaining_refund"])
    if remaining <= 1e-9:
        raise ReceiveServiceError("credit already fully refunded", code="already_paid")

    amount = round(abs(float(refund_amt)), 2)
    if amount <= 0:
        raise ReceiveServiceError("refund amount must be > 0", code="validation")
    if amount - remaining > 0.01:
        raise ReceiveServiceError(
            f"refund ({amount}) exceeds remaining credit ({remaining})",
            code="validation",
        )

    # Reuse in-flight Tiger refund for this note (dedupe / reopen after close).
    if method == "cash":
        existing = get_pending_tiger_receipt_for_note(client, acct, note)
        if existing and float(existing.get("netamt") or 0) < 0:
            receipt_id = str(existing.get("id") or "")
            attempt = get_ar_refund_attempt(receipt_id) if receipt_id else None
            status = str((attempt or {}).get("status") or "").lower()
            if attempt and status == "used":
                return complete_tiger_refund(
                    receipt_id=receipt_id,
                    operator=operator,
                    settings=settings,
                )
            if attempt and status not in ("failed", "cancelled", "canceled", "expired"):
                return {
                    "awaiting_tiger": True,
                    "is_refund": True,
                    "receipt": existing,
                    "tiger_attempt": attempt,
                    **note_refund_snapshot(
                        acctno=acct, noteno=note, note_net=note_net, client=client
                    ),
                }
            if receipt_id:
                patch_receipt(
                    client,
                    receipt_id,
                    {
                        "workflow_status": "failed",
                        "kss_sync_error": f"tiger_{status or 'missing'}",
                    },
                )

    prior = prior_allocations_for_bills(
        client, [str(b.get("BILLNO") or "").strip() for b in bills]
    )
    enriched = _allocate_refund_bills(bills, refund_amt=amount, prior=prior)
    jourmode = str(enriched[0].get("JOURMODE") or "1")
    billamt = round(sum(float(a["allocate_amt"]) for a in enriched), 2)  # negative
    disc = round(float(discount or 0), 2)
    netamt = round(billamt - disc, 2)  # negative
    day = (chkdate or date.today().isoformat())

    cash_amt = amount if method == "cash" else 0.0
    transfer_amt = amount if method == "transfer" else 0.0
    cheque_amt = amount if method == "cheque" else 0.0
    needs_tiger = method == "cash"
    proof_needed = method in ("transfer", "cheque")

    receipt = insert_receipt(
        client,
        {
            "acctno": acct,
            "acctname": (acctname or "").strip(),
            "noteno": note,
            "jourmode": jourmode,
            "received_at": date.today().isoformat(),
            "received_by": operator,
            "remark": f"refund BN {note}",
            "billamt": billamt,
            "discount": disc,
            "netamt": netamt,
            "cash_amt": cash_amt,
            "transfer_amt": transfer_amt,
            "cheque_amt": cheque_amt,
            "workflow_status": "awaiting_tiger" if needs_tiger else "review",
            "proof_status": "none",
            "kss_sync_status": "pending",
            "cash_mode": "tiger" if needs_tiger else None,
            "money_confirmed": False,
        },
    )
    receipt_id = receipt["id"]
    insert_receipt_bills(
        client,
        [
            {
                "receipt_id": receipt_id,
                "billno": a["billno"],
                "aftertax": a["aftertax"],
                "allocate_amt": a["allocate_amt"],
                "fully_paid": bool(a["fully_paid"]),
            }
            for a in enriched
        ],
    )
    channel_row = {
        "receipt_id": receipt_id,
        "settle_method": method,
        "amount": amount,
        "chkno": (chkno or None),
        "chkdate": day,
        "receive_bank_key": receive_bank_key,
        "bankname": None,
        "bank_gl": None,
    }
    if method == "transfer":
        from src.receive_notes.company_banks import resolve_company_receive_account

        bank = resolve_company_receive_account(receive_bank_key)
        channel_row["receive_bank_key"] = bank["key"]
        channel_row["bankname"] = bank["bank_name"]
        channel_row["bank_gl"] = bank["gl"]
        if not channel_row.get("chkno"):
            channel_row["chkno"] = "โอน"
    insert_receipt_channels(client, [channel_row])

    # Stash note credit snapshot for finalize remaining check (no schema migration).
    patch_receipt(
        client,
        receipt_id,
        {"cash_manual_reason": f"credit:{snap['credit_amt']}"},
    )

    out: dict[str, Any] = {
        "is_refund": True,
        "receipt": get_receipt(client, receipt_id),
        **note_refund_snapshot(acctno=acct, noteno=note, note_net=note_net, client=client),
    }

    if needs_tiger:
        try:
            attempt = start_ar_refund_voucher_attempt(
                receipt_id=receipt_id,
                amount=amount,
                noteno=note,
                submitted_by=operator,
                submitted_by_name=operator,
                note=f"AR refund {note} {receipt_id}",
            )
        except ReceiveTigerError as exc:
            patch_receipt(
                client,
                receipt_id,
                {"workflow_status": "failed", "kss_sync_error": str(exc)},
            )
            raise ReceiveServiceError(str(exc), code=exc.code) from exc
        patch_receipt(
            client,
            receipt_id,
            {
                "tiger_attempt_id": attempt.get("id"),
                "tiger_payment_no": attempt.get("voucher_num"),
            },
        )
        out["awaiting_tiger"] = True
        out["tiger_attempt"] = attempt
        out["receipt"] = get_receipt(client, receipt_id)
        return out

    # Transfer / cheque — confirm money now; KSS PVN when credit fully cleared.
    done = finalize_refund_kss_for_receipt(
        receipt_id=receipt_id,
        settings=settings,
        operator=operator,
    )
    out["awaiting_tiger"] = False
    out["kss"] = done
    out["receipt"] = get_receipt(client, receipt_id)
    out.update(
        note_refund_snapshot(acctno=acct, noteno=note, note_net=note_net, client=client)
    )
    return out


def complete_tiger_refund(
    *,
    receipt_id: str,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    receipt = get_receipt(client, receipt_id)
    if not receipt:
        raise ReceiveServiceError("receipt not found", code="not_found")

    attempt = refresh_ar_refund_attempt(receipt_id) or get_ar_refund_attempt(receipt_id)
    if not attempt:
        raise ReceiveServiceError("no Tiger refund voucher for receipt", code="tiger_missing")
    status = str(attempt.get("status") or "").lower()
    if status != "used":
        if status in ("failed", "cancelled", "canceled", "expired"):
            patch_receipt(
                client,
                receipt_id,
                {"workflow_status": "failed", "kss_sync_error": f"tiger_{status}"},
            )
            raise ReceiveServiceError(f"Tiger status={status}", code="tiger_failed")
        raise ReceiveServiceError(f"Tiger still {status}", code="tiger_pending")

    voucher_num = str(attempt.get("voucher_num") or "").strip() or None
    patch_receipt(
        client,
        receipt_id,
        {
            "tiger_attempt_id": attempt.get("id"),
            "tiger_payment_no": voucher_num,
            "money_confirmed": True,
        },
    )
    kss = finalize_refund_kss_for_receipt(
        receipt_id=receipt_id,
        settings=settings,
        operator=operator,
        tiger_voucher_num=voucher_num,
    )
    return {
        "attempt": attempt,
        "kss": kss,
        "receipt": get_receipt(client, receipt_id),
        "is_refund": True,
        "awaiting_tiger": False,
    }


def sync_tiger_refund(
    *,
    receipt_id: str,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Poll Tiger refund voucher; write KSS PVN only after status used (+ full clear)."""
    settings = settings or get_receive_notes_settings()
    client = get_receive_notes_supabase_client()
    receipt = get_receipt(client, receipt_id)
    if not receipt:
        raise ReceiveServiceError("receipt not found", code="not_found")

    if receipt.get("voucno") and receipt.get("kss_sync_status") == "synced":
        return {
            "awaiting_tiger": False,
            "done": True,
            "is_refund": True,
            "receipt": receipt,
            "kss": {"voucno": receipt.get("voucno"), "noteno": receipt.get("noteno")},
        }

    if receipt.get("money_confirmed") and str(receipt.get("workflow_status")) != "awaiting_tiger":
        # Partial already finalized without KSS.
        return {
            "awaiting_tiger": False,
            "done": True,
            "is_refund": True,
            "partial": True,
            "receipt": receipt,
            "kss": {
                "voucno": receipt.get("voucno"),
                "noteno": receipt.get("noteno"),
                "partial": True,
                "kss_deferred": receipt.get("kss_sync_status") != "synced",
            },
        }

    attempt = refresh_ar_refund_attempt(receipt_id) or get_ar_refund_attempt(receipt_id)
    if not attempt:
        raise ReceiveServiceError("no Tiger refund voucher for receipt", code="tiger_missing")
    status = str(attempt.get("status") or "").lower()
    if status == "used":
        done = complete_tiger_refund(
            receipt_id=receipt_id, operator=operator, settings=settings
        )
        return {
            "awaiting_tiger": False,
            "done": True,
            "is_refund": True,
            "receipt": done.get("receipt"),
            "tiger_attempt": done.get("attempt"),
            "kss": done.get("kss"),
        }
    if status in ("failed", "cancelled", "canceled", "expired"):
        patch_receipt(
            client,
            receipt_id,
            {"workflow_status": "failed", "kss_sync_error": f"tiger_{status}"},
        )
        return {
            "awaiting_tiger": False,
            "done": False,
            "failed": True,
            "is_refund": True,
            "tiger_status": status,
            "receipt": get_receipt(client, receipt_id),
            "tiger_attempt": attempt,
        }
    return {
        "awaiting_tiger": True,
        "done": False,
        "is_refund": True,
        "tiger_status": status,
        "receipt": receipt,
        "tiger_attempt": attempt,
    }


def _snapshot_receive_meta(
    *,
    received_at: str | None,
    remark: str | None,
    receive_bank_key: str | None,
    bankname: str | None = None,
    bank_gl: str | None = None,
) -> dict[str, Any]:
    return {
        "received_at": (received_at or "").strip()[:10] or None,
        "remark": (remark or "").strip() or "",
        "receive_bank_key": (receive_bank_key or "").strip() or None,
        "bankname": (bankname or "").strip() or None,
        "bank_gl": (bank_gl or "").strip() or None,
    }


def edit_vouchered_receive_meta(
    *,
    acctno: str,
    noteno: str,
    received_at: str | None = None,
    remark: str | None = None,
    receive_bank_key: str | None = None,
    accounting_reviewed: bool = False,
    operator: str | None = None,
    settings: ReceiveNotesSettings | None = None,
) -> dict[str, Any]:
    """Edit receive date / remark / bank on an existing voucher without re-cutting money.

    Leaves VOUCDATE, amounts, settle method, and Tiger transactions untouched.
    """
    settings = settings or get_receive_notes_settings()
    if not settings.receive_notes_write_enabled:
        raise ReceiveServiceError("RECEIVE_NOTES_WRITE_ENABLED is false", code="write_disabled")

    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        raise ReceiveServiceError("acctno and noteno required", code="validation")

    client = get_receive_notes_supabase_client()
    header = get_note_header(settings.site, acct, note)
    if not header:
        raise ReceiveServiceError("note not found in KSS", code="not_found")
    voucno = str(header.get("voucno") or "").strip()
    if not voucno:
        raise ReceiveServiceError("note is not vouchered yet", code="not_vouchered")

    payments = list_brdet(settings.site, voucno)
    gate = assess_receive_edit_gate(header=header, payments=payments)
    if gate["needs_accounting_review"] and not accounting_reviewed:
        raise ReceiveServiceError(
            "accounting review required before edit "
            f"({', '.join(gate['reasons']) or 'locked'})",
            code="needs_accounting_review",
        )

    overlay = get_receipt_by_voucno(client, voucno)
    rem = get_note(client, acct, note)
    channels = list((overlay or {}).get("receipt_channel") or [])
    pay0 = payments[0] if payments else {}
    channel0 = channels[0] if channels else {}

    old_bank_key = (
        str(channel0.get("receive_bank_key") or "").strip()
        or receive_bank_key_from_gl(pay0.get("ACCTNO") or channel0.get("bank_gl"))
        or receive_bank_key_from_bankname(pay0.get("BANKNAME") or channel0.get("bankname"))
    )
    old_remark = str((rem or {}).get("remark") or "").strip()
    if not old_remark and overlay:
        old_remark = str(overlay.get("remark") or "").strip()
    old_snap = _snapshot_receive_meta(
        received_at=(
            str(channel0.get("chkdate") or "").strip()
            or str((overlay or {}).get("received_at") or "").strip()
            or str(pay0.get("CHKDATE") or "").strip()
        ),
        remark=old_remark,
        receive_bank_key=old_bank_key,
        bankname=str(pay0.get("BANKNAME") or channel0.get("bankname") or "") or None,
        bank_gl=str(pay0.get("ACCTNO") or channel0.get("bank_gl") or "") or None,
    )

    new_date = (
        str(received_at).strip()[:10]
        if received_at is not None
        else old_snap["received_at"]
    )
    if received_at is not None:
        try:
            datetime.strptime(new_date, "%Y-%m-%d")
        except ValueError as exc:
            raise ReceiveServiceError(
                "received_at must be YYYY-MM-DD", code="validation"
            ) from exc

    new_remark = str(remark).strip() if remark is not None else old_snap["remark"]
    update_bank = receive_bank_key is not None
    new_bank_key = (
        str(receive_bank_key).strip() if update_bank else (old_snap["receive_bank_key"] or "")
    )
    bank_acct = None
    settle = str(channel0.get("settle_method") or "").lower()
    if not settle:
        settle = infer_settle_method(
            pay0.get("CHKNO"),
            bankname=pay0.get("BANKNAME"),
            acctno=pay0.get("ACCTNO"),
        )
    if update_bank:
        if settle == "cash":
            raise ReceiveServiceError(
                "cash receipts have no receive bank to edit",
                code="not_editable",
            )
        if not new_bank_key:
            raise ReceiveServiceError("receive_bank_key required", code="validation")
        bank_acct = resolve_company_receive_account(new_bank_key)
        new_bank_key = bank_acct["key"]

    new_snap = _snapshot_receive_meta(
        received_at=new_date,
        remark=new_remark,
        receive_bank_key=new_bank_key or None,
        bankname=(bank_acct["bank_name"] if bank_acct else old_snap["bankname"]),
        bank_gl=(bank_acct["gl"] if bank_acct else old_snap["bank_gl"]),
    )
    if new_snap == old_snap:
        return {
            "unchanged": True,
            "voucno": voucno,
            "old_values": old_snap,
            "new_values": new_snap,
            "edit_gate": gate,
            "receipt": overlay,
            "audit": None,
        }

    date_changed = new_snap["received_at"] != old_snap["received_at"]
    bank_changed = update_bank and new_snap["receive_bank_key"] != old_snap["receive_bank_key"]
    kss: dict[str, Any] | None = None
    if date_changed or bank_changed:
        try:
            kss = update_voucher_receive_meta(
                settings=settings,
                voucno=voucno,
                chkdate=new_snap["received_at"] if date_changed else None,
                bankname=new_snap["bankname"] if bank_changed else None,
                bank_gl=new_snap["bank_gl"] if bank_changed else None,
                update_bank=bank_changed,
            )
        except ReceiveNoteWriteError as exc:
            raise ReceiveServiceError(str(exc), code=exc.code) from exc

    if overlay:
        receipt_patch: dict[str, Any] = {}
        if date_changed:
            receipt_patch["received_at"] = new_snap["received_at"]
        if remark is not None:
            receipt_patch["remark"] = new_snap["remark"]
        if receipt_patch:
            overlay = patch_receipt(client, overlay["id"], receipt_patch)
        if date_changed or bank_changed:
            for ch in channels:
                ch_patch: dict[str, Any] = {}
                if date_changed:
                    ch_patch["chkdate"] = new_snap["received_at"]
                if bank_changed and str(ch.get("settle_method") or "").lower() != "cash":
                    ch_patch["receive_bank_key"] = new_snap["receive_bank_key"]
                    ch_patch["bankname"] = new_snap["bankname"]
                    ch_patch["bank_gl"] = new_snap["bank_gl"]
                if ch_patch and ch.get("id"):
                    patch_receipt_channel(client, str(ch["id"]), ch_patch)
            overlay = get_receipt(client, overlay["id"])

    if remark is not None:
        try:
            patch_note(client, acct, note, {"remark": new_snap["remark"]})
        except Exception:
            pass

    try:
        audit = insert_receipt_edit_audit(
            client,
            {
                "receipt_id": (overlay or {}).get("id"),
                "acctno": acct,
                "noteno": note,
                "voucno": voucno,
                "edited_by": operator,
                "accounting_reviewed": bool(accounting_reviewed),
                "gate_reasons": gate["reasons"],
                "old_values": old_snap,
                "new_values": new_snap,
            },
        )
    except Exception as exc:
        raise ReceiveServiceError(
            "receipt edit audit unavailable "
            "(apply receive_note.receipt_edit_audit migration / reload PostgREST)",
            code="audit_unavailable",
        ) from exc
    history = list_receipt_edit_audits(client, voucno=voucno, limit=20)
    return {
        "unchanged": False,
        "voucno": voucno,
        "voucdate": header.get("VOUCDATE"),
        "kss": kss,
        "old_values": old_snap,
        "new_values": new_snap,
        "edit_gate": gate,
        "receipt": overlay,
        "audit": audit,
        "edit_history": history,
        "settle_method": settle,
    }

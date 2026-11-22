from __future__ import annotations

from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from src.receive_notes.company_banks import brdet_line_from_payment
from src.receive_notes.config import ReceiveNotesSettings, get_receive_notes_settings
from src.receive_notes.db import (
    get_pending_tiger_receipt_for_note,
    get_receipt,
    get_receive_notes_supabase_client,
    insert_note,
    insert_receipt,
    insert_receipt_bills,
    insert_receipt_channels,
    patch_note,
    patch_receipt,
    prior_allocations_for_bills,
)
from src.receive_notes.parts9 import fetch_bills_for_receive
from src.receive_notes.tiger import (
    ReceiveTigerError,
    get_ar_attempt,
    is_ar_pos_bill_id,
    receipt_id_from_pos_bill_id,
    start_ar_cash_attempt,
)
from src.receive_notes.writer import ReceiveNoteWriteError, create_receive_note, create_receipt_voucher

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
        lines.append(
            brdet_line_from_payment(
                settle_method=method,
                chkno=str(ch.get("chkno") or ""),
                chkamt=float(ch.get("amount") or ch.get("chkamt") or 0),
                chkdate=str(ch.get("chkdate") or date.today().isoformat()),
                receive_bank_key=ch.get("receive_bank_key") or ch.get("bankname"),
                tiger_payment_no=tiger_payment_no if method == "cash" else None,
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
        remaining = round(aftertax - prior.get(bno, 0.0), 2)
        amount = round(float(alloc.get("allocate_amt") or remaining), 2)
        if remaining <= 0:
            raise ReceiveServiceError(f"bill {bno} already fully allocated", code="already_paid")
        if amount <= 0 or amount - remaining > 1e-6:
            raise ReceiveServiceError(f"invalid allocate for {bno}", code="validation")
        enriched.append(
            {
                "billno": bno,
                "aftertax": aftertax,
                "allocate_amt": amount,
                "JOURMODE": str(bill.get("JOURMODE") or "1").strip() or "1",
                "fully_paid": amount + prior.get(bno, 0.0) + 1e-6 >= aftertax,
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
        # Prior attempt died — fall through to a fresh overlay + Tiger send.

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

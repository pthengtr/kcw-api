from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.engine import Engine

from src.db import get_engine
from src.tiger_pay import cash_repos
from src.tiger_pay.config import get_tiger_pay_settings
from src.tiger_pay.normalize import BANGKOK_TZ
from src.tiger_pay.open_api import TigerPayOpenApiError, get_open_api_client

logger = logging.getLogger("kcw.tiger_pay.cash")

SNAPSHOT_TRIGGERS = frozenset({"webhook", "startup", "eod", "manual"})
HOPPER_STATUSES = frozenset({"success", "fail", "cancel", "cancelled", "failed"})


def parse_cash_items(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list):
        return []
    items: list[dict[str, Any]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        value = _as_number(entry.get("value") if "value" in entry else entry.get("denomination"))
        amount = _as_number(entry.get("amount") if "amount" in entry else entry.get("quantity"))
        if value is None or amount is None:
            continue
        kind = (
            str(entry.get("type") or entry.get("denominationType") or "").strip()
            or _infer_kind(value)
        )
        items.append(
            {
                "type": kind,
                "value": int(value) if value == int(value) else value,
                "amount": int(amount) if amount == int(amount) else amount,
            }
        )
    return items


def score_change_level(
    items: list[dict[str, Any]],
    *,
    change_ready: bool | None,
    watched: tuple[int, ...],
    warn_pieces: int,
    crit_pieces: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []
    if change_ready is False:
        reasons.append("เครื่องทอนเงินไม่พร้อม")

    present: dict[int, int] = {}
    for item in items:
        value = int(item["value"])
        if value not in watched:
            continue
        present[value] = present.get(value, 0) + int(item["amount"])

    worst = "green"
    for value, count in sorted(present.items(), reverse=True):
        label = _denom_label(value, _kind_for_value(items, value))
        if count <= crit_pieces:
            worst = "red"
            reasons.append(f"{label} เหลือ {count} ใบ")
        elif count <= warn_pieces:
            if worst == "green":
                worst = "orange"
            reasons.append(f"{label} เหลือ {count} ใบ")

    if change_ready is False:
        return "red", reasons
    return worst, reasons


def hopper_moved_by_webhook(
    transaction: dict[str, Any],
    payload: dict[str, Any] | None = None,
    *,
    duplicate: bool = False,
) -> bool:
    if duplicate:
        return False
    status = str(transaction.get("status") or "").strip().lower()
    payment_type = str(transaction.get("payment_type") or "").strip().lower()
    if status not in HOPPER_STATUSES:
        return False

    change_amount = _as_number(transaction.get("change_amount")) or 0
    if change_amount > 0:
        return True

    payment = None
    if isinstance(payload, dict):
        maybe_payment = payload.get("payment")
        payment = maybe_payment if isinstance(maybe_payment, dict) else payload
    cash_list = parse_cash_items((payment or {}).get("cashList") if isinstance(payment, dict) else None)
    if cash_list:
        return True
    return payment_type == "cash"


def items_total_baht(items: list[dict[str, Any]]) -> Decimal:
    total = Decimal("0")
    for item in items:
        total += Decimal(str(item["value"])) * Decimal(str(item["amount"]))
    return total


def capture_snapshot(
    engine: Engine | None = None,
    *,
    trigger: str,
    shop_code: str | None = None,
    tiger_payment_id: int | None = None,
    payment_no: str | None = None,
    payment_status: str | None = None,
    skip_if_busy: bool = True,
) -> dict[str, Any] | None:
    """GET live hopper from the cashbox and persist. Never raises to callers."""
    if trigger not in SNAPSHOT_TRIGGERS:
        raise ValueError(f"invalid snapshot trigger: {trigger}")

    settings = get_tiger_pay_settings()
    shop = (shop_code or settings.tiger_pay_default_shop_code).strip() or "1"
    db = engine or get_engine()

    if (
        tiger_payment_id is not None
        and payment_status
        and cash_repos.recent_snapshot_for_payment(
            db,
            tiger_payment_id=int(tiger_payment_id),
            payment_status=str(payment_status),
        )
    ):
        logger.info(
            "skip hopper snapshot; recent snapshot exists tiger_payment_id=%s status=%s",
            tiger_payment_id,
            payment_status,
        )
        return None

    client = get_open_api_client()
    if skip_if_busy and trigger != "webhook":
        try:
            current = client.get_current()
        except TigerPayOpenApiError:
            logger.exception("hopper snapshot skipped; get_current failed trigger=%s", trigger)
            return None
        if current is not None:
            logger.info("skip hopper snapshot; payment in flight trigger=%s", trigger)
            return None

    try:
        raw_items = client.get_cash()
        change_ready = client.get_change_status()
    except TigerPayOpenApiError:
        logger.exception("hopper snapshot device GET failed trigger=%s", trigger)
        return None

    items = parse_cash_items(raw_items)
    cash_box_items: list[dict[str, Any]] = []
    try:
        cash_box_items = parse_cash_items(client.get_cash_box())
    except TigerPayOpenApiError:
        logger.exception("cash_box snapshot device GET failed trigger=%s", trigger)

    level, reasons = score_change_level(
        items,
        change_ready=change_ready,
        watched=settings.tiger_pay_change_denoms,
        warn_pieces=settings.tiger_pay_change_warn_pieces,
        crit_pieces=settings.tiger_pay_change_crit_pieces,
    )
    now = datetime.now(BANGKOK_TZ)
    try:
        return cash_repos.insert_cash_snapshot(
            db,
            captured_at=now,
            biz_day=now.date() if now.tzinfo else cash_repos.bangkok_biz_day(now),
            trigger=trigger,
            shop_code=shop,
            change_ready=change_ready,
            change_level=level,
            change_reasons=reasons,
            items=items,
            total_baht=items_total_baht(items),
            cash_box_items=cash_box_items,
            cash_box_total_baht=items_total_baht(cash_box_items),
            tiger_payment_id=tiger_payment_id,
            payment_no=payment_no,
            payment_status=payment_status,
        )
    except Exception:
        logger.exception("hopper snapshot persist failed trigger=%s", trigger)
        return None


def maybe_snapshot_after_webhook(
    transaction: dict[str, Any],
    payload: dict[str, Any] | None,
    *,
    duplicate: bool,
    engine: Engine | None = None,
) -> dict[str, Any] | None:
    if not hopper_moved_by_webhook(transaction, payload, duplicate=duplicate):
        return None
    payment_id = transaction.get("tiger_payment_id")
    try:
        payment_id_int = int(payment_id) if payment_id is not None else None
    except (TypeError, ValueError):
        payment_id_int = None
    shop = str(transaction.get("shop_code") or "").strip() or None
    return capture_snapshot(
        engine,
        trigger="webhook",
        shop_code=shop,
        tiger_payment_id=payment_id_int,
        payment_no=str(transaction.get("payment_no") or "") or None,
        payment_status=str(transaction.get("status") or "") or None,
        skip_if_busy=False,
    )


def maybe_run_eod(engine: Engine | None = None) -> dict[str, Any] | None:
    settings = get_tiger_pay_settings()
    now = datetime.now(BANGKOK_TZ)
    if now.hour < settings.tiger_pay_eod_hour:
        return None
    shop = settings.tiger_pay_default_shop_code
    db = engine or get_engine()
    biz_day = now.date()
    existing = cash_repos.get_daily_close(db, biz_day=biz_day, shop_code=shop)
    if existing:
        return existing
    snapshot = capture_snapshot(db, trigger="eod", shop_code=shop)
    if snapshot is None:
        return None
    return freeze_daily_close(
        db,
        biz_day=biz_day,
        shop_code=shop,
        closing_snapshot=snapshot,
        trigger="eod_auto",
    )


def process_pending_commands(engine: Engine | None = None) -> None:
    db = engine or get_engine()
    command = cash_repos.claim_next_cash_command(db)
    if command is None:
        return
    command_id = str(command["id"])
    shop = str(command.get("shop_code") or "").strip() or get_tiger_pay_settings().tiger_pay_default_shop_code
    kind = str(command.get("command") or "")
    try:
        snapshot = capture_snapshot(db, trigger="manual" if kind == "refresh" else "eod", shop_code=shop)
        if snapshot is None:
            cash_repos.finish_cash_command(
                db,
                command_id,
                status="failed",
                error="hopper snapshot skipped (device busy or GET failed)",
            )
            return
        if kind == "close":
            biz_day = _parse_biz_day(command.get("biz_day")) or cash_repos.bangkok_biz_day()
            freeze_daily_close(
                db,
                biz_day=biz_day,
                shop_code=shop,
                closing_snapshot=snapshot,
                trigger="manual",
            )
        cash_repos.finish_cash_command(
            db,
            command_id,
            status="done",
            snapshot_id=str(snapshot.get("id") or ""),
        )
    except Exception as exc:
        logger.exception("cash_command failed id=%s command=%s", command_id, kind)
        cash_repos.finish_cash_command(
            db,
            command_id,
            status="failed",
            error=str(exc)[:500],
        )


def freeze_daily_close(
    engine: Engine,
    *,
    biz_day: date,
    shop_code: str,
    closing_snapshot: dict[str, Any],
    trigger: str,
) -> dict[str, Any]:
    existing = cash_repos.get_daily_close(engine, biz_day=biz_day, shop_code=shop_code)
    if existing:
        return existing

    opening_id = cash_repos.previous_closing_snapshot_id(
        engine, biz_day=biz_day, shop_code=shop_code
    )
    opening = (
        cash_repos.get_snapshot_by_id(engine, opening_id) if opening_id else None
    )
    if opening is None:
        first = cash_repos.first_snapshot_of_day(
            engine, biz_day=biz_day, shop_code=shop_code
        )
        if first and str(first.get("id")) != str(closing_snapshot.get("id")):
            opening = first
            opening_id = str(first.get("id"))

    txns = cash_repos.list_payment_transactions_for_day(
        engine, biz_day=biz_day, shop_code=shop_code
    )
    vouchers = cash_repos.list_voucher_attempts_for_day(engine, biz_day=biz_day)
    report = build_daily_report(
        txns,
        vouchers=vouchers,
        opening_items=parse_cash_items((opening or {}).get("items")),
        closing_items=parse_cash_items(closing_snapshot.get("items")),
    )
    return cash_repos.insert_daily_close(
        engine,
        biz_day=biz_day,
        shop_code=shop_code,
        trigger=trigger,
        opening_snapshot_id=opening_id,
        closing_snapshot_id=str(closing_snapshot["id"]),
        report=report,
    )


def build_daily_report(
    txns: list[dict[str, Any]],
    *,
    vouchers: list[dict[str, Any]],
    opening_items: list[dict[str, Any]],
    closing_items: list[dict[str, Any]],
) -> dict[str, Any]:
    success = [row for row in txns if str(row.get("status") or "").lower() == "success"]
    billed = _sum_money(success, "amount")
    cash_success = [
        row for row in success if str(row.get("payment_type") or "").lower() == "cash"
    ]
    cash_in = _sum_money(cash_success, "total_pay")
    change_out = _sum_money(cash_success, "change_amount")
    qr_in = _sum_money(
        [row for row in success if str(row.get("payment_type") or "").lower() in {"qr", "promptpay"}],
        "total_pay",
    )

    denom_in: dict[str, int] = {}
    denom_out: dict[str, int] = {}
    unspecified_in = Decimal("0")
    exceptions: list[dict[str, Any]] = []

    for row in txns:
        payload = row.get("payload") if isinstance(row.get("payload"), dict) else {}
        payment = payload.get("payment") if isinstance(payload.get("payment"), dict) else payload
        inserted = parse_cash_items((payment or {}).get("cashList") if isinstance(payment, dict) else None)
        change = (payment or {}).get("change") if isinstance(payment, dict) else None
        change_list = parse_cash_items((change or {}).get("cashList") if isinstance(change, dict) else None)

        status = str(row.get("status") or "").lower()
        payment_type = str(row.get("payment_type") or "").lower()
        listed_in = items_total_baht(inserted)
        total_pay = Decimal(str(row.get("total_pay") or 0))

        if status == "success" and payment_type == "cash":
            for item in inserted:
                key = str(int(item["value"]))
                denom_in[key] = denom_in.get(key, 0) + int(item["amount"])
            gap = total_pay - listed_in
            if gap > Decimal("0.009"):
                unspecified_in += gap
            for item in change_list:
                key = str(int(item["value"]))
                denom_out[key] = denom_out.get(key, 0) + int(item["amount"])
        elif inserted or change_list or (_as_number(row.get("change_amount")) or 0) > 0:
            exceptions.append(
                {
                    "payment_no": row.get("payment_no"),
                    "status": status,
                    "payment_type": payment_type,
                    "total_pay": float(total_pay),
                    "change_amount": float(Decimal(str(row.get("change_amount") or 0))),
                    "remark": row.get("remark"),
                }
            )
            for item in inserted:
                key = str(int(item["value"]))
                denom_in[key] = denom_in.get(key, 0) + int(item["amount"])
            for item in change_list:
                key = str(int(item["value"]))
                denom_out[key] = denom_out.get(key, 0) + int(item["amount"])

    opening = _item_counts(opening_items)
    closing = _item_counts(closing_items)
    expected: dict[str, int] = {}
    keys = set(opening) | set(denom_in) | set(denom_out) | set(closing)
    for key in keys:
        expected[key] = opening.get(key, 0) + denom_in.get(key, 0) - denom_out.get(key, 0)
    variance = {
        key: closing.get(key, 0) - expected.get(key, 0)
        for key in keys
    }

    voucher_used = [
        row for row in vouchers if str(row.get("status") or "").lower() in {"used", "success"}
    ]
    counts: dict[str, int] = {}
    for row in txns:
        status = str(row.get("status") or "").lower() or "unknown"
        counts[status] = counts.get(status, 0) + 1

    return {
        "billed": float(billed),
        "cash_in": float(cash_in),
        "change_out": float(change_out),
        "cash_net": float(cash_in - change_out),
        "qr_promptpay_in": float(qr_in),
        "txn_counts": counts,
        "success_count": len(success),
        "denom_in": denom_in,
        "denom_out": denom_out,
        "unspecified_in": float(unspecified_in),
        "hopper_opening": opening,
        "hopper_expected": expected,
        "hopper_actual": closing,
        "variance": variance,
        "exceptions": exceptions,
        "voucher_used_count": len(voucher_used),
        "voucher_used_amount": float(_sum_money(voucher_used, "amount")),
    }


def cached_or_live_cash(
    engine: Engine,
    *,
    live: bool,
    shop_code: str | None = None,
) -> dict[str, Any]:
    settings = get_tiger_pay_settings()
    shop = (shop_code or settings.tiger_pay_default_shop_code).strip() or "1"
    error: str | None = None
    snapshot: dict[str, Any] | None = None
    if live:
        snapshot = capture_snapshot(engine, trigger="manual", shop_code=shop)
        if snapshot is None:
            error = "ไม่สามารถอ่านเครื่องได้ตอนนี้ (อาจมีรายการค้างหรือเครื่องไม่ตอบ)"
    if snapshot is None:
        snapshot = cash_repos.latest_cash_snapshot(engine, shop)
    return {
        "snapshot": snapshot,
        "live": bool(live and snapshot and snapshot.get("trigger") == "manual" and error is None),
        "error": error,
    }


def _as_number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, str) and value.strip():
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _infer_kind(value: float) -> str:
    return "Banknote" if value >= 20 else "Coin"


def _kind_for_value(items: list[dict[str, Any]], value: int) -> str:
    for item in items:
        if int(item["value"]) == value:
            return str(item.get("type") or _infer_kind(value))
    return _infer_kind(value)


def _denom_label(value: int, kind: str) -> str:
    prefix = "ธนบัตร" if kind.lower() == "banknote" else "เหรียญ"
    return f"{prefix} {value}"


def _sum_money(rows: list[dict[str, Any]], key: str) -> Decimal:
    total = Decimal("0")
    for row in rows:
        total += Decimal(str(row.get(key) or 0))
    return total


def _item_counts(items: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        key = str(int(item["value"]))
        counts[key] = counts.get(key, 0) + int(item["amount"])
    return counts


def _parse_biz_day(value: Any) -> date | None:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError:
            return None
    return None

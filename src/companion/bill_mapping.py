from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

import pandas as pd

from src.companion.bills import PosBill

logger = logging.getLogger("kcw.companion.bill_mapping")

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")

REQUIRED_COLUMNS = (
    "ID",
    "BILLNO",
    "AFTERTAX",
    "BILLDATE",
    "BILLTIME",
    "PAID",
    "CASHED",
)


def normalize_flag(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().upper()


def blank(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def is_excluded_bill_number(bill_number: object) -> bool:
    """Exclude transfer-style bills (TF... / TFV...)."""
    text = blank(bill_number).upper()
    return text.startswith("TFV") or text.startswith("TF")


def parse_bill_datetime(bill_date: object, bill_time: object) -> datetime:
    date_text = blank(bill_date)
    time_text = blank(bill_time)
    if not date_text:
        raise ValueError("empty BILLDATE")

    # SQL Server / pandas may already give date/datetime objects.
    if isinstance(bill_date, datetime):
        parsed_date = bill_date.date()
    elif isinstance(bill_date, date):
        parsed_date = bill_date
    else:
        parsed_date = None
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d", "%d-%m-%Y", "%Y%m%d"):
            try:
                candidate = date_text
                if fmt == "%Y%m%d":
                    candidate = date_text.replace("-", "").replace("/", "")[:8]
                elif len(candidate) > 10:
                    candidate = candidate[:10]
                parsed_date = datetime.strptime(candidate, fmt).date()
                break
            except ValueError:
                continue
        if parsed_date is None:
            parsed = pd.to_datetime(date_text, errors="raise", dayfirst=True)
            parsed_date = parsed.date()

    if isinstance(bill_time, datetime):
        parsed_time = bill_time.time()
    elif isinstance(bill_time, time):
        parsed_time = bill_time
    else:
        parsed_time = time(0, 0, 0)
        if time_text:
            for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S", "%H%M"):
                try:
                    parsed_time = datetime.strptime(time_text, fmt).time()
                    break
                except ValueError:
                    continue

    return datetime.combine(parsed_date, parsed_time, tzinfo=BANGKOK_TZ)


def row_to_bill(row: pd.Series) -> PosBill | None:
    try:
        amount = Decimal(blank(row["AFTERTAX"]) or "nan")
    except (InvalidOperation, AttributeError, TypeError):
        logger.warning(
            "Skipping bill with invalid AFTERTAX id=%s value=%r",
            row.get("ID"),
            row.get("AFTERTAX"),
        )
        return None

    bill_id = blank(row["ID"])
    bill_number = blank(row["BILLNO"])
    if not bill_id or not bill_number:
        return None
    if is_excluded_bill_number(bill_number):
        return None

    try:
        created_at = parse_bill_datetime(row.get("BILLDATE"), row.get("BILLTIME"))
    except Exception:
        logger.warning("Skipping bill with invalid date/time id=%s", bill_id)
        return None

    pos_status = blank(row.get("PAID")) or "unknown"
    salesperson_raw = blank(row.get("SALE"))
    salesperson = salesperson_raw or None

    return PosBill(
        id=bill_id,
        bill_number=bill_number,
        amount=amount,
        created_at=created_at,
        pos_status=pos_status,
        salesperson=salesperson,
    )


def frames_to_bills(frame: pd.DataFrame) -> list[PosBill]:
    bills: list[PosBill] = []
    for _, row in frame.iterrows():
        bill = row_to_bill(row)
        if bill is not None:
            bills.append(bill)
    return bills

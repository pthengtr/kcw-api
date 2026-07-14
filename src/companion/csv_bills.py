from __future__ import annotations

import logging
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from src.companion.bills import PosBill
from src.companion.config import CompanionBillSettings, get_companion_bill_settings

logger = logging.getLogger("kcw.companion.csv_bills")

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


def _normalize_flag(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().upper()


def _blank(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def _parse_bill_datetime(bill_date: object, bill_time: object) -> datetime:
    date_text = _blank(bill_date)
    time_text = _blank(bill_time)
    if not date_text:
        raise ValueError("empty BILLDATE")

    parsed_date: date | None = None
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

    parsed_time = time(0, 0, 0)
    if time_text:
        for fmt in ("%H:%M:%S", "%H:%M", "%H%M%S", "%H%M"):
            try:
                parsed_time = datetime.strptime(time_text, fmt).time()
                break
            except ValueError:
                continue

    return datetime.combine(parsed_date, parsed_time, tzinfo=BANGKOK_TZ)


def _row_to_bill(row: pd.Series) -> PosBill | None:
    try:
        amount = Decimal(_blank(row["AFTERTAX"]) or "nan")
    except (InvalidOperation, AttributeError, TypeError):
        logger.warning(
            "Skipping bill with invalid AFTERTAX id=%s value=%r",
            row.get("ID"),
            row.get("AFTERTAX"),
        )
        return None

    bill_id = _blank(row["ID"])
    bill_number = _blank(row["BILLNO"])
    if not bill_id or not bill_number:
        return None

    try:
        created_at = _parse_bill_datetime(row.get("BILLDATE"), row.get("BILLTIME"))
    except Exception:
        logger.warning("Skipping bill with invalid date/time id=%s", bill_id)
        return None

    pos_status = _blank(row.get("PAID")) or "unknown"
    salesperson_raw = _blank(row.get("SALE"))
    salesperson = salesperson_raw or None

    return PosBill(
        id=bill_id,
        bill_number=bill_number,
        amount=amount,
        created_at=created_at,
        pos_status=pos_status,
        salesperson=salesperson,
    )


def _load_cash_frame(csv_path: Path) -> pd.DataFrame:
    if not csv_path.is_file():
        raise FileNotFoundError(f"POS bills CSV not found: {csv_path}")

    header = pd.read_csv(csv_path, nrows=0)
    available = set(header.columns.astype(str))
    missing = [col for col in REQUIRED_COLUMNS if col not in available]
    if missing:
        raise ValueError(f"POS bills CSV missing columns: {', '.join(missing)}")

    usecols = list(REQUIRED_COLUMNS)
    if "SALE" in available:
        usecols.append("SALE")

    frame = pd.read_csv(csv_path, usecols=usecols, dtype=str, keep_default_na=False)
    frame = frame[frame["CASHED"].map(_normalize_flag) == "Y"].copy()
    if frame.empty:
        frame["_created_at"] = []
        return frame

    created_at_values: list[datetime | pd.NaT] = []
    for _, row in frame.iterrows():
        try:
            created_at_values.append(
                _parse_bill_datetime(row.get("BILLDATE"), row.get("BILLTIME"))
            )
        except Exception:
            created_at_values.append(pd.NaT)

    frame["_created_at"] = created_at_values
    frame = frame[frame["_created_at"].notna()].copy()
    return frame.sort_values("_created_at", ascending=False)


def list_csv_bills(settings: CompanionBillSettings | None = None) -> list[PosBill]:
    settings = settings or get_companion_bill_settings()
    csv_path = Path(settings.pos_bills_csv_path)
    frame = _load_cash_frame(csv_path)

    if frame.empty:
        return []

    if settings.pos_bills_mode == "today":
        today = datetime.now(BANGKOK_TZ).date()
        frame = frame[frame["_created_at"].map(lambda dt: dt.date() == today)]

    frame = frame.head(int(settings.pos_bills_limit))

    bills: list[PosBill] = []
    for _, row in frame.iterrows():
        bill = _row_to_bill(row)
        if bill is not None:
            bills.append(bill)
    return bills


def get_csv_bill(pos_bill_id: str, settings: CompanionBillSettings | None = None) -> PosBill | None:
    settings = settings or get_companion_bill_settings()
    csv_path = Path(settings.pos_bills_csv_path)
    frame = _load_cash_frame(csv_path)
    if frame.empty:
        return None

    target = str(pos_bill_id).strip()
    matches = frame[frame["ID"].map(_blank) == target]
    if matches.empty:
        return None
    return _row_to_bill(matches.iloc[0])

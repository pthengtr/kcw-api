from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from src.companion.bill_mapping import (
    REQUIRED_COLUMNS,
    frames_to_bills,
    is_excluded_bill_number,
    normalize_flag,
    parse_bill_datetime,
    blank,
    row_to_bill,
)
from src.companion.bills import PosBill
from src.companion.config import CompanionBillSettings, get_companion_bill_settings

logger = logging.getLogger("kcw.companion.csv_bills")


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
    frame = frame[frame["CASHED"].map(normalize_flag) == "Y"].copy()
    frame = frame[~frame["BILLNO"].map(is_excluded_bill_number)].copy()
    if frame.empty:
        frame["_created_at"] = []
        return frame

    created_at_values: list = []
    for _, row in frame.iterrows():
        try:
            created_at_values.append(
                parse_bill_datetime(row.get("BILLDATE"), row.get("BILLTIME"))
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
        from datetime import datetime

        from src.companion.bill_mapping import BANGKOK_TZ

        today = datetime.now(BANGKOK_TZ).date()
        frame = frame[frame["_created_at"].map(lambda dt: dt.date() == today)]

    frame = frame.head(int(settings.pos_bills_limit))
    return frames_to_bills(frame)


def get_csv_bill(pos_bill_id: str, settings: CompanionBillSettings | None = None) -> PosBill | None:
    settings = settings or get_companion_bill_settings()
    csv_path = Path(settings.pos_bills_csv_path)
    frame = _load_cash_frame(csv_path)
    if frame.empty:
        return None

    target = str(pos_bill_id).strip()
    matches = frame[frame["ID"].map(blank) == target]
    if matches.empty:
        return None
    return row_to_bill(matches.iloc[0])

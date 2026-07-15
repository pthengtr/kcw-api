from __future__ import annotations

import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal

from src.companion.config import get_companion_bill_settings

logger = logging.getLogger("kcw.companion.bills")


@dataclass(frozen=True)
class PosBill:
    id: str
    bill_number: str
    amount: Decimal
    created_at: datetime
    pos_status: str = "open"
    salesperson: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["amount"] = float(self.amount)
        payload["created_at"] = self.created_at.isoformat()
        return payload


_MOCK_BILLS: tuple[PosBill, ...] = (
    PosBill(
        id="bill-1001",
        bill_number="B2607140001",
        amount=Decimal("250.00"),
        created_at=datetime(2026, 7, 14, 9, 15, tzinfo=timezone.utc),
        pos_status="N",
        salesperson="mock.user",
    ),
    PosBill(
        id="bill-1002",
        bill_number="B2607140002",
        amount=Decimal("89.50"),
        created_at=datetime(2026, 7, 14, 10, 2, tzinfo=timezone.utc),
        pos_status="N",
        salesperson="mock.user",
    ),
    PosBill(
        id="bill-1003",
        bill_number="B2607140003",
        amount=Decimal("1250.00"),
        created_at=datetime(2026, 7, 14, 11, 40, tzinfo=timezone.utc),
        pos_status="Y",
        salesperson="mock.user",
    ),
)


def _settings_with_mode(mode: str | None):
    settings = get_companion_bill_settings()
    if mode is None:
        return settings
    normalized = mode.strip().lower()
    if normalized not in {"latest", "today"}:
        raise ValueError("mode must be 'latest' or 'today'")
    if normalized == settings.pos_bills_mode:
        return settings
    return settings.model_copy(update={"pos_bills_mode": normalized})


def _filter_mock_bills(mode: str) -> list[PosBill]:
    if mode != "today":
        return list(_MOCK_BILLS)
    from src.companion.bill_mapping import BANGKOK_TZ

    today = datetime.now(BANGKOK_TZ).date()
    return [
        bill
        for bill in _MOCK_BILLS
        if bill.created_at.astimezone(BANGKOK_TZ).date() == today
    ]


def list_open_bills(*, mode: str | None = None) -> list[PosBill]:
    settings = _settings_with_mode(mode)
    source = settings.pos_bill_source

    if source == "csv":
        from src.companion.csv_bills import list_csv_bills

        try:
            return list_csv_bills(settings)
        except Exception:
            logger.exception("Failed to load POS bills from CSV; returning empty list")
            return []

    if source == "mssql":
        from src.companion.mssql_bills import list_mssql_bills

        try:
            return list_mssql_bills(settings)
        except Exception:
            logger.exception("Failed to load POS bills from MSSQL; returning empty list")
            return []

    return _filter_mock_bills(settings.pos_bills_mode)


def get_open_bill(pos_bill_id: str) -> PosBill | None:
    settings = get_companion_bill_settings()
    source = settings.pos_bill_source

    if source == "csv":
        from src.companion.csv_bills import get_csv_bill

        try:
            return get_csv_bill(pos_bill_id, settings)
        except Exception:
            logger.exception("Failed to load POS bill %s from CSV", pos_bill_id)
            return None

    if source == "mssql":
        from src.companion.mssql_bills import get_mssql_bill

        try:
            return get_mssql_bill(pos_bill_id, settings)
        except Exception:
            logger.exception("Failed to load POS bill %s from MSSQL", pos_bill_id)
            return None

    for bill in _MOCK_BILLS:
        if bill.id == pos_bill_id:
            return bill
    return None

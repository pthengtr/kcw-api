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


# Practical ceiling when the UI asks for "all" bills.
_ALL_BILLS_LIMIT = 1_000_000


def _settings_with_overrides(
    *,
    mode: str | None = None,
    limit: int | str | None = None,
):
    settings = get_companion_bill_settings()
    updates: dict[str, object] = {}

    if mode is not None:
        normalized_mode = mode.strip().lower()
        if normalized_mode not in {"latest", "today"}:
            raise ValueError("mode must be 'latest' or 'today'")
        if normalized_mode != settings.pos_bills_mode:
            updates["pos_bills_mode"] = normalized_mode

    if limit is not None:
        if isinstance(limit, str) and limit.strip().lower() == "all":
            updates["pos_bills_limit"] = _ALL_BILLS_LIMIT
        else:
            try:
                parsed_limit = int(limit)
            except (TypeError, ValueError) as exc:
                raise ValueError("limit must be 10, 20, or all") from exc
            if parsed_limit <= 0:
                raise ValueError("limit must be greater than zero")
            if parsed_limit != settings.pos_bills_limit:
                updates["pos_bills_limit"] = parsed_limit

    if not updates:
        return settings
    return settings.model_copy(update=updates)


def _filter_mock_bills(mode: str, *, limit: int) -> list[PosBill]:
    bills = list(_MOCK_BILLS)
    if mode == "today":
        from src.companion.bill_mapping import BANGKOK_TZ

        today = datetime.now(BANGKOK_TZ).date()
        bills = [
            bill
            for bill in bills
            if bill.created_at.astimezone(BANGKOK_TZ).date() == today
        ]
    return bills[:limit]


def list_open_bills(
    *,
    mode: str | None = None,
    limit: int | str | None = None,
) -> list[PosBill]:
    settings = _settings_with_overrides(mode=mode, limit=limit)
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

    return _filter_mock_bills(
        settings.pos_bills_mode,
        limit=int(settings.pos_bills_limit),
    )


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

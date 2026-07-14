from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True)
class PosBill:
    id: str
    bill_number: str
    amount: Decimal
    created_at: datetime
    pos_status: str = "open"

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
    ),
    PosBill(
        id="bill-1002",
        bill_number="B2607140002",
        amount=Decimal("89.50"),
        created_at=datetime(2026, 7, 14, 10, 2, tzinfo=timezone.utc),
    ),
    PosBill(
        id="bill-1003",
        bill_number="B2607140003",
        amount=Decimal("1250.00"),
        created_at=datetime(2026, 7, 14, 11, 40, tzinfo=timezone.utc),
    ),
)


def list_open_bills() -> list[PosBill]:
    """Phase 1: read-only mock unpaid/open POS bills."""
    return list(_MOCK_BILLS)


def get_open_bill(pos_bill_id: str) -> PosBill | None:
    for bill in _MOCK_BILLS:
        if bill.id == pos_bill_id:
            return bill
    return None

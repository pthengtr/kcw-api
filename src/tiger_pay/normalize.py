import math
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

BANGKOK_TZ = ZoneInfo("Asia/Bangkok")


def blank_to_none(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


def normalize_positive_decimal(value: Any, field_name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be a valid number")

    if isinstance(value, int):
        decimal_value = Decimal(value)
    elif isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"{field_name} must be a valid number")
        decimal_value = Decimal(str(value))
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{field_name} must be a valid number")
        try:
            decimal_value = Decimal(text)
        except InvalidOperation as exc:
            raise ValueError(f"{field_name} must be a valid number") from exc
    elif isinstance(value, Decimal):
        decimal_value = value
    else:
        raise ValueError(f"{field_name} must be a valid number")

    if decimal_value.is_nan() or decimal_value.is_infinite():
        raise ValueError(f"{field_name} must be a valid number")
    if decimal_value < 0:
        raise ValueError(f"{field_name} must not be negative")

    return decimal_value


def decimal_to_json_string(value: Decimal) -> str:
    return format(value, "f")


def normalize_change_amount(change: Any) -> Decimal:
    if isinstance(change, dict):
        if "amount" in change:
            return normalize_positive_decimal(change["amount"], "payment.change.amount")
        return Decimal("0")

    if isinstance(change, (int, float, str, Decimal)):
        return normalize_positive_decimal(change, "payment.change")

    return Decimal("0")


def normalize_tiger_timestamp(value: str) -> str:
    text = value.strip()
    if not text:
        raise ValueError("timestamp must not be empty")

    try:
        if text.endswith("Z"):
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
        elif _has_explicit_offset(text):
            parsed = datetime.fromisoformat(text)
        else:
            parsed = datetime.fromisoformat(text).replace(tzinfo=BANGKOK_TZ)
    except ValueError as exc:
        raise ValueError("timestamp is invalid") from exc

    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=BANGKOK_TZ)

    return parsed.isoformat()


def _has_explicit_offset(value: str) -> bool:
    if len(value) < 6:
        return False

    tail = value[10:]
    plus_index = tail.find("+")
    minus_index = tail.rfind("-")
    return plus_index != -1 or minus_index != -1

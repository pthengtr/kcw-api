from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_CENT = Decimal("0.01")
_VAT_RATE = Decimal("7")
_VAT_DIV = Decimal("107")


def money(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0.00")
    return Decimal(str(value)).quantize(_CENT, rounding=ROUND_HALF_UP)


def split_inclusive(total: Decimal | float | int | str) -> tuple[Decimal, Decimal, Decimal]:
    """Split VAT-inclusive amount into (beforetax, tax, aftertax) using ×7/107."""
    after = money(total)
    tax = (after * _VAT_RATE / _VAT_DIV).quantize(_CENT, rounding=ROUND_HALF_UP)
    before = (after - tax).quantize(_CENT, rounding=ROUND_HALF_UP)
    return before, tax, after


def totals_from_amounts(amounts: list) -> dict[str, Decimal]:
    before = Decimal("0.00")
    tax = Decimal("0.00")
    after = Decimal("0.00")
    for raw in amounts:
        b, t, a = split_inclusive(raw)
        before += b
        tax += t
        after += a
    return {
        "beforetax": before.quantize(_CENT, rounding=ROUND_HALF_UP),
        "tax": tax.quantize(_CENT, rounding=ROUND_HALF_UP),
        "aftertax": after.quantize(_CENT, rounding=ROUND_HALF_UP),
    }

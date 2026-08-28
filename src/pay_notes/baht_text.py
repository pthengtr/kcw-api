"""Thai currency wording (บาท / สตางค์) for pay-note printouts."""

from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

_ONES = ["", "หนึ่ง", "สอง", "สาม", "สี่", "ห้า", "หก", "เจ็ด", "แปด", "เก้า"]


def _read_below_million(n: int) -> str:
    if n <= 0:
        return ""
    digits = [int(ch) for ch in f"{n:06d}"]
    labels = ["แสน", "หมื่น", "พัน", "ร้อย", "สิบ", ""]
    parts: list[str] = []
    for i, d in enumerate(digits):
        if d == 0:
            continue
        pos = 5 - i
        if pos == 1:
            if d == 1:
                parts.append("สิบ")
            elif d == 2:
                parts.append("ยี่สิบ")
            else:
                parts.append(_ONES[d] + "สิบ")
        elif pos == 0:
            if d == 1 and n >= 10:
                parts.append("เอ็ด")
            else:
                parts.append(_ONES[d])
        else:
            parts.append(_ONES[d] + labels[i])
    return "".join(parts)


def _read_int(n: int) -> str:
    if n == 0:
        return "ศูนย์"
    chunks: list[int] = []
    rest = n
    while rest > 0:
        chunks.append(rest % 1_000_000)
        rest //= 1_000_000
    words: list[str] = []
    for i, chunk in enumerate(reversed(chunks)):
        mill = len(chunks) - 1 - i
        if chunk == 0:
            continue
        words.append(_read_below_million(chunk) + ("ล้าน" * mill))
    return "".join(words)


def baht_text(amount: float | int | Decimal | None) -> str:
    """18454.25 → หนึ่งหมื่นแปดพันสี่ร้อยห้าสิบสี่บาทยี่สิบห้าสตางค์."""
    val = Decimal("0") if amount is None else Decimal(str(amount))
    val = val.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    negative = val < 0
    val = abs(val)
    baht = int(val)
    satang = int((val - Decimal(baht)) * 100)
    if baht == 0 and satang == 0:
        text = "ศูนย์บาทถ้วน"
    elif satang == 0:
        text = _read_int(baht) + "บาทถ้วน"
    elif baht == 0:
        text = _read_below_million(satang) + "สตางค์"
    else:
        text = _read_int(baht) + "บาท" + _read_below_million(satang) + "สตางค์"
    if negative:
        text = "ลบ" + text
    return text

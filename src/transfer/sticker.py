"""5×3.5 cm product barcode stickers for TSC TE310 / TTP-244 Pro (TSPL).

Shop two-up reference (each 50×35 mm sticker):

    19P-1-3                 [======= BARCODE =======]
    SAK                          13010754
    หน่วย ตนถ
    SMA                     OPMXTM2605
    30 มิล เหล็ก
    ตาน้ำถ้วย
    SAK-03010

Left stack is location, brand, ``หน่วย`` + unit, abbreviation, optional
company/model, two-line product name, factory no. Barcode + BCODE sit in
the top-right; price code shares the abbreviation row on the right.
Thai text is rasterized (TSC built-in fonts are ASCII-only) as BITMAP.

TTP-244 Pro and TE310 both print the shop 2-across 50×35 mm roll
(SIZE 102×35 mm). Both invert BITMAP polarity (TSC prints 0-bits) so
labels stay black-on-white.
"""

from __future__ import annotations

import ipaddress
import logging
import math
import socket
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any, Iterable

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

LABEL_WIDTH_MM = 50.0
LABEL_HEIGHT_MM = 35.0
LABEL_GAP_MM = 2.0
# Top-right barcode starts here; left stack (location → name) stays left of it.
BARCODE_LEFT_MM = 21.5
LABEL_PAD_MM = 2.2
BODY_FONT_MM = 2.3
LINE_H_MM = 3.75
NAME_H_MM = 3.9
LOC_FONT_MM = 2.6
ATTR_FONT_MM = 2.4
BARCODE_HEIGHT_MM = 8.0
# Keep รหัสราคา under the human-readable BCODE, never on the bars.
PRICE_BELOW_BARCODE_MM = 3.2
TSPL_BIT0_PRINTS_MARK = "kcw_tspl_bit0_prints"
MAX_QTY_PER_LINE = 200
MAX_COPIES_TOTAL = 1000
PRINTER_PORT = 9100
PRINTER_TIMEOUT_SEC = 8.0

PRINTER_MODELS: dict[str, dict[str, Any]] = {
    # Shop TE310: same 2-across 50×35 mm stock + BITMAP polarity as 244 Pro.
    "te310": {
        "id": "te310",
        "label": "TSC TE310",
        "dpi": 300,
        "dots_mm": 12,
        "columns": 2,
        "invert_bitmap": True,
        "column_gap_mm": 2.0,
    },
    # Shop 244 Pro: 2-across 50×35 mm stock. TSC BITMAP uses 0=printed, so we
    # invert the in-memory 1=black raster or the label comes out white-on-black.
    "ttp244pro": {
        "id": "ttp244pro",
        "label": "TSC 244 Pro",
        "dpi": 203,
        "dots_mm": 8,
        "columns": 2,
        "invert_bitmap": True,
        "column_gap_mm": 2.0,
    },
}

# Shop letter cipher printed on the sticker (ราคาทุน / ราคาขาย).
PRICE_DIGIT_TO_LETTER = {
    "0": "M",
    "1": "P",
    "2": "T",
    "3": "N",
    "4": "L",
    "5": "B",
    "6": "V",
    "7": "S",
    "8": "R",
    "9": "C",
}
PRICE_LETTER_TO_DIGIT = {v: k for k, v in PRICE_DIGIT_TO_LETTER.items()}

# Noto Sans Thai has no Latin glyphs — pair it with Noto/DejaVu for BCODE/prices.
_FONT_THAI_CANDIDATES = (
    Path("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoLoopedThai-Regular.ttf"),
    Path("/usr/share/fonts/truetype/tlwg/Waree.ttf"),
    Path("/usr/share/fonts/truetype/tlwg/Loma.ttf"),
)
_FONT_THAI_BOLD_CANDIDATES = (
    Path("/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"),
    Path("/usr/share/fonts/truetype/noto/NotoLoopedThai-Bold.ttf"),
    Path("/usr/share/fonts/truetype/tlwg/Waree-Bold.ttf"),
)
_FONT_LATIN_CANDIDATES = (
    Path("/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
)
_FONT_LATIN_BOLD_CANDIDATES = (
    Path("/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
    Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
)

# Code 128 patterns: 6 run lengths (bar, space, bar, space, bar, space).
# Index 0–102 = data; 103=Start A, 104=Start B, 105=Start C; Stop is separate.
_CODE128_PATTERNS: tuple[tuple[int, ...], ...] = (
    (2, 1, 2, 2, 2, 2), (2, 2, 2, 1, 2, 2), (2, 2, 2, 2, 2, 1), (1, 2, 1, 2, 2, 3),
    (1, 2, 1, 3, 2, 2), (1, 3, 1, 2, 2, 2), (1, 2, 2, 2, 1, 3), (1, 2, 2, 3, 1, 2),
    (1, 3, 2, 2, 1, 2), (2, 2, 1, 2, 1, 3), (2, 2, 1, 3, 1, 2), (2, 3, 1, 2, 1, 2),
    (1, 1, 2, 2, 3, 2), (1, 2, 2, 1, 3, 2), (1, 2, 2, 2, 3, 1), (1, 1, 3, 2, 2, 2),
    (1, 2, 3, 1, 2, 2), (1, 2, 3, 2, 2, 1), (2, 2, 3, 2, 1, 1), (2, 2, 1, 1, 3, 2),
    (2, 2, 1, 2, 3, 1), (2, 1, 3, 2, 1, 2), (2, 2, 3, 1, 1, 2), (3, 1, 2, 1, 3, 1),
    (3, 1, 1, 2, 2, 2), (3, 2, 1, 1, 2, 2), (3, 2, 1, 2, 2, 1), (3, 1, 2, 2, 1, 2),
    (3, 2, 2, 1, 1, 2), (3, 2, 2, 2, 1, 1), (2, 1, 2, 1, 2, 3), (2, 1, 2, 3, 2, 1),
    (2, 3, 2, 1, 2, 1), (1, 1, 1, 3, 2, 3), (1, 3, 1, 1, 2, 3), (1, 3, 1, 3, 2, 1),
    (1, 1, 2, 3, 1, 3), (1, 3, 2, 1, 1, 3), (1, 3, 2, 3, 1, 1), (2, 1, 1, 3, 1, 3),
    (2, 3, 1, 1, 1, 3), (2, 3, 1, 3, 1, 1), (1, 1, 2, 1, 3, 3), (1, 1, 2, 3, 3, 1),
    (1, 3, 2, 1, 3, 1), (1, 1, 3, 1, 2, 3), (1, 1, 3, 3, 2, 1), (1, 3, 3, 1, 2, 1),
    (3, 1, 3, 1, 2, 1), (2, 1, 1, 3, 3, 1), (2, 3, 1, 1, 3, 1), (2, 1, 3, 1, 1, 3),
    (2, 1, 3, 3, 1, 1), (2, 1, 3, 1, 3, 1), (3, 1, 1, 1, 2, 3), (3, 1, 1, 3, 2, 1),
    (3, 3, 1, 1, 2, 1), (3, 1, 2, 1, 1, 3), (3, 1, 2, 3, 1, 1), (3, 3, 2, 1, 1, 1),
    (3, 1, 4, 1, 1, 1), (2, 2, 1, 4, 1, 1), (4, 3, 1, 1, 1, 1), (1, 1, 1, 2, 2, 4),
    (1, 1, 1, 4, 2, 2), (1, 2, 1, 1, 2, 4), (1, 2, 1, 4, 2, 1), (1, 4, 1, 1, 2, 2),
    (1, 4, 1, 2, 2, 1), (1, 1, 2, 2, 1, 4), (1, 1, 2, 4, 1, 2), (1, 2, 2, 1, 1, 4),
    (1, 2, 2, 4, 1, 1), (1, 4, 2, 1, 1, 2), (1, 4, 2, 2, 1, 1), (2, 4, 1, 2, 1, 1),
    (2, 2, 1, 1, 1, 4), (4, 1, 3, 1, 1, 1), (2, 4, 1, 1, 1, 2), (1, 3, 4, 1, 1, 1),
    (1, 1, 1, 2, 4, 2), (1, 2, 1, 1, 4, 2), (1, 2, 1, 2, 4, 1), (1, 1, 4, 2, 1, 2),
    (1, 2, 4, 1, 1, 2), (1, 2, 4, 2, 1, 1), (4, 1, 1, 2, 1, 2), (4, 2, 1, 1, 1, 2),
    (4, 2, 1, 2, 1, 1), (2, 1, 2, 1, 4, 1), (2, 1, 4, 1, 2, 1), (4, 1, 2, 1, 2, 1),
    (1, 1, 1, 1, 4, 3), (1, 1, 1, 3, 4, 1), (1, 3, 1, 1, 4, 1), (1, 1, 4, 1, 1, 3),
    (1, 1, 4, 3, 1, 1), (4, 1, 1, 1, 1, 3), (4, 1, 1, 3, 1, 1), (1, 1, 3, 1, 4, 1),
    (1, 1, 4, 1, 3, 1), (3, 1, 1, 1, 4, 1), (4, 1, 1, 1, 3, 1), (2, 1, 1, 4, 1, 2),
    (2, 1, 1, 2, 1, 4), (2, 1, 1, 2, 3, 2), (2, 3, 3, 1, 1, 1, 2),
)
_CODE128_START_B = 104
_CODE128_STOP = 106


@dataclass(frozen=True)
class StickerLabel:
    bcode: str
    descr: str = ""
    location: str = ""
    brand: str = ""
    unit: str = ""
    abbreviation: str = ""
    company: str = ""
    model: str = ""
    factory_no: str = ""
    genuine_no: str = ""
    price_code: str = ""
    qty: int = 1

    def as_preview_dict(self) -> dict[str, Any]:
        return {
            "bcode": self.bcode,
            "descr": self.descr,
            "location": self.location,
            "brand": self.brand,
            "unit": self.unit,
            "abbreviation": self.abbreviation,
            "company": self.company,
            "model": self.model,
            "factory_no": self.factory_no,
            "genuine_no": self.genuine_no,
            "price_code": self.price_code,
            "qty": self.qty,
        }


def normalize_printer_model(model: str | None) -> str:
    key = (model or "").strip().lower().replace(" ", "").replace("-", "")
    aliases = {
        "te310": "te310",
        "te300": "te310",
        "tsc te310": "te310",
        "244pro": "ttp244pro",
        "ttp244pro": "ttp244pro",
        "ttp244": "ttp244pro",
        "244": "ttp244pro",
    }
    resolved = aliases.get(key) or aliases.get((model or "").strip().lower())
    if resolved in PRINTER_MODELS:
        return resolved
    return "te310"


def printer_profile(model: str | None) -> dict[str, Any]:
    return PRINTER_MODELS[normalize_printer_model(model)]


def encode_price_digits(value: Any) -> str:
    """Map a baht amount to the shop letter cipher (270 → TSM)."""
    if value is None or value == "":
        return ""
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return ""
    if number < 0 or not math.isfinite(number):
        return ""
    whole = str(int(round(number)))
    return "".join(PRICE_DIGIT_TO_LETTER.get(ch, "") for ch in whole)


def decode_price_letters(coded: str) -> int | None:
    letters = (coded or "").strip().upper()
    if not letters:
        return None
    digits = []
    for ch in letters:
        if ch not in PRICE_LETTER_TO_DIGIT:
            return None
        digits.append(PRICE_LETTER_TO_DIGIT[ch])
    return int("".join(digits))


def format_price_code(*, cost: Any = None, sell: Any = None) -> str:
    """O = ราคาทุน, X = ราคาขาย. Example: cost 270 + sell 420 → OTSMXLTM."""
    cost_code = encode_price_digits(cost)
    sell_code = encode_price_digits(sell)
    parts: list[str] = []
    if cost_code:
        parts.append("O" + cost_code)
    if sell_code:
        parts.append("X" + sell_code)
    return "".join(parts)


def clamp_sticker_qty(qty: Any) -> int:
    try:
        n = int(round(float(qty)))
    except (TypeError, ValueError):
        return 0
    return max(0, min(n, MAX_QTY_PER_LINE))


def format_unit_line(unit: str) -> str:
    """Shop stickers print the unit as ``หน่วย {ui1}``."""
    raw = (unit or "").strip()
    if not raw:
        return ""
    if raw.startswith("หน่วย"):
        return raw
    return f"หน่วย {raw}"


def label_from_icmas(row: dict[str, Any], *, qty: int = 1) -> StickerLabel:
    loc1 = str(row.get("location1") or row.get("LOCATION1") or "").strip()
    loc2 = str(row.get("location2") or row.get("LOCATION2") or "").strip()
    location = loc1 or loc2
    cost = row.get("costnet")
    if cost is None:
        cost = row.get("COSTNET")
    sell = row.get("price1")
    if sell is None:
        sell = row.get("PRICE1")
    return StickerLabel(
        bcode=str(row.get("bcode") or row.get("BCODE") or "").strip(),
        descr=str(row.get("descr") or row.get("DESCR") or "").strip(),
        location=location,
        brand=str(row.get("brand") or row.get("BRAND") or "").strip(),
        unit=str(row.get("unit") or row.get("ui1") or row.get("UI1") or "").strip(),
        abbreviation=str(row.get("abbreviation") or row.get("acode") or row.get("ACODE") or "").strip(),
        company=str(row.get("company") or row.get("vendor") or row.get("VENDOR") or "").strip(),
        model=str(row.get("model") or row.get("MODEL") or "").strip(),
        factory_no=str(row.get("factory_no") or row.get("mcode") or row.get("MCODE") or "").strip(),
        genuine_no=str(row.get("genuine_no") or row.get("pcode") or row.get("PCODE") or "").strip(),
        price_code=str(row.get("price_code") or "").strip()
        or format_price_code(cost=cost, sell=sell),
        qty=clamp_sticker_qty(qty),
    )


def _first_font(candidates: tuple[Path, ...], size: int) -> ImageFont.ImageFont | None:
    for path in candidates:
        if path.is_file():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue
    return None


def _load_font_pair(size: int, *, bold: bool = False) -> tuple[ImageFont.ImageFont, ImageFont.ImageFont]:
    thai = _first_font(_FONT_THAI_BOLD_CANDIDATES if bold else _FONT_THAI_CANDIDATES, size)
    latin = _first_font(_FONT_LATIN_BOLD_CANDIDATES if bold else _FONT_LATIN_CANDIDATES, size)
    fallback = ImageFont.load_default()
    if thai is None:
        thai = latin or fallback
    if latin is None:
        latin = thai or fallback
    return latin, thai


def _is_thai(ch: str) -> bool:
    return "\u0e00" <= ch <= "\u0e7f"


def _script_runs(text: str) -> list[tuple[str, bool]]:
    runs: list[tuple[str, bool]] = []
    for ch in text:
        thai = _is_thai(ch)
        if runs and runs[-1][1] == thai:
            runs[-1] = (runs[-1][0] + ch, thai)
        else:
            runs.append((ch, thai))
    return runs


def _text_length(draw: ImageDraw.ImageDraw, text: str, latin: ImageFont.ImageFont, thai: ImageFont.ImageFont) -> float:
    return sum(
        draw.textlength(chunk, font=thai if is_thai else latin)
        for chunk, is_thai in _script_runs(text)
    )


def _draw_mixed(
    draw: ImageDraw.ImageDraw,
    xy: tuple[float, float],
    text: str,
    latin: ImageFont.ImageFont,
    thai: ImageFont.ImageFont,
) -> None:
    x, y = xy
    for chunk, is_thai in _script_runs(text):
        font = thai if is_thai else latin
        draw.text((x, y), chunk, font=font, fill=0)
        x += draw.textlength(chunk, font=font)


def _mm(dots_mm: int, mm: float) -> int:
    return int(round(mm * dots_mm))


def _draw_code128(draw: ImageDraw.ImageDraw, text: str, box: tuple[int, int, int, int]) -> None:
    """Draw a Code 128B barcode inside (x0, y0, x1, y1)."""
    payload = (text or "").strip()
    if not payload:
        return
    values = [_CODE128_START_B]
    checksum = _CODE128_START_B
    for i, ch in enumerate(payload):
        code = ord(ch)
        if code < 32 or code > 126:
            code = 32
        value = code - 32
        values.append(value)
        checksum += value * (i + 1)
    values.append(checksum % 103)
    modules: list[int] = []
    for value in values:
        modules.extend(_CODE128_PATTERNS[value])
    modules.extend(_CODE128_PATTERNS[_CODE128_STOP])
    x0, y0, x1, y1 = box
    width = max(1, x1 - x0)
    height = max(1, y1 - y0)
    total = sum(modules)
    # Quiet zone ≈ 10 modules each side.
    total_with_quiet = total + 20
    unit = max(1, width // total_with_quiet)
    used = unit * total_with_quiet
    x = x0 + max(0, (width - used) // 2) + unit * 10
    bar = True
    for run in modules:
        w = unit * run
        if bar:
            draw.rectangle([x, y0, x + w - 1, y0 + height - 1], fill=0)
        x += w
        bar = not bar


def _fit_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    latin: ImageFont.ImageFont,
    thai: ImageFont.ImageFont,
    max_width: int,
) -> str:
    raw = (text or "").strip()
    if not raw:
        return ""
    if _text_length(draw, raw, latin, thai) <= max_width:
        return raw
    ellipsis = "…"
    for i in range(len(raw), 0, -1):
        candidate = raw[:i].rstrip() + ellipsis
        if _text_length(draw, candidate, latin, thai) <= max_width:
            return candidate
    return ellipsis


def _wrap_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    latin: ImageFont.ImageFont,
    thai: ImageFont.ImageFont,
    max_width: int,
    max_lines: int = 2,
) -> list[str]:
    raw = (text or "").strip()
    if not raw:
        return []
    words = raw.split()
    if not words:
        return []
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        trial = current + " " + word
        if _text_length(draw, trial, latin, thai) <= max_width:
            current = trial
        else:
            lines.append(current)
            current = word
            if len(lines) == max_lines:
                break
    if len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines:
        lines[-1] = _fit_text(draw, lines[-1], latin, thai, max_width)
    return lines[:max_lines]


def price_text_y(dots_mm: int, abbrev_y: int, barcode_bottom: int) -> int:
    """Price shares the abbreviation row only when that row is below the barcode."""
    return max(abbrev_y, barcode_bottom + _mm(dots_mm, PRICE_BELOW_BARCODE_MM))


def _left_text_width(dots_mm: int) -> int:
    barcode_left = _mm(dots_mm, BARCODE_LEFT_MM)
    pad = _mm(dots_mm, LABEL_PAD_MM)
    return barcode_left - _mm(dots_mm, 0.6) - pad


def sticker_name_lines(descr: str, *, printer_model: str = "te310") -> list[str]:
    """Wrap the product name the same way the shop sticker does (left column, 2 lines)."""
    profile = printer_profile(printer_model)
    dots_mm = int(profile["dots_mm"])
    probe = Image.new("1", (8, 8), 1)
    draw = ImageDraw.Draw(probe)
    latin, thai = _load_font_pair(max(11, _mm(dots_mm, BODY_FONT_MM)))
    return _wrap_text(draw, descr, latin, thai, _left_text_width(dots_mm), max_lines=2)


def render_label_image(label: StickerLabel, *, printer_model: str = "te310") -> Image.Image:
    """Rasterize one 50×35 mm sticker at the printer's native DPI."""
    profile = printer_profile(printer_model)
    dots_mm = int(profile["dots_mm"])
    width = _mm(dots_mm, LABEL_WIDTH_MM)
    height = _mm(dots_mm, LABEL_HEIGHT_MM)
    img = Image.new("1", (width, height), 1)
    draw = ImageDraw.Draw(img)

    pad = _mm(dots_mm, LABEL_PAD_MM)
    barcode_left = _mm(dots_mm, BARCODE_LEFT_MM)
    left_w = barcode_left - _mm(dots_mm, 0.8)
    line_h = _mm(dots_mm, LINE_H_MM)
    name_h = _mm(dots_mm, NAME_H_MM)
    latin_loc, thai_loc = _load_font_pair(max(13, _mm(dots_mm, LOC_FONT_MM)), bold=True)
    latin_attr, thai_attr = _load_font_pair(max(12, _mm(dots_mm, ATTR_FONT_MM)), bold=True)
    latin_body, thai_body = _load_font_pair(max(11, _mm(dots_mm, BODY_FONT_MM)))
    latin_bcode, thai_bcode = _load_font_pair(max(12, _mm(dots_mm, 2.5)), bold=True)
    latin_price, thai_price = _load_font_pair(max(11, _mm(dots_mm, 2.2)))
    latin_foot, thai_foot = _load_font_pair(max(12, _mm(dots_mm, ATTR_FONT_MM)), bold=True)

    barcode_top = pad
    barcode_bottom = pad + _mm(dots_mm, BARCODE_HEIGHT_MM)
    barcode_right = width - pad
    _draw_code128(draw, label.bcode, (barcode_left, barcode_top, barcode_right, barcode_bottom))

    bcode = _fit_text(draw, label.bcode, latin_bcode, thai_bcode, barcode_right - barcode_left)
    if bcode:
        bw = _text_length(draw, bcode, latin_bcode, thai_bcode)
        bx = barcode_left + max(0, (barcode_right - barcode_left - bw) / 2)
        _draw_mixed(
            draw,
            (bx, barcode_bottom + _mm(dots_mm, 0.15)),
            bcode,
            latin_bcode,
            thai_bcode,
        )

    y = pad
    loc = _fit_text(draw, label.location, latin_loc, thai_loc, left_w - pad)
    if loc:
        _draw_mixed(draw, (pad, y), loc, latin_loc, thai_loc)
        y += line_h

    brand = _fit_text(draw, label.brand, latin_attr, thai_attr, left_w - pad)
    if brand:
        _draw_mixed(draw, (pad, y), brand, latin_attr, thai_attr)
        y += line_h

    unit = _fit_text(draw, format_unit_line(label.unit), latin_body, thai_body, left_w - pad)
    if unit:
        _draw_mixed(draw, (pad, y), unit, latin_body, thai_body)
        y += line_h

    abbrev = _fit_text(draw, label.abbreviation, latin_attr, thai_attr, left_w - pad)
    price = _fit_text(draw, label.price_code, latin_price, thai_price, barcode_right - barcode_left)
    abbrev_y = y
    if abbrev:
        _draw_mixed(draw, (pad, abbrev_y), abbrev, latin_attr, thai_attr)
        y += line_h
    if price:
        py = price_text_y(dots_mm, abbrev_y, barcode_bottom)
        _draw_mixed(draw, (barcode_left, py), price, latin_price, thai_price)

    for extra in (label.company, label.model):
        text = _fit_text(draw, extra, latin_attr, thai_attr, left_w - pad)
        if text:
            _draw_mixed(draw, (pad, y), text, latin_attr, thai_attr)
            y += line_h

    foot_y = height - pad - _mm(dots_mm, 3.2)
    # Keep the name in the left column so long Thai titles wrap like the shop print
    # ("30 มิล เหล็ก" / "ตาน้ำถ้วย"), not one wide line under the barcode.
    name_lines = sticker_name_lines(label.descr, printer_model=printer_model)
    for line in name_lines:
        if y + name_h > foot_y - _mm(dots_mm, 0.4):
            break
        _draw_mixed(draw, (pad, y), line, latin_body, thai_body)
        y += name_h

    factory = _fit_text(draw, label.factory_no, latin_foot, thai_foot, width - pad * 2)
    if factory:
        _draw_mixed(draw, (pad, foot_y), factory, latin_foot, thai_foot)
    genuine = _fit_text(draw, label.genuine_no, latin_body, thai_body, _mm(dots_mm, 22.0))
    if genuine:
        gw = _text_length(draw, genuine, latin_body, thai_body)
        _draw_mixed(draw, (width - pad - gw, foot_y), genuine, latin_body, thai_body)

    return img


def render_label_png(label: StickerLabel, *, printer_model: str = "te310") -> bytes:
    img = render_label_image(label, printer_model=printer_model)
    # Scale preview to a crisp 4× logical size so the 5×3.5 cm card is readable.
    preview = img.convert("L").resize(
        (img.width * 2, img.height * 2),
        Image.Resampling.NEAREST,
    )
    buf = BytesIO()
    preview.save(buf, format="PNG")
    return buf.getvalue()


def _image_to_bitmap_bytes(img: Image.Image, *, invert: bool = False) -> tuple[int, int, bytes]:
    mono = img.convert("1")
    width, height = mono.size
    width_bytes = (width + 7) // 8
    pixels = mono.load()
    out = bytearray(width_bytes * height)
    i = 0
    for y in range(height):
        for xb in range(width_bytes):
            byte = 0
            for bit in range(8):
                x = xb * 8 + bit
                if x < width and pixels[x, y] == 0:
                    byte |= 0x80 >> bit
            out[i] = byte
            i += 1
    if invert:
        out = bytearray(b ^ 0xFF for b in out)
    return width_bytes, height, bytes(out)


def page_width_mm(profile: dict[str, Any]) -> float:
    columns = max(1, int(profile.get("columns") or 1))
    gap = float(profile.get("column_gap_mm") or 0)
    if columns <= 1:
        return LABEL_WIDTH_MM
    return LABEL_WIDTH_MM * columns + gap * (columns - 1)


def _compose_row_images(
    label_imgs: list[Image.Image],
    *,
    columns: int,
    dots_mm: int,
    column_gap_mm: float,
) -> Image.Image:
    if not label_imgs:
        raise ValueError("no stickers to compose")
    label_w, label_h = label_imgs[0].size
    gap = _mm(dots_mm, column_gap_mm) if columns > 1 else 0
    page_w = label_w * max(1, columns) + gap * max(0, columns - 1)
    page = Image.new("1", (page_w, label_h), 1)
    for i, img in enumerate(label_imgs[:columns]):
        if img.size != (label_w, label_h):
            img = img.resize((label_w, label_h), Image.Resampling.NEAREST)
        page.paste(img, (i * (label_w + gap), 0))
    return page


def _tspl_page(img: Image.Image, *, width_mm: float, copies: int, invert: bool) -> bytes:
    width_bytes, height, bitmap = _image_to_bitmap_bytes(img, invert=invert)
    polarity = f"REM {TSPL_BIT0_PRINTS_MARK}\r\n" if invert else ""
    header = (
        f"SIZE {width_mm:g} mm,{LABEL_HEIGHT_MM:g} mm\r\n"
        f"GAP {LABEL_GAP_MM:g} mm,0 mm\r\n"
        f"{polarity}"
        "DENSITY 10\r\n"
        "DIRECTION 0\r\n"
        "REFERENCE 0,0\r\n"
        "CLS\r\n"
        f"BITMAP 0,0,{width_bytes},{height},0,"
    ).encode("ascii")
    footer = f"\r\nPRINT 1,{max(1, copies)}\r\n".encode("ascii")
    return header + bitmap + footer


def build_label_tspl(label: StickerLabel, *, printer_model: str = "te310") -> bytes:
    """TSPL for one SKU. PRINT copies = received qty (one sticker per unit)."""
    return build_batch_tspl([label], printer_model=printer_model)


def build_batch_tspl(labels: Iterable[StickerLabel], *, printer_model: str = "te310") -> bytes:
    """Pack copies onto the printer's columns so two qty=1 SKUs share one row."""
    profile = printer_profile(printer_model)
    columns = max(1, int(profile.get("columns") or 1))
    invert = bool(profile.get("invert_bitmap"))
    dots_mm = int(profile["dots_mm"])
    width_mm = page_width_mm(profile)
    gap_mm = float(profile.get("column_gap_mm") or 0)

    tiles: list[Image.Image] = []
    for label in labels:
        if not label.bcode:
            continue
        copies = max(1, clamp_sticker_qty(label.qty) or 1)
        img = render_label_image(label, printer_model=printer_model)
        tiles.extend([img] * copies)
    if not tiles:
        return b""

    if columns <= 1:
        return b"".join(_tspl_page(img, width_mm=width_mm, copies=1, invert=invert) for img in tiles)

    chunks: list[bytes] = []
    for i in range(0, len(tiles), columns):
        row = _compose_row_images(
            tiles[i : i + columns],
            columns=columns,
            dots_mm=dots_mm,
            column_gap_mm=gap_mm,
        )
        chunks.append(_tspl_page(row, width_mm=width_mm, copies=1, invert=invert))
    return b"".join(chunks)


def count_copies(labels: Iterable[StickerLabel]) -> int:
    return sum(max(0, int(label.qty or 0)) for label in labels)


def is_lan_printer_host(host: str) -> bool:
    """Allow only loopback / RFC1918 / Tailscale CGNAT — no open-internet SSRF."""
    raw = (host or "").strip()
    if not raw or raw.startswith("[") or "%" in raw:
        return False
    if raw.lower() in {"localhost"}:
        return True
    try:
        ip = ipaddress.ip_address(raw)
    except ValueError:
        # Hostnames: only simple LAN-ish names (no dots required, no scheme).
        if "/" in raw or ":" in raw or " " in raw:
            return False
        return raw.replace("-", "").replace(".", "").isalnum() and len(raw) <= 64
    return bool(
        ip.is_loopback
        or ip.is_private
        or ip.is_link_local
        or (isinstance(ip, ipaddress.IPv4Address) and ip in ipaddress.ip_network("100.64.0.0/10"))
    )


def send_tspl(
    payload: bytes,
    *,
    host: str,
    port: int = PRINTER_PORT,
    timeout: float = PRINTER_TIMEOUT_SEC,
) -> None:
    if not payload:
        raise ValueError("empty TSPL payload")
    if not is_lan_printer_host(host):
        raise ValueError("printer host must be a LAN / Tailscale address")
    with socket.create_connection((host, int(port)), timeout=timeout) as sock:
        sock.settimeout(timeout)
        sock.sendall(payload)


def resolve_sticker_labels(
    lines: Iterable[dict[str, Any]],
    catalog: dict[str, dict[str, Any]] | None = None,
) -> list[StickerLabel]:
    """Merge receive lines (bcode + qty) with ICMAS catalog rows."""
    catalog = catalog or {}
    merged: dict[str, dict[str, Any]] = {}
    for raw in lines:
        bcode = str(raw.get("bcode") or "").strip()
        if not bcode:
            continue
        qty = clamp_sticker_qty(raw.get("qty") if raw.get("qty") is not None else raw.get("qty_receive"))
        if qty <= 0:
            continue
        if bcode in merged:
            merged[bcode]["qty"] = clamp_sticker_qty(merged[bcode]["qty"] + qty)
            continue
        merged[bcode] = {
            "bcode": bcode,
            "qty": qty,
            "descr": raw.get("descr") or "",
            "model": raw.get("model") or "",
        }
    out: list[StickerLabel] = []
    for bcode, raw in merged.items():
        row = dict(catalog.get(bcode) or {})
        row.setdefault("bcode", bcode)
        if raw.get("descr") and not row.get("descr"):
            row["descr"] = raw.get("descr")
        if raw.get("model") and not row.get("model"):
            row["model"] = raw.get("model")
        out.append(label_from_icmas(row, qty=int(raw["qty"])))
    return out


def validate_batch(labels: list[StickerLabel]) -> str | None:
    if not labels:
        return "ไม่มีรายการที่เลือกพิมพ์"
    copies = count_copies(labels)
    if copies <= 0:
        return "ระบุจำนวนดวงอย่างน้อย 1"
    if copies > MAX_COPIES_TOTAL:
        return f"พิมพ์ได้สูงสุด {MAX_COPIES_TOTAL} ดวงต่อครั้ง"
    return None


def sticker_config_payload(*, model: str = "te310", host: str = "") -> dict[str, Any]:
    resolved = normalize_printer_model(model)
    return {
        "printers": [
            {
                "id": p["id"],
                "label": p["label"],
                "dpi": p["dpi"],
                "dots_mm": p["dots_mm"],
                "columns": int(p.get("columns") or 1),
                "invert_bitmap": bool(p.get("invert_bitmap")),
            }
            for p in PRINTER_MODELS.values()
        ],
        "default_model": resolved,
        "default_host": (host or "").strip(),
        "label_width_mm": LABEL_WIDTH_MM,
        "label_height_mm": LABEL_HEIGHT_MM,
        "max_qty_per_line": MAX_QTY_PER_LINE,
        "max_copies_total": MAX_COPIES_TOTAL,
    }

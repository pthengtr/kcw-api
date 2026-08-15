#!/usr/bin/env python3
"""Generate a simple/minimal KCW LINE rich-menu PNG (2500x843, half-height, 3 taps).

Visual language mirrors the v2 shop tools (companion + PARTS9 explorer):
dark canvas, Prompt type, one icon + one label per column — no cards/header clutter.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rich_menu.png"
FONTS = ROOT / "fonts"

W, H = 2500, 843

# Match parts9 explorer / companion dark theme
BG = (12, 16, 20)  # #0c1014
LINE = (42, 53, 66)  # #2a3542
TEXT = (236, 241, 246)
MUTED = (122, 138, 154)

STOCK = (230, 180, 80)  # explorer --warn
PAY = (47, 158, 123)  # companion --accent #2f9e7b
SEARCH = (61, 156, 240)  # explorer --acc #3d9cf0

CELLS = [
    {"title": "เช็คสต็อก", "accent": STOCK, "icon": "boxes", "tint": (28, 24, 14)},
    {"title": "ไทเกอร์เพย์", "accent": PAY, "icon": "pay", "tint": (14, 28, 24)},
    {"title": "สำรวจสินค้า", "accent": SEARCH, "icon": "search", "tint": (14, 22, 32)},
]


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    if path.is_file():
        return ImageFont.truetype(str(path), size=size)
    # Fallbacks if fonts/ is missing locally
    for fallback in (
        "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(fallback).is_file():
            return ImageFont.truetype(fallback, size=size)
    return ImageFont.load_default()


def _blend(base: tuple[int, int, int], overlay: tuple[int, int, int], alpha: float) -> tuple[int, int, int]:
    return tuple(int(b * (1 - alpha) + o * alpha) for b, o in zip(base, overlay))


def _center_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, int, int],
) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x - tw // 2 - bbox[0], y - th // 2 - bbox[1]), text, font=font, fill=fill)


def _draw_boxes_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    # Two simple stacked crates
    w, h = 78, 58
    draw.rounded_rectangle([cx - 52, cy - 8, cx + 26, cy + h - 8], radius=8, outline=color, width=5)
    draw.rounded_rectangle([cx - 26, cy - 36, cx + 52, cy + 22], radius=8, outline=color, width=5)
    draw.line([(cx - 26, cy - 6), (cx + 52, cy - 6)], fill=color, width=4)


def _draw_pay_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    # Minimal payment card
    draw.rounded_rectangle([cx - 72, cy - 48, cx + 72, cy + 48], radius=14, outline=color, width=5)
    draw.line([(cx - 72, cy - 18), (cx + 72, cy - 18)], fill=color, width=5)
    draw.rounded_rectangle([cx - 40, cy + 10, cx - 4, cy + 28], radius=4, fill=color)


def _draw_search_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    r = 42
    draw.ellipse([cx - r - 10, cy - r - 6, cx + r - 10, cy + r - 6], outline=color, width=5)
    draw.line([(cx + 24, cy + 24), (cx + 56, cy + 56)], fill=color, width=6)


def generate() -> Path:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    widths = [833, 834, 833]
    title_font = _font("Prompt-SemiBold.ttf", 70)
    x = 0

    for i, (cell, cw) in enumerate(zip(CELLS, widths)):
        # Soft column wash (no inset cards)
        fill = _blend(BG, cell["tint"], 0.55)
        draw.rectangle([x, 0, x + cw, H], fill=fill)

        # Thin vertical divider
        if i > 0:
            draw.line([(x, 56), (x, H - 56)], fill=LINE, width=2)

        cx = x + cw // 2
        # Keep icon + label as one centered cluster
        icon_y = 340
        title_y = 510

        # Small accent tick just above the icon
        tick_w = 40
        draw.rounded_rectangle(
            [cx - tick_w // 2, icon_y - 118, cx + tick_w // 2, icon_y - 110],
            radius=3,
            fill=cell["accent"],
        )

        if cell["icon"] == "boxes":
            _draw_boxes_icon(draw, cx, icon_y, cell["accent"])
        elif cell["icon"] == "pay":
            _draw_pay_icon(draw, cx, icon_y, cell["accent"])
        else:
            _draw_search_icon(draw, cx, icon_y, cell["accent"])

        _center_text(draw, (cx, title_y), cell["title"], title_font, TEXT)

        x += cw

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    size_kb = OUT.stat().st_size / 1024
    if size_kb > 1024:
        raise SystemExit(f"Image too large for LINE rich menu: {size_kb:.0f} KB (max 1 MB)")
    print(f"Wrote {OUT} ({size_kb:.1f} KB)")
    return OUT


if __name__ == "__main__":
    generate()

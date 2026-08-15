#!/usr/bin/env python3
"""Generate the KCW LINE rich-menu PNG (2500x843, half-height, 3 taps)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rich_menu.png"

W, H = 2500, 843
# Auto-parts workshop palette (steel + amber safety accent — not purple/cream AI defaults)
BG = (18, 28, 38)
PANEL = (28, 42, 56)
PANEL_ALT = (34, 52, 68)
LINE = (55, 78, 98)
AMBER = (232, 156, 48)
AMBER_DIM = (180, 118, 36)
TEXT = (245, 247, 250)
MUTED = (160, 176, 192)

THAI_BOLD = "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf"
THAI_REG = "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf"
LATIN_BOLD = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
LATIN_REG = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"

CELLS = [
    {
        "title": "เช็คสต็อก",
        "sub": "HQ  SYP",
        "sub_script": "latin",
        "hint": "ตรวจนับบนไวไฟสาขา",
        "accent": AMBER,
        "icon": "boxes",
    },
    {
        "title": "ไทเกอร์เพย์",
        "sub": "เก็บเงิน",
        "sub_script": "thai",
        "hint": "เปิดบิลเก็บเงิน",
        "accent": (72, 180, 140),
        "icon": "pay",
    },
    {
        "title": "สำรวจสินค้า",
        "sub": "PARTS9",
        "sub_script": "latin",
        "hint": "ค้นหาและสำรวจแคตตาล็อก",
        "accent": (88, 156, 220),
        "icon": "search",
    },
]


def _font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size=size)


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
    draw.text((x - tw // 2, y - th // 2), text, font=font, fill=fill)


def _draw_boxes_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    s = 54
    # back box
    draw.rectangle([cx - s, cy - s + 10, cx + 10, cy + 18], outline=color, width=5)
    # front box
    draw.rectangle([cx - 10, cy - 18, cx + s, cy + s - 10], outline=color, width=5)
    draw.line([(cx - 10, cy), (cx + s, cy)], fill=color, width=4)


def _draw_pay_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    r = 58
    draw.rounded_rectangle([cx - r, cy - int(r * 0.72), cx + r, cy + int(r * 0.72)], radius=14, outline=color, width=5)
    draw.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline=color, width=5)
    draw.line([(cx, cy - 34), (cx, cy + 34)], fill=color, width=4)


def _draw_search_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color: tuple[int, int, int]) -> None:
    r = 38
    draw.ellipse([cx - r - 8, cy - r - 4, cx + r - 8, cy + r - 4], outline=color, width=5)
    draw.line([(cx + 22, cy + 22), (cx + 52, cy + 52)], fill=color, width=6)


def generate() -> Path:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # subtle top brand bar
    draw.rectangle([0, 0, W, 10], fill=AMBER)
    brand_font = _font(LATIN_BOLD, 36)
    brand_th = _font(THAI_REG, 28)
    _center_text(draw, (W // 2, 48), "KCW", brand_font, AMBER)
    _center_text(draw, (W // 2, 88), "เครื่องมือประจำวัน", brand_th, MUTED)

    widths = [833, 834, 833]
    x = 0
    title_font = _font(THAI_BOLD, 72)
    sub_latin = _font(LATIN_BOLD, 34)
    sub_thai = _font(THAI_BOLD, 36)
    hint_font = _font(THAI_REG, 30)

    for i, (cell, cw) in enumerate(zip(CELLS, widths)):
        panel = PANEL if i % 2 == 0 else PANEL_ALT
        # inset panel
        pad = 28
        draw.rounded_rectangle(
            [x + pad, 120, x + cw - pad, H - 36],
            radius=28,
            fill=panel,
            outline=LINE,
            width=3,
        )
        # left accent stripe
        draw.rounded_rectangle(
            [x + pad, 120, x + pad + 14, H - 36],
            radius=8,
            fill=cell["accent"],
        )

        cx = x + cw // 2
        icon_y = 250
        if cell["icon"] == "boxes":
            _draw_boxes_icon(draw, cx, icon_y, cell["accent"])
        elif cell["icon"] == "pay":
            _draw_pay_icon(draw, cx, icon_y, cell["accent"])
        else:
            _draw_search_icon(draw, cx, icon_y, cell["accent"])

        sub_font = sub_thai if cell["sub_script"] == "thai" else sub_latin
        _center_text(draw, (cx, 400), cell["title"], title_font, TEXT)
        _center_text(draw, (cx, 490), cell["sub"], sub_font, cell["accent"])
        _center_text(draw, (cx, 570), cell["hint"], hint_font, MUTED)

        # divider between cells (except last)
        if i < 2:
            draw.line([(x + cw, 140), (x + cw, H - 50)], fill=LINE, width=2)

        x += cw

    # bottom chat-bar cue strip
    draw.rectangle([0, H - 8, W, H], fill=AMBER_DIM)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(OUT, format="PNG", optimize=True)
    size_kb = OUT.stat().st_size / 1024
    if size_kb > 1024:
        raise SystemExit(f"Image too large for LINE rich menu: {size_kb:.0f} KB (max 1 MB)")
    print(f"Wrote {OUT} ({size_kb:.1f} KB)")
    return OUT


if __name__ == "__main__":
    generate()

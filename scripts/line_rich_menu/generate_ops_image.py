#!/usr/bin/env python3
"""Generate admin-only LINE rich-menu PNG for live ใบสั่งซื้อ (2500x843)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rich_menu_ops.png"
FONTS = ROOT / "fonts"

W, H = 2500, 843
BG = (12, 16, 20)
LINE = (42, 53, 66)
TEXT = (236, 241, 246)
ACCENT = (154, 215, 181)


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    if path.is_file():
        return ImageFont.truetype(str(path), size=size)
    for fallback in (
        "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        if Path(fallback).is_file():
            return ImageFont.truetype(fallback, size=size)
    return ImageFont.load_default()


def main() -> None:
    img = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)
    title = _font("Prompt-SemiBold.ttf", 92)
    sub = _font("Prompt-Regular.ttf", 40)
    label = "ใบสั่งซื้อ"
    hint = "ข้อมูลสดจาก PARTS9"
    bbox = draw.textbbox((0, 0), label, font=title)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.rounded_rectangle((80, 80, W - 80, H - 80), radius=36, outline=LINE, width=4)
    draw.ellipse((180, 300, 280, 400), outline=ACCENT, width=8)
    draw.text(((W - tw) / 2, (H - th) / 2 - 30), label, font=title, fill=TEXT)
    sb = draw.textbbox((0, 0), hint, font=sub)
    sw = sb[2] - sb[0]
    draw.text(((W - sw) / 2, (H - th) / 2 + 80), hint, font=sub, fill=ACCENT)
    img.save(OUT, "PNG", optimize=True)
    size_kb = OUT.stat().st_size / 1024
    if size_kb > 1024:
        raise SystemExit(f"Image too large for LINE rich menu: {size_kb:.0f} KB")
    print(f"Wrote {OUT} ({size_kb:.1f} KB)")


if __name__ == "__main__":
    main()

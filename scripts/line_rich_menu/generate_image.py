#!/usr/bin/env python3
"""Generate the KCW LINE rich-menu PNG (2500x1686, full-height, 3x2 taps).

Visual: light ice-blue canvas, equal white-blue cards, royal-blue icons,
navy titles. No footer bar — LINE shows chatBarText on its own menu tab.
Actions live in menu_spec.json — this file only paints the image.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "rich_menu.png"
FONTS = ROOT / "fonts"

W, H = 2500, 1686
SCALE = 2
SW, SH = W * SCALE, H * SCALE

BG = (243, 248, 255)  # #F3F8FF
CARD = (252, 254, 255)  # ขาวอมฟ้า
CARD_LINE = (214, 226, 246)
NAVY = (10, 31, 58)
ROYAL = (65, 105, 225)  # #4169E1
DEEP = (12, 28, 84)
SUB = (122, 143, 179)

COL_WIDTHS = [833, 834, 833]
# Column gap is 2 * OUTER (40px pad on each cell). Bottom row extends to the
# canvas edge — LINE draws its own chat-bar tab (chatBarText) below the image.
GAP = 80
OUTER = 40
# Top row height unchanged so menu_spec.json tap split (y=749) still lines up.
ROW0_CARD_H = (H - 148 - OUTER - GAP * 2) // 2  # 669 — legacy footer slot reclaimed by row 2
ROW0_Y = OUTER
ROW1_Y = OUTER + ROW0_CARD_H + GAP
ROW1_CARD_H = H - ROW1_Y  # 897 — fills former footer + bottom gap
TAP_SPLIT_Y = ROW0_Y + ROW0_CARD_H + GAP // 2  # 749 — matches menu_spec.json

CELLS = [
    {"title": "เช็คสต็อก", "sub": "", "icon": "boxes"},
    {"title": "Tiger Pay", "sub": "เก็บเงิน", "icon": "pay"},
    {"title": "ค้นหา", "sub": "", "icon": "search"},
    {"title": "PO โอนสินค้า", "sub": "", "icon": "po"},
    {"title": "จัดการรูปสินค้า", "sub": "", "icon": "image"},
    {"title": "วิธีใช้ Bot", "sub": "", "icon": "help"},
]


def _px(n: float) -> int:
    return int(round(n * SCALE))


def _font(name: str, size: int) -> ImageFont.FreeTypeFont:
    path = FONTS / name
    candidates = [path] if path.is_file() else []
    candidates.extend(
        Path(p)
        for p in (
            "/usr/share/fonts/truetype/noto/NotoSansThai-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf",
            "/usr/share/fonts/truetype/noto/NotoLoopedThai-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoLoopedThai-Regular.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        )
    )
    for cand in candidates:
        if cand.is_file():
            return ImageFont.truetype(str(cand), size=size)
    return ImageFont.load_default()


def _center_text(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    fill: tuple[int, ...],
) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((x - tw // 2 - bbox[0], y - th // 2 - bbox[1]), text, font=font, fill=fill)


def _card_layer(size: tuple[int, int], radius: int) -> tuple[Image.Image, int]:
    w, h = size
    pad = _px(28)
    layer = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        [pad, pad + _px(8), pad + w, pad + h + _px(12)],
        radius=radius,
        fill=(27, 54, 93, 36),
    )
    layer = layer.filter(ImageFilter.GaussianBlur(_px(10)))
    d = ImageDraw.Draw(layer)
    d.rounded_rectangle(
        [pad, pad, pad + w, pad + h],
        radius=radius,
        fill=(*CARD, 255),
        outline=(*CARD_LINE, 255),
        width=max(_px(1.5), 2),
    )
    return layer, pad


def _stroke() -> int:
    return max(_px(6.5), 8)


def _draw_boxes_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color) -> None:
    sw = _stroke()
    draw.rounded_rectangle(
        [cx - _px(54), cy - _px(4), cx + _px(28), cy + _px(54)],
        radius=_px(10),
        outline=color,
        width=sw,
    )
    draw.rounded_rectangle(
        [cx - _px(28), cy - _px(40), cx + _px(54), cy + _px(22)],
        radius=_px(10),
        outline=color,
        width=sw,
    )
    draw.line([(cx - _px(28), cy - _px(8)), (cx + _px(54), cy - _px(8))], fill=color, width=_px(5))


def _draw_pay_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color) -> None:
    sw = _stroke()
    draw.rounded_rectangle(
        [cx - _px(72), cy - _px(48), cx + _px(72), cy + _px(48)],
        radius=_px(14),
        outline=color,
        width=sw,
    )
    draw.line([(cx - _px(72), cy - _px(16)), (cx + _px(72), cy - _px(16))], fill=color, width=sw)
    draw.rounded_rectangle(
        [cx - _px(48), cy + _px(10), cx - _px(8), cy + _px(28)],
        radius=_px(4),
        fill=color,
    )
    draw.rounded_rectangle(
        [cx + _px(18), cy + _px(14), cx + _px(48), cy + _px(24)],
        radius=_px(3),
        fill=color,
    )


def _draw_search_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color) -> None:
    sw = _stroke()
    r = _px(40)
    ox, oy = _px(10), _px(8)
    draw.ellipse([cx - r - ox, cy - r - oy, cx + r - ox, cy + r - oy], outline=color, width=sw)
    draw.line(
        [(cx + _px(22), cy + _px(22)), (cx + _px(56), cy + _px(56))],
        fill=color,
        width=_px(8),
    )


def _draw_po_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color) -> None:
    sw = _stroke()
    draw.rounded_rectangle(
        [cx - _px(44), cy - _px(50), cx + _px(44), cy + _px(54)],
        radius=_px(10),
        outline=color,
        width=sw,
    )
    draw.rounded_rectangle(
        [cx - _px(22), cy - _px(64), cx + _px(22), cy - _px(36)],
        radius=_px(8),
        outline=color,
        width=sw,
    )
    for i, y in enumerate((-8, 12, 32)):
        w = _px(48 if i < 2 else 28)
        draw.line([(cx - _px(24), cy + _px(y)), (cx - _px(24) + w, cy + _px(y))], fill=color, width=_px(6))
    ay = cy + _px(72)
    draw.line([(cx - _px(38), ay), (cx + _px(38), ay)], fill=color, width=_px(6))
    draw.polygon(
        [(cx + _px(24), ay - _px(12)), (cx + _px(46), ay), (cx + _px(24), ay + _px(12))],
        fill=color,
    )
    draw.polygon(
        [(cx - _px(24), ay - _px(12)), (cx - _px(46), ay), (cx - _px(24), ay + _px(12))],
        fill=color,
    )


def _draw_image_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color) -> None:
    sw = _stroke()
    draw.rounded_rectangle(
        [cx - _px(64), cy - _px(50), cx + _px(64), cy + _px(50)],
        radius=_px(14),
        outline=color,
        width=sw,
    )
    draw.ellipse(
        [cx + _px(18), cy - _px(34), cx + _px(46), cy - _px(6)],
        outline=color,
        width=_px(6),
    )
    draw.polygon(
        [
            (cx - _px(50), cy + _px(36)),
            (cx - _px(14), cy - _px(8)),
            (cx + _px(10), cy + _px(16)),
            (cx + _px(28), cy + _px(2)),
            (cx + _px(50), cy + _px(36)),
        ],
        outline=color,
        width=_px(6),
    )


def _draw_sales_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color) -> None:
    sw = _stroke()
    base = cy + _px(48)
    draw.line([(cx - _px(56), base), (cx + _px(56), base)], fill=color, width=sw)
    bars = [(_px(22), _px(36)), (_px(22), _px(4)), (_px(22), _px(20))]
    x = cx - _px(44)
    for _w, top in bars:
        draw.rounded_rectangle(
            [x, cy - _px(40) + top, x + _px(22), base - _px(6)],
            radius=_px(6),
            outline=color,
            width=sw,
        )
        x += _px(36)


def _draw_help_icon(draw: ImageDraw.ImageDraw, cx: int, cy: int, color) -> None:
    """Closed guidebook + question mark."""
    sw = _stroke()
    bx0, by0, bx1, by1 = cx - _px(52), cy - _px(40), cx + _px(28), cy + _px(52)
    draw.rounded_rectangle([bx0, by0, bx1, by1], radius=_px(8), outline=color, width=sw)
    draw.line([(bx0 + _px(16), by0 + _px(4)), (bx0 + _px(16), by1 - _px(4))], fill=color, width=_px(6))
    for y in (cy - _px(16), cy, cy + _px(16)):
        draw.line([(bx0 + _px(28), y), (bx1 - _px(14), y)], fill=color, width=_px(5))
    qx, qy = cx + _px(46), cy - _px(28)
    draw.ellipse([qx - _px(28), qy - _px(28), qx + _px(28), qy + _px(28)], outline=color, width=sw)
    qfont = _font("Prompt-SemiBold.ttf", _px(36))
    _center_text(draw, (qx, qy - _px(2)), "?", qfont, color)


def _draw_icon(draw: ImageDraw.ImageDraw, name: str, cx: int, cy: int) -> None:
    if name == "boxes":
        _draw_boxes_icon(draw, cx, cy, ROYAL)
    elif name == "pay":
        _draw_pay_icon(draw, cx, cy, ROYAL)
    elif name == "search":
        _draw_search_icon(draw, cx, cy, ROYAL)
    elif name == "po":
        _draw_po_icon(draw, cx, cy, ROYAL)
    elif name == "image":
        _draw_image_icon(draw, cx, cy, ROYAL)
    elif name == "sales":
        _draw_sales_icon(draw, cx, cy, ROYAL)
    else:
        _draw_help_icon(draw, cx, cy, ROYAL)


def generate(*, cells: list[dict] | None = None, out: Path | None = None) -> Path:
    cell_list = cells or CELLS
    dest = out or OUT
    if ROW1_Y + ROW1_CARD_H != H:
        raise SystemExit("Bottom row must extend to the canvas edge")
    if GAP != OUTER * 2:
        raise SystemExit("Row gap must match the visible column gap (2 * OUTER)")

    img = Image.new("RGBA", (SW, SH), (*BG, 255))

    pad_x = _px(OUTER)
    radius = _px(36)  # ~16px on a phone-width LINE surface
    title_max_w = min(_px(w) for w in COL_WIDTHS) - pad_x * 2 - _px(56)
    row_specs = [
        (_px(ROW0_Y), _px(ROW0_CARD_H)),
        (_px(ROW1_Y), _px(ROW1_CARD_H)),
    ]

    def _fit_font(name: str, texts: list[str], max_w: int, max_size: int, min_size: int):
        dummy = ImageDraw.Draw(Image.new("RGB", (8, 8)))
        for size in range(max_size, min_size - 1, -1):
            font = _font(name, size)
            if all(
                dummy.textbbox((0, 0), t, font=font)[2]
                - dummy.textbbox((0, 0), t, font=font)[0]
                <= max_w
                for t in texts
            ):
                return font, size
        return _font(name, min_size), min_size

    title_font, title_size = _fit_font(
        "Prompt-SemiBold.ttf",
        [c["title"] for c in cell_list],
        title_max_w,
        _px(112),
        _px(80),
    )
    print(
        f"Title font {title_size // SCALE}px · row0 {ROW0_CARD_H}px · "
        f"row1 {ROW1_CARD_H}px · gap {GAP}px (row=col)"
    )
    noto_regular = Path("/usr/share/fonts/truetype/noto/NotoSansThai-Regular.ttf")
    sub_font = (
        ImageFont.truetype(str(noto_regular), size=_px(44))
        if noto_regular.is_file()
        else _font("Prompt-SemiBold.ttf", _px(44))
    )

    idx = 0
    for row_y, card_h in row_specs:
        x = 0
        for cw in COL_WIDTHS:
            cell = cell_list[idx]
            scw = _px(cw)
            card_w = scw - pad_x * 2
            layer, pad = _card_layer((card_w, card_h), radius)
            img.alpha_composite(layer, (x + pad_x - pad, row_y - pad))

            overlay = ImageDraw.Draw(img)
            cx = x + scw // 2
            icon_y = row_y + card_h * 33 // 100
            title_y = row_y + card_h * 66 // 100
            sub_y = row_y + card_h * 78 // 100

            _draw_icon(overlay, cell["icon"], cx, icon_y)
            _center_text(overlay, (cx, title_y), cell["title"], title_font, NAVY)
            if cell["sub"]:
                _center_text(overlay, (cx, sub_y), cell["sub"], sub_font, SUB)

            x += scw
            idx += 1

    rgb = img.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
    dest.parent.mkdir(parents=True, exist_ok=True)
    rgb.save(dest, format="PNG", optimize=True)
    size_kb = dest.stat().st_size / 1024
    if size_kb > 1024:
        raise SystemExit(f"Image too large for LINE rich menu: {size_kb:.0f} KB (max 1 MB)")
    print(f"Wrote {dest} ({size_kb:.1f} KB)")
    return dest


if __name__ == "__main__":
    generate()

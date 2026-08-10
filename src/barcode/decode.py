"""Decode barcodes from image bytes (LINE camera / camera-roll photos)."""

from __future__ import annotations

import io

from PIL import Image, ImageOps
from pyzbar.pyzbar import ZBarSymbol, decode as zbar_decode

from src.barcode.sanitize import sanitize_barcode

# Prefer symbologies common on Thai auto-parts labels / product stickers.
_SYMBOLS = [
    ZBarSymbol.CODE128,
    ZBarSymbol.CODE39,
    ZBarSymbol.EAN13,
    ZBarSymbol.EAN8,
    ZBarSymbol.UPCA,
    ZBarSymbol.UPCE,
    ZBarSymbol.QRCODE,
]


def _iter_decode_candidates(image: Image.Image) -> list[Image.Image]:
    """Yield image variants that improve decode success on phone photos."""
    base = image
    if base.mode not in ("RGB", "L"):
        base = base.convert("RGB")

    gray = ImageOps.grayscale(base)
    candidates = [base, gray, ImageOps.autocontrast(gray)]

    # Mild downscale helps some oversampled phone shots; keep original first.
    w, h = gray.size
    if max(w, h) > 1600:
        scale = 1600 / float(max(w, h))
        resized = gray.resize(
            (max(int(w * scale), 1), max(int(h * scale), 1)),
            Image.Resampling.LANCZOS,
        )
        candidates.append(resized)
        candidates.append(ImageOps.autocontrast(resized))

    return candidates


def decode_barcodes_from_image(image_bytes: bytes) -> list[str]:
    """
    Return raw barcode payloads found in the image (best-effort, de-duplicated).

    Empty list means nothing readable was found.
    """
    if not image_bytes:
        return []

    try:
        image = Image.open(io.BytesIO(image_bytes))
        image.load()
    except Exception as e:
        print("BARCODE IMAGE OPEN ERROR:", e)
        return []

    found: list[str] = []
    seen: set[str] = set()

    for candidate in _iter_decode_candidates(image):
        try:
            results = zbar_decode(candidate, symbols=_SYMBOLS)
        except Exception as e:
            print("BARCODE DECODE ERROR:", e)
            continue

        for result in results:
            try:
                raw = result.data.decode("utf-8", errors="ignore").strip()
            except Exception:
                continue
            if not raw or raw in seen:
                continue
            seen.add(raw)
            found.append(raw)

        if found:
            break

    return found


def pick_best_barcode(raw_codes: list[str] | None) -> str | None:
    """Pick the first sanitizable barcode from decode results."""
    for raw in raw_codes or []:
        code = sanitize_barcode(raw)
        if code:
            return code
    return None

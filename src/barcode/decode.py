"""Decode barcodes from image bytes (LINE camera / camera-roll photos)."""

from __future__ import annotations

import io
from functools import lru_cache
from typing import Any

from PIL import Image, ImageOps

from src.barcode.sanitize import sanitize_barcode


class BarcodeDecodeUnavailable(RuntimeError):
    """Raised when pyzbar/zbar cannot be loaded in this environment."""


@lru_cache(maxsize=1)
def _load_zbar() -> tuple[Any, Any]:
    """
    Lazy-load pyzbar so a missing libzbar does not crash app import /health.

    Railway/Nixpacks must ship `zbar` / `libzbar0` (see nixpacks.toml).
    """
    try:
        from pyzbar.pyzbar import ZBarSymbol, decode as zbar_decode
    except Exception as e:
        raise BarcodeDecodeUnavailable(
            "Barcode decoder unavailable (pyzbar/libzbar). "
            "Install libzbar0 / nix zbar for product scan."
        ) from e

    symbols = [
        ZBarSymbol.CODE128,
        ZBarSymbol.CODE39,
        ZBarSymbol.EAN13,
        ZBarSymbol.EAN8,
        ZBarSymbol.UPCA,
        ZBarSymbol.UPCE,
        ZBarSymbol.QRCODE,
    ]
    return zbar_decode, symbols


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
    Raises BarcodeDecodeUnavailable if the decoder cannot load.
    """
    if not image_bytes:
        return []

    zbar_decode, symbols = _load_zbar()

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
            results = zbar_decode(candidate, symbols=symbols)
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

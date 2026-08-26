#!/usr/bin/env python3
"""Generate admin/exec LINE rich-menu PNG (same 3x2 layout as default staff menu)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generate_image import generate

OUT = ROOT / "rich_menu_ops.png"


def main() -> None:
    generate(out=OUT)


if __name__ == "__main__":
    main()

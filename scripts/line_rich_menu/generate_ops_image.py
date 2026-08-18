#!/usr/bin/env python3
"""Generate admin/exec LINE rich-menu PNG (staff 3x2 + ภาพรวมยอดขาย)."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from generate_image import CELLS, generate

OUT = ROOT / "rich_menu_ops.png"

OPS_CELLS = list(CELLS)
OPS_CELLS[-1] = {"title": "ภาพรวมยอดขาย", "sub": "", "icon": "sales"}


def main() -> None:
    generate(cells=OPS_CELLS, out=OUT)


if __name__ == "__main__":
    main()

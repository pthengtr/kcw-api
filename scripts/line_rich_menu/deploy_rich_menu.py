#!/usr/bin/env python3
"""
Create / replace the default LINE rich menu for KCW tools.

Requires LINE_CHANNEL_ACCESS_TOKEN in the environment or repo-root .env.

Usage:
  source /workspace/.venv/bin/activate   # optional
  python scripts/line_rich_menu/generate_image.py
  python scripts/line_rich_menu/deploy_rich_menu.py
  python scripts/line_rich_menu/deploy_rich_menu.py --dry-run
  python scripts/line_rich_menu/deploy_rich_menu.py --keep-old   # do not delete previous defaults
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parents[1]
SPEC_PATH = ROOT / "menu_spec.json"
IMAGE_PATH = ROOT / "rich_menu.png"

API = "https://api.line.me/v2/bot"
API_DATA = "https://api-data.line.me/v2/bot"


def _token() -> str:
    load_dotenv(REPO / ".env")
    token = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
    if not token or token.lower() in {"placeholder", "changeme"}:
        raise SystemExit(
            "LINE_CHANNEL_ACCESS_TOKEN is missing. Set it in .env or the environment, then re-run."
        )
    return token


def _headers(token: str, *, json_body: bool = False) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


def list_rich_menus(token: str) -> list[dict]:
    r = requests.get(f"{API}/richmenu/list", headers=_headers(token), timeout=30)
    r.raise_for_status()
    return list(r.json().get("richmenus") or [])


def get_default_rich_menu_id(token: str) -> str | None:
    r = requests.get(f"{API}/user/all/richmenu", headers=_headers(token), timeout=30)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return (r.json() or {}).get("richMenuId")


def create_rich_menu(token: str, spec: dict) -> str:
    r = requests.post(
        f"{API}/richmenu",
        headers=_headers(token, json_body=True),
        data=json.dumps(spec, ensure_ascii=False).encode("utf-8"),
        timeout=30,
    )
    if not r.ok:
        raise SystemExit(f"Create rich menu failed ({r.status_code}): {r.text}")
    rich_menu_id = r.json().get("richMenuId")
    if not rich_menu_id:
        raise SystemExit(f"Unexpected create response: {r.text}")
    return rich_menu_id


def upload_image(token: str, rich_menu_id: str, image_path: Path) -> None:
    content_type = "image/png" if image_path.suffix.lower() == ".png" else "image/jpeg"
    with image_path.open("rb") as f:
        r = requests.post(
            f"{API_DATA}/richmenu/{rich_menu_id}/content",
            headers={**_headers(token), "Content-Type": content_type},
            data=f,
            timeout=60,
        )
    if not r.ok:
        raise SystemExit(f"Upload image failed ({r.status_code}): {r.text}")


def set_default(token: str, rich_menu_id: str) -> None:
    r = requests.post(
        f"{API}/user/all/richmenu/{rich_menu_id}",
        headers=_headers(token),
        timeout=30,
    )
    if not r.ok:
        raise SystemExit(f"Set default failed ({r.status_code}): {r.text}")


def delete_rich_menu(token: str, rich_menu_id: str) -> None:
    r = requests.delete(f"{API}/richmenu/{rich_menu_id}", headers=_headers(token), timeout=30)
    if r.status_code not in (200, 404):
        print(f"Warning: could not delete {rich_menu_id}: {r.status_code} {r.text}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy KCW LINE rich menu")
    parser.add_argument("--dry-run", action="store_true", help="Print plan only; no API writes")
    parser.add_argument(
        "--keep-old",
        action="store_true",
        help="Do not delete previously listed rich menus after switching default",
    )
    parser.add_argument("--image", type=Path, default=IMAGE_PATH)
    parser.add_argument("--spec", type=Path, default=SPEC_PATH)
    args = parser.parse_args()

    if not args.spec.is_file():
        raise SystemExit(f"Missing spec: {args.spec}")
    if not args.image.is_file():
        raise SystemExit(f"Missing image: {args.image} (run generate_image.py first)")

    size_kb = args.image.stat().st_size / 1024
    if size_kb > 1024:
        raise SystemExit(f"Image too large: {size_kb:.0f} KB (LINE max 1 MB)")

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    print("Rich menu plan")
    print(f"  name: {spec.get('name')}")
    print(f"  size: {spec['size']['width']}x{spec['size']['height']}")
    print(f"  chatBarText: {spec.get('chatBarText')}")
    print(f"  image: {args.image} ({size_kb:.1f} KB)")
    for i, area in enumerate(spec.get("areas") or [], 1):
        action = area.get("action") or {}
        print(f"  area {i}: {action.get('label')} → message «{action.get('text')}»")

    if args.dry_run:
        print("Dry run — no changes made.")
        return 0

    token = _token()
    previous_default = get_default_rich_menu_id(token)
    existing = list_rich_menus(token)
    print(f"Existing rich menus: {len(existing)}")
    if previous_default:
        print(f"Current default: {previous_default}")

    rich_menu_id = create_rich_menu(token, spec)
    print(f"Created: {rich_menu_id}")
    upload_image(token, rich_menu_id, args.image)
    print("Uploaded image")
    set_default(token, rich_menu_id)
    print(f"Set as default for all users: {rich_menu_id}")

    if not args.keep_old:
        for menu in existing:
            mid = menu.get("richMenuId")
            if mid and mid != rich_menu_id:
                delete_rich_menu(token, mid)
                print(f"Deleted old menu: {mid} ({menu.get('name')})")

    print("Done. Open the OA chat on LINE to verify the rich menu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

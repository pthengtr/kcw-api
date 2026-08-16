#!/usr/bin/env python3
"""Create an admin-only LINE rich menu and link it to admin/exec users.

Does NOT change the default 3-tap staff menu.

  python scripts/line_rich_menu/generate_ops_image.py
  python scripts/line_rich_menu/deploy_ops_rich_menu.py --dry-run
  python scripts/line_rich_menu/deploy_ops_rich_menu.py --link-admins
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
SPEC_PATH = ROOT / "menu_spec_ops.json"
IMAGE_PATH = ROOT / "rich_menu_ops.png"

API = "https://api.line.me/v2/bot"
API_DATA = "https://api-data.line.me/v2/bot"


def _token() -> str:
    load_dotenv(REPO / ".env")
    token = (os.getenv("LINE_CHANNEL_ACCESS_TOKEN") or "").strip()
    if not token or token.lower() in {"placeholder", "changeme"}:
        raise SystemExit("LINE_CHANNEL_ACCESS_TOKEN is missing.")
    return token


def _headers(token: str, *, json_body: bool = False) -> dict[str, str]:
    h = {"Authorization": f"Bearer {token}"}
    if json_body:
        h["Content-Type"] = "application/json"
    return h


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
    content_type = "image/png" if image_path.suffix.lower() == "png" else "image/png"
    with image_path.open("rb") as f:
        r = requests.post(
            f"{API_DATA}/richmenu/{rich_menu_id}/content",
            headers={**_headers(token), "Content-Type": content_type},
            data=f,
            timeout=60,
        )
    if not r.ok:
        raise SystemExit(f"Upload image failed ({r.status_code}): {r.text}")


def link_user(token: str, user_id: str, rich_menu_id: str) -> None:
    r = requests.post(
        f"{API}/user/{user_id}/richmenu/{rich_menu_id}",
        headers=_headers(token),
        timeout=30,
    )
    if not r.ok:
        raise SystemExit(f"Link {user_id} failed ({r.status_code}): {r.text}")


def admin_line_user_ids() -> list[tuple[str, str]]:
    from src.db import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "select line_user_id, coalesce(display_name, '') "
                "from ops.line_access "
                "where lower(access_group) in ('admin', 'exec') "
                "and coalesce(is_allowed, false) = true"
            )
        ).all()
    return [(str(r[0]), str(r[1])) for r in rows if r[0]]


def main() -> int:
    parser = argparse.ArgumentParser(description="Deploy admin-only KCW ops LINE rich menu")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--link-admins", action="store_true", help="Link menu to admin/exec LINE users")
    parser.add_argument("--image", type=Path, default=IMAGE_PATH)
    parser.add_argument("--spec", type=Path, default=SPEC_PATH)
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    print("Ops rich menu plan (NOT default)")
    print(f"  name: {spec.get('name')}")
    print(f"  chatBarText: {spec.get('chatBarText')}")
    for i, area in enumerate(spec.get("areas") or [], 1):
        action = area.get("action") or {}
        print(f"  area {i}: {action.get('label')} → «{action.get('text')}»")

    if args.dry_run:
        if args.link_admins:
            users = admin_line_user_ids()
            print(f"Would link to {len(users)} admin/exec users:")
            for uid, name in users:
                print(f"  {name or '-'} {uid}")
        print("Dry run — no changes. Default staff menu is untouched.")
        return 0

    if not args.image.is_file():
        raise SystemExit(f"Missing image: {args.image} (run generate_ops_image.py first)")

    token = _token()
    rich_menu_id = create_rich_menu(token, spec)
    print(f"Created: {rich_menu_id}")
    upload_image(token, rich_menu_id, args.image)
    print("Uploaded image")
    print("NOT set as default.")

    if args.link_admins:
        users = admin_line_user_ids()
        for uid, name in users:
            link_user(token, uid, rich_menu_id)
            print(f"Linked {name or uid}")
        print(f"Linked {len(users)} admin/exec users.")
    else:
        print("Skip --link-admins. Menu exists but is not shown until linked.")

    print(f"richMenuId={rich_menu_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

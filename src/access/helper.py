import requests
import os
from src.access.config import COMMAND_PERMISSIONS

LINE_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")


def fetch_line_display_name(line_user_id: str) -> str | None:
    if not line_user_id:
        return None

    try:
        url = f"https://api.line.me/v2/bot/profile/{line_user_id}"
        headers = {
            "Authorization": f"Bearer {LINE_TOKEN}"
        }

        resp = requests.get(url, headers=headers, timeout=5)

        if resp.status_code != 200:
            print("LINE profile fetch failed:", resp.text)
            return None

        data = resp.json()
        return data.get("displayName")

    except Exception as e:
        print("LINE profile error:", e)
        return None

def get_line_user_id(event: dict) -> str:
    source = event.get("source", {}) or {}
    return (source.get("userId") or "").strip()


def get_or_create_line_access(engine, line_user_id: str) -> dict:
    if not line_user_id:
        return {
            "line_user_id": "",
            "access_group": "guest",
            "is_allowed": False,
            "is_new": False,
        }

    with engine.begin() as conn:

        row = conn.exec_driver_sql(
            """
            select line_user_id, access_group, is_allowed, display_name
            from ops.line_access
            where line_user_id = %s
            """,
            (line_user_id,),
        ).fetchone()

        if row:
            return {
                "line_user_id": row[0],
                "access_group": row[1],
                "is_allowed": row[2],
                "display_name": row[3],
                "is_new": False,
            }

        # ⭐ fetch display name from LINE
        display_name = fetch_line_display_name(line_user_id)

        conn.exec_driver_sql(
            """
            insert into ops.line_access (
                line_user_id,
                display_name,
                access_group,
                is_allowed
            )
            values (%s, %s, 'guest', false)
            """,
            (line_user_id, display_name),
        )

    return {
        "line_user_id": line_user_id,
        "access_group": "guest",
        "is_allowed": False,
        "display_name": display_name,
        "is_new": True,
    }


def build_access_denied_message(access: dict) -> str:
    name = access.get("display_name") or ""

    if access.get("is_new"):
        return (
            f"สวัสดีครับ {name} 👋\n"
            "ระบบได้บันทึกบัญชีของคุณแล้ว\n"
            "แต่ยังไม่ได้รับสิทธิ์ใช้งาน\n"
            "กรุณาติดต่อผู้ดูแลเพื่อขออนุญาตก่อนครับ"
        )

    return (
        f"สวัสดีครับ {name} 🙏\n"
        "บัญชีนี้ยังไม่ได้รับสิทธิ์ใช้งานระบบ\n"
        "กรุณาติดต่อผู้ดูแลเพื่อขออนุญาตก่อนครับ"
    )

def can_execute(access_group: str, command: str) -> bool:
    allowed = COMMAND_PERMISSIONS.get(command)

    # command not registered → deny by default
    if allowed is None:
        return False

    return access_group in allowed
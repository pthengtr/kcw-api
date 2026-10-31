from src.access.helper import can_execute
from src.tar_transfer.push import push_recipient_ids
from src.tar_transfer.summary import (
    command_date,
    format_tar_transfer_message,
    is_tar_transfer_command,
    load_tar_transfer,
)

__all__ = [
    "COMMAND",
    "handle_tar_transfer_command",
    "is_tar_transfer_command",
]

COMMAND = "โอนtar"


def handle_tar_transfer_command(engine, user_text: str, access: dict | None) -> dict:
    group = (access or {}).get("access_group") or ""
    line_user_id = (access or {}).get("line_user_id") or ""
    allowed = can_execute(group, COMMAND)
    if not allowed and line_user_id:
        allowed = line_user_id in set(push_recipient_ids(engine))
    if not allowed:
        return {"type": "text", "text": "บัญชีนี้ไม่มีสิทธิ์ใช้คำสั่งนี้ครับ"}

    try:
        target = command_date(user_text)
    except ValueError as exc:
        return {"type": "text", "text": str(exc)}

    summary = load_tar_transfer(engine, target)
    return {"type": "text", "text": format_tar_transfer_message(summary)}

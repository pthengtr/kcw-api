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
            select line_user_id, access_group, is_allowed
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
                "is_new": False,
            }

        conn.exec_driver_sql(
            """
            insert into ops.line_access (
                line_user_id,
                access_group,
                is_allowed
            )
            values (%s, 'guest', false)
            """,
            (line_user_id,),
        )

    return {
        "line_user_id": line_user_id,
        "access_group": "guest",
        "is_allowed": False,
        "is_new": True,
    }


def build_access_denied_message(access: dict) -> str:
    if access.get("is_new"):
        return (
            "สวัสดีครับ 👋\n"
            "ระบบได้บันทึกบัญชีของคุณแล้ว\n"
            "แต่ยังไม่ได้รับสิทธิ์ใช้งาน\n"
            "กรุณาติดต่อผู้ดูแลเพื่อขออนุญาตก่อนครับ"
        )

    return (
        "สวัสดีครับ 🙏\n"
        "บัญชีนี้ยังไม่ได้รับสิทธิ์ใช้งานระบบ\n"
        "กรุณาติดต่อผู้ดูแลเพื่อขออนุญาตก่อนครับ"
    )
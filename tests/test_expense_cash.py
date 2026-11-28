from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.access.config import COMMAND_PERMISSIONS
from src.access.helper import can_execute
from src.expense_cash.approvers import (
    CARTOON_LINE_USER_ID,
    CASH_APPROVER_GROUP,
    ICE_LINE_USER_ID,
    JEAB_LINE_USER_ID,
    MAY_LINE_USER_ID,
    PEUNG_LINE_USER_ID,
    PHU_LINE_USER_ID,
    is_cash_approver,
)
from src.expense_cash.copy import (
    approved_peer_notice,
    pending_ack,
    rejected_peer_notice,
)
from src.expense_cash.notify import (
    notify_admins_new_request,
    notify_other_approvers_approved,
    notify_other_approvers_rejected,
)
from src.expense_cash.service import parse_amount
from src.expense_cash.tiger import expense_cash_pos_bill_id
from src.handlers.expense_cash import (
    is_expense_cash_admin_command,
    is_expense_cash_intent,
    is_expense_cash_postback,
)


def test_parse_amount_digits_only():
    assert parse_amount("500") == 500
    assert parse_amount(" 1,200 ") == 1200
    assert parse_amount("0") is None
    assert parse_amount("500.50") is None
    assert parse_amount("500 บาท") is None
    assert parse_amount("-10") is None


def test_intent_aliases():
    assert is_expense_cash_intent("เบิกเงิน")
    assert is_expense_cash_intent("เบิก ค่าใช้จ่าย")
    assert is_expense_cash_intent("ถอนเงิน")
    assert not is_expense_cash_intent("ยอดขาย")


def test_admin_commands():
    assert is_expense_cash_admin_command("รายการเบิก")
    assert is_expense_cash_admin_command("อนุมัติ 3")
    assert is_expense_cash_admin_command("อนุมัติ #12")
    assert is_expense_cash_admin_command("ส่งกลับ 3 ขอใบเสร็จ")
    assert is_expense_cash_admin_command("ปฏิเสธ 3 ไม่ผ่าน")
    assert is_expense_cash_admin_command("สถานะเบิก 3")
    assert is_expense_cash_admin_command("ยกเลิกเบิก 12")
    assert is_expense_cash_admin_command("ส่งเบิก 44")
    assert is_expense_cash_admin_command("ส่งเบิก #44")
    assert not is_expense_cash_admin_command("อนุมัติ")
    assert not is_expense_cash_admin_command("ส่งเบิก")


def test_pending_ack_warns_when_notify_fails():
    ok = pending_ack(short_code=44, amount=10, reason="ค่าขนส่ง", notify_ok=True)
    assert "แอดมินดู" in ok
    assert "โควต้า" not in ok
    bad = pending_ack(short_code=44, amount=10, reason="ค่าขนส่ง", notify_ok=False)
    assert "โควต้า" in bad or "ส่งหาแอดมินไม่สำเร็จ" in bad
    assert "อนุมัติ 44" in bad
    assert "รายการเบิก" in bad


def test_notify_admins_skips_requester_and_uses_multicast():
    engine = MagicMock()
    row = {
        "id": "req-1",
        "short_code": 44,
        "amount": 10,
        "reason": "ค่าขนส่ง",
        "status": "pending",
        "requester_line_user_id": PEUNG_LINE_USER_ID,
        "requester_name": "peung",
    }
    roster = [
        PHU_LINE_USER_ID,
        PEUNG_LINE_USER_ID,
        ICE_LINE_USER_ID,
    ]
    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=roster,
        ),
        patch("src.expense_cash.notify.multicast_line_messages") as multi,
        patch("src.expense_cash.notify.push_line_messages") as push,
    ):
        assert notify_admins_new_request(engine, row) is True
        multi.assert_called_once()
        sent_ids, msgs = multi.call_args.args
        assert PEUNG_LINE_USER_ID not in sent_ids
        assert set(sent_ids) == {PHU_LINE_USER_ID, ICE_LINE_USER_ID}
        assert msgs and msgs[0]["type"] == "flex"
        push.assert_not_called()


def test_notify_admins_fans_out_to_both_line_channels(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-old")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-old")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-new")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-new")
    monkeypatch.delenv("EXPENSE_CASH_LINE_CHANNEL", raising=False)

    engine = MagicMock()
    row = {
        "id": "req-1",
        "short_code": 44,
        "amount": 10,
        "reason": "ค่าขนส่ง",
        "status": "pending",
        "requester_line_user_id": "U_requester",
    }
    tokens: list[str] = []

    def fake_push(to, messages):
        import src.bot.line_bot as line_bot

        tokens.append(line_bot._access_token())

    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=[PHU_LINE_USER_ID],
        ),
        patch("src.expense_cash.notify.push_line_messages", side_effect=fake_push),
    ):
        assert notify_admins_new_request(engine, row) is True
    assert tokens == ["tok-old", "tok-new"]


def test_notify_admins_can_pin_new_channel(monkeypatch):
    monkeypatch.setenv("LINE_CHANNEL_SECRET", "sec-old")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN", "tok-old")
    monkeypatch.setenv("LINE_CHANNEL_SECRET_2", "sec-new")
    monkeypatch.setenv("LINE_CHANNEL_ACCESS_TOKEN_2", "tok-new")
    monkeypatch.setenv("EXPENSE_CASH_LINE_CHANNEL", "new")

    engine = MagicMock()
    row = {
        "id": "req-1",
        "short_code": 44,
        "amount": 10,
        "reason": "ค่าขนส่ง",
        "status": "pending",
        "requester_line_user_id": "U_requester",
    }
    tokens: list[str] = []

    def fake_multi(ids, messages):
        import src.bot.line_bot as line_bot

        tokens.append(line_bot._access_token())
        return ids

    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=[PHU_LINE_USER_ID],
        ),
        patch(
            "src.expense_cash.notify.multicast_line_messages",
            side_effect=fake_multi,
        ),
    ):
        assert notify_admins_new_request(engine, row) is True
    assert tokens == ["tok-new"]


def test_notify_admins_falls_back_when_multicast_fails():
    engine = MagicMock()
    row = {
        "id": "req-1",
        "short_code": 44,
        "amount": 10,
        "reason": "ค่าขนส่ง",
        "status": "pending",
        "requester_line_user_id": "U_requester",
        "requester_name": "Boss",
    }
    roster = [PHU_LINE_USER_ID, ICE_LINE_USER_ID]
    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=roster,
        ),
        patch(
            "src.expense_cash.notify.multicast_line_messages",
            side_effect=RuntimeError("quota"),
        ),
        patch("src.expense_cash.notify.push_line_messages") as push,
    ):
        assert notify_admins_new_request(engine, row) is True
        assert push.call_count == 2


def test_notify_admins_returns_false_when_all_pushes_fail():
    engine = MagicMock()
    row = {
        "id": "req-1",
        "short_code": 44,
        "amount": 10,
        "reason": "ค่าขนส่ง",
        "status": "pending",
        "requester_line_user_id": "U_requester",
    }
    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=[PHU_LINE_USER_ID],
        ),
        patch(
            "src.expense_cash.notify.multicast_line_messages",
            side_effect=RuntimeError("quota"),
        ),
        patch(
            "src.expense_cash.notify.push_line_messages",
            side_effect=RuntimeError("quota"),
        ),
    ):
        assert notify_admins_new_request(engine, row) is False


def test_peer_approve_notify_on_by_default(monkeypatch):
    monkeypatch.delenv("EXPENSE_CASH_PEER_NOTIFY", raising=False)
    engine = MagicMock()
    row = {
        "short_code": 7,
        "amount": 1500,
        "requester_name": "น้องบอส",
    }
    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=[PEUNG_LINE_USER_ID, PHU_LINE_USER_ID, ICE_LINE_USER_ID],
        ),
        patch("src.expense_cash.notify.multicast_line_messages") as multi,
    ):
        notify_other_approvers_approved(
            engine,
            row,
            reviewer_line_user_id=PEUNG_LINE_USER_ID,
            reviewer_name="peung",
        )
        multi.assert_called_once()
        sent_ids, msgs = multi.call_args.args
        assert PEUNG_LINE_USER_ID not in sent_ids
        assert set(sent_ids) == {PHU_LINE_USER_ID, ICE_LINE_USER_ID}
        assert "อนุมัติ" in msgs[0]["text"]
        assert "#7" in msgs[0]["text"]


def test_peer_approve_notify_when_disabled(monkeypatch):
    monkeypatch.setenv("EXPENSE_CASH_PEER_NOTIFY", "0")
    engine = MagicMock()
    row = {
        "short_code": 7,
        "amount": 1500,
        "requester_name": "น้องบอส",
    }
    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=[PHU_LINE_USER_ID, ICE_LINE_USER_ID],
        ),
        patch("src.expense_cash.notify.multicast_line_messages") as multi,
        patch("src.expense_cash.notify.push_line_messages") as push,
    ):
        notify_other_approvers_approved(
            engine,
            row,
            reviewer_line_user_id=PEUNG_LINE_USER_ID,
            reviewer_name="peung",
        )
        multi.assert_not_called()
        push.assert_not_called()


def test_peer_reject_notify_on_by_default(monkeypatch):
    monkeypatch.delenv("EXPENSE_CASH_PEER_NOTIFY", raising=False)
    engine = MagicMock()
    row = {
        "short_code": 9,
        "amount": 800,
        "requester_name": "น้องบอส",
        "admin_note": "เอกสารไม่ครบ",
    }
    with (
        patch(
            "src.expense_cash.notify.repos.list_approver_line_ids",
            return_value=[PEUNG_LINE_USER_ID, PHU_LINE_USER_ID, ICE_LINE_USER_ID],
        ),
        patch("src.expense_cash.notify.multicast_line_messages") as multi,
    ):
        notify_other_approvers_rejected(
            engine,
            row,
            reviewer_line_user_id=PHU_LINE_USER_ID,
            reviewer_name="phu",
        )
        multi.assert_called_once()
        sent_ids, msgs = multi.call_args.args
        assert PHU_LINE_USER_ID not in sent_ids
        assert set(sent_ids) == {PEUNG_LINE_USER_ID, ICE_LINE_USER_ID}
        assert "ปฏิเสธ" in msgs[0]["text"]
        assert "#9" in msgs[0]["text"]
        assert "เอกสารไม่ครบ" in msgs[0]["text"]


def test_postback_prefix():
    assert is_expense_cash_postback("expense_cash:approve:abc")
    assert not is_expense_cash_postback("kb_select:1")


def test_synthetic_pos_bill_id():
    from src.expense_cash.tiger import is_expense_cash_pos_bill_id

    assert expense_cash_pos_bill_id("uuid-here") == "expense-cash:uuid-here"
    assert is_expense_cash_pos_bill_id("expense-cash:uuid-here")
    assert not is_expense_cash_pos_bill_id("574142")
    assert not is_expense_cash_pos_bill_id(None)


def test_expense_commands_use_cash_approver_group_not_admin_exec():
    for cmd in ("รายการเบิก", "อนุมัติเบิก", "ส่งกลับเบิก", "ปฏิเสธเบิก"):
        assert COMMAND_PERMISSIONS[cmd] == {CASH_APPROVER_GROUP}
        assert can_execute(CASH_APPROVER_GROUP, cmd)
        assert not can_execute("admin", cmd)
        assert not can_execute("exec", cmd)


def test_cash_approver_roster_named_approvers():
    for uid, group in (
        (PEUNG_LINE_USER_ID, "admin"),
        (PHU_LINE_USER_ID, "exec"),
        (ICE_LINE_USER_ID, "exec"),
        (MAY_LINE_USER_ID, "user"),
        (CARTOON_LINE_USER_ID, "user"),
        (JEAB_LINE_USER_ID, "exec"),
    ):
        assert is_cash_approver(
            {
                "line_user_id": uid,
                "access_group": group,
                "is_allowed": True,
            }
        )
    # Other admin/exec must not approve.
    assert not is_cash_approver(
        {
            "line_user_id": "U_other_admin",
            "access_group": "admin",
            "is_allowed": True,
        }
    )
    assert not is_cash_approver(
        {
            "line_user_id": "U_other_exec",
            "access_group": "exec",
            "is_allowed": True,
        }
    )
    # Dedicated group still works for non-roster users.
    assert is_cash_approver(
        {
            "line_user_id": "U_future",
            "access_group": CASH_APPROVER_GROUP,
            "is_allowed": True,
        }
    )
    assert not is_cash_approver(
        {
            "line_user_id": PEUNG_LINE_USER_ID,
            "access_group": "admin",
            "is_allowed": False,
        }
    )


def test_approved_peer_notice_copy():
    text = approved_peer_notice(
        short_code=7,
        amount=1500,
        reviewer_name="peung",
        requester_name="น้องบอส",
    )
    assert "#7" in text
    assert "1,500" in text
    assert "peung" in text
    assert "น้องบอส" in text
    assert "อนุมัติ" in text


def test_rejected_peer_notice_copy():
    text = rejected_peer_notice(
        short_code=9,
        amount=800,
        reviewer_name="phu",
        requester_name="น้องบอส",
        admin_note="เอกสารไม่ครบ",
    )
    assert "#9" in text
    assert "800" in text
    assert "phu" in text
    assert "น้องบอส" in text
    assert "ปฏิเสธ" in text
    assert "เอกสารไม่ครบ" in text

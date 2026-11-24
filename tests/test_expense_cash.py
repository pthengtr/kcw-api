from __future__ import annotations

from src.access.config import COMMAND_PERMISSIONS
from src.access.helper import can_execute
from src.expense_cash.approvers import (
    CASH_APPROVER_GROUP,
    ICE_LINE_USER_ID,
    PEUNG_LINE_USER_ID,
    PHU_LINE_USER_ID,
    is_cash_approver,
)
from src.expense_cash.copy import approved_peer_notice
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
    assert not is_expense_cash_admin_command("อนุมัติ")


def test_postback_prefix():
    assert is_expense_cash_postback("expense_cash:approve:abc")
    assert not is_expense_cash_postback("kb_select:1")


def test_synthetic_pos_bill_id():
    assert expense_cash_pos_bill_id("uuid-here") == "expense-cash:uuid-here"


def test_expense_commands_use_cash_approver_group_not_admin_exec():
    for cmd in ("รายการเบิก", "อนุมัติเบิก", "ส่งกลับเบิก", "ปฏิเสธเบิก"):
        assert COMMAND_PERMISSIONS[cmd] == {CASH_APPROVER_GROUP}
        assert can_execute(CASH_APPROVER_GROUP, cmd)
        assert not can_execute("admin", cmd)
        assert not can_execute("exec", cmd)


def test_cash_approver_roster_peung_phu_ice_only():
    assert is_cash_approver(
        {
            "line_user_id": PEUNG_LINE_USER_ID,
            "access_group": "admin",
            "is_allowed": True,
        }
    )
    assert is_cash_approver(
        {
            "line_user_id": PHU_LINE_USER_ID,
            "access_group": "exec",
            "is_allowed": True,
        }
    )
    assert is_cash_approver(
        {
            "line_user_id": ICE_LINE_USER_ID,
            "access_group": "exec",
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

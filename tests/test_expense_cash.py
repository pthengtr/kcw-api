from __future__ import annotations

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

COMMAND_PERMISSIONS = {
    "ยอดขาย": {"admin", "exec"},
    "โอนtar": {"admin", "exec"},
    "ประวัติสินค้า": {"admin", "exec", "staff"},
    "สินค้า": {"admin", "exec", "staff"},
    "job": {"admin", "exec", "user"},
    "sync": {"admin", "exec", "user"},
    "ที่เก็บ": {"admin", "exec", "user"},
    "สแกนตาราง": {"admin", "exec", "staff"},
    "สถานะใบสั่งซื้อ": {"admin", "exec", "staff"},
    # Expense cash: dedicated cash_approver group (not blanket admin/exec).
    # Peung/Phu/Ice are also allowed by LINE id roster in expense_cash.approvers.
    "รายการเบิก": {"cash_approver"},
    "อนุมัติเบิก": {"cash_approver"},
    "ส่งกลับเบิก": {"cash_approver"},
    "ปฏิเสธเบิก": {"cash_approver"},
}

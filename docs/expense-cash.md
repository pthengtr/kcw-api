# Expense cash request (เบิกเงินสด → Tiger QR)

LINE chat flow on **Railway** `POST /line-webhook` for cashbox withdrawals. Not the same as kcw-v2 `expense_receipt` bookkeeping.

## Staff

1. `เบิกเงิน` / `เบิกค่าใช้จ่าย` / `ถอนเงิน` / `ขอเบิก`
2. Bot asks reason → amount (digits only)
3. Row in `public.expense_cash_request` (`pending`)
4. Cash approvers get Flex with Approve / Need info / Reject

Approvers are **Peung / Phu / Ice** only (LINE id roster in `src/expense_cash/approvers.py`), plus anyone with `ops.line_access.access_group = cash_approver`. Not blanket admin/exec. On approve, the requester gets the QR and the other approvers get a peer notice.

## Approver (LINE)

- `รายการเบิก`
- `อนุมัติ 3`
- `ส่งกลับ 3 ขอใบเสร็จ`
- `ปฏิเสธ 3 ไม่ผ่าน`
- `สถานะเบิก 3` (refresh Tiger voucher: รอสแกน / ถอนแล้ว / ยกเลิก)
- `ยกเลิกเบิก 3` (cancel unused QR; marks request cancelled)
- Or Flex postbacks (Need info / Reject then ask for a note)

## Admin (kcw-v2)

`/expense/cash-requests` (admin role). Actions proxy to Railway:

`POST /expense-cash/requests/{id}/approve|needs-info|reject`

## Railway env

Already: `LINE_*`, Supabase service role.

Add:

- `TIGER_VOUCHER_USERNAME` / `PASSWORD` / `MOBILE` (+ optional host/flags)
- `EXPENSE_CASH_INTERNAL_SECRET` (shared with kcw-v2)

kcw-v2 needs:

- `EXPENSE_CASH_INTERNAL_SECRET` (same value)
- `KCW_API_PUBLIC_URL` (default `https://kcw-api-production.up.railway.app`)

## Tiger link

`pos_bill_id = expense-cash:{uuid}` in `tiger_pay.voucher_attempt`. QR PNG uploaded to `pictures/expense-cash/{id}.png` and pushed on LINE. When voucher becomes `used`, request status → `paid`.

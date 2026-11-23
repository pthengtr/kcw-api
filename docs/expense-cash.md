# Expense cash request (เบิกเงินสด → Tiger QR)

LINE chat flow on **Railway** `POST /line-webhook` for cashbox withdrawals. Not the same as kcw-v2 `expense_receipt` bookkeeping.

## Staff

1. `เบิกเงิน` / `เบิกค่าใช้จ่าย` / `ถอนเงิน` / `ขอเบิก`
2. Bot asks reason → amount (digits only)
3. Row in `public.expense_cash_request` (`pending`)
4. Admins (`ops.line_access` admin/exec) get Flex with Approve / Need info / Reject

## Admin (LINE)

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

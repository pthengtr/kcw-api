# Expense cash request (เบิกเงินสด → Tiger QR)

LINE chat flow on **Railway** `POST /line-webhook` for cashbox withdrawals. Not the same as kcw-v2 `expense_receipt` bookkeeping.

## Staff

1. `เบิกเงิน` / `เบิกค่าใช้จ่าย` / `ถอนเงิน` / `ขอเบิก`
2. Bot asks reason → amount (digits only)
3. Row in `public.expense_cash_request` (`pending`)
4. Cash approvers get Flex with Approve / Need info / Reject

Approvers are **Peung / Phu / Ice / May / Cartoon / Jeab** (LINE id roster in `src/expense_cash/approvers.py`), plus anyone with `ops.line_access.access_group = cash_approver`. Not blanket admin/exec. On approve, the requester gets the QR and the other approvers get a peer notice.

## Approver (LINE)

- `รายการเบิก`
- `อนุมัติ 3`
- `ส่งกลับ 3 ขอใบเสร็จ`
- `ปฏิเสธ 3 ไม่ผ่าน`
- `สถานะเบิก 3` (refresh Tiger voucher: รอสแกน / ถอนแล้ว / ยกเลิก)
- `ยกเลิกเบิก 3` (cancel unused QR; marks request cancelled)
- `ส่งเบิก 3` (re-push the Flex to approvers — use after LINE push quota recovers)
- Or Flex postbacks (Need info / Reject then ask for a note)

Approver Flex notifies use multicast and skip the requester. Peer-approve
text pushes are off by default (set `EXPENSE_CASH_PEER_NOTIFY=1` to enable);
they burn the monthly LINE message quota quickly. If the OA hits the plan
limit (e.g. free 500/mo), new requests still save as `pending` but Flex
pushes fail — requester ack warns, and approvers can use `รายการเบิก` /
`อนุมัติ N` / `ส่งเบิก N` via reply.

## Admin (kcw-v2)

`/expense/cash-requests` (admin role). Actions proxy to Railway:

`POST /expense-cash/requests/{id}/approve|needs-info|reject`

## Railway env

Already: `LINE_*` (supports optional `LINE_CHANNEL_*_2` for a second OA), Supabase service role.

With two OAs, expense-cash **pushes always use the new channel** (`EXPENSE_CASH_LINE_CHANNEL=new` → secondary/`*_2` by default). Webhook replies still follow whichever OA signed the event. Approver `line_user_id`s must belong to that push channel.

Add:

- `TIGER_VOUCHER_USERNAME` / `PASSWORD` / `MOBILE` (+ optional host/flags)
- `EXPENSE_CASH_INTERNAL_SECRET` (shared with kcw-v2)

kcw-v2 needs:

- `EXPENSE_CASH_INTERNAL_SECRET` (same value)
- `KCW_API_PUBLIC_URL` (default `https://kcw-api-production.up.railway.app`)

## Tiger link

`pos_bill_id = expense-cash:{uuid}` in `tiger_pay.voucher_attempt`. QR PNG uploaded to `pictures/expense-cash/{id}.png` and pushed on LINE. When voucher becomes `used`, request status → `paid`.

# Pay notes / ชำระเจ้าหนี้ (**HQ only**)

LAN + Tailscale UI for AP payment notes on **HQ PARTS9 (`KSS`)**. Port **8791**, routes under `/pay-notes/`.

**This service is HQ-only.** Do **not** run it on SYP (`syp-ubuntu-server` / `kss-pc`). There is no SYP site switch in the UI; `PAY_NOTES_SITE` must stay `HQ`.

LINE command: `ชำระเจ้าหนี้` (aliases: `โน้ตจ่าย`, `paynote`).

## Scope — workflow tabs

| Tab | What you do | Editable? | KSS / Supabase |
|-----|-------------|-----------|----------------|
| 1. สร้าง | Create note (vendor, bills, discount, images) | yes (new) | `PVMAS` INSERT + `PIMAS` stamp; `pay_note.reminder` |
| 2. รอชำระ | Pending payment board; edit note; record payment | **yes** (bills, discount, due, bank, remark) | unvouchered `PVMAS` + reminder |
| 3. รอแนบหลักฐาน | Vouchered, upload payment proof | no | vouchered `PVMAS`; `payment/{VOUCNO}/` images |
| 4. ใบสำคัญจ่าย | Complete vouchers (proof attached); view bill + proof images | no | vouchered `PVMAS` with proof |
| 5. ค้นหาตามเจ้าหนี้ | Browse all notes/vouchers per AP vendor | edit button when stage = รอชำระ | `GET /api/notes?acctno=` |

After proof upload on tab 3, the row moves to tab 4 automatically (if AI payment verify passes, or AI is off). If AI detects a slip amount mismatch, the operator must tick **ยืนยันว่ายอดสลิปถูกต้อง (AI อ่านผิด)** before completing.

### Tab 1 create modes

| Mode | Label | Behavior |
|------|-------|----------|
| **กรอกเอง** | Manual | Original form — all steps visible |
| **ช่วยอ่านเอกสาร** | AI assist | 6-step wizard: vendor → scan document → confirm bills → discount → note details → upload |

AI assist scans vendor bill/statement images, extracts bill numbers + amounts per line, matches to KSS pickable bills (billno + amount scoring), and shows a line-by-line review with total compare (**ก่อนส่วนลด**). If scan fails, use **ข้ามไปเลือกบิลเอง**.

### AI APIs

- `POST /api/ai/scan-bills` — `acctno` + 1–5 `files` → line match result (+ `usage` token stats)
- `POST /api/ai/verify-payment` — `voucno` + `file` → slip amount vs net payable

Requires `OPENAI_API_KEY` and `PAY_NOTES_AI_ENABLED=true` (default on when key is set).

### APIs

- `GET /api/notes?acctno=&noteno=` — header, attached purchase bills with `PIDET` lines (qty / price / amount), voucher payments, reminder, images (`noteno` may contain `/`; use query params)
- `GET /api/notes` — all service notes (optional `acctno` filter); includes `stage`, `workflow_status`, `is_editable`
- `PATCH /api/notes?acctno=&noteno=` — edit pending note (bills, discount, reminder fields)
- `GET /api/bills?acctno=&noteno=` — bills for edit UI (attached + pickable)
- `GET /api/vouchered?proof=awaiting|done|all` — vouchered board (removed: `/api/awaiting-proof`, `/api/paid`)

Write rules: [kcw-docs PVMAS/RVMAS dictionary §9](https://github.com/pthengtr/kcw-docs/blob/main/dictionaries/kcw-pvmas-rvmas-notes-vouchers-data-dictionary.md). Voucher `VOUCNO`: `JOURMODE=1` (VAT / vendor `7*`) → `P{YYMM}-###`; `JOURMODE=2` → `KCPN{YYMM}-###` (Buddhist YY).

## Enable (HQ Linux)

```env
PAY_NOTES_ENABLED=true
PAY_NOTES_SITE=HQ
PAY_NOTES_LISTEN_PORT=8791
PAY_NOTES_WRITE_ENABLED=true
PAY_NOTES_AI_ENABLED=true
PAY_NOTES_AI_MODEL=gpt-4o-mini
PAY_NOTES_AI_TIMEOUT_SECONDS=45
PAY_NOTES_TOKEN_SECRET=   # optional; falls back to STOCK_CHECK_TOKEN_SECRET
POS_MSSQL_WRITER_USERNAME=python_writer
POS_MSSQL_WRITER_PASSWORD=...
```

systemd: `scripts/systemd/kcw-pay-notes.service` → `kcw-pay-notes.service` on `hq-ubuntu-server`.

```bash
systemctl --user enable --now kcw-pay-notes
curl -s http://127.0.0.1:8791/health
```

SQL grants for `python_writer` (run on HQ `PARTS9` as admin, e.g. WinRM + `sqlcmd -E`):

`scripts/sql/grant_pay_notes_writer.sql`

Supabase: schema `pay_note` (vendor_bank, reminder) + image bucket paths under `public/pay_note/…`. Migrations `2026082712*_pay_note_*.sql`, `20260827140000_pay_note_reminder_discount.sql` (`discount_mode` / `discount_input` / `discount_amount` on reminder), `20260828120000_pay_note_reminder_kbiz_datetime.sql` (`kbiz_datetime` optional on reminder), `20260831120000_pay_note_remark_structured.sql` (`bill_month` + `remark_extra` on reminder).

### Remark (structured)

Operator remark is stored in Supabase `pay_note.reminder` only (not written to KSS `PVMAS`). Format:

`{acctno}-บิลเดือน m/yyyy` with optional suffix ` / {free text}`

UI uses AP code (readonly) + month picker + optional extra note. `bill_month` (date, first of month) powers the **บิลเดือน** filter on all list tabs. Composed text is kept in `remark` for print/detail views.

## Auth

Same HMAC token pattern as stock-check / explorer (`APP=pay-notes`). LINE link `?t=` or session cookie. Tailscale CGNAT clients get a `tailnet` identity without a token.

## Consistency (KSS + Supabase)

PARTS9 and Supabase **cannot** share one ACID transaction. Create-note order:

1. Write note in KSS (`PVMAS` + `PIMAS`) in one SQL Server transaction  
2. Insert `pay_note.reminder` in Supabase  
3. If step 2 fails → **compensate**: clear `PIMAS` stamps and set `PVMAS.CANCELED='Y'` so bills are free and the noteno can be reused  

Do not leave a live KSS note without a reminder going forward.

### Vendor NOTENO reuse (`_1` suffix)

`NOTENO` is the supplier’s label (≤15 chars) and may be reused across payment cycles. When KSS already has PIMAS/PVMAS stamps on that label, pay-notes auto-allocates `EE1044-04_1`, `EE1044-04_2`, … on create. The UI shows the bare vendor label (`EE1044-04`); storage/API use the suffixed KSS value.

Remediate existing open notes with paid+open PIMAS on one label:

`python scripts/remediate_noteno_collisions.py` (dry-run) · `--apply` to write.

## Not on SYP

Do not copy `kcw-pay-notes.service` to the SYP box. Do not set `PAY_NOTES_SITE=SYP`. SYP deploy scripts intentionally omit this unit.

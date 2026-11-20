# Receive notes / รับชำระลูกหนี้ (**HQ only**)

LAN + Tailscale UI for AR billing notes / receipt vouchers on **HQ PARTS9 (`KSS`)**. Port **8797**, routes under `/receive-notes/`.

**This service is HQ-only.** Do **not** run it on SYP. `RECEIVE_NOTES_SITE` must stay `HQ`.

LINE command: `รับชำระลูกหนี้` (aliases: `รับชำระ`, `receivenote`, `receive note`).

Template: [`pay-notes.md`](./pay-notes.md) — same Layout / Process / Function as ชำระเจ้าหนี้ (AP), adapted for AR.

## Scope — workflow tabs

| Tab | What you do | Editable? | KSS / Supabase |
|-----|-------------|-----------|----------------|
| 1. สร้าง | Create note (debtor → bills → discount → save) | yes (new) | `RVMAS` INSERT + `SIMAS` stamp; `receive_note.note` |
| 2. รอรับชำระ | Pending board; edit note; cancel mistaken note; record receive | yes while unvouchered | unvouchered `RVMAS` + overlay |
| 3. รอแนบหลักฐาน | Vouchered, upload payment proof | no | vouchered `RVMAS`; `payment/{VOUCNO}/` images |
| 4. ใบเสร็จรับเงิน | Complete vouchers (proof attached); issued after receive confirm | proof images only | vouchered `RVMAS` with proof |
| 5. ค้นหาตามลูกหนี้ | Browse notes/vouchers per AR debtor | edit when รอรับชำระ | `GET /api/notes?acctno=` |

### Tab 1 — create (differs from AP)

- No กรอกเอง / ช่วยอ่านเอกสาร
- No manual เลขที่ใบวางบิล (system allocates)
- No เอกสารแนบ on create (we issue the note ourselves)
- Optional **บัญชีสำหรับรับชำระ** (company bank shown on billing note; not required)
- Flow: เลือกลูกหนี้ → เลือกบิล → ส่วนลด (ถ้ามี) → บัญชีรับชำระ (optional) → บันทึก

### Number series

| Doc | JOURMODE | Stem | Example |
|-----|----------|------|---------|
| Note `NOTENO` | 2 Non-VAT | `BNN{YYMM}-` | `BNN6911-001` |
| Note `NOTENO` | 1 VAT | `BN{YYMM}-` | `BN6911-001` |
| Voucher `VOUCNO` | 2 Non-VAT | `RCN{YYMM}-` | `RCN6911-001` |
| Voucher `VOUCNO` | 1 VAT | `RC{YYMM}-` | `RC6911-001` |

Mixed VAT/Non-VAT bills → reject (`mixed_jourmode`). Voucher is **note-first only**; duplicate cut blocked (`already_vouchered`).

### Tab 2 — รอรับชำระ

- Column: ยอดที่ต้องรับ (bill − overlay discount); no วิธีรับชำระ filter/column
- Cancel mistaken note → soft cancel **both** systems (`RVMAS.CANCELED='Y'` + overlay `status=canceled`); keep document no.; red **ยกเลิก**; blocked if already vouchered
- No KBIZ reminder
- Button / modal: **รับชำระ** (actual settle method chosen here)
- Shows ส่วนลดจากใบวางบิล (read-only) to prevent double discount
- Receive accounts: กรุงไทย 248-0-44244-6, 248-6-00138-7, 248-0-42113-9 · กสิกร 064-8-91723-6, 064-8-92039-3

### Print format

- Company header matches ใบ TO (logo / name / address / phone / tax id)
- Left: customer code, name, address, tax id; Right: doc no, date, ref note (receipt), bill month
- `@page { margin: 0 }` to avoid browser print header/footer chrome
- Receipt title **ใบเสร็จรับเงิน** (prefix `RC` / `RCN` unchanged); checkboxes show actual BRDET settle only

## KSS mapping

| Role | Table |
|------|-------|
| Note / voucher header | `RVMAS` (`NR` note → `CR` voucher) |
| Sales bills | `SIMAS` (`CASHED=N`, unpaid) |
| Instruments | `BRDET` |
| Debtor master | `ARMAS` |

Write rules: [kcw-docs §10](https://github.com/pthengtr/kcw-docs/blob/main/dictionaries/kcw-pvmas-rvmas-notes-vouchers-data-dictionary.md) (update stems when deploying this series).

## APIs (AP-shaped)

Same path names as pay-notes where possible (`/api/notes`, `/api/pending`, `/api/vouchers`, `/api/vouchered`, …). Aliases: `/api/vendors` → debtors; `/api/company-pay-accounts` → receive accounts. `/api/banks` returns `[]`.

## Enable (HQ Linux)

```env
RECEIVE_NOTES_ENABLED=true
RECEIVE_NOTES_SITE=HQ
RECEIVE_NOTES_LISTEN_PORT=8797
RECEIVE_NOTES_WRITE_ENABLED=false
RECEIVE_NOTES_TOKEN_SECRET=
```

systemd: `scripts/systemd/kcw-receive-notes.service`

```bash
systemctl --user enable --now kcw-receive-notes
curl -s http://127.0.0.1:8797/health
```

SQL grants: `scripts/sql/grant_receive_notes_writer.sql`  
Supabase: schema `receive_note` (migrations `*_receive_note_*.sql`, including `20261120120000_receive_note_note_reminder_fields.sql` for discount/settle/remark).

## Consistency

1. Write KSS (`RVMAS` / `SIMAS` / `BRDET`)
2. Upsert overlay (`receive_note.note`)
3. If overlay fails after create → compensate: soft-cancel KSS note (`CANCELED='Y'`, clear `SIMAS` stamps)

## Deferred (after main process test)

- Tiger cash-in / multi-channel receive-first
- AI scan
- Daily channel reports / review queue extras

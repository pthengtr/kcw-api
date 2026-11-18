# Receive notes / รับชำระลูกหนี้ (**HQ only**)

LAN + Tailscale UI for AR receipt notes/vouchers on **HQ PARTS9 (`KSS`)**. Port **8797**, routes under `/receive-notes/`.

**This service is HQ-only.** Do **not** run it on SYP. `RECEIVE_NOTES_SITE` must stay `HQ`.

LINE command: `รับชำระลูกหนี้` (aliases: `รับชำระ`, `receivenote`, `receive note`).

Template: [`pay-notes.md`](./pay-notes.md) — same auth/shell pattern, **receive-first** tabs (no cancel).

## Scope — workflow tabs

| Tab | What you do |
|-----|-------------|
| 1. รับชำระ | Pick AR + open credit bills; multi-channel receive **without** a prior note |
| 2. ใบวางบิล | Create / edit / print / track notes (`RVMAS` NR); receive from a note |
| 3. รอตรวจสอบ | Awaiting proof, transfer/cheque confirm, or Tiger problems |
| 4. ใบสำคัญรับเงิน | History, attach proof later, print, daily channel totals, Tiger reconcile, KSS resync |
| 5. ข้อมูลลูกหนี้ | One-page debt / open bills / notes / receipt history |

Manual cash is an **exception** (overflow menu + required reason). Default cash path = Tiger.

## KSS mapping

| Role | Table |
|------|-------|
| Note / voucher header | `RVMAS` (`NR` note → `CR` voucher) |
| Sales bills | `SIMAS` (`CASHED=N`, unpaid) |
| Instruments | `BRDET` |
| Debtor master | `ARMAS` |

Write rules: [kcw-docs §10](https://github.com/pthengtr/kcw-docs/blob/main/dictionaries/kcw-pvmas-rvmas-notes-vouchers-data-dictionary.md).

| Series | Format |
|--------|--------|
| Non-VAT `VOUCNO` | `{YYMM}-###` e.g. `6911-001` |
| VAT `VOUCNO` | `RC{YYMM}-###` e.g. `RC6911-001` |
| Note `NOTENO` | `BN{YYMM}-###` |

Mixed VAT/Non-VAT in one receive → **split into two vouchers**.

Partial pay: overlay tracks allocations; stamp `SIMAS` only when a bill is fully covered.

## Tiger cash-in

Reuse Companion Open API / webhook / poller. Attempt key:

- `pos_bill_id` = `ar:{receipt_id}` (≤ fits unique indexes)
- Send **cash portion only** (floor baht)
- On `success` → finish KSS voucher + proof auto
- Busy / prior success / active attempt → block duplicate receive

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
Supabase: schema `receive_note` (migrations `*_receive_note_*.sql`).

## Consistency

PARTS9 + Supabase are not one ACID transaction:

1. Write KSS (`RVMAS` / `SIMAS` / `BRDET`)
2. Upsert overlay (`receive_note.receipt` / note / channels)
3. On overlay failure after KSS success → mark `kss_sync_status=orphan_overlay` for operator resync UI (idempotent — existing `VOUCNO` is reused, never double-insert)

## Out of scope

- Cancel / void / reverse AR receipts
- SYP deploy
- AI bill scan (pay-notes only for now)

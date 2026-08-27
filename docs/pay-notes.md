# Pay notes / ชำระเจ้าหนี้ (**HQ only**)

LAN + Tailscale UI for AP payment notes on **HQ PARTS9 (`KSS`)**. Port **8791**, routes under `/pay-notes/`.

**This service is HQ-only.** Do **not** run it on SYP (`syp-ubuntu-server` / `kss-pc`). There is no SYP site switch in the UI; `PAY_NOTES_SITE` must stay `HQ`.

LINE command: `ชำระเจ้าหนี้` (aliases: `โน้ตจ่าย`, `paynote`).

## Scope

| Step | Tab | KSS / Supabase |
|------|-----|----------------|
| Create note | ใบวางบิล | `PVMAS` INSERT (`JOURTYPE=NP`) + `PIMAS` stamp `NOTENO`; bill images → Supabase `pay_note` storage; reminder row |
| Due / pay | รอชำระ | reminder due + bank; voucher → `PVMAS` UPDATE + `BPDET` INSERT |
| Proof | ใบสำคัญจ่าย | payment images on voucher |

Write rules: [kcw-docs PVMAS/RVMAS dictionary §9](https://github.com/pthengtr/kcw-docs/blob/main/dictionaries/kcw-pvmas-rvmas-notes-vouchers-data-dictionary.md).

## Enable (HQ Linux)

```env
PAY_NOTES_ENABLED=true
PAY_NOTES_SITE=HQ
PAY_NOTES_LISTEN_PORT=8791
PAY_NOTES_WRITE_ENABLED=true
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

Supabase: schema `pay_note` (vendor_bank, reminder) + image bucket paths under `public/pay_note/…`. Migrations `2026082712*_pay_note_*.sql`.

## Auth

Same HMAC token pattern as stock-check / explorer (`APP=pay-notes`). LINE link `?t=` or session cookie. Tailscale CGNAT clients get a `tailnet` identity without a token.

## Not on SYP

Do not copy `kcw-pay-notes.service` to the SYP box. Do not set `PAY_NOTES_SITE=SYP`. SYP deploy scripts intentionally omit this unit.

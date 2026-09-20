# Tiger Pay API reference

Summarized from the Postman collections:

- `Open API Payment v2` — device / cashbox Open API (what KCW Companion uses)
- `Tiger Voucher` — cloud voucher API on `api.tigercashbox.com`

Use this doc when exploring Tiger Pay capabilities. Raw Postman exports (if present) live under `docs/postman/`.

---

## 1. Open API Payment v2

Base URL pattern: `{{api_host}}api/open/v2/...`

`TIGER_PAY_API_HOST` in this repo should be the host root with trailing slash (e.g. `https://<device-or-gateway>/`). Paths below are relative to that host.

### Auth

JWT (`HS256`) in `Authorization: Bearer <token>`.

| Claim | When |
| --- | --- |
| `clientId` | Always (`TIGER_PAY_CLIENT_ID`) |
| `messageDigest` | Body-bearing mutating calls that require integrity (Create Payment in Postman) |

`messageDigest` = hex SHA-256 of the **canonical JSON body string** (Postman pre-request: `JSON.stringify(JSON.parse(body))`).

Signed with `TIGER_PAY_CLIENT_SECRET`.

KCW client: `src/tiger_pay/open_api.py` (`TigerPayOpenApiClient`).

### Envelope

Success responses typically look like:

```json
{
  "data": { },
  "message": "Success"
}
```

List endpoints put rows under `data.items` plus `page`, `limit`, `resultRows`. Errors still use the envelope (`data` may be `null`) with a `message`.

### Payment object (common fields)

| Field | Notes |
| --- | --- |
| `id` | Tiger payment id (integer) |
| `paymentNo` | e.g. `PA2602190001` |
| `type` | Observed: `cash`, `qr` |
| `amount` | Requested amount |
| `totalPay` | Amount received so far |
| `refNo1`, `refNo2` | Merchant references (KCW uses bill linkage on `refNo2`) |
| `note` | Free text |
| `status` | See statuses below |
| `remark` | Failure / device message (Thai string) |
| `cashList` | Inserted notes/coins: `{ value, amount, createdAt }` |
| `change` | Dispense info when change is given |
| `dynamicQR` | PromptPay / bank QR payload when present |
| `category`, `tag`, `promptPay`, `drop` | Optional / often null in samples |
| `createdAt`, `updatedAt` | Timestamps |

**Statuses observed:** `pending`, `success`, `fail` (plus cancel flows via Cancel endpoint).

**QR sub-status (`dynamicQR.status`):** `I` (issued / waiting), `C` (completed / paid).

### Endpoints

#### List payments

`GET api/open/v2/payment?page=1&limit=10`

Returns paginated `data.items`.

#### Get payment

`GET api/open/v2/payment/:id`

Single payment. Sample variants in Postman: cash, QR, mixed (cash + QR top-up).

#### Get current payment

`GET api/open/v2/payment/current`

- `200` + payment when a payment is active on the device
- `404` + `"No current payment exists."` when idle

Useful to detect “Tiger busy” before creating another payment (KCW does this).

#### Categories

`GET api/open/v2/payment/categories`

```json
{
  "data": [
    { "id": 1, "type": "payment", "name": "มัดจำค่าห้อง", "isDefault": true, "status": "enable" }
  ],
  "message": "Success"
}
```

#### Change-machine ready?

`GET api/open/v2/payment/change_status`

`data` is a boolean (`true` = can dispense change in the sample).

#### Cash inventory

`GET api/open/v2/payment/cash`

Array of `{ type: "Banknote"|"Coin", value, amount }` for hopper/cassette counts.

#### Create payment

`POST api/open/v2/payment`  
Auth: JWT with `clientId` + `messageDigest`

```json
{
  "type": "cash",
  "amount": 100,
  "note": "ค่าอาหาร",
  "refNo1": "REF0001",
  "refNo2": "REF0002"
}
```

Also works with `"type": "qr"` — response includes `dynamicQR` (`qrRawData`, base64 `qrImage`, refs, status `I`).

Created payments start as `pending` with `totalPay: 0`.

**Implemented in KCW:** `TigerPayOpenApiClient.create_payment` (default `type=cash`).
Cash create amounts are **floored to whole baht** before send (Tiger rejects fractional cash `amount`); the payment attempt still stores the original POS `AFTERTAX`.

#### Create QR on existing payment

`POST api/open/v2/payment/:id/qr/create`

```json
{
  "paymentGateway": "SCB"
}
```

`paymentGateway`: `SCB` or `KBANK`. Used to add a QR top-up to a cash (or mixed) payment for the remaining balance.

**Implemented in KCW:** `TigerPayOpenApiClient.create_qr`. Companion uses this as QR-create fallback when `type=qr` returns no displayable QR. Mixed remainder QR is created on the Tiger box, not by Companion.

#### Cancel QR

`PUT api/open/v2/payment/:id/qr/cancel`  
(empty body in Postman)

**Not wrapped yet.**

#### Confirm payment

`PUT api/open/v2/payment/:id/confirm`  
(empty body)

Marks payment `success` after QR/cash completion (samples show QR and mixed).

**Implemented in KCW:** `TigerPayOpenApiClient.confirm_payment` (poller, including mixed cash+QR).

#### Cancel payment

`PUT api/open/v2/payment/:id/cancel`

```json
{
  "note": ""
}
```

**Implemented in KCW:** `TigerPayOpenApiClient.cancel_payment`.

### Typical device flows (from samples)

1. **Cash only** — Create `type=cash` → customer inserts cash (`cashList` / `totalPay` grow via current/get) → success or fail (e.g. insufficient change / dispenser error in `remark`).
2. **QR only** — Create `type=qr` → scan `dynamicQR` → Confirm → `success`, QR status `C`, payer fields filled.
3. **Mixed** — Create cash → partial cash → Create QR for remainder → pay QR → Confirm → `success`.

   KCW: Companion only `ส่งเงินสด`. The Tiger box handles the cash/QR split. Companion settles from webhook + poller confirm.

### KCW mapping (Open API)

| Tiger capability | KCW today |
| --- | --- |
| Create payment | Companion `POST /companion/bills/{pos_bill_id}/pay` |
| Create QR on existing cash payment | Tiger box UI (not Companion) |
| Get payment / current | Poller + reconcile |
| Cancel payment | `POST /companion/payments/{attempt_id}/cancel` |
| Webhook ingest | `POST /webhooks/tiger-pay` |
| List / categories | Not exposed |
| Cash inventory + change_status | Companion `GET /companion/cash` (cached snapshot) and `?live=true` (device GET, persist snapshot). kcw-v2 reads `tiger_pay.cash_snapshot` only. |
| Confirm QR / mixed | Poller confirm (`KBANK`) |

Companion stores the auth submitter on each payment/voucher attempt:
`submitted_by` = LINE user id, or `tailscale` for Tailscale access;
`submitted_by_name` = LINE display name, or `Tailscale account`.

---

## 2. Tiger Voucher API

Separate cloud API (not the device Open API). Host in Postman: `https://api.tigercashbox.com`.

Auth model differs: login once → Bearer token for voucher calls.

### Login

`POST /api/tigerpay/login`  
`multipart/form-data`: `username`, `password`, `mobile`

Response contains a token (Postman checks `success.token`, `token`, `data.token`, `access_token`, or `data.access_token`). Store as Bearer for subsequent calls.

### Create voucher

`POST /api/voucher/create`  
Bearer auth, `multipart/form-data`:

| Field | Sample | Notes |
| --- | --- | --- |
| `amount` | `10` | Voucher face value |
| `number_of_voucher` | `1` | Count to create |
| `start_date` | `28-05-2024` | `DD-MM-YYYY` |
| `expire_date` | `28-05-2024` | `DD-MM-YYYY` |
| `start_time` | `14:24:00` | |
| `expire_time` | `14:26:00` | |
| `ref_num` | `A1234567` | External reference |
| `category` | `ทดสอบ` | |
| `authen_required` | `1` | |
| `approved_required` | `1` | |
| `note` | | Postman export had a corrupted key `ืnote`; treat intended field as `note` |

### Show voucher

`GET /api/voucher/show/{{voucher_num}}`  
Bearer auth.

### Cancel voucher

`GET /api/voucher/cancel/{{voucher_num}}`  
Bearer auth (named “cancel” but method is GET in the collection).

### Query vouchers

`POST /api/voucher/query`  
Bearer auth, `multipart/form-data`:

| Field | Sample |
| --- | --- |
| `start_date` | `24-02-2023` |
| `end_date` | `24-02-2023` |
| `find_by` | `created_date` |
| `used` | `A` |

**Implemented in KCW (Companion CN cash-return):**

| Tiger capability | KCW |
| --- | --- |
| Login | `TigerVoucherApiClient.login` |
| Create voucher | Companion `POST /companion/bills/{pos_bill_id}/voucher` |
| Show voucher | Poll via `GET /companion/vouchers/{attempt_id}` |
| Cancel voucher | `POST /companion/vouchers/{attempt_id}/cancel` |
| Query vouchers | Client method only (not exposed in UI yet) |

CN / cash-return bill selection: any cashed row with negative `AFTERTAX` (including `KCN*` and normal `5K` / `8K` bills), plus unpaid `CN*` / `3CN*` (exclude `CNTF*` / `CNTAD*`). Amount = `abs(AFTERTAX)`. Stored in `tiger_pay.voucher_attempt` + `voucher_event` (see `docs/sql/tiger_pay_voucher_attempt.sql`).

---

## 3. Env vars (this repo)

| Variable | Used for |
| --- | --- |
| `TIGER_PAY_API_HOST` | Open API host |
| `TIGER_PAY_CLIENT_ID` | Open API JWT `clientId` |
| `TIGER_PAY_CLIENT_SECRET` | Open API JWT secret (+ webhook auth) |
| `TIGER_PAY_POLL_INTERVAL_SECONDS` | Companion poller |
| `TIGER_PAY_POLL_WEBHOOK_QUIET_SECONDS` | Skip device GETs this many seconds after a webhook (default `20`, `0` disables) |
| `TIGER_PAY_MAX_BODY_BYTES` | Webhook body limit |
| `TIGER_VOUCHER_API_HOST` | Voucher API host (default `https://api.tigercashbox.com`) |
| `TIGER_VOUCHER_USERNAME` | Voucher login username |
| `TIGER_VOUCHER_PASSWORD` | Voucher login password |
| `TIGER_VOUCHER_MOBILE` | Voucher login mobile |
| `TIGER_VOUCHER_AUTHEN_REQUIRED` | Create form flag (default `0`) |
| `TIGER_VOUCHER_APPROVED_REQUIRED` | Create form flag (default `0`) |
| `TIGER_VOUCHER_EXPIRE_HOURS` | Voucher validity window (default `8`) |

---

## 4. Source collections

Original uploads for this summary:

- Open API Payment v2 Postman collection
- Tiger Voucher Postman collection

If you add the JSON files under `docs/postman/`, keep secrets out of committed variable values (`client_id`, `client_secret`, passwords).

---

## 5. Production notes (HQ companion)

Cash Open API still **floors satang to whole baht**. That is an accepted vendor limit, not a Companion bug.

**POS `PAID` is not written back.** SIMAS close-out stays with the cashier. Companion uses `tiger_pay.payment_attempt` as the payment source of truth.

**Webhooks** should hit HQ `POST /webhooks/tiger-pay` (LAN or Tailscale, JWT + body digest). HQ ACKs `200` after auth/parse, then writes Supabase in the background so the cashbox is not blocked on ingest. If persist fails, Companion still has the 1.5s poller. After a webhook, the poller skips device GETs for `TIGER_PAY_POLL_WEBHOOK_QUIET_SECONDS` (default 20s). `/health/ready` reports webhook recency.

**Device payment ids were reset** around 1 Sep 2026 (`TIGER_PAY_ID_EPOCH`). Pre-epoch `unknown` rows are not polled by id.

Rotate `TIGER_VOUCHER_PASSWORD` to 8+ characters before unattended voucher use.

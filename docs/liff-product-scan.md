# LIFF product scanner (LINE ↔ kcw-v2)

End-to-end flow keeps LINE Reply API free (no Push for the happy path):

1. User sends `สแกนสินค้า` in LINE
2. `kcw-api` replies (Reply API) with a button opening the LIFF app
3. LIFF loads `kcw-v2` `/liff/scan-product`, user scans a barcode
4. LIFF calls `liff.sendMessages()` with `📦 สแกนสินค้า: <code>`
5. LINE delivers that as a normal user message → new webhook + fresh `replyToken`
6. `kcw-api` parses the callback deterministically and replies with product info (Reply API)

## Auth model

- **No Supabase / kcw-v2 login** inside LIFF for this flow (avoid double credential).
- `/liff/*` is a public path on kcw-v2 so LINE’s WebView can open it.
- Trust boundary: LINE webhook signature + `ops.line_access` in **kcw-api** when the callback message arrives.
- Plain browser visits can open the URL but cannot `liff.sendMessages` (and must never fall back to Push API).

## LINE Developers setup (manual)

LIFF apps **cannot** be added to a Messaging API channel anymore. Create / use a **LINE Login** channel under the **same provider** as the bot.

1. Open [LINE Developers](https://developers.line.biz/) → the **provider** that already owns your Messaging API bot channel.
2. Create a **LINE Login** channel (or reuse an existing one on that provider):
   - App type: **Web app**
   - Region / service area: whatever matches your account (Thailand etc.)
3. On that **LINE Login** channel → **LIFF** tab → **Add**:
   - **Size:** Full (recommended for camera)
   - **Endpoint URL:** `https://<your-kcw-v2-host>/liff/scan-product`
   - **Scopes:** `profile`, `openid`, and **`chat_message.write`** (required for `liff.sendMessages`; may be under **View all**)
   - **Module mode:** off
4. Copy the LIFF ID / LIFF URL (`https://liff.line.me/<LIFF_ID>`).
5. Keep the bot webhook on the **Messaging API** channel as today. The Login channel is only for LIFF; no need to move the bot.

LINE MINI App is recommended by LINE for some regions (Japan / approved Taiwan). If that doesn't apply, continue with LIFF on a LINE Login channel.

Without `chat_message.write`, the scanner UI can decode barcodes but cannot post the result back into the chat.

## Environment variables

### kcw-api

| Variable | Example | Purpose |
|----------|---------|---------|
| `KCW_LIFF_PRODUCT_SCANNER_URL` | `https://liff.line.me/1234567890-AbCdEfGh` | URI opened by the Reply button |

Also requires the existing `LINE_CHANNEL_SECRET` / `LINE_CHANNEL_ACCESS_TOKEN`.

### kcw-v2

| Variable | Example | Purpose |
|----------|---------|---------|
| `NEXT_PUBLIC_LINE_LIFF_PRODUCT_SCANNER_ID` | `1234567890-AbCdEfGh` | LIFF ID for `liff.init` |

Do **not** put channel secret, channel access token, or Supabase service keys in `NEXT_PUBLIC_*`.

## Callback contract

```
📦 สแกนสินค้า: <barcode>
```

Example: `📦 สแกนสินค้า: 22010585`

- Formatted in `kcw-v2` (`src/lib/liff/product-scan-contract.ts`)
- Parsed in `kcw-api` (`src/liff/product_scan_contract.py`) before AI / free-text search
- Lookup reuses the existing `เช็ค {bcode}` path (`handle_check_response`)

Scanned values are treated as product codes (`BCODE`) consistent with the current LINE bot.

## Local / testing notes

- `/liff/*` is a public path on kcw-v2 (no Supabase login) so LINE’s WebView can open it.
- Opening the page outside LINE can still exercise the camera for UI testing; sending back to chat requires the LIFF in-client context.
- Unit tests: `pytest tests/test_product_scan.py` (kcw-api) and `npm test` LIFF contract tests (kcw-v2).
- End-to-end needs a deployed HTTPS kcw-v2 endpoint registered as the LIFF endpoint (LINE does not accept `localhost` LIFF endpoints without a tunnel such as ngrok).

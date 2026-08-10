"""Product scan via LINE camera / camera-roll (kcw-api barcode decode).

End-to-end flow keeps LINE Reply API free (no Push for the happy path):

1. User sends `สแกนสินค้า` (or `สแกน` / `scan` / …) in LINE
2. `kcw-api` replies (Reply API) with quick replies: camera + cameraRoll + cancel
3. User takes a photo or picks an image from the album
4. LINE delivers an image message → webhook + fresh `replyToken`
5. `kcw-api` downloads the image, decodes the barcode (pyzbar), runs product search
6. Bot replies with the same product-search answer as typing the barcode directly

## Why not LIFF?

The earlier LIFF scanner posted `📦 สแกนสินค้า: <code>` and then ran the heavier
`เช็ค` lookup. Camera + server-side decode uses the fast product-search path
(same as posting a bare barcode) and needs no LINE Login / LIFF app.

## Auth model

- Trust boundary: LINE webhook signature + `ops.line_access` in **kcw-api**
- No kcw-v2 / Supabase login required for this flow

## LINE Developers setup

No LIFF app is required. Use the existing Messaging API channel webhook.

Quick-reply actions used:

- `camera` — open LINE camera
- `cameraRoll` — pick from album
- `message` — cancel / scan again / check product

## Environment variables

| Variable | Example | Purpose |
|----------|---------|---------|
| `PRODUCT_SCAN_SESSION_TTL_SECONDS` | `600` | How long the scan session stays open |
| `LINE_CHANNEL_SECRET` | … | Webhook signature verification |
| `LINE_CHANNEL_ACCESS_TOKEN` | … | Download image content + Reply API |

System dependency for barcode decode: `libzbar0` (Debian/Ubuntu) so `pyzbar` can load.

Python packages: `pillow`, `pyzbar` (see `requirements.txt`).

## Command aliases

`สแกน`, `สแกนสินค้า`, `สแกนบาร์โค้ด`, `scan`, `scan product`, `scan barcode`

## Lookup behavior

Decoded barcodes go through `handle_product_query_response` (product search),
not the heavier `เช็ค` report. After a hit, quick replies offer `เช็ค {bcode}`
if the user wants the full order-check view.

## Legacy LIFF callback

Text messages shaped like `📦 สแกนสินค้า: <code>` are still parsed and routed to
product search for older clients, but new installs should use camera / photo only.

## Local / testing notes

- Unit tests: `pytest tests/test_product_scan.py`
- Decode needs `libzbar0` installed on the host
- End-to-end needs a real LINE chat + Messaging API credentials

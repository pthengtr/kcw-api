# KCW PRN Printer

Windows helper for transfer-desk sticker printing: double-click a `.prn` → preview stickers / barcode quantities → send RAW to a local TSC (or other) printer.

Served by the **transfer** app (`kcw-transfer`, typically `:8792`).

## For transfer users

On the sticker print screen, expand **ตัวช่วยพิมพ์ .prn บน Windows**, or open:

`http://<transfer-host>:8792/tools/prn-printer/`

One-line install / update / replace (PowerShell):

```powershell
irm http://<transfer-host>:8792/tools/prn-printer/install.ps1 | iex
```

Re-running the same command **replaces** the previous install under `%LOCALAPPDATA%\KCW\PrnPrinter` and keeps the `.prn` file association.

## Local / offline install

From this folder:

```powershell
powershell -ExecutionPolicy Bypass -File .\Install-PrnPrinter.ps1
```

## API endpoints (transfer app)

| Path | Purpose |
|------|---------|
| `GET /tools/prn-printer/` | Install instructions (HTML) |
| `GET /tools/prn-printer/version` | `{ version, notes, ... }` |
| `GET /tools/prn-printer/install.ps1` | Bootstrap installer |
| `GET /tools/prn-printer/download.zip` | Full package zip |

## Third-party

Barcode decode uses [ZXing.Net](https://github.com/micjahn/ZXing.Net) (`lib/zxing*.dll`, Apache-2.0).

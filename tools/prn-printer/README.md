# KCW PRN Printer

Windows helper for transfer sticker printing: double-click a `.prn` to preview and print.

Served by the **transfer** app (`kcw-transfer`, typically `:8792`).

## For ops (simple)

1. Download `KCW-PRN-Install-v….cmd` from the sticker screen or `/tools/prn-printer/install.cmd`
2. Double-click it
3. Done — next time just double-click downloaded `.prn` files

To update later: download and double-click again (replaces the old install).

## API

| Path | Purpose |
|------|---------|
| `GET /tools/prn-printer/` | Short install page |
| `GET /tools/prn-printer/install.cmd` | **Double-click installer** (download) |
| `GET /tools/prn-printer/install.ps1` | PowerShell bootstrap (advanced) |
| `GET /tools/prn-printer/version` | Version JSON |
| `GET /tools/prn-printer/download.zip` | Full package zip |

## Third-party

Barcode decode uses [ZXing.Net](https://github.com/micjahn/ZXing.Net) (`lib/zxing*.dll`, Apache-2.0).

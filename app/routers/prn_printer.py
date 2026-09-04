from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

router = APIRouter(prefix="/tools/prn-printer", tags=["prn-printer"])

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "tools" / "prn-printer"

_ZIP_NAMES = (
    "PrintPrn.ps1",
    "PrintPrn.cmd",
    "Install-PrnPrinter.ps1",
    "Uninstall-PrnPrinter.ps1",
    "VERSION.json",
    "README.md",
    "index.html",
    "lib/zxing.dll",
    "lib/zxing.presentation.dll",
    "lib/NOTICE.txt",
)


def _require_package() -> Path:
    if not _PACKAGE_DIR.is_dir():
        raise HTTPException(status_code=404, detail="PRN printer package not found")
    return _PACKAGE_DIR


def _version_payload() -> dict:
    path = _require_package() / "VERSION.json"
    if not path.is_file():
        return {"name": "kcw-prn-printer", "version": "0.0.0"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid VERSION.json: {exc}") from exc


def _public_base(request: Request) -> str:
    # Prefer proxy headers when deployed behind Railway/nginx
    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if forwarded_host:
        proto = forwarded_proto or request.url.scheme or "https"
        return f"{proto}://{forwarded_host}".rstrip("/")
    return str(request.base_url).rstrip("/")


@router.get("/", response_class=HTMLResponse)
async def prn_printer_page() -> HTMLResponse:
    index = _require_package() / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Install page missing")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


@router.get("/version")
async def prn_printer_version() -> dict:
    return _version_payload()


@router.get("/install.ps1", response_class=PlainTextResponse)
async def prn_printer_install_ps1(request: Request) -> PlainTextResponse:
    """One-liner bootstrap: irm .../install.ps1 | iex"""
    base = _public_base(request)
    body = f"""#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$BaseUrl = '{base}'
$env:KCW_PRN_INSTALL_BASE = $BaseUrl
$installerUrl = "$BaseUrl/tools/prn-printer/files/Install-PrnPrinter.ps1"
$tmp = Join-Path $env:TEMP ("Install-PrnPrinter-" + [guid]::NewGuid().ToString('N') + ".ps1")
try {{
  Invoke-WebRequest -Uri $installerUrl -OutFile $tmp -UseBasicParsing
  & $tmp -BaseUrl $BaseUrl
  if ($LASTEXITCODE -and $LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}
}}
finally {{
  Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue
}}
"""
    return PlainTextResponse(
        content=body,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'inline; filename="install.ps1"'},
    )


@router.get("/download.zip")
async def prn_printer_download_zip() -> Response:
    root = _require_package()
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for rel in _ZIP_NAMES:
            path = root / rel
            if not path.is_file():
                continue
            zf.write(path, arcname=f"prn-printer/{rel.replace(chr(92), '/')}")
    data = buf.getvalue()
    version = _version_payload().get("version", "0.0.0")
    filename = f"kcw-prn-printer-{version}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/files/{file_path:path}")
async def prn_printer_raw_file(file_path: str) -> Response:
    """Optional direct file access for debugging / manual copy."""
    root = _require_package().resolve()
    target = (root / file_path).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media = "application/octet-stream"
    if target.suffix.lower() in {".ps1", ".cmd", ".md", ".txt", ".json", ".html"}:
        media = "text/plain; charset=utf-8"
        if target.suffix.lower() == ".html":
            media = "text/html; charset=utf-8"
        if target.suffix.lower() == ".json":
            media = "application/json"
    return Response(content=target.read_bytes(), media_type=media)

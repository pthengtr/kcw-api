from __future__ import annotations

import json
import os
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response

router = APIRouter(prefix="/tools/windows-remote", tags=["windows-remote"])

_PACKAGE_DIR = Path(__file__).resolve().parents[2] / "tools" / "windows-remote"


def _require_package() -> Path:
    if not _PACKAGE_DIR.is_dir():
        raise HTTPException(status_code=404, detail="Windows remote package not found")
    return _PACKAGE_DIR


def _version_payload() -> dict:
    path = _require_package() / "VERSION.json"
    if not path.is_file():
        return {"name": "kcw-windows-remote", "version": "0.0.0"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid VERSION.json: {exc}") from exc


def _public_base(request: Request) -> str:
    # Explicit override (optional). Otherwise use the Host the client actually hit
    # so LAN vs Railway downloads both bake the right origin into install.cmd.
    configured = (os.getenv("WINDOWS_REMOTE_PUBLIC_BASE_URL") or "").strip().rstrip("/")
    if configured:
        return configured

    forwarded_proto = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip()
    forwarded_host = (request.headers.get("x-forwarded-host") or "").split(",")[0].strip()
    if forwarded_host:
        proto = forwarded_proto or request.url.scheme or "https"
        return f"{proto}://{forwarded_host}".rstrip("/")

    base = str(request.base_url).rstrip("/")
    host = (request.url.hostname or "").lower()
    if host in {"127.0.0.1", "localhost"}:
        railway_domain = (os.getenv("RAILWAY_PUBLIC_DOMAIN") or "").strip().rstrip("/")
        if railway_domain:
            if "://" not in railway_domain:
                railway_domain = f"https://{railway_domain}"
            return railway_domain
        public = (os.getenv("PUBLIC_BASE_URL") or "").strip().rstrip("/")
        if public:
            return public
    return base


def _auth_key() -> str:
    return (os.getenv("KCW_TAILSCALE_AUTHKEY") or os.getenv("TAILSCALE_AUTHKEY") or "").strip()


@router.get("/", response_class=HTMLResponse)
async def windows_remote_page() -> HTMLResponse:
    index = _require_package() / "index.html"
    if not index.is_file():
        raise HTTPException(status_code=404, detail="Install page missing")
    return HTMLResponse(content=index.read_text(encoding="utf-8"))


@router.get("/version")
async def windows_remote_version() -> dict:
    return _version_payload()


@router.get("/install.ps1", response_class=PlainTextResponse)
async def windows_remote_install_ps1(request: Request) -> PlainTextResponse:
    """One-liner bootstrap: irm .../install.ps1 | iex  (elevated)."""
    base = _public_base(request)
    auth_key = _auth_key()
    # Keep auth key out of process listings where possible by passing as env to child.
    auth_assign = (
        f"$env:KCW_TAILSCALE_AUTHKEY = '{auth_key.replace(chr(39), chr(39)+chr(39))}'\n"
        if auth_key
        else ""
    )
    body = f"""#Requires -Version 5.1
$ErrorActionPreference = 'Stop'
$BaseUrl = '{base}'
$env:KCW_WINDOWS_REMOTE_BASE = $BaseUrl
{auth_assign}$installerUrl = "$BaseUrl/tools/windows-remote/files/Install-WindowsRemote.ps1"
$tmp = Join-Path $env:TEMP ("Install-WindowsRemote-" + [guid]::NewGuid().ToString('N') + ".ps1")
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


@router.get("/install.cmd")
async def windows_remote_install_cmd(request: Request) -> Response:
    """Double-clickable Windows installer bootstrap (download then elevated run)."""
    base = _public_base(request).rstrip("/")
    boot_url = f"{base}/tools/windows-remote/install.ps1"
    body = f"""@echo off
setlocal
title KCW Windows Remote Setup
net session >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
  echo.
  echo  Please right-click this file and choose "Run as administrator".
  echo.
  pause
  exit /b 1
)
set "BASE={base}"
set "BOOT=%TEMP%\\kcw-windows-remote-boot.ps1"
echo.
echo  KCW Windows Remote - installing Tailscale + OpenSSH...
echo  Source: %BASE%
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "Invoke-WebRequest -Uri '{boot_url}' -OutFile $env:TEMP\\kcw-windows-remote-boot.ps1 -UseBasicParsing; & $env:TEMP\\kcw-windows-remote-boot.ps1"
set ERR=%ERRORLEVEL%
del /q "%BOOT%" >nul 2>nul
if %ERR% NEQ 0 (
  echo.
  echo  Install failed. Ask IT / admin for help.
  echo.
  pause
  exit /b %ERR%
)
echo.
echo  Done. You can close this window.
echo.
pause
exit /b 0
"""
    version = _version_payload().get("version", "0.0.0")
    filename = f"KCW-Windows-Remote-v{version}.cmd"
    return Response(
        content=body.encode("ascii", errors="replace"),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.get("/files/{file_path:path}")
async def windows_remote_raw_file(file_path: str) -> Response:
    root = _require_package().resolve()
    target = (root / file_path).resolve()
    if not str(target).startswith(str(root)) or not target.is_file():
        raise HTTPException(status_code=404, detail="File not found")
    media = "application/octet-stream"
    suffix = target.suffix.lower()
    if suffix in {".ps1", ".cmd", ".md", ".txt"}:
        media = "text/plain; charset=utf-8"
    elif suffix == ".html":
        media = "text/html; charset=utf-8"
    elif suffix == ".json":
        media = "application/json"
    elif target.name == "authorized_keys":
        media = "text/plain; charset=utf-8"
    return Response(content=target.read_bytes(), media_type=media)

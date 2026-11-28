"""Render HQ purchase-order sheet HTML to a real PDF (no browser print dialog)."""

from __future__ import annotations

import base64
import logging
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx

from src.hq_po.guards import HqPoError
from src.hq_po.sheet import build_sheet_forms

logger = logging.getLogger(__name__)

_UNSAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")
_IMG_TAG = re.compile(r"<img\b[^>]*>", re.IGNORECASE)
_IMG_SRC = re.compile(r"""\bsrc=(["'])(https?://.*?)\1""", re.IGNORECASE)


def sheet_pdf_filename(groups: list[dict[str, Any]]) -> str:
    """PO number when known, e.g. HP6911-CD8B.pdf."""
    for group in groups or []:
        if not isinstance(group, dict):
            continue
        docno = str(group.get("docno") or "").strip()
        if docno:
            safe = _UNSAFE_NAME.sub("-", docno).strip("-._") or "PO"
            return f"{safe}.pdf"
    return "PO.pdf"


def content_disposition(filename: str) -> str:
    """ASCII filename plus RFC 5987 fallback for non-ASCII PO numbers."""
    ascii_name = filename.encode("ascii", "replace").decode("ascii").replace("?", "_")
    if not ascii_name.lower().endswith(".pdf"):
        ascii_name = f"{ascii_name}.pdf"
    if ascii_name == filename:
        return f'inline; filename="{ascii_name}"'
    return f"inline; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def wrap_sheet_document(fragment: str) -> str:
    """Full HTML document so headless Chrome prints the same sheet CSS.

    Use local fonts only — a Google Fonts <link> can stall headless Chrome
    for tens of seconds and make mobile clients report "Failed to fetch".
    """
    body = fragment or ""
    return f"""<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<style>
  html, body {{
    margin: 0;
    padding: 0;
    background: #fff;
    font-family: "Noto Sans Thai", "Noto Sans", Prompt, sans-serif;
  }}
</style>
</head>
<body>
{body}
</body>
</html>
"""


def _chrome_bin() -> str | None:
    configured = (os.environ.get("HQ_PO_CHROME_BIN") or "").strip()
    if configured:
        return configured
    for name in ("google-chrome", "chromium", "chromium-browser", "google-chrome-stable"):
        found = shutil.which(name)
        if found:
            return found
    return None


def _data_uri_for(url: str, *, timeout_s: float = 2.5) -> str | None:
    """Fetch a remote image for embedding. Missing/slow URLs become None."""
    try:
        with httpx.Client(timeout=timeout_s, follow_redirects=True) as client:
            resp = client.get(url)
        if resp.status_code != 200 or not resp.content:
            return None
        ctype = (resp.headers.get("content-type") or "image/jpeg").split(";")[0].strip()
        if not ctype.startswith("image/"):
            ctype = "image/jpeg"
        return f"data:{ctype};base64,{base64.b64encode(resp.content).decode('ascii')}"
    except Exception:
        logger.debug("hq po pdf image inline failed url=%s", url[:160], exc_info=True)
        return None


def inline_remote_images(html: str) -> str:
    """Embed http(s) <img> as data URIs.

    Headless Chrome printing a file:// document stalls ~20s+ on remote images
    (even fast 4xx), which makes mobile clients time out with "Failed to fetch".
    """
    cache: dict[str, str | None] = {}

    def repl(match: re.Match[str]) -> str:
        tag = match.group(0)
        src = _IMG_SRC.search(tag)
        if not src:
            return tag
        url = src.group(2)
        if url not in cache:
            cache[url] = _data_uri_for(url)
        data = cache[url]
        if not data:
            return ""
        quote = src.group(1)
        return tag[: src.start()] + f"src={quote}{data}{quote}" + tag[src.end() :]

    return _IMG_TAG.sub(repl, html or "")


def html_to_pdf(html: str, *, timeout_s: float = 60.0) -> bytes:
    """Print an HTML document to PDF bytes via headless Chrome."""
    chrome = _chrome_bin()
    if not chrome:
        raise HqPoError("pdf_unavailable", "เครื่องเซิร์ฟเวอร์ยังไม่มีโปรแกรมสร้าง PDF")

    with tempfile.TemporaryDirectory(prefix="hq-po-pdf-") as tmp:
        root = Path(tmp)
        html_path = root / "sheet.html"
        pdf_path = root / "sheet.pdf"
        html_path.write_text(html, encoding="utf-8")
        cmd = [
            chrome,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--disable-extensions",
            "--disable-dev-shm-usage",
            "--hide-scrollbars",
            "--no-pdf-header-footer",
            f"--print-to-pdf={pdf_path}",
            html_path.resolve().as_uri(),
        ]
        # Trusted HQ HTML only; systemd/user services often lack a sandbox profile.
        if (os.environ.get("HQ_PO_CHROME_SANDBOX") or "").strip().lower() not in {
            "1",
            "true",
            "yes",
            "on",
        }:
            cmd.insert(1, "--no-sandbox")
        try:
            completed = subprocess.run(
                cmd,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout_s,
            )
        except subprocess.TimeoutExpired as exc:
            raise HqPoError("pdf_failed", "สร้าง PDF ใช้เวลานานเกินไป") from exc
        except OSError as exc:
            logger.warning("hq po chrome launch failed", exc_info=True)
            raise HqPoError("pdf_failed", "เปิดโปรแกรมสร้าง PDF ไม่สำเร็จ") from exc

        if completed.returncode != 0 or not pdf_path.is_file() or pdf_path.stat().st_size < 64:
            err = (completed.stderr or completed.stdout or "").strip()
            logger.warning(
                "hq po chrome pdf failed code=%s err=%s",
                completed.returncode,
                err[:500],
            )
            raise HqPoError("pdf_failed", "สร้าง PDF ไม่สำเร็จ")
        return pdf_path.read_bytes()


def build_sheet_pdf(groups: list[dict[str, Any]], variant: str = "simple") -> tuple[bytes, str]:
    """Return (pdf_bytes, filename) for the selected sheet variant."""
    forms = build_sheet_forms(groups)
    key = "full_html" if str(variant or "").strip().lower() == "full" else "simple_html"
    fragment = forms.get(key) or ""
    if not fragment.strip():
        raise HqPoError("empty", "ไม่มีรายการสำหรับใบสั่งซื้อ")
    doc = inline_remote_images(wrap_sheet_document(fragment))
    pdf = html_to_pdf(doc)
    return pdf, sheet_pdf_filename(groups)

"""Platform TTS helpers for the cloud QR announce worker."""

from __future__ import annotations

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

logger = logging.getLogger("kcw.tiger_pay.announce_tts")

# Natural Thai neural voice used when Windows has no th-TH SAPI voice.
# PremwadeeNeural currently returns NoAudioReceived from the cashbox network;
# NiwatNeural synthesizes reliably there.
DEFAULT_EDGE_VOICE = "th-TH-NiwatNeural"


def format_amount_for_speech(amount: Any) -> str:
    try:
        n = float(amount)
    except (TypeError, ValueError):
        return str(amount or "")
    if abs(n - round(n)) < 0.005:
        return str(int(round(n)))
    return f"{n:.2f}"


def cloud_qr_success_phrase(row: dict[str, Any]) -> str:
    amount = row.get("paid_amount")
    if amount is None or amount == "":
        amount = row.get("amount")
    spoken = format_amount_for_speech(amount)
    return f"ชำระเงินผ่าน QR สำเร็จ จำนวน {spoken} บาท"


def speak_thai(text: str, *, dry_run: bool = False) -> None:
    cleaned = str(text or "").strip()
    if not cleaned:
        return
    if dry_run:
        logger.info("announce dry-run: %s", cleaned)
        print(f"[announce dry-run] {cleaned}", flush=True)
        return

    if sys.platform.startswith("win"):
        if _windows_has_thai_sapi():
            _speak_windows_sapi(cleaned)
            return
        # Cashbox currently ships English SAPI only; edge-tts speaks Thai well.
        _speak_windows_edge_tts(cleaned)
        return

    if _speak_linux_espeak(cleaned):
        return
    raise RuntimeError(
        "No TTS backend available (Windows SAPI/edge-tts or espeak-ng required)"
    )


def _creationflags() -> int:
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
    return 0


def _windows_has_thai_sapi() -> bool:
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "$hit = $false; "
        "foreach ($v in $s.GetInstalledVoices()) { "
        "  if ($v.VoiceInfo.Culture.Name -like 'th*') { $hit = $true } "
        "}; "
        "$s.Dispose(); "
        "if ($hit) { exit 0 } else { exit 1 }"
    )
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps,
        ],
        capture_output=True,
        timeout=20,
        check=False,
        creationflags=_creationflags(),
    )
    return proc.returncode == 0


def _speak_windows_sapi(text: str) -> None:
    # Built-in System.Speech; Thai voice must be installed on the till PC.
    ps = (
        "Add-Type -AssemblyName System.Speech; "
        "$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; "
        "try { "
        "$s.SelectVoiceByHints("
        "[System.Speech.Synthesis.VoiceGender]::NotSet, "
        "[System.Speech.Synthesis.VoiceAge]::NotSet, 0, "
        "[Globalization.CultureInfo]::GetCultureInfo('th-TH')"
        ") "
        "} catch { }; "
        "$s.Rate = 0; "
        "$s.Speak([Console]::In.ReadToEnd()); "
        "$s.Dispose()"
    )
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps,
        ],
        input=text,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
        creationflags=_creationflags(),
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"Windows SAPI speak failed: {err}")


def _speak_windows_edge_tts(text: str) -> None:
    try:
        import edge_tts  # type: ignore
    except ImportError as exc:
        raise RuntimeError(
            "edge-tts is required for Thai speech when no th-TH SAPI voice is installed"
        ) from exc

    import asyncio

    voice = (
        os.getenv("ANNOUNCE_EDGE_VOICE", "").strip() or DEFAULT_EDGE_VOICE
    )
    tmp = tempfile.NamedTemporaryFile(prefix="kcw-announce-", suffix=".mp3", delete=False)
    path = Path(tmp.name)
    tmp.close()
    try:

        async def _synth() -> None:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(str(path))

        asyncio.run(_synth())
        _play_mp3_windows(path)
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            logger.debug("temp mp3 cleanup failed", exc_info=True)


def _play_mp3_windows(path: Path) -> None:
    # WMPlayer COM is available on the Tiger cashbox Windows image.
    escaped = str(path).replace("'", "''")
    ps = (
        f"$p = New-Object -ComObject WMPlayer.OCX.7; "
        f"$p.URL = '{escaped}'; "
        f"$p.settings.volume = 100; "
        f"$p.controls.play(); "
        f"$deadline = (Get-Date).AddSeconds(60); "
        f"Start-Sleep -Milliseconds 300; "
        f"while ($p.playState -eq 3 -and (Get-Date) -lt $deadline) {{ "
        f"  Start-Sleep -Milliseconds 200 "
        f"}}; "
        f"$p.close()"
    )
    proc = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-NonInteractive",
            "-ExecutionPolicy",
            "Bypass",
            "-Command",
            ps,
        ],
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
        creationflags=_creationflags(),
    )
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"Windows mp3 playback failed: {err}")


def _speak_linux_espeak(text: str) -> bool:
    for binary, args in (
        ("espeak-ng", ["-v", "th", "--", text]),
        ("espeak", ["-v", "th", "--", text]),
    ):
        path = shutil.which(binary)
        if not path:
            continue
        proc = subprocess.run(
            [path, *args],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if proc.returncode == 0:
            return True
        logger.warning(
            "%s failed rc=%s err=%s",
            binary,
            proc.returncode,
            (proc.stderr or "").strip(),
        )
    return False


def env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "on"}


def env_float(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or not str(raw).strip():
        return default
    try:
        return float(str(raw).strip())
    except ValueError:
        return default


def amount_as_decimal(value: Any) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except Exception:
        return None

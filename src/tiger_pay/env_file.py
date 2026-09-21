"""Best-effort rewrite of KEY=value lines in a dotenv file."""

from __future__ import annotations

from pathlib import Path


def upsert_env_key(path: Path, key: str, value: str) -> bool:
    """
    Set ``key=value`` in ``path``, preserving other lines.

    Returns True when the file content changed.
    """
    key = key.strip()
    if not key:
        raise ValueError("env key must not be empty")
    new_line = f"{key}={value}"

    if path.exists():
        text = path.read_text(encoding="utf-8")
    else:
        text = ""

    lines = text.splitlines()
    found = False
    out: list[str] = []
    for raw in lines:
        stripped = raw.lstrip()
        if stripped.startswith("#") or "=" not in raw:
            out.append(raw)
            continue
        existing_key = raw.split("=", 1)[0].strip()
        if existing_key != key:
            out.append(raw)
            continue
        found = True
        out.append(new_line)

    if not found:
        out.append(new_line)

    new_text = "\n".join(out)
    if text and not text.endswith("\n"):
        # Keep files that previously omitted a trailing newline as-is only if unchanged.
        pass
    if not new_text.endswith("\n"):
        new_text += "\n"

    old_normalized = text if text.endswith("\n") or not text else text + "\n"
    if old_normalized == new_text:
        return False

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new_text, encoding="utf-8")
    return True

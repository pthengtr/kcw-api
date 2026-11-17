"""SQL Server nvarchar length helpers (UTF-16 code units)."""

from __future__ import annotations


def sql_nvarchar_len(text: str) -> int:
    """SQL Server nvarchar length: supplementary-plane chars count as 2."""
    return sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)


def truncate_sql_nvarchar(text: str, max_len: int) -> str:
    """Truncate so the value fits an nvarchar(max_len) column."""
    if max_len <= 0:
        return ""
    out: list[str] = []
    used = 0
    for ch in text:
        units = 2 if ord(ch) > 0xFFFF else 1
        if used + units > max_len:
            break
        out.append(ch)
        used += units
    return "".join(out)

"""Yesterday's TAR net from billgen.fin_*, the same rows the Drive Excel is built from.

CNTAR / 3CNTAR amounts are stored negative. The daily net is TAR + CNTAR,
matching the Excel สรุป TAR CNTAR sheet (sales + returns).
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from sqlalchemy import text

BANGKOK = ZoneInfo("Asia/Bangkok")

_COMMAND = re.compile(r"^โอน\s*tar(?:\s+(\S+))?$", re.IGNORECASE)
_DATE_ERROR = "วันที่ไม่ถูกต้องครับ ใช้ 2026-10-30 หรือ 30/10/2026"

_SUMMARY_SQL = text(
    """
    select
        (select coalesce(sum(amount), 0) from billgen.fin_tar_lines where billdate = :d),
        (select count(*) from billgen.fin_tar_lines where billdate = :d),
        (select coalesce(sum(amount), 0) from billgen.fin_cntar_lines where billdate = :d),
        (select count(*) from billgen.fin_cntar_lines where billdate = :d),
        (select coalesce(sum(amount), 0) from billgen.fin_3tar_lines where billdate = :d),
        (select count(*) from billgen.fin_3tar_lines where billdate = :d),
        (select coalesce(sum(amount), 0) from billgen.fin_3cntar_lines where billdate = :d),
        (select count(*) from billgen.fin_3cntar_lines where billdate = :d),
        billgen.max_fin_billdate()
    """
)


def bangkok_today(now: datetime | None = None) -> date:
    current = now or datetime.now(BANGKOK)
    return current.astimezone(BANGKOK).date()


def is_tar_transfer_command(text: str) -> bool:
    return _COMMAND.fullmatch((text or "").strip()) is not None


def _normalize_year(year: int, today: date) -> int:
    if year >= 2400:
        return year - 543
    if year < 100:
        century = 2000 + year
        if abs(century - today.year) <= 1:
            return century
        return 2500 + year - 543
    return year


def parse_user_date(raw: str, *, today: date | None = None) -> date:
    token = (raw or "").strip()
    today = today or bangkok_today()
    parsed: date | None = None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            parsed = datetime.strptime(token, fmt).date()
            break
        except ValueError:
            continue

    if parsed is None:
        match = re.fullmatch(r"(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})", token)
        if not match:
            raise ValueError(_DATE_ERROR)
        day, month, year = (int(match.group(i)) for i in (1, 2, 3))
        try:
            parsed = date(year, month, day)
        except ValueError as exc:
            raise ValueError(_DATE_ERROR) from exc

    year = _normalize_year(parsed.year, today)
    if year == parsed.year:
        return parsed
    try:
        return date(year, parsed.month, parsed.day)
    except ValueError as exc:
        raise ValueError(_DATE_ERROR) from exc


def command_date(text: str, *, today: date | None = None) -> date:
    match = _COMMAND.fullmatch((text or "").strip())
    if match is None:
        raise ValueError("ไม่ใช่คำสั่งโอน TAR ครับ")
    today = today or bangkok_today()
    raw = match.group(1)
    if not raw:
        return today - timedelta(days=1)
    return parse_user_date(raw, today=today)


def _decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def format_money(value: Decimal) -> str:
    quantized = _decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return f"{quantized:,.2f}"


def load_tar_transfer(engine, target: date) -> dict:
    with engine.connect() as conn:
        row = conn.execute(_SUMMARY_SQL, {"d": target}).one()

    tar, n_tar, cntar, n_cntar, tar3, n_tar3, cntar3, n_cntar3, latest = row
    count = int(n_tar) + int(n_cntar) + int(n_tar3) + int(n_cntar3)
    latest_date = latest if isinstance(latest, date) else None
    ready = count > 0 or (latest_date is not None and latest_date >= target)
    hq_net = _decimal(tar) + _decimal(cntar)
    syp_net = _decimal(tar3) + _decimal(cntar3)
    return {
        "date": target.isoformat(),
        "ready": ready,
        "latest": latest_date.isoformat() if latest_date else None,
        "tar": _decimal(tar),
        "cntar": _decimal(cntar),
        "tar3": _decimal(tar3),
        "cntar3": _decimal(cntar3),
        "hq_net": hq_net,
        "syp_net": syp_net,
    }


def format_tar_transfer_message(summary: dict) -> str:
    if not summary.get("ready"):
        lines = [f"ยังไม่มีข้อมูล TAR ของวันที่ {summary['date']}"]
        if summary.get("latest"):
            lines.append(f"ข้อมูลล่าสุดถึงวันที่ {summary['latest']}")
        return "\n".join(lines)
    return (
        f"โอน TAR วันที่ {summary['date']}\n"
        f"TAR-CNTAR: {format_money(summary['hq_net'])}\n"
        f"3TAR-3CNTAR: {format_money(summary['syp_net'])}"
    )

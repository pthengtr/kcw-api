from collections import OrderedDict
from datetime import datetime

from src.queries import get_top_matched_locations_with_products

BRANCH_ALIASES = {
    "HQ": "HQ",
    "SYP": "SYP",
    "สนญ": "HQ",
    "สำนักงานใหญ่": "HQ",
    "สาขา": "SYP",
}

BRANCH_LABEL = {
    "HQ": "สนญ",
    "SYP": "สาขา",
}

def is_location_request(text: str) -> bool:
    return (text or "").strip().startswith("ที่เก็บ ")


def parse_location_request(text: str) -> tuple[str | None, str | None]:
    parts = (text or "").strip().split(maxsplit=2)
    if len(parts) < 3:
        return None, None

    branch_raw = parts[1].strip()
    location_kw = parts[2].strip()

    branch = BRANCH_ALIASES.get(branch_raw.upper()) or BRANCH_ALIASES.get(branch_raw)
    if not branch or not location_kw:
        return None, None

    return branch, location_kw


def _fmt_updated_at(value) -> str:
    if not value:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    return str(value)


def handle_location_query(engine, user_text: str) -> str:
    branch, location_kw = parse_location_request(user_text)

    if not branch or not location_kw:
        return (
            "กรุณาระบุคำสั่งเป็น:\n"
            "ที่เก็บ [HQ|SYP] [location]\n\n"
            "เช่น:\n"
            "• ที่เก็บ HQ A1\n"
            "• ที่เก็บ SYP B-02"
        )

    rows = get_top_matched_locations_with_products(
        engine,
        branch=branch,
        location_keyword=location_kw,
        max_locations=3,
        max_products_per_location=100,
    )

    if not rows:
        return f"ไม่พบสินค้าที่เก็บ {branch} ตรงกับ '{location_kw}'"

    grouped = OrderedDict()
    latest_updated = None

    for row in rows:
        matched_location = str(row.get("MATCHED_LOCATION") or "-").strip() or "-"
        grouped.setdefault(matched_location, []).append(row)

        updated_at = row.get("UPDATED_AT")
        if updated_at is not None:
            if latest_updated is None or updated_at > latest_updated:
                latest_updated = updated_at

    total_location_matches = 0
    if rows:
        total_location_matches = int(rows[0].get("TOTAL_LOCATION_MATCHES") or 0)

    shown_location_count = len(grouped)

    branch_label = BRANCH_LABEL.get(branch, branch)

    lines = [
        f"ที่เก็บ {branch_label} ค้นหา: {location_kw}",
        f"อัปเดตล่าสุด: {_fmt_updated_at(latest_updated)}",
        f"พบที่เก็บทั้งหมด {total_location_matches:,} จุด แสดง {shown_location_count:,} จุดแรก",
        "",
    ]

    for idx, (loc, items) in enumerate(grouped.items(), start=1):
        lines.append(f"{idx}. {loc}")
        for item in items:
            bcode = str(item.get("BCODE") or "-").strip() or "-"
            descr = str(item.get("DESCR") or "-").strip() or "-"
            qty = float(item.get("QTY") or 0)
            lines.append(f"- {bcode} | {descr} | คงเหลือ: {qty:,.0f}")
        lines.append("")

    return "\n".join(lines).rstrip()
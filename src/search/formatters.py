import pandas as pd
from zoneinfo import ZoneInfo
from datetime import datetime

LOCAL_TZ = ZoneInfo("Asia/Singapore")

CODE1_DISPLAY_MAP = {
    "A": {"name": "ถ่าน", "size_labels": ["สูง", "กว้าง"]},
    "C": {"name": "ซีล", "size_labels": ["ใน", "นอก", "หนา"]},
    "D": {"name": "บู๊ช", "size_labels": ["ใน", "นอก", "หนา"]},
    "E": {"name": "ลูกปืนเข็ม/กรงนก", "size_labels": ["ใน", "นอก", "หนา"]},
    "F": {"name": "ไส้กรองอากาศ", "size_labels": ["ใน", "นอก", "สูง"]},
    "G": {"name": "ยอยกากบาท", "size_labels": ["ปลอก", "ยาว"]},
    "I": {"name": "ลูกปืนตลับ", "size_labels": ["ใน", "นอก", "หนา"]},
    "K": {"name": "จานคลัช", "size_labels": ["ยาว(นิ้ว)", "ฟัน", "ขนาดรูเฟือง"]},
    "L": {"name": "สายอ่อน", "size_labels": ["หัวสาย 1", "หัวสาย 2", "ยาว"]},
    "O": {"name": "โอริง", "size_labels": ["ใน", "หนา"]},
    "P": {"name": "ไส้กรองน้ำมันเครื่อง", "size_labels": ["ใน", "นอก", "สูง"]},
    "Q": {"name": "ลูกหมาก", "size_labels": ["เตเปอร์", "แกนโต"]},
    "R": {"name": "ลูกยาง", "size_labels": ["ใน", "นอก", "หนา"]},
}

def format_location_pair(loc1, loc2) -> str:
    parts = []
    for v in [loc1, loc2]:
        s = _safe_size_value(v)
        if s:
            parts.append(s)
    return " / ".join(parts)

def _safe_text(value, default: str = "-") -> str:
    if value is None:
        return default
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return default
    return s


def _safe_size_value(value) -> str:
    if value is None:
        return ""
    s = str(value).strip()
    if s == "" or s.lower() == "nan":
        return ""
    return s


def format_price(value) -> str:
    try:
        if value is None or str(value).strip() in {"", "nan"}:
            return "-"
        return f"{float(str(value).replace(',', '')):,.0f}"
    except Exception:
        return _safe_text(value)


def format_qty_whole(value) -> str:
    try:
        if value is None or str(value).strip() in {"", "nan"}:
            return "-"
        return f"{round(float(str(value).replace(',', ''))):,.0f}"
    except Exception:
        return _safe_text(value)


def format_last_updated(value) -> str:
    try:
        if not value:
            return "-"
        dt = pd.to_datetime(value, utc=True, errors="coerce")
        if pd.isna(dt):
            return "-"
        dt_local = dt.tz_convert(LOCAL_TZ)
        now = datetime.now(LOCAL_TZ)
        diff = now - dt_local

        minutes = int(diff.total_seconds() // 60)
        if minutes < 1:
            return "อัปเดตเมื่อสักครู่"
        if minutes < 60:
            return f"อัปเดต {minutes} นาทีที่แล้ว"

        hours = minutes // 60
        if hours < 24:
            return f"อัปเดต {hours} ชม.ที่แล้ว"

        days = hours // 24
        return f"อัปเดต {days} วันที่แล้ว"
    except Exception:
        return "-"


def _fmt_price_or_dash(v):
    if v is None:
        return "-"
    try:
        v = float(v)
    except Exception:
        return "-"
    if v == 0:
        return "-"
    return format_price(v)


def format_code1_line(code1_value) -> str:
    code1 = _safe_text(code1_value, "").upper()
    if not code1:
        return ""

    meta = CODE1_DISPLAY_MAP.get(code1)
    if meta:
        return f" รหัสคุม: {code1} ({meta['name']})\n"

    return f" รหัสคุม: {code1}\n"


def format_size_line(code1_value, size1, size2, size3) -> str:
    code1 = _safe_text(code1_value, "").upper()
    values = [
        _safe_size_value(size1),
        _safe_size_value(size2),
        _safe_size_value(size3),
    ]

    if not any(values):
        return ""

    meta = CODE1_DISPLAY_MAP.get(code1)

    if not meta:
        shown = [v for v in values if v]
        return f" ขนาด: {' / '.join(shown)}\n"

    labels = meta["size_labels"]
    pairs = []

    for idx, label in enumerate(labels):
        if idx < len(values) and values[idx]:
            pairs.append(f"{label} {values[idx]}")

    if not pairs:
        return ""

    return f" ขนาด: {' | '.join(pairs)}\n"


def format_product_answer(search_result: dict) -> str:
    df = search_result.get("items", pd.DataFrame())
    total = int(search_result.get("total", 0) or 0)

    if df.empty:
        return "ไม่พบสินค้า"

    lines = []

    for i, (_, row) in enumerate(df.iterrows(), start=1):
        bcode = _safe_text(row.get("BCODE"))
        descr = _safe_text(row.get("DESCR"))
        brand = _safe_text(row.get("BRAND"))
        model = _safe_text(row.get("MODEL"))
        ui1 = _safe_text(row.get("UI1"))
        ui2 = _safe_text(row.get("UI2"))
        pricem1 = format_price(row.get("PRICEM1"))
        qty_hq = format_qty_whole(row.get("qty_hq"))
        qty_syp = format_qty_whole(row.get("qty_syp"))
        costnet = format_price(row.get("COSTNET"))
        ingested_at = format_last_updated(row.get("_ingested_at"))
        updated_at_hq = format_last_updated(row.get("updated_at_hq"))
        updated_at_syp = format_last_updated(row.get("updated_at_syp"))

        detail_parts = [x for x in [descr, brand, model] if x != "-"]
        product_detail = " | ".join(detail_parts) if detail_parts else "-"

        loc_hq = format_location_pair(row.get("location1_hq"), row.get("location2_hq"))
        loc_syp = format_location_pair(row.get("location1_syp"), row.get("location2_syp"))

        p1 = _fmt_price_or_dash(row.get("PRICE1"))
        p2 = _fmt_price_or_dash(row.get("PRICE2"))
        p3 = _fmt_price_or_dash(row.get("PRICE3"))

        if ui1 != "-":
            price_ui1_line = f"ราคา/{ui1}: ({p1}/{p2}/{p3})"
        else:
            price_ui1_line = f"ราคา: ({p1}/{p2}/{p3})"

        price_ui2_line = f"ราคา/{ui2}: {pricem1}" if ui2 != "-" and pricem1 != "-" else "ราคา/หน่วยใหญ่: -"

        code1_line = format_code1_line(row.get("CODE1"))
        size_line = format_size_line(
            row.get("CODE1"),
            row.get("SIZE1"),
            row.get("SIZE2"),
            row.get("SIZE3"),
        )

        lines.append(
            f"{i}.\n"
            f" รหัสสินค้า: {bcode}\n"
            f"{code1_line}"
            f" ชื่อ: {product_detail}\n"
            f"{size_line}"
            f" {price_ui1_line}\n"
            f" {price_ui2_line}\n"
            f" ทุน: {costnet}\n"
            f" สนญ: {qty_hq}" + (f" | {loc_hq}" if loc_hq else "") + "\n"
            f" ({updated_at_hq})\n"
            f" สาขา: {qty_syp}" + (f" | {loc_syp}" if loc_syp else "")  + "\n"
            f" ({updated_at_syp})\n"
            f" ข้อมูลสินค้าอัปเดต: {ingested_at}"
        )

    shown = len(df)
    if total > shown:
        lines.append(
            f"\nพบทั้งหมด {total:,.0f} รายการ "
            f"(แสดง {shown:,.0f} รายการแรก)\n"
            f"กรุณาเพิ่มคำค้น เช่น ยี่ห้อ รุ่น หรือรหัสสินค้า"
        )

    return "\n\n".join(lines)
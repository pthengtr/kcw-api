
import pandas as pd
from zoneinfo import ZoneInfo


def _safe_text(value, default: str = "-") -> str:
    if value is None:
        return default
    s = str(value).strip()
    if s == "" or s.lower() == "nan" or s == "<NA>":
        return default
    return s


def format_price(value) -> str:
    try:
        if value is None or str(value).strip() in {"", "<NA>", "nan"}:
            return "-"
        return f"{float(str(value).replace(',', '')):,.0f}"
    except Exception:
        return _safe_text(value)


def format_qty_whole(value) -> str:
    try:
        if value is None or str(value).strip() in {"", "<NA>", "nan"}:
            return "-"
        return f"{round(float(str(value).replace(',', ''))):,.0f}"
    except Exception:
        return _safe_text(value)


LOCAL_TZ = ZoneInfo("Asia/Singapore")   # or Asia/Bangkok


from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd

LOCAL_TZ = ZoneInfo("Asia/Singapore")


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

        price1 = format_price(row.get("PRICE1"))
        price2 = format_price(row.get("PRICE2"))
        price3 = format_price(row.get("PRICE3"))
        pricem1 = format_price(row.get("PRICEM1"))

        qty_hq = format_qty_whole(row.get("qty_hq"))
        qty_syp = format_qty_whole(row.get("qty_syp"))

        costnet = format_price(row.get("COSTNET"))

        ingested_at = format_last_updated(row.get("_ingested_at"))
        updated_at_hq = format_last_updated(row.get("updated_at_hq"))
        updated_at_syp = format_last_updated(row.get("updated_at_syp"))

        detail_parts = [x for x in [descr, brand, model] if x != "-"]
        product_detail = " | ".join(detail_parts) if detail_parts else "-"

        p1 = _fmt_price_or_dash(row.get("PRICE1"))
        p2 = _fmt_price_or_dash(row.get("PRICE2"))
        p3 = _fmt_price_or_dash(row.get("PRICE3"))

        ui1 = _safe_text(row.get("UI1"))

        if ui1 != "-":
            price_ui1_line = f"ราคา/{ui1}: ({p1}/{p2}/{p3})"
        else:
            price_ui1_line = f"ราคา: ({p1}/{p2}/{p3})"

        price_ui2_line = f"ราคา/{ui2}: {pricem1}" if ui2 != "-" and pricem1 != "-" else "ราคา/หน่วยใหญ่: -"

        lines.append(
            f"{i}. รหัสสินค้า: {bcode}\n"
            f"   ชื่อ: {product_detail}\n"
            f"   {price_ui1_line}\n"
            f"   {price_ui2_line}\n"
            f"   ทุน: {costnet}\n"
            f"   สนญ: {qty_hq} ({updated_at_hq})\n"
            f"   สาขา: {qty_syp} ({updated_at_syp})\n"
            f"   ข้อมูลสินค้าอัปเดต: {ingested_at}"
        )

    shown = len(df)
    if total > shown:
        lines.append(
            f"\nพบทั้งหมด {total:,.0f} รายการ "
            f"(แสดง {shown:,.0f} รายการแรก)\n"
            f"กรุณาเพิ่มคำค้น เช่น ยี่ห้อ รุ่น หรือรหัสสินค้า"
        )

    return "\n\n".join(lines)
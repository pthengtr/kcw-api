import pandas as pd


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


def format_ingested_at(value) -> str:
    try:
        if value is None or str(value).strip() in {"", "<NA>", "nan"}:
            return "-"
        dt = pd.to_datetime(value, errors="coerce")
        if pd.isna(dt):
            return _safe_text(value)
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return _safe_text(value)


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
        pricem1 = format_price(row.get("PRICEM1"))
        qtyoh2 = format_qty_whole(row.get("QTYOH2"))
        ingested_at = format_ingested_at(row.get("_ingested_at"))

        detail_parts = [x for x in [descr, brand, model] if x != "-"]
        product_detail = " | ".join(detail_parts) if detail_parts else "-"

        price_parts = []
        if ui1 != "-" and price1 != "-":
            price_parts.append(f"ราคา/{ui1}: {price1}")
        elif price1 != "-":
            price_parts.append(f"ราคา: {price1}")

        if ui2 != "-" and pricem1 != "-":
            price_parts.append(f"ราคา/{ui2}: {pricem1}")

        price_line = " | ".join(price_parts) if price_parts else "ราคา: -"

        lines.append(
            f"{i}. รหัสสินค้า: {bcode}\n"
            f"   รายละเอียดสินค้า: {product_detail}\n"
            f"   {price_line}\n"
            f"   คงเหลือ: {qtyoh2} ณ {ingested_at}"
        )

    shown = len(df)
    if total > shown:
        lines.append(
            f"\nพบทั้งหมด {total:,.0f} รายการ "
            f"(แสดง {shown:,.0f} รายการแรก)\n"
            f"กรุณาเพิ่มคำค้น เช่น ยี่ห้อ รุ่น หรือรหัสสินค้า"
        )

    return "\n\n".join(lines)
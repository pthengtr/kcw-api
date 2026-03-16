from typing import Any
import pandas as pd


def _safe_text(v: Any) -> str:
    if pd.isna(v):
        return "-"
    text = str(v).strip()
    return text if text else "-"


def format_price(v: Any) -> str:
    if pd.isna(v):
        return "-"
    try:
        return f"{float(v):,.2f}"
    except Exception:
        return str(v)


def format_product_answer(df: pd.DataFrame, max_rows: int = 5) -> str:
    if df is None or df.empty:
        return "ไม่พบสินค้า"

    lines: list[str] = []

    for i, (_, row) in enumerate(df.head(max_rows).iterrows(), start=1):
        bcode = _safe_text(row.get("BCODE"))
        descr = _safe_text(row.get("DESCR"))
        brand = _safe_text(row.get("BRAND"))
        model = _safe_text(row.get("MODEL"))
        price1 = format_price(row.get("PRICE1"))
        qtyoh2 = format_price(row.get("QTYOH2"))

        lines.append(
            f"{i}. {bcode} | {descr}\n"
            f"   BRAND: {brand} | MODEL: {model}\n"
            f"   PRICE1: {price1} | QTYOH2: {qtyoh2}\n"
        )

    if len(df) > max_rows:
        lines.append(f"\nแสดง {max_rows} จาก {len(df)} รายการ")

    return "\n\n".join(lines)
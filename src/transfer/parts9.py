from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.engine import Engine


def _parse_qty(val) -> float:
    if val is None:
        return 0.0
    try:
        return float(str(val).replace(",", ""))
    except (TypeError, ValueError):
        return 0.0


def suggest_transfer_skus(engine: Engine, *, limit: int = 200) -> list[dict[str, Any]]:
    """SYP ICMAS: QTYOH2 <= QTYMIN, suggest QTYGET; skip QTYMIN < 0."""
    sql = text(
        """
        select top (:lim)
          trim(BCODE) as bcode,
          trim(DESCR) as descr,
          QTYOH2,
          QTYMIN,
          QTYGET
        from dbo.ICMAS with (nolock)
        where CANCELED = 'N'
          and QTYMIN is not null
          and QTYMIN >= 0
          and ISNUMERIC(REPLACE(CONVERT(varchar(50), QTYOH2), ',', '')) = 1
          and ISNUMERIC(REPLACE(CONVERT(varchar(50), QTYMIN), ',', '')) = 1
          and CONVERT(float, REPLACE(CONVERT(varchar(50), QTYOH2), ',', ''))
              <= CONVERT(float, REPLACE(CONVERT(varchar(50), QTYMIN), ',', ''))
        order by BCODE
        """
    )
    with engine.connect() as conn:
        rows = conn.execute(sql, {"lim": int(limit)}).mappings().all()

    out: list[dict[str, Any]] = []
    for row in rows:
        qtyoh2 = _parse_qty(row["QTYOH2"])
        qtymin = _parse_qty(row["QTYMIN"])
        qtyget = _parse_qty(row["QTYGET"])
        suggest = qtyget if qtyget > 0 else max(qtymin - qtyoh2, 1.0)
        out.append(
            {
                "bcode": (row["bcode"] or "").strip(),
                "descr": (row["descr"] or "").strip(),
                "qtyoh2": qtyoh2,
                "qtymin": qtymin,
                "qtyget": qtyget,
                "suggest_qty": suggest,
            }
        )
    return out

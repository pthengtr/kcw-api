from __future__ import annotations

from typing import Any


class HqPoError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _flag(value: Any) -> str:
    return str(value or "").strip().upper()


def can_stamp_row(row: dict[str, Any]) -> str | None:
    """None when this live ICLOW row may be marked ordered."""
    if _flag(row.get("canceled")) == "Y":
        return "canceled"
    if _flag(row.get("received")) == "Y":
        return "already_received"
    if _flag(row.get("ordered")) == "Y":
        return "already_ordered"
    return None


def can_revert_row(row: dict[str, Any], docno: str) -> str | None:
    """None when the row still belongs to our PO, or our stamp is already gone.

    PIMAS receive blocks the revert. A different DOCNO blocks it too.
    """
    if _flag(row.get("received")) == "Y":
        return "already_received"
    current = str(row.get("docno") or "").strip()
    expected = (docno or "").strip()
    if expected and current == expected:
        return None
    if _flag(row.get("ordered")) != "Y" and not current:
        return None
    return "docno_mismatch"


def receive_view(row: dict[str, Any] | None, pimas: dict[str, Any] | None = None) -> dict[str, Any]:
    """Read-only receive state. This service never writes RECEIVED."""
    if not row:
        return {
            "received": False,
            "unknown": True,
            "rcvdno": None,
            "rcvddate": None,
            "pimas_billno": None,
            "pimas_link_missing": False,
            "label": "ไม่ทราบ",
        }
    received = _flag(row.get("received")) == "Y"
    rcvdno = str(row.get("rcvdno") or "").strip() or None
    hit = pimas or {}
    return {
        "received": received,
        "unknown": False,
        "rcvdno": rcvdno,
        "rcvddate": str(row.get("rcvddate") or "").strip()[:10] or None,
        "pimas_billno": hit.get("pimas_matched_billno"),
        "pimas_link_missing": bool(hit.get("pimas_link_missing")) if received and rcvdno else False,
        "label": "รับแล้ว" if received else "ค้างรับ",
    }


def plan_confirm(
    lines: list[dict[str, Any]],
    live_by_id: dict[int, dict[str, Any]],
    *,
    vendor: str,
) -> list[dict[str, Any]]:
    """Checked lines for one vendor. Qty and identity come from live ICLOW, not the client."""
    if not lines:
        raise HqPoError("empty", "ยังไม่ได้เลือกรายการ")
    vendor_key = (vendor or "").strip()
    out: list[dict[str, Any]] = []
    seen: set[int] = set()
    for raw in lines:
        try:
            iclow_id = int(raw.get("iclow_id"))
        except (TypeError, ValueError):
            raise HqPoError("not_confirmable", "รายการ AI ที่ยังไม่มี ICLOW สั่งจากหน้านี้ไม่ได้") from None
        if iclow_id <= 0:
            raise HqPoError("not_confirmable", "รายการ AI ที่ยังไม่มี ICLOW สั่งจากหน้านี้ไม่ได้")
        if iclow_id in seen:
            raise HqPoError("duplicate", f"เลือก ICLOW {iclow_id} ซ้ำ")
        seen.add(iclow_id)
        live = live_by_id.get(iclow_id)
        if not live:
            raise HqPoError("missing", f"ไม่พบ ICLOW {iclow_id}")
        live_vendor = str(live.get("vendor") or "").strip()
        if live_vendor != vendor_key:
            raise HqPoError("vendor_mismatch", "ยืนยันได้ครั้งละหนึ่งเจ้าหนี้")
        blocked = can_stamp_row(live)
        if blocked == "already_ordered":
            raise HqPoError(blocked, f"{live.get('bcode') or iclow_id} สั่งไปแล้ว")
        if blocked == "already_received":
            raise HqPoError(blocked, f"{live.get('bcode') or iclow_id} รับแล้ว")
        if blocked == "canceled":
            raise HqPoError(blocked, f"{live.get('bcode') or iclow_id} ถูกยกเลิก")
        qty = _qty(live.get("qty"))
        if qty <= 0:
            raise HqPoError("bad_qty", f"{live.get('bcode') or iclow_id} จำนวนไม่ถูกต้อง")
        out.append(
            {
                "iclow_id": iclow_id,
                "bcode": str(live.get("bcode") or "").strip(),
                "descr": str(live.get("descr") or "").strip() or None,
                "qty": qty,
                "ui": str(live.get("ui") or "").strip() or None,
                "vendor": live_vendor,
                "propose_meta": raw.get("propose_meta"),
            }
        )
    return out


def plan_cancel(live_rows: list[dict[str, Any]], docno: str) -> None:
    if not live_rows:
        raise HqPoError("missing", "ไม่พบแถว ICLOW ของใบนี้")
    for row in live_rows:
        blocked = can_revert_row(row, docno)
        if blocked == "already_received":
            raise HqPoError(blocked, "มีรายการที่ PIMAS รับแล้ว ยกเลิกใบนี้ไม่ได้")
        if blocked == "docno_mismatch":
            raise HqPoError(blocked, "DOCNO บน ICLOW ไม่ใช่ใบนี้แล้ว")


def _qty(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0

"""Supabase-backed online-sale drafts (pre-TAD pick list)."""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from src.db.engine import get_conn
from src.online_sale.errors import OnlineSaleError

BKK = ZoneInfo("Asia/Bangkok")
ACTIVE_STATUSES = ("open", "printed")


def _connect():
    conn = get_conn()
    conn.row_factory = dict_row
    return conn


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(BKK).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _num(value) -> float:
    if value is None or value == "":
        return 0.0
    return float(Decimal(str(value)))


def _normalize_lines(raw_lines: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for i, raw in enumerate(raw_lines or [], start=1):
        bcode = str(raw.get("bcode") or "").strip()
        qty = abs(float(raw.get("qty") or 0))
        price = abs(float(raw.get("price") or 0))
        if not bcode or qty <= 0 or price <= 0:
            continue
        mtp = abs(float(raw.get("mtp") or 1)) or 1.0
        out.append(
            {
                "line_no": i * 10,
                "bcode": bcode,
                "detail": str(raw.get("detail") or raw.get("descr") or "").strip(),
                "descr": str(raw.get("descr") or raw.get("detail") or "").strip(),
                "qty": qty,
                "price": price,
                "amount": round(qty * price, 2),
                "ui": str(raw.get("ui") or "หน่วย").strip() or "หน่วย",
                "mtp": mtp,
                "ui1": str(raw.get("ui1") or "").strip(),
                "ui2": str(raw.get("ui2") or "").strip(),
                "mtp2": float(raw.get("mtp2") or 1) or 1.0,
                "location": str(raw.get("location") or raw.get("location1") or "").strip(),
                "location1": str(raw.get("location1") or raw.get("location") or "").strip(),
                "qtyoh2": float(raw.get("qtyoh2") or 0),
            }
        )
    if not out:
        raise OnlineSaleError("lines", "ต้องมีรายการสินค้าอย่างน้อย 1 รายการ")
    return out


def _aftertax(lines: list[dict[str, Any]]) -> float:
    return round(sum(float(ln.get("amount") or 0) for ln in lines), 2)


def public_draft(row: dict[str, Any], *, include_lines: bool = True) -> dict[str, Any]:
    status = str(row.get("status") or "open")
    lines_raw = row.get("lines")
    if isinstance(lines_raw, str):
        try:
            lines_raw = json.loads(lines_raw)
        except json.JSONDecodeError:
            lines_raw = []
    lines = list(lines_raw or []) if include_lines else None
    draft_id = str(row.get("draft_id") or "")
    out: dict[str, Any] = {
        "draft_id": draft_id,
        "billno": f"DRAFT-{draft_id[:8].upper()}" if draft_id else "DRAFT",
        "kind": "draft",
        "status": status,
        "status_label": (
            "พิมพ์ใบจัดแล้ว"
            if status == "printed"
            else (
                "ยกเลิก"
                if status == "canceled"
                else ("ขายแล้ว" if status == "sold" else "ฉบับร่าง")
            )
        ),
        "pick_printed": status == "printed" or bool(row.get("pick_printed_at")),
        "canceled": status == "canceled",
        "platform": str(row.get("platform") or "").strip(),
        "acctno": str(row.get("acctno") or "").strip(),
        "acctname": str(row.get("acctname") or "").strip(),
        "shop_name": str(row.get("shop_name") or "").strip(),
        "online_po": str(row.get("online_po") or "").strip(),
        "aftertax": _num(row.get("aftertax")),
        "beforetax": 0.0,
        "tax": 0.0,
        "bill_date": (_iso(row.get("created_at")) or "")[:10],
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
        "pick_printed_at": _iso(row.get("pick_printed_at")),
        "sold_billno": str(row.get("sold_billno") or "").strip(),
        "sold_at": _iso(row.get("sold_at")),
        "created_by": str(row.get("created_by") or "").strip(),
        "updated_by": str(row.get("updated_by") or "").strip(),
    }
    if lines is not None:
        out["lines"] = lines
    return out


def find_duplicate_draft_po(
    acctno: str,
    online_po: str,
    *,
    exclude_draft_id: str = "",
) -> list[dict[str, Any]]:
    acct = (acctno or "").strip()
    po = (online_po or "").strip()
    if not acct or not po:
        return []
    skip = (exclude_draft_id or "").strip()
    with _connect() as conn:
        rows = conn.execute(
            """
            select draft_id, online_po, status, created_at
            from online_sale.drafts
            where acctno = %s
              and online_po = %s
              and status = any(%s)
            order by created_at desc
            limit 5
            """,
            (acct, po, list(ACTIVE_STATUSES)),
        ).fetchall()
    out = []
    for row in rows:
        draft_id = str(row["draft_id"])
        if skip and draft_id == skip:
            continue
        out.append(
            {
                "billno": f"DRAFT-{draft_id[:8].upper()}",
                "draft_id": draft_id,
                "bill_date": (_iso(row.get("created_at")) or "")[:10],
                "online_po": str(row.get("online_po") or "").strip(),
                "kind": "draft",
            }
        )
    return out


def create_draft(
    *,
    platform: str,
    acctno: str,
    acctname: str,
    shop_name: str,
    online_po: str,
    lines: list[dict[str, Any]],
    actor: str,
) -> dict[str, Any]:
    normalized = _normalize_lines(lines)
    total = _aftertax(normalized)
    with _connect() as conn:
        with conn.transaction():
            row = conn.execute(
                """
                insert into online_sale.drafts (
                  status, platform, acctno, acctname, shop_name, online_po,
                  aftertax, lines, created_by, updated_by
                ) values (
                  'open', %s, %s, %s, %s, %s,
                  %s, %s, %s, %s
                )
                returning *
                """,
                (
                    (platform or "").strip().lower() or None,
                    acctno.strip(),
                    (acctname or "").strip() or None,
                    (shop_name or "").strip() or None,
                    online_po.strip(),
                    total,
                    Jsonb(normalized),
                    (actor or "")[:80] or None,
                    (actor or "")[:80] or None,
                ),
            ).fetchone()
    return public_draft(row)


def update_draft(
    draft_id: str,
    *,
    platform: str,
    acctno: str,
    acctname: str,
    shop_name: str,
    online_po: str,
    lines: list[dict[str, Any]],
    actor: str,
) -> dict[str, Any]:
    exact = str(UUID(str(draft_id).strip()))
    normalized = _normalize_lines(lines)
    total = _aftertax(normalized)
    with _connect() as conn:
        with conn.transaction():
            current = conn.execute(
                "select * from online_sale.drafts where draft_id = %s",
                (exact,),
            ).fetchone()
            if not current:
                raise OnlineSaleError("draft", "ไม่พบฉบับร่าง", status=404)
            if current["status"] not in ACTIVE_STATUSES:
                raise OnlineSaleError("draft", "แก้ไขได้เฉพาะฉบับร่างที่ยังไม่ขาย/ยกเลิก")
            row = conn.execute(
                """
                update online_sale.drafts
                set platform = %s,
                    acctno = %s,
                    acctname = %s,
                    shop_name = %s,
                    online_po = %s,
                    aftertax = %s,
                    lines = %s,
                    updated_by = %s,
                    updated_at = now()
                where draft_id = %s
                  and status = any(%s)
                returning *
                """,
                (
                    (platform or "").strip().lower() or None,
                    acctno.strip(),
                    (acctname or "").strip() or None,
                    (shop_name or "").strip() or None,
                    online_po.strip(),
                    total,
                    Jsonb(normalized),
                    (actor or "")[:80] or None,
                    exact,
                    list(ACTIVE_STATUSES),
                ),
            ).fetchone()
    if not row:
        raise OnlineSaleError("draft", "อัปเดตฉบับร่างไม่สำเร็จ", status=409)
    return public_draft(row)


def get_draft(draft_id: str) -> dict[str, Any]:
    exact = str(UUID(str(draft_id).strip()))
    with _connect() as conn:
        row = conn.execute(
            "select * from online_sale.drafts where draft_id = %s",
            (exact,),
        ).fetchone()
    if not row:
        raise OnlineSaleError("draft", "ไม่พบฉบับร่าง", status=404)
    return public_draft(row)


def list_drafts(
    *,
    q: str = "",
    platform: str = "",
    acctno: str = "",
    date_from: str = "",
    date_to: str = "",
    include_inactive: bool = False,
) -> list[dict[str, Any]]:
    clauses = ["1=1"]
    params: list[Any] = []
    if include_inactive:
        clauses.append("status = any(%s)")
        params.append(["open", "printed", "canceled", "sold"])
    else:
        clauses.append("status = any(%s)")
        params.append(list(ACTIVE_STATUSES))
    plat = (platform or "").strip().lower()
    if plat:
        clauses.append("platform = %s")
        params.append(plat)
    acct = (acctno or "").strip()
    if acct:
        clauses.append("acctno = %s")
        params.append(acct)
    raw_q = (q or "").strip()
    if raw_q:
        like = f"%{raw_q}%"
        clauses.append(
            "(online_po ilike %s or acctname ilike %s or shop_name ilike %s "
            "or cast(draft_id as text) ilike %s)"
        )
        params.extend([like, like, like, like])
    df = (date_from or "").strip()
    if df:
        clauses.append("created_at >= %s::date")
        params.append(df)
    dt = (date_to or "").strip()
    if dt:
        clauses.append("created_at < (%s::date + interval '1 day')")
        params.append(dt)
    sql = f"""
        select *
        from online_sale.drafts
        where {' and '.join(clauses)}
        order by updated_at desc
        limit 80
    """
    with _connect() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [public_draft(r) for r in rows]


def cancel_draft(draft_id: str, actor: str) -> dict[str, Any]:
    exact = str(UUID(str(draft_id).strip()))
    with _connect() as conn:
        with conn.transaction():
            row = conn.execute(
                """
                update online_sale.drafts
                set status = 'canceled',
                    canceled_at = now(),
                    canceled_by = %s,
                    updated_by = %s,
                    updated_at = now()
                where draft_id = %s
                  and status = any(%s)
                returning *
                """,
                (
                    (actor or "")[:80] or None,
                    (actor or "")[:80] or None,
                    exact,
                    list(ACTIVE_STATUSES),
                ),
            ).fetchone()
    if not row:
        raise OnlineSaleError("draft", "ยกเลิกได้เฉพาะฉบับร่างที่ยังไม่ขาย", status=409)
    return public_draft(row)


def mark_drafts_printed(draft_ids: list[str]) -> list[dict[str, Any]]:
    ids: list[str] = []
    for raw in draft_ids:
        try:
            ids.append(str(UUID(str(raw).strip())))
        except (TypeError, ValueError):
            continue
    if not ids:
        return []
    with _connect() as conn:
        with conn.transaction():
            rows = conn.execute(
                """
                update online_sale.drafts
                set status = case when status = 'open' then 'printed' else status end,
                    pick_printed_at = coalesce(pick_printed_at, now()),
                    updated_at = now()
                where draft_id = any(%s::uuid[])
                  and status = any(%s)
                returning *
                """,
                (ids, list(ACTIVE_STATUSES)),
            ).fetchall()
    return [public_draft(r) for r in rows]


def mark_draft_sold(draft_id: str, billno: str, actor: str) -> dict[str, Any]:
    exact = str(UUID(str(draft_id).strip()))
    with _connect() as conn:
        with conn.transaction():
            row = conn.execute(
                """
                update online_sale.drafts
                set status = 'sold',
                    sold_billno = %s,
                    sold_at = now(),
                    updated_by = %s,
                    updated_at = now()
                where draft_id = %s
                  and status = any(%s)
                returning *
                """,
                (
                    (billno or "").strip().upper(),
                    (actor or "")[:80] or None,
                    exact,
                    list(ACTIVE_STATUSES),
                ),
            ).fetchone()
    if not row:
        raise OnlineSaleError("draft", "ยืนยันขายได้เฉพาะฉบับร่างที่ยังเปิดอยู่", status=409)
    return public_draft(row, include_lines=False)


def drafts_for_pick(draft_ids: list[str]) -> list[dict[str, Any]]:
    """Load active drafts shaped for the pick sheet (ref = online_po)."""
    ids: list[str] = []
    for raw in draft_ids:
        try:
            ids.append(str(UUID(str(raw).strip())))
        except (TypeError, ValueError):
            continue
    if not ids:
        raise OnlineSaleError("draft", "เลือกฉบับร่างที่จะพิมพ์ใบจัดสินค้า")
    with _connect() as conn:
        rows = conn.execute(
            """
            select *
            from online_sale.drafts
            where draft_id = any(%s::uuid[])
            """,
            (ids,),
        ).fetchall()
    by_id = {str(r["draft_id"]): r for r in rows}
    bills: list[dict[str, Any]] = []
    for draft_id in ids:
        row = by_id.get(draft_id)
        if not row:
            raise OnlineSaleError("draft", f"ไม่พบฉบับร่าง {draft_id[:8]}", status=404)
        if row["status"] not in ACTIVE_STATUSES:
            raise OnlineSaleError(
                "draft",
                f"ฉบับร่าง {row['online_po']} ไม่สามารถพิมพ์ได้ (สถานะ {row['status']})",
            )
        draft = public_draft(row)
        # Pick sheet uses online_po as the packing reference (not TAD).
        bills.append(
            {
                "billno": draft["online_po"],
                "online_po": draft["online_po"],
                "bill_date": draft["bill_date"],
                "platform": draft["platform"],
                "shop_name": draft["shop_name"] or draft["acctname"],
                "acctname": draft["acctname"],
                "lines": [
                    {
                        **ln,
                        "detail": ln.get("detail") or ln.get("descr") or "",
                        "location1": ln.get("location1") or ln.get("location") or "",
                    }
                    for ln in draft.get("lines") or []
                ],
            }
        )
    return bills

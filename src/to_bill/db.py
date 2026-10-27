from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from psycopg.rows import dict_row

from src.db.engine import get_conn
from src.to_bill.buyers import Buyer
from src.to_bill.errors import ToBillError
from src.to_bill.kss import LiveBill
from src.to_bill.numbering import buddhist_yymm, format_docno, month_bounds

BKK = ZoneInfo("Asia/Bangkok")


def _connect():
    conn = get_conn()
    conn.row_factory = dict_row
    return conn


def _num(value) -> Decimal:
    if value is None or value == "":
        return Decimal("0")
    return Decimal(str(value))


def _json_num(value) -> float:
    return float(_num(value))


def _iso(value) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def public_invoice(row: dict[str, Any], lines: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    out = {
        "invoice_id": str(row.get("invoice_id") or ""),
        "docno": row.get("docno"),
        "tad_billno": row.get("tad_billno") or "",
        "status": row.get("status") or "",
        "bill_date": _iso(row.get("bill_date")),
        "acctno": row.get("acctno") or "",
        "acctname_kss": row.get("acctname_kss") or "",
        "online_po": row.get("online_po") or "",
        "beforetax": _json_num(row.get("beforetax")),
        "tax": _json_num(row.get("tax")),
        "aftertax": _json_num(row.get("aftertax")),
        "discount": _json_num(row.get("discount")),
        "kss_canceled": bool(row.get("kss_canceled")),
        "source_read_at": _iso(row.get("source_read_at")),
        "customer_name": row.get("customer_name") or "",
        "address": row.get("address") or "",
        "phone": row.get("phone") or "",
        "tax_id": row.get("tax_id") or "",
        "branch_label": row.get("branch_label") or "สำนักงานใหญ่",
        "email": row.get("email") or "",
        "issued_at": _iso(row.get("issued_at")),
        "issued_by": row.get("issued_by") or "",
        "voided_at": _iso(row.get("voided_at")),
        "void_reason": row.get("void_reason") or "",
        "voided_by": row.get("voided_by") or "",
        "created_by": row.get("created_by") or "",
        "created_at": _iso(row.get("created_at")),
        "updated_at": _iso(row.get("updated_at")),
    }
    if lines is not None:
        out["lines"] = [
            {
                "line_no": int(line.get("line_no") or 0),
                "bcode": line.get("bcode") or "",
                "detail": line.get("detail") or "",
                "qty": _json_num(line.get("qty")),
                "ui": line.get("ui") or "",
                "price": _json_num(line.get("price")),
                "amount": _json_num(line.get("amount")),
            }
            for line in lines
        ]
    return out


def _lines_for(conn, invoice_id: str) -> list[dict[str, Any]]:
    return list(
        conn.execute(
            """
            select line_no, bcode, detail, qty, ui, price, amount
            from to_bill.lines
            where invoice_id = %s
            order by line_no
            """,
            (invoice_id,),
        ).fetchall()
    )


def open_for_bills(billnos: list[str]) -> dict[str, dict[str, Any]]:
    wanted = []
    seen: set[str] = set()
    for raw in billnos:
        billno = (raw or "").strip().upper()
        if billno and billno not in seen:
            seen.add(billno)
            wanted.append(billno)
    if not wanted:
        return {}
    with _connect() as conn:
        rows = conn.execute(
            """
            select invoice_id, tad_billno, status, docno
            from to_bill.invoices
            where tad_billno = any(%s)
              and status in ('draft', 'issued')
            """,
            (wanted,),
        ).fetchall()
    return {
        str(row["tad_billno"]): {
            "invoice_id": str(row["invoice_id"]),
            "status": row["status"],
            "docno": row["docno"],
        }
        for row in rows
    }


def get_invoice(invoice_id: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "select * from to_bill.invoices where invoice_id = %s",
            (invoice_id,),
        ).fetchone()
        if not row:
            return None
        lines = _lines_for(conn, str(row["invoice_id"]))
    return public_invoice(row, lines)


def get_invoice_by_docno(docno: str) -> dict[str, Any] | None:
    with _connect() as conn:
        row = conn.execute(
            "select * from to_bill.invoices where docno = %s",
            (docno,),
        ).fetchone()
        if not row:
            return None
        lines = _lines_for(conn, str(row["invoice_id"]))
    return public_invoice(row, lines)


def list_invoices(*, status: str, q: str, yymm: str) -> list[dict[str, Any]]:
    start, end = month_bounds(yymm)
    like = f"%{q.strip()}%" if q.strip() else ""
    status_filter = status.strip()
    with _connect() as conn:
        rows = conn.execute(
            """
            select *
            from to_bill.invoices
            where coalesce(issued_at, created_at) >= %s
              and coalesce(issued_at, created_at) < %s
              and (%s = '' or status = %s)
              and (
                %s = ''
                or coalesce(docno, '') ilike %s
                or tad_billno ilike %s
                or coalesce(customer_name, '') ilike %s
              )
            order by coalesce(issued_at, created_at) desc
            limit 200
            """,
            (start, end, status_filter, status_filter, like, like, like, like),
        ).fetchall()
    return [public_invoice(row) for row in rows]


def suggest_buyers(q: str) -> list[dict[str, Any]]:
    raw = (q or "").strip()
    if len(raw) < 2:
        return []
    digits = "".join(ch for ch in raw if ch.isdigit())
    with _connect() as conn:
        if len(digits) >= 3 and digits == raw.replace("-", "").replace(" ", ""):
            rows = conn.execute(
                """
                select distinct on (tax_id)
                  tax_id, customer_name, address, phone, email, branch_label
                from to_bill.invoices
                where status = 'issued'
                  and coalesce(tax_id, '') <> ''
                  and tax_id like %s
                order by tax_id, issued_at desc
                limit 8
                """,
                (digits + "%",),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                select distinct on (tax_id)
                  tax_id, customer_name, address, phone, email, branch_label
                from to_bill.invoices
                where status = 'issued'
                  and coalesce(tax_id, '') <> ''
                  and customer_name ilike %s
                order by tax_id, issued_at desc
                limit 8
                """,
                (f"%{raw}%",),
            ).fetchall()
    return [dict(row) for row in rows]


def peek_next_docno(on: date | None = None) -> str:
    yymm = buddhist_yymm(on)
    with _connect() as conn:
        row = conn.execute(
            "select last_seq from to_bill.counters where yymm = %s",
            (yymm,),
        ).fetchone()
    last = int(row["last_seq"]) if row else 0
    return format_docno(yymm, last + 1)


def _insert_lines(conn, invoice_id: str, bill: LiveBill) -> None:
    for line in bill.lines:
        conn.execute(
            """
            insert into to_bill.lines
              (invoice_id, line_no, bcode, detail, qty, ui, price, amount)
            values (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                invoice_id,
                line.line_no,
                line.bcode,
                line.detail,
                line.qty,
                line.ui,
                line.price,
                line.amount,
            ),
        )


def _snapshot_params(bill: LiveBill) -> tuple:
    return (
        bill.bill_date,
        bill.acctno,
        bill.acctname,
        bill.online_po,
        bill.beforetax,
        bill.tax,
        bill.aftertax,
        bill.discount,
        bill.canceled,
    )


def create_draft(bill: LiveBill, actor: str) -> dict[str, Any]:
    from psycopg.errors import UniqueViolation

    try:
        with _connect() as conn:
            with conn.transaction():
                row = conn.execute(
                    """
                    insert into to_bill.invoices (
                      tad_billno, status, bill_date, acctno, acctname_kss, online_po,
                      beforetax, tax, aftertax, discount, kss_canceled, source_read_at,
                      created_by
                    ) values (
                      %s, 'draft', %s, %s, %s, %s,
                      %s, %s, %s, %s, %s, now(),
                      %s
                    )
                    returning *
                    """,
                    (bill.billno, *_snapshot_params(bill), actor),
                ).fetchone()
                invoice_id = str(row["invoice_id"])
                _insert_lines(conn, invoice_id, bill)
                conn.execute(
                    """
                    insert into to_bill.events (invoice_id, action, actor)
                    values (%s, 'created', %s)
                    """,
                    (invoice_id, actor),
                )
                lines = _lines_for(conn, invoice_id)
            return public_invoice(row, lines)
    except UniqueViolation as exc:
        existing = open_for_bills([bill.billno]).get(bill.billno)
        if not existing:
            raise ToBillError("conflict", "มีใบเต็มของบิลนี้อยู่แล้ว") from exc
        loaded = get_invoice(existing["invoice_id"])
        if not loaded:
            raise ToBillError("conflict", "มีใบเต็มของบิลนี้อยู่แล้ว") from exc
        return loaded


def find_open(billno: str) -> dict[str, Any] | None:
    found = open_for_bills([billno]).get(billno.strip().upper())
    if not found:
        return None
    return get_invoice(found["invoice_id"])


def save_buyer(invoice_id: str, buyer: Buyer) -> dict[str, Any]:
    with _connect() as conn:
        with conn.transaction():
            row = conn.execute(
                """
                update to_bill.invoices
                set customer_name = %s,
                    address = %s,
                    phone = %s,
                    tax_id = %s,
                    branch_label = %s,
                    email = %s,
                    updated_at = now()
                where invoice_id = %s
                  and status = 'draft'
                returning *
                """,
                (
                    buyer.customer_name,
                    buyer.address,
                    buyer.phone,
                    buyer.tax_id,
                    buyer.branch_label,
                    buyer.email,
                    invoice_id,
                ),
            ).fetchone()
            if not row:
                raise ToBillError("not_draft", "แก้ได้เฉพาะฉบับร่าง", status=409)
            lines = _lines_for(conn, invoice_id)
    return public_invoice(row, lines)


def refresh_draft(invoice_id: str, bill: LiveBill, actor: str) -> dict[str, Any]:
    with _connect() as conn:
        with conn.transaction():
            row = conn.execute(
                """
                update to_bill.invoices
                set bill_date = %s,
                    acctno = %s,
                    acctname_kss = %s,
                    online_po = %s,
                    beforetax = %s,
                    tax = %s,
                    aftertax = %s,
                    discount = %s,
                    kss_canceled = %s,
                    source_read_at = now(),
                    updated_at = now()
                where invoice_id = %s
                  and status = 'draft'
                  and tad_billno = %s
                returning *
                """,
                (*_snapshot_params(bill), invoice_id, bill.billno),
            ).fetchone()
            if not row:
                raise ToBillError("not_draft", "ดึงใหม่ได้เฉพาะฉบับร่าง", status=409)
            conn.execute("delete from to_bill.lines where invoice_id = %s", (invoice_id,))
            _insert_lines(conn, invoice_id, bill)
            conn.execute(
                """
                insert into to_bill.events (invoice_id, action, actor)
                values (%s, 'refreshed', %s)
                """,
                (invoice_id, actor),
            )
            lines = _lines_for(conn, invoice_id)
    return public_invoice(row, lines)


def issue_invoice(invoice_id: str, bill: LiveBill, buyer: Buyer, actor: str) -> dict[str, Any]:
    yymm = buddhist_yymm()
    with _connect() as conn:
        with conn.transaction():
            current = conn.execute(
                "select status, tad_billno from to_bill.invoices where invoice_id = %s for update",
                (invoice_id,),
            ).fetchone()
            if not current:
                raise ToBillError("missing", "ไม่พบใบเต็ม", status=404)
            if current["status"] != "draft":
                raise ToBillError("not_draft", "ออกเอกสารได้เฉพาะฉบับร่าง")
            if str(current["tad_billno"]) != bill.billno:
                raise ToBillError("bill_mismatch", "บิล KSS ไม่ตรงกับฉบับร่าง")
            conn.execute(
                """
                insert into to_bill.counters (yymm, last_seq)
                values (%s, 0)
                on conflict (yymm) do nothing
                """,
                (yymm,),
            )
            counter = conn.execute(
                """
                update to_bill.counters
                set last_seq = last_seq + 1
                where yymm = %s
                returning last_seq
                """,
                (yymm,),
            ).fetchone()
            docno = format_docno(yymm, int(counter["last_seq"]))
            row = conn.execute(
                """
                update to_bill.invoices
                set docno = %s,
                    status = 'issued',
                    bill_date = %s,
                    acctno = %s,
                    acctname_kss = %s,
                    online_po = %s,
                    beforetax = %s,
                    tax = %s,
                    aftertax = %s,
                    discount = %s,
                    kss_canceled = %s,
                    source_read_at = now(),
                    customer_name = %s,
                    address = %s,
                    phone = %s,
                    tax_id = %s,
                    branch_label = %s,
                    email = %s,
                    issued_at = now(),
                    issued_by = %s,
                    updated_at = now()
                where invoice_id = %s
                returning *
                """,
                (
                    docno,
                    *_snapshot_params(bill),
                    buyer.customer_name,
                    buyer.address,
                    buyer.phone,
                    buyer.tax_id,
                    buyer.branch_label,
                    buyer.email,
                    actor,
                    invoice_id,
                ),
            ).fetchone()
            conn.execute("delete from to_bill.lines where invoice_id = %s", (invoice_id,))
            _insert_lines(conn, invoice_id, bill)
            conn.execute(
                """
                insert into to_bill.events (invoice_id, action, actor, note)
                values (%s, 'issued', %s, %s)
                """,
                (invoice_id, actor, docno),
            )
            lines = _lines_for(conn, invoice_id)
    return public_invoice(row, lines)


def void_invoice(invoice_id: str, reason: str, actor: str) -> dict[str, Any]:
    with _connect() as conn:
        with conn.transaction():
            row = conn.execute(
                """
                update to_bill.invoices
                set status = 'void',
                    voided_at = now(),
                    void_reason = %s,
                    voided_by = %s,
                    updated_at = now()
                where invoice_id = %s
                  and status = 'issued'
                returning *
                """,
                (reason, actor, invoice_id),
            ).fetchone()
            if not row:
                raise ToBillError("not_issued", "ยกเลิกได้เฉพาะเอกสารที่ออกแล้ว")
            conn.execute(
                """
                insert into to_bill.events (invoice_id, action, actor, note)
                values (%s, 'voided', %s, %s)
                """,
                (invoice_id, actor, reason),
            )
            lines = _lines_for(conn, invoice_id)
    return public_invoice(row, lines)


def mark_printed(invoice_id: str, actor: str) -> None:
    with _connect() as conn:
        with conn.transaction():
            row = conn.execute(
                "select status from to_bill.invoices where invoice_id = %s",
                (invoice_id,),
            ).fetchone()
            if not row or row["status"] not in {"issued", "void"}:
                raise ToBillError("not_issued", "พิมพ์ได้หลังออกเอกสาร", status=409)
            conn.execute(
                """
                insert into to_bill.events (invoice_id, action, actor)
                values (%s, 'printed', %s)
                """,
                (invoice_id, actor),
            )

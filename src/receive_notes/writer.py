from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.receive_notes.config import ReceiveNotesSettings
from src.receive_notes.noteno import buddhist_yymm, next_noteno
from src.stock_check.parts9 import get_parts9_engine

_BKK = ZoneInfo("Asia/Bangkok")

# Marketplace / TAD debtor codes → RVI receipt series (online settlement).
RVI_ACCTNOS = frozenset(
    {
        "7LAZ1",
        "7LAZ2",
        "7LPNT",
        "7LICE",
        "7IAPL",
        "7SP",
        "7SPNT",
        "7SICE",
        "7IAPS",
        "7ICE",
    }
)


class ReceiveNoteWriteError(RuntimeError):
    def __init__(self, message: str, *, code: str = "write_failed"):
        super().__init__(message)
        self.code = code


def uses_rvi_voucher(acctno: str | None) -> bool:
    return (acctno or "").strip().upper() in RVI_ACCTNOS


def _writer_engine(settings: ReceiveNotesSettings) -> Engine:
    if not settings.pos_mssql_writer_username:
        raise ReceiveNoteWriteError(
            "POS_MSSQL_WRITER_USERNAME not configured",
            code="writer_not_configured",
        )
    return get_parts9_engine(writer=True)


def _map_write_exc(exc: Exception) -> ReceiveNoteWriteError:
    msg = str(exc).lower()
    if "permission" in msg or "denied" in msg:
        return ReceiveNoteWriteError(
            "KSS writer missing grants on RVMAS/SIMAS/BRDET "
            "(see scripts/sql/grant_receive_notes_writer.sql)",
            code="permission_denied",
        )
    return ReceiveNoteWriteError(str(exc), code="write_failed")


def voucher_stem(
    jourmode: str,
    when: datetime | None = None,
    *,
    acctno: str | None = None,
    refund: bool = False,
) -> str:
    """VAT → RC… ; Non-VAT → RCN… ; marketplace TAD → RVI… ; customer refund → PVN…"""
    yymm = buddhist_yymm(when)
    if refund:
        # Customer credit refund (ใบสำคัญจ่าย) — Service AR only; not PVMAS AP.
        return f"PVN{yymm}-"
    if uses_rvi_voucher(acctno):
        return f"RVI{yymm}-"
    mode = (jourmode or "1").strip() or "1"
    if mode == "2":
        return f"RCN{yymm}-"
    return f"RC{yymm}-"


def next_voucno(
    conn,
    *,
    jourmode: str,
    when: datetime | None = None,
    acctno: str | None = None,
    refund: bool = False,
) -> str:
    stem = voucher_stem(jourmode, when, acctno=acctno, refund=refund)
    row = conn.execute(
        text("SELECT MAX(VOUCNO) AS max_no FROM dbo.RVMAS WHERE VOUCNO LIKE :pat"),
        {"pat": stem + "%"},
    ).mappings().first()
    max_no = (row or {}).get("max_no") or ""
    seq = 1
    if max_no and "-" in str(max_no):
        try:
            seq = int(str(max_no).rsplit("-", 1)[-1]) + 1
        except ValueError:
            seq = 1
    candidate = f"{stem}{seq:03d}"
    if len(candidate) > 15:
        raise ReceiveNoteWriteError("generated VOUCNO exceeds 15 chars", code="voucno_overflow")
    return candidate


def proof_required(*, voucno: str = "", settle_method: str = "") -> bool:
    """RVI marketplace receipts, PVN cash refunds, and cash settles skip the proof tab."""
    method = (settle_method or "").strip().lower()
    if method == "cash":
        return False
    vo = (voucno or "").strip().upper()
    if vo.startswith("RVI"):
        return False
    # Customer refund PVN: transfer/cheque still need proof; cash already skipped.
    return True


def _parse_day(raw: str | None, fallback: datetime) -> datetime:
    text_v = (raw or "").strip()
    if text_v:
        return datetime.strptime(text_v[:10], "%Y-%m-%d")
    return fallback


def create_receive_note(
    *,
    settings: ReceiveNotesSettings,
    acctno: str,
    acctname: str,
    billnos: list[str],
    operator: str | None = None,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Create ใบวางบิล (NR) — does not cut AR."""
    if not settings.receive_notes_write_enabled:
        raise ReceiveNoteWriteError("RECEIVE_NOTES_WRITE_ENABLED is false", code="write_disabled")

    from src.receive_notes.parts9 import fetch_bills_for_receive

    acct = (acctno or "").strip()
    name = (acctname or "").strip()
    if not acct:
        raise ReceiveNoteWriteError("acctno required", code="validation")

    site = settings.site
    write_eng = engine or _writer_engine(settings)
    try:
        bills = fetch_bills_for_receive(site, acct, billnos, engine=engine)
        if len(bills) != len({b.strip() for b in billnos if b.strip()}):
            raise ReceiveNoteWriteError("one or more bills unavailable for note", code="bill_invalid")

        jourmodes = {str(b.get("JOURMODE") or "1").strip() or "1" for b in bills}
        if len(jourmodes) > 1:
            raise ReceiveNoteWriteError(
                "mixed VAT/non-VAT bills — split note per JOURMODE",
                code="mixed_jourmode",
            )
        jourmode = jourmodes.pop()
        billamt = round(sum(float(b.get("AFTERTAX") or 0) for b in bills), 2)
        billcnt = len(bills)
        notedate = datetime.now(_BKK).replace(hour=0, minute=0, second=0, microsecond=0)

        with write_eng.begin() as conn:
            noteno = next_noteno(conn, jourmode=jourmode, when=notedate)
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.RVMAS (
                      JOURMODE, JOURTYPE, NOTED, NOTEDATE, NOTENO,
                      ACCTNO, ACCTNAME, BILLCNT, BILLAMT,
                      DEPTNO, BOOKNO, VOUCED,
                      POSTED1, POSTED2, DONE, CANCELED
                    )
                    VALUES (
                      :jourmode, 'NR', 'Y', :notedate, :noteno,
                      :acctno, :acctname, :billcnt, :billamt,
                      '1', '1', 'N',
                      'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "notedate": notedate,
                    "noteno": noteno,
                    "acctno": acct,
                    "acctname": name[:60],
                    "billcnt": billcnt,
                    "billamt": billamt,
                },
            )
            stamped = 0
            for bill in bills:
                bno = str(bill.get("BILLNO") or "").strip()
                # Require empty NOTENO so a concurrent create cannot steal stamps
                # from another note (double-submit race).
                result = conn.execute(
                    text(
                        """
                        UPDATE dbo.SIMAS
                        SET NOTENO = :noteno, NOTEDATE = :notedate
                        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                          AND LTRIM(RTRIM(BILLNO)) = :billno
                          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                          AND ISNULL(PAID, 'N') = 'N'
                          AND ISNULL(CANCELED, 'N') <> 'Y'
                          AND ISNULL(LTRIM(RTRIM(NOTENO)), '') = ''
                        """
                    ),
                    {
                        "noteno": noteno,
                        "notedate": notedate,
                        "acctno": acct,
                        "billno": bno,
                    },
                )
                if int(result.rowcount or 0) != 1:
                    raise ReceiveNoteWriteError(
                        f"bill already on another note or unavailable: {bno}",
                        code="bill_conflict",
                    )
                stamped += 1
            if stamped != billcnt:
                raise ReceiveNoteWriteError(
                    "SIMAS stamp count mismatch",
                    code="stamp_mismatch",
                )
    except ReceiveNoteWriteError:
        raise
    except Exception as exc:
        raise _map_write_exc(exc) from exc

    _ = operator
    return {
        "acctno": acct,
        "noteno": noteno,
        "billcnt": billcnt,
        "billamt": billamt,
        "notedate": notedate.date().isoformat(),
        "jourmode": jourmode,
    }


def update_receive_note(
    *,
    settings: ReceiveNotesSettings,
    acctno: str,
    noteno: str,
    billnos: list[str],
    operator: str | None = None,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Update bill membership on an unvouchered receive note."""
    if not settings.receive_notes_write_enabled:
        raise ReceiveNoteWriteError("RECEIVE_NOTES_WRITE_ENABLED is false", code="write_disabled")

    from src.receive_notes.parts9 import fetch_bills_for_receive, list_note_bills

    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        raise ReceiveNoteWriteError("acctno and noteno required", code="validation")

    requested = [b.strip() for b in billnos if (b or "").strip()]
    if not requested:
        raise ReceiveNoteWriteError("select at least one bill", code="validation")
    if len(requested) != len(set(requested)):
        raise ReceiveNoteWriteError("duplicate bill numbers", code="validation")

    site = settings.site
    write_eng = engine or _writer_engine(settings)
    billcnt = 0
    billamt = 0.0
    try:
        with write_eng.begin() as conn:
            header = conn.execute(
                text(
                    """
                    SELECT TOP 1 ID, JOURMODE, VOUCED, VOUCNO, NOTEDATE
                    FROM dbo.RVMAS
                    WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                      AND LTRIM(RTRIM(NOTENO)) = :noteno
                      AND NOTED = 'Y'
                      AND ISNULL(CANCELED, 'N') <> 'Y'
                    """
                ),
                {"acctno": acct, "noteno": note},
            ).mappings().first()
            if not header:
                raise ReceiveNoteWriteError("note not found in KSS", code="not_found")
            if str(header.get("VOUCED") or "N").strip().upper() == "Y" or (header.get("VOUCNO") or "").strip():
                raise ReceiveNoteWriteError("note already vouchered", code="not_editable")

            current_rows = list_note_bills(site, acct, note, engine=write_eng)
            current_nos = {str(b.get("BILLNO") or "").strip() for b in current_rows}
            requested_set = set(requested)
            to_remove = current_nos - requested_set
            to_add = requested_set - current_nos

            if to_add:
                new_bills = fetch_bills_for_receive(
                    site, acct, sorted(to_add), engine=write_eng, noteno=note
                )
                if len(new_bills) != len(to_add):
                    raise ReceiveNoteWriteError("one or more bills unavailable for note", code="bill_invalid")
            else:
                new_bills = []

            all_bills = fetch_bills_for_receive(
                site, acct, requested, engine=write_eng, noteno=note
            )
            if len(all_bills) != len(requested):
                raise ReceiveNoteWriteError("one or more bills unavailable for note", code="bill_invalid")

            jourmodes = {str(b.get("JOURMODE") or "1").strip() or "1" for b in all_bills}
            if len(jourmodes) > 1:
                raise ReceiveNoteWriteError(
                    "mixed VAT/non-VAT bills — split note per JOURMODE",
                    code="mixed_jourmode",
                )

            notedate = header.get("NOTEDATE")
            if isinstance(notedate, datetime):
                pass
            elif notedate:
                notedate = datetime.strptime(str(notedate)[:10], "%Y-%m-%d")
            else:
                notedate = datetime.now(_BKK).replace(hour=0, minute=0, second=0, microsecond=0)

            for bno in to_remove:
                conn.execute(
                    text(
                        """
                        UPDATE dbo.SIMAS
                        SET NOTENO = '', NOTEDATE = NULL
                        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                          AND LTRIM(RTRIM(BILLNO)) = :billno
                          AND LTRIM(RTRIM(NOTENO)) = :noteno
                          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                          AND ISNULL(PAID, 'N') = 'N'
                        """
                    ),
                    {"acctno": acct, "billno": bno, "noteno": note},
                )

            for bill in new_bills:
                bno = str(bill.get("BILLNO") or "").strip()
                conn.execute(
                    text(
                        """
                        UPDATE dbo.SIMAS
                        SET NOTENO = :noteno, NOTEDATE = :notedate
                        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                          AND LTRIM(RTRIM(BILLNO)) = :billno
                          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                          AND ISNULL(PAID, 'N') = 'N'
                          AND (
                            ISNULL(LTRIM(RTRIM(NOTENO)), '') = ''
                            OR LTRIM(RTRIM(NOTENO)) = :noteno
                          )
                        """
                    ),
                    {
                        "noteno": note,
                        "notedate": notedate,
                        "acctno": acct,
                        "billno": bno,
                    },
                )

            billamt = sum(float(b.get("AFTERTAX") or 0) for b in all_bills)
            billcnt = len(all_bills)
            conn.execute(
                text(
                    """
                    UPDATE dbo.RVMAS
                    SET BILLCNT = :billcnt, BILLAMT = :billamt
                    WHERE ID = :id
                      AND ISNULL(VOUCED, 'N') <> 'Y'
                    """
                ),
                {"billcnt": billcnt, "billamt": billamt, "id": header["ID"]},
            )
    except ReceiveNoteWriteError:
        raise
    except Exception as exc:
        raise _map_write_exc(exc) from exc

    _ = operator
    return {
        "acctno": acct,
        "noteno": note,
        "billcnt": billcnt,
        "billamt": billamt,
    }


def cancel_unvouchered_receive_note(
    *,
    settings: ReceiveNotesSettings,
    acctno: str,
    noteno: str,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Soft-cancel an unvouchered receive note in KSS (no hard DELETE)."""
    if not settings.receive_notes_write_enabled:
        raise ReceiveNoteWriteError("RECEIVE_NOTES_WRITE_ENABLED is false", code="write_disabled")

    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        raise ReceiveNoteWriteError("acctno and noteno required", code="validation")

    write_eng = engine or _writer_engine(settings)
    try:
        with write_eng.begin() as conn:
            header = conn.execute(
                text(
                    """
                    SELECT TOP 1 ID, VOUCED, CANCELED
                    FROM dbo.RVMAS
                    WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                      AND LTRIM(RTRIM(NOTENO)) = :noteno
                    """
                ),
                {"acctno": acct, "noteno": note},
            ).mappings().first()
            if not header:
                return {"acctno": acct, "noteno": note, "canceled": False, "reason": "not_found"}
            if str(header.get("VOUCED") or "N").strip().upper() == "Y":
                raise ReceiveNoteWriteError(
                    "cannot cancel vouchered note",
                    code="already_vouchered",
                )
            if str(header.get("CANCELED") or "N").strip().upper() == "Y":
                return {"acctno": acct, "noteno": note, "canceled": False, "reason": "already_canceled"}

            conn.execute(
                text(
                    """
                    UPDATE dbo.SIMAS
                    SET NOTENO = '', NOTEDATE = NULL
                    WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                      AND LTRIM(RTRIM(NOTENO)) = :noteno
                      AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                    """
                ),
                {"acctno": acct, "noteno": note},
            )
            conn.execute(
                text(
                    """
                    UPDATE dbo.RVMAS
                    SET CANCELED = 'Y'
                    WHERE ID = :id
                      AND ISNULL(VOUCED, 'N') <> 'Y'
                    """
                ),
                {"id": header["ID"]},
            )
    except ReceiveNoteWriteError:
        raise
    except Exception as exc:
        raise _map_write_exc(exc) from exc

    return {"acctno": acct, "noteno": note, "canceled": True}


def _stamp_simas_paid(conn, *, acctno: str, billno: str, voucno: str, voucd: datetime) -> None:
    conn.execute(
        text(
            """
            UPDATE dbo.SIMAS
            SET VOUCNO2 = :voucno,
                VOUCDATE2 = :voucd,
                PAID = 'Y',
                PAYSTAT = '$'
            WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
              AND LTRIM(RTRIM(BILLNO)) = :billno
              AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
              AND ISNULL(PAID, 'N') = 'N'
              AND ISNULL(CANCELED, 'N') <> 'Y'
            """
        ),
        {"voucno": voucno, "voucd": voucd, "acctno": acctno, "billno": billno},
    )


def _insert_brdet_lines(
    conn,
    *,
    jourmode: str,
    voucno: str,
    voucd: datetime,
    brdet_lines: list[dict[str, Any]],
) -> None:
    for line in brdet_lines:
        chkamt = float(line.get("chkamt") or 0)
        if chkamt <= 0:
            raise ReceiveNoteWriteError("BRDET CHKAMT must be > 0", code="validation")
        chkno = str(line.get("chkno") or "").strip()
        bankname = str(line.get("bankname") or "").strip()[:60]
        bank_gl = str(line.get("acctno") or "").strip()[:10]
        paytype = int(line.get("paytype") or 2)
        chkdate = _parse_day(str(line.get("chkdate") or ""), voucd)
        conn.execute(
            text(
                """
                INSERT INTO dbo.BRDET (
                  JOURMODE, JOURTYPE, VOUCDATE, VOUCNO, ACCTNO, PAYTYPE,
                  CHKNO, CHKDATE, CHKAMT, BANKNAME, STATUS, CANCELED, DONE
                )
                VALUES (
                  :jourmode, 'CR', :voucd, :voucno, :bank_gl, :paytype,
                  :chkno, :chkdate, :chkamt, :bankname, '=', 'N', 'N'
                )
                """
            ),
            {
                "jourmode": jourmode,
                "voucd": voucd,
                "voucno": voucno,
                "bank_gl": bank_gl or None,
                "paytype": paytype,
                "chkno": (chkno[:15] if chkno else None),
                "chkdate": chkdate,
                "chkamt": chkamt,
                "bankname": bankname or None,
            },
        )


def create_receipt_voucher(
    *,
    settings: ReceiveNotesSettings,
    acctno: str,
    acctname: str,
    bill_allocations: list[dict[str, Any]],
    brdet_lines: list[dict[str, Any]],
    discount: float = 0.0,
    noteno: str | None = None,
    existing_voucno: str | None = None,
    operator: str | None = None,
    engine: Engine | None = None,
    refund: bool | None = None,
) -> dict[str, Any]:
    """Create or complete an AR receipt / refund voucher (CR). Idempotent if existing_voucno set.

    When ``refund`` is True (or net is negative), allocates ``PVN{YYMM}-`` and treats
    BRDET CHKAMT as the positive payout amount matching ``abs(netamt)``.
    """
    if not settings.receive_notes_write_enabled:
        raise ReceiveNoteWriteError("RECEIVE_NOTES_WRITE_ENABLED is false", code="write_disabled")

    from src.receive_notes.parts9 import fetch_bills_for_receive, get_voucher_header

    acct = (acctno or "").strip()
    name = (acctname or "").strip()
    note = (noteno or "").strip() or None
    if not acct:
        raise ReceiveNoteWriteError("acctno required", code="validation")
    if not note:
        raise ReceiveNoteWriteError(
            "noteno required — receive voucher must start from a ใบวางบิล",
            code="note_required",
        )
    if not bill_allocations:
        raise ReceiveNoteWriteError("select at least one bill", code="validation")

    site = settings.site
    # Idempotent resync: voucher already in KSS
    if existing_voucno:
        existing = get_voucher_header(site, existing_voucno, engine=engine)
        if existing:
            return {
                "acctno": acct,
                "noteno": note or existing.get("NOTENO"),
                "voucno": existing_voucno,
                "voucdate": existing.get("VOUCDATE"),
                "billamt": float(existing.get("BILLAMT") or 0),
                "discount": float(existing.get("DISCOUNT") or 0),
                "netamt": float(existing.get("NETAMT") or existing.get("PAYAMT") or 0),
                "idempotent": True,
                "stamped_bills": [],
            }

    billnos = [str(a.get("billno") or "").strip() for a in bill_allocations]
    bills = fetch_bills_for_receive(site, acct, billnos, engine=engine, noteno=note)
    by_no = {str(b.get("BILLNO") or "").strip(): b for b in bills}
    if len(by_no) != len(set(billnos)):
        missing = [b for b in billnos if b not in by_no]
        raise ReceiveNoteWriteError(
            f"bills unavailable: {', '.join(missing)}",
            code="bill_invalid",
        )

    jourmodes = {str(b.get("JOURMODE") or "1").strip() or "1" for b in bills}
    if len(jourmodes) > 1:
        raise ReceiveNoteWriteError(
            "mixed VAT/non-VAT bills — split voucher per JOURMODE",
            code="mixed_jourmode",
        )
    jourmode = jourmodes.pop()

    alloc_rows: list[dict[str, Any]] = []
    billamt = 0.0
    for alloc in bill_allocations:
        bno = str(alloc.get("billno") or "").strip()
        bill = by_no[bno]
        aftertax = round(float(bill.get("AFTERTAX") or 0), 2)
        amount = round(float(alloc.get("allocate_amt") or aftertax), 2)
        # Sale bills: positive allocate up to AFTERTAX.
        # Credit notes (ใบลดหนี้): negative AFTERTAX is a valid allocate, not a discount.
        if aftertax >= 0:
            if amount <= 0:
                raise ReceiveNoteWriteError(
                    f"allocate_amt must be > 0 for {bno}", code="validation"
                )
            if amount - aftertax > 1e-6:
                raise ReceiveNoteWriteError(
                    f"allocate_amt exceeds AFTERTAX for {bno}",
                    code="validation",
                )
            fully = amount + 1e-6 >= aftertax
        else:
            if amount >= 0:
                raise ReceiveNoteWriteError(
                    f"allocate_amt must be < 0 for credit bill {bno}",
                    code="validation",
                )
            if amount < aftertax - 1e-6:
                raise ReceiveNoteWriteError(
                    f"allocate_amt exceeds AFTERTAX for {bno}",
                    code="validation",
                )
            fully = amount - 1e-6 <= aftertax
        alloc_rows.append(
            {
                "billno": bno,
                "aftertax": aftertax,
                "allocate_amt": amount,
                "fully_paid": fully,
            }
        )
        billamt += amount

    billamt = round(billamt, 2)
    disc = float(discount or 0)
    netamt = round(billamt - disc, 2)
    # Negative BILLAMT (CN / ใบลดหนี้) is a valid note net — only reject discount overflow
    # on non-negative totals.
    if billamt >= 0 and disc - billamt > 1e-9:
        raise ReceiveNoteWriteError("discount exceeds bill amount", code="validation")

    is_refund = bool(refund) if refund is not None else netamt < -1e-9
    channel_target = round(abs(netamt), 2) if is_refund else netamt
    channel_sum = round(sum(float(l.get("chkamt") or 0) for l in brdet_lines), 2)
    if brdet_lines and abs(channel_sum - channel_target) > 0.05:
        raise ReceiveNoteWriteError(
            f"channel sum {channel_sum} != net {channel_target}",
            code="channel_mismatch",
        )
    if not brdet_lines and channel_target > 1e-9:
        raise ReceiveNoteWriteError("at least one BRDET line required", code="validation")

    cash_amt = round(
        sum(
            float(l.get("chkamt") or 0)
            for l in brdet_lines
            if str(l.get("settle_method") or "").lower() == "cash"
            or (
                not str(l.get("bankname") or "").strip()
                and not str(l.get("acctno") or "").strip()
            )
        ),
        2,
    )

    write_eng = engine or _writer_engine(settings)
    voucd = datetime.now(_BKK).replace(hour=0, minute=0, second=0, microsecond=0)
    stamped: list[str] = []

    try:
        with write_eng.begin() as conn:
            voucno = next_voucno(
                conn, jourmode=jourmode, when=voucd, acctno=acct, refund=is_refund
            )
            if note:
                header = conn.execute(
                    text(
                        """
                        SELECT TOP 1 ID, JOURMODE, BILLAMT, VOUCED, VOUCNO
                        FROM dbo.RVMAS
                        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                          AND LTRIM(RTRIM(NOTENO)) = :noteno
                          AND NOTED = 'Y'
                          AND ISNULL(CANCELED, 'N') <> 'Y'
                        """
                    ),
                    {"acctno": acct, "noteno": note},
                ).mappings().first()
                if not header:
                    raise ReceiveNoteWriteError("note not found in KSS", code="not_found")
                if str(header.get("VOUCED") or "N").strip().upper() == "Y" or (
                    header.get("VOUCNO") or ""
                ).strip():
                    raise ReceiveNoteWriteError("note already vouchered", code="already_vouchered")
                conn.execute(
                    text(
                        """
                        UPDATE dbo.RVMAS
                        SET VOUCED = 'Y',
                            VOUCDATE = :voucd,
                            VOUCNO = :voucno,
                            RCPTNO = :voucno,
                            JOURTYPE = 'CR',
                            DISCOUNT = :discount,
                            NETAMT = :netamt,
                            PAYAMT = :netamt,
                            CHKAMT = :netamt,
                            CASHAMT = :cashamt,
                            PAID = 'Y',
                            BILLAMT = :billamt,
                            BILLCNT = :billcnt
                        WHERE ID = :id
                          AND ISNULL(VOUCED, 'N') <> 'Y'
                          AND ISNULL(LTRIM(RTRIM(VOUCNO)), '') = ''
                        """
                    ),
                    {
                        "voucd": voucd,
                        "voucno": voucno,
                        "discount": disc if disc else None,
                        "netamt": netamt,
                        "cashamt": cash_amt if cash_amt > 0 else None,
                        "billamt": billamt,
                        "billcnt": len(alloc_rows),
                        "id": header["ID"],
                    },
                )
                if conn.execute(
                    text(
                        """
                        SELECT TOP 1 ID FROM dbo.RVMAS
                        WHERE ID = :id AND LTRIM(RTRIM(VOUCNO)) = :voucno
                        """
                    ),
                    {"id": header["ID"], "voucno": voucno},
                ).first() is None:
                    raise ReceiveNoteWriteError(
                        "note already vouchered (concurrent)",
                        code="already_vouchered",
                    )

            for row in alloc_rows:
                if row["fully_paid"]:
                    _stamp_simas_paid(
                        conn,
                        acctno=acct,
                        billno=row["billno"],
                        voucno=voucno,
                        voucd=voucd,
                    )
                    stamped.append(row["billno"])

            _insert_brdet_lines(
                conn,
                jourmode=jourmode,
                voucno=voucno,
                voucd=voucd,
                brdet_lines=brdet_lines,
            )
    except ReceiveNoteWriteError:
        raise
    except Exception as exc:
        raise _map_write_exc(exc) from exc

    _ = operator
    return {
        "acctno": acct,
        "acctname": name,
        "noteno": note,
        "voucno": voucno,
        "voucdate": voucd.date().isoformat(),
        "jourmode": jourmode,
        "billamt": billamt,
        "discount": disc,
        "netamt": netamt,
        "cash_amt": cash_amt,
        "brdet_count": len(brdet_lines),
        "allocations": alloc_rows,
        "stamped_bills": stamped,
        "idempotent": False,
    }

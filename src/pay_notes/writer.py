from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.engine import Engine

from src.pay_notes.config import PayNotesSettings
from src.stock_check.parts9 import get_parts9_engine

_BKK = ZoneInfo("Asia/Bangkok")


class PayNoteWriteError(RuntimeError):
    def __init__(self, message: str, *, code: str = "write_failed"):
        super().__init__(message)
        self.code = code


def _writer_engine(settings: PayNotesSettings) -> Engine:
    use_writer = bool(settings.pos_mssql_writer_username)
    if not use_writer:
        raise PayNoteWriteError(
            "POS_MSSQL_WRITER_USERNAME not configured",
            code="writer_not_configured",
        )
    return get_parts9_engine(writer=True)


def _map_write_exc(exc: Exception) -> PayNoteWriteError:
    msg = str(exc).lower()
    if "permission" in msg or "denied" in msg:
        return PayNoteWriteError(
            "KSS writer missing grants on PVMAS/PIMAS/BPDET "
            "(see scripts/sql/grant_pay_notes_writer.sql)",
            code="permission_denied",
        )
    return PayNoteWriteError(str(exc), code="write_failed")


def create_pay_note(
    *,
    settings: PayNotesSettings,
    acctno: str,
    acctname: str,
    noteno: str,
    billnos: list[str],
    operator: str | None = None,
    engine: Engine | None = None,
) -> dict[str, Any]:
    if not settings.pay_notes_write_enabled:
        raise PayNoteWriteError("PAY_NOTES_WRITE_ENABLED is false", code="write_disabled")

    acct = (acctno or "").strip()
    name = (acctname or "").strip()
    from src.pay_notes.noteno import display_noteno
    from src.pay_notes.parts9 import (
        fetch_bills_for_note,
        note_exists,
        open_unvouchered_note_exists,
        resolve_stored_noteno,
    )

    bare = display_noteno((noteno or "").strip())
    if not acct or not bare:
        raise PayNoteWriteError("acctno and noteno required", code="validation")
    if len(bare) > 15:
        raise PayNoteWriteError("NOTENO exceeds 15 chars", code="validation")

    site = settings.site
    # SELECTs use the reader login; python_writer is INSERT/UPDATE-only until grants include SELECT.
    # Injected `engine` (tests) is used for both read and write.
    write_eng = engine or _writer_engine(settings)
    try:
        if open_unvouchered_note_exists(site, acct, bare, engine=engine):
            raise PayNoteWriteError("note already exists in KSS", code="duplicate_note")

        try:
            note = resolve_stored_noteno(site, acct, bare, engine=engine)
        except ValueError as exc:
            raise PayNoteWriteError(str(exc), code="validation") from exc
        except RuntimeError as exc:
            raise PayNoteWriteError(str(exc), code="noteno_exhausted") from exc

        if note_exists(site, acct, note, engine=engine):
            raise PayNoteWriteError("note already exists in KSS", code="duplicate_note")

        bills = fetch_bills_for_note(site, acct, billnos, engine=engine)
        if len(bills) != len(set(b.strip() for b in billnos if b.strip())):
            raise PayNoteWriteError("one or more bills unavailable for note", code="bill_invalid")

        jourmodes = {str(b.get("JOURMODE") or "1").strip() or "1" for b in bills}
        if len(jourmodes) > 1:
            raise PayNoteWriteError(
                "mixed VAT/non-VAT bills — split note per JOURMODE",
                code="mixed_jourmode",
            )
        jourmode = jourmodes.pop()
        billamt = sum(float(b.get("AFTERTAX") or 0) for b in bills)
        billcnt = len(bills)
        notedate = datetime.now(_BKK).replace(hour=0, minute=0, second=0, microsecond=0)

        with write_eng.begin() as conn:
            # No OUTPUT INSERTED — that requires SELECT on PVMAS.
            conn.execute(
                text(
                    """
                    INSERT INTO dbo.PVMAS (
                      JOURMODE, JOURTYPE, NOTED, NOTEDATE, NOTENO,
                      ACCTNO, ACCTNAME, BILLCNT, BILLAMT,
                      DEPTNO, BOOKNO, VOUCED,
                      POSTED1, POSTED2, DONE, CANCELED
                    )
                    VALUES (
                      :jourmode, 'NP', 'Y', :notedate, :noteno,
                      :acctno, :acctname, :billcnt, :billamt,
                      '1', '1', 'N',
                      'N', 'N', 'N', 'N'
                    )
                    """
                ),
                {
                    "jourmode": jourmode,
                    "notedate": notedate,
                    "noteno": note,
                    "acctno": acct,
                    "acctname": name[:60],
                    "billcnt": billcnt,
                    "billamt": billamt,
                },
            )
            for bill in bills:
                bno = str(bill.get("BILLNO") or "").strip()
                conn.execute(
                    text(
                        """
                        UPDATE dbo.PIMAS
                        SET NOTENO = :noteno, NOTEDATE = :notedate
                        WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                          AND LTRIM(RTRIM(BILLNO)) = :billno
                          AND ISNULL(LTRIM(RTRIM(NOTENO)), '') = ''
                          AND ISNULL(LTRIM(RTRIM(VOUCNO2)), '') = ''
                          AND ISNULL(PAID, 'N') = 'N'
                        """
                    ),
                    {
                        "noteno": note,
                        "notedate": notedate,
                        "acctno": acct,
                        "billno": bno,
                    },
                )
    except PayNoteWriteError:
        raise
    except Exception as exc:
        raise _map_write_exc(exc) from exc

    _ = operator
    return {
        "acctno": acct,
        "noteno": note,
        "noteno_display": bare,
        "billcnt": billcnt,
        "billamt": billamt,
        "notedate": notedate.date().isoformat(),
        "jourmode": jourmode,
    }


def update_pay_note(
    *,
    settings: PayNotesSettings,
    acctno: str,
    noteno: str,
    billnos: list[str],
    operator: str | None = None,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Update bill membership on an unvouchered pay note."""
    if not settings.pay_notes_write_enabled:
        raise PayNoteWriteError("PAY_NOTES_WRITE_ENABLED is false", code="write_disabled")

    from src.pay_notes.parts9 import fetch_bills_for_note, list_note_bills

    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        raise PayNoteWriteError("acctno and noteno required", code="validation")

    requested = [b.strip() for b in billnos if (b or "").strip()]
    if not requested:
        raise PayNoteWriteError("select at least one bill", code="validation")
    if len(requested) != len(set(requested)):
        raise PayNoteWriteError("duplicate bill numbers", code="validation")

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
                    FROM dbo.PVMAS
                    WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                      AND LTRIM(RTRIM(NOTENO)) = :noteno
                      AND NOTED = 'Y'
                      AND ISNULL(CANCELED, 'N') <> 'Y'
                    """
                ),
                {"acctno": acct, "noteno": note},
            ).mappings().first()
            if not header:
                raise PayNoteWriteError("note not found in KSS", code="not_found")
            if str(header.get("VOUCED") or "N").strip().upper() == "Y" or (header.get("VOUCNO") or "").strip():
                raise PayNoteWriteError("note already vouchered", code="not_editable")

            current_rows = list_note_bills(site, acct, note, engine=write_eng)
            current_nos = {str(b.get("BILLNO") or "").strip() for b in current_rows}
            requested_set = set(requested)
            to_remove = current_nos - requested_set
            to_add = requested_set - current_nos

            if to_add:
                new_bills = fetch_bills_for_note(
                    site, acct, sorted(to_add), engine=write_eng, noteno=note
                )
                if len(new_bills) != len(to_add):
                    raise PayNoteWriteError("one or more bills unavailable for note", code="bill_invalid")
            else:
                new_bills = []

            all_bills = fetch_bills_for_note(
                site, acct, requested, engine=write_eng, noteno=note
            )
            if len(all_bills) != len(requested):
                raise PayNoteWriteError("one or more bills unavailable for note", code="bill_invalid")

            jourmodes = {str(b.get("JOURMODE") or "1").strip() or "1" for b in all_bills}
            if len(jourmodes) > 1:
                raise PayNoteWriteError(
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
                        UPDATE dbo.PIMAS
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
                        UPDATE dbo.PIMAS
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
                    UPDATE dbo.PVMAS
                    SET BILLCNT = :billcnt, BILLAMT = :billamt
                    WHERE ID = :id
                      AND ISNULL(VOUCED, 'N') <> 'Y'
                    """
                ),
                {"billcnt": billcnt, "billamt": billamt, "id": header["ID"]},
            )
    except PayNoteWriteError:
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


def cancel_unvouchered_pay_note(
    *,
    settings: PayNotesSettings,
    acctno: str,
    noteno: str,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Compensate create_pay_note when the Supabase reminder write fails.

    KSS and Supabase cannot share one ACID transaction — on reminder failure we
    clear PIMAS stamps and mark the PVMAS row canceled so bills are free again
    and note_exists() returns false.
    """
    if not settings.pay_notes_write_enabled:
        raise PayNoteWriteError("PAY_NOTES_WRITE_ENABLED is false", code="write_disabled")

    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        raise PayNoteWriteError("acctno and noteno required", code="validation")

    write_eng = engine or _writer_engine(settings)
    try:
        with write_eng.begin() as conn:
            header = conn.execute(
                text(
                    """
                    SELECT TOP 1 ID, VOUCED, CANCELED
                    FROM dbo.PVMAS
                    WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                      AND LTRIM(RTRIM(NOTENO)) = :noteno
                    """
                ),
                {"acctno": acct, "noteno": note},
            ).mappings().first()
            if not header:
                return {"acctno": acct, "noteno": note, "canceled": False, "reason": "not_found"}
            if str(header.get("VOUCED") or "N").strip().upper() == "Y":
                raise PayNoteWriteError(
                    "cannot cancel vouchered note",
                    code="already_vouchered",
                )
            if str(header.get("CANCELED") or "N").strip().upper() == "Y":
                return {"acctno": acct, "noteno": note, "canceled": False, "reason": "already_canceled"}

            conn.execute(
                text(
                    """
                    UPDATE dbo.PIMAS
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
                    UPDATE dbo.PVMAS
                    SET CANCELED = 'Y'
                    WHERE ID = :id
                      AND ISNULL(VOUCED, 'N') <> 'Y'
                    """
                ),
                {"id": header["ID"]},
            )
    except PayNoteWriteError:
        raise
    except Exception as exc:
        raise _map_write_exc(exc) from exc

    return {"acctno": acct, "noteno": note, "canceled": True}


def voucher_stem(jourmode: str, when: datetime | None = None) -> str:
    """PARTS9 pay voucher prefix: JOURMODE 1 (VAT / 7* vendors) → P{YYMM}-; else KCPN{YYMM}-."""
    when = when or datetime.now(_BKK)
    # Thai Buddhist year in PARTS9 (2569 → 69)
    yy = (when.year + 543) % 100
    mm = when.month
    if str(jourmode or "2").strip() == "1":
        return f"P{yy:02d}{mm:02d}-"
    return f"KCPN{yy:02d}{mm:02d}-"


def next_voucno(conn, *, jourmode: str, when: datetime | None = None) -> str:
    """Allocate next payment VOUCNO for the note's JOURMODE from live PVMAS."""
    stem = voucher_stem(jourmode, when)
    row = conn.execute(
        text("SELECT MAX(VOUCNO) AS max_no FROM dbo.PVMAS WHERE VOUCNO LIKE :pat"),
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
        raise PayNoteWriteError("generated VOUCNO exceeds 15 chars", code="voucno_overflow")
    return candidate


def next_kcpn_voucno(conn, when: datetime | None = None) -> str:
    """Backward-compatible non-VAT allocator."""
    return next_voucno(conn, jourmode="2", when=when)


def create_voucher(
    *,
    settings: PayNotesSettings,
    acctno: str,
    noteno: str,
    bpdet_lines: list[dict[str, Any]],
    discount: float = 0.0,
    operator: str | None = None,
    engine: Engine | None = None,
) -> dict[str, Any]:
    """Finance mark-paid: update PVMAS + stamp PIMAS + insert BPDET from reminder bank/net."""
    if not settings.pay_notes_write_enabled:
        raise PayNoteWriteError("PAY_NOTES_WRITE_ENABLED is false", code="write_disabled")

    acct = (acctno or "").strip()
    note = (noteno or "").strip()
    if not acct or not note:
        raise PayNoteWriteError("acctno and noteno required", code="validation")

    eng = engine or _writer_engine(settings)
    voucd = datetime.now(_BKK).replace(hour=0, minute=0, second=0, microsecond=0)
    disc = float(discount or 0)

    try:
        with eng.begin() as conn:
            header = conn.execute(
                text(
                    """
                    SELECT TOP 1 ID, JOURMODE, BILLAMT, VOUCED, VOUCNO
                    FROM dbo.PVMAS
                    WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                      AND LTRIM(RTRIM(NOTENO)) = :noteno
                      AND NOTED = 'Y'
                      AND ISNULL(CANCELED, 'N') <> 'Y'
                    """
                ),
                {"acctno": acct, "noteno": note},
            ).mappings().first()
            if not header:
                raise PayNoteWriteError("note not found in KSS", code="not_found")
            if str(header.get("VOUCED") or "N").strip().upper() == "Y" or (header.get("VOUCNO") or "").strip():
                raise PayNoteWriteError("note already vouchered", code="already_vouchered")

            billamt = float(header.get("BILLAMT") or 0)
            netamt = billamt - disc
            if netamt < 0:
                raise PayNoteWriteError("discount exceeds BILLAMT", code="validation")
            if not bpdet_lines and netamt > 1e-9:
                raise PayNoteWriteError("at least one BPDET line required", code="validation")

            jourmode = str(header.get("JOURMODE") or "1").strip() or "1"
            voucno = next_voucno(conn, jourmode=jourmode, when=voucd)

            conn.execute(
                text(
                    """
                    UPDATE dbo.PVMAS
                    SET VOUCED = 'Y',
                        VOUCDATE = :voucd,
                        VOUCNO = :voucno,
                        JOURTYPE = 'CP',
                        DISCOUNT = :discount,
                        NETAMT = :netamt,
                        PAYAMT = :netamt,
                        CHKAMT = :netamt,
                        PAID = 'Y'
                    WHERE ID = :id
                    """
                ),
                {
                    "voucd": voucd,
                    "voucno": voucno,
                    "discount": disc if disc else None,
                    "netamt": netamt,
                    "id": header["ID"],
                },
            )

            conn.execute(
                text(
                    """
                    UPDATE dbo.PIMAS
                    SET VOUCNO2 = :voucno,
                        VOUCDATE2 = :voucd,
                        PAID = 'Y',
                        PAYSTAT = '$'
                    WHERE LTRIM(RTRIM(ACCTNO)) = :acctno
                      AND LTRIM(RTRIM(NOTENO)) = :noteno
                      AND ISNULL(CANCELED, 'N') <> 'Y'
                    """
                ),
                {"voucno": voucno, "voucd": voucd, "acctno": acct, "noteno": note},
            )

            for line in bpdet_lines:
                # CHKNO is free text: cheque number, "โอน", or blank (cash / legacy).
                chkno = str(line.get("chkno") or "").strip()
                chkamt = float(line.get("chkamt") or 0)
                if chkamt <= 0:
                    raise PayNoteWriteError("BPDET CHKAMT must be > 0", code="validation")
                bankname = str(line.get("bankname") or "").strip()[:60]
                bank_gl = str(line.get("acctno") or "").strip()[:10]
                paytype = int(line.get("paytype") or 2)
                chkdate_raw = str(line.get("chkdate") or "").strip()
                if chkdate_raw:
                    chkdate = datetime.strptime(chkdate_raw[:10], "%Y-%m-%d")
                else:
                    chkdate = voucd

                conn.execute(
                    text(
                        """
                        INSERT INTO dbo.BPDET (
                          JOURMODE, JOURTYPE, VOUCDATE, VOUCNO, ACCTNO, PAYTYPE,
                          CHKNO, CHKDATE, CHKAMT, BANKNAME, STATUS, CANCELED, DONE
                        )
                        VALUES (
                          :jourmode, 'CP', :voucd, :voucno, :bank_gl, :paytype,
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
    except PayNoteWriteError:
        raise
    except Exception as exc:
        raise _map_write_exc(exc) from exc

    _ = operator
    return {
        "acctno": acct,
        "noteno": note,
        "voucno": voucno,
        "voucdate": voucd.date().isoformat(),
        "billamt": billamt,
        "discount": disc,
        "netamt": netamt,
        "bpdet_count": len(bpdet_lines),
    }

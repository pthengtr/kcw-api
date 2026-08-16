from __future__ import annotations

from typing import Any

from sqlalchemy import text

from src.db import get_engine


def fetch_prepare_headers(docnos: list[str]) -> dict[str, dict[str, Any]]:
    docs = [d.strip() for d in docnos if (d or "").strip()]
    if not docs:
        return {}
    engine = get_engine()
    out: dict[str, dict[str, Any]] = {}
    with engine.connect() as conn:
        for doc in docs:
            row = conn.execute(
                text(
                    "select docno, prepared, prepared_at, prepared_by::text as prepared_by, note "
                    "from public.po_syp_prepare where docno = :doc"
                ),
                {"doc": doc},
            ).mappings().first()
            if row:
                out[str(row["docno"])] = dict(row)
    return out


def fetch_prepare_lines(docno: str) -> dict[str, dict[str, Any]]:
    doc = (docno or "").strip()
    if not doc:
        return {}
    engine = get_engine()
    out: dict[str, dict[str, Any]] = {}
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "select line, prepared, prepared_at, prepared_by::text as prepared_by "
                "from public.po_syp_prepare_line where docno = :doc"
            ),
            {"doc": doc},
        ).mappings().all()
    for row in rows:
        out[str(row["line"]).strip()] = dict(row)
    return out


def upsert_prepare_header(*, docno: str, prepared: bool, note: str | None = None) -> dict[str, Any]:
    doc = (docno or "").strip()
    if not doc:
        raise ValueError("missing docno")
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                insert into public.po_syp_prepare (docno, prepared, prepared_at, note, updated_at)
                values (
                    :doc,
                    :prepared,
                    case when :prepared then now() else null end,
                    :note,
                    now()
                )
                on conflict (docno) do update set
                    prepared = excluded.prepared,
                    prepared_at = case
                        when excluded.prepared then coalesce(public.po_syp_prepare.prepared_at, now())
                        else null
                    end,
                    note = excluded.note,
                    updated_at = now()
                """
            ),
            {"doc": doc, "prepared": prepared, "note": note},
        )
        row = conn.execute(
            text(
                "select docno, prepared, prepared_at, note from public.po_syp_prepare where docno = :doc"
            ),
            {"doc": doc},
        ).mappings().first()
    return dict(row) if row else {"docno": doc, "prepared": prepared}

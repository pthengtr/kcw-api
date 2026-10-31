"""Tie an HQ waiting line to a live APMAS account, and remember who has no stock.

A trail (`หมด`, `ไม่มี`, or one trailing `1`) is ops writing on the vendor
code because PARTS9 has nowhere else to say the vendor does not have the
product. The original account stays on the line. The trail is stored here.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_NOTES = ("หมด", "ไม่มี")


def trail_parent(code: str, live: set[str]) -> str:
    """The APMAS account under a trail, or empty when the code is not a trail."""
    raw = str(code or "").strip()
    if not raw or raw in live:
        return ""
    noted = raw
    for suffix in _NOTES:
        if raw.endswith(suffix) and len(raw) > len(suffix):
            noted = raw[: -len(suffix)]
            break
    if noted != raw:
        if noted in live:
            return noted
        if noted.endswith("1") and len(noted) > 1 and noted[:-1] in live:
            return noted[:-1]
        return ""
    if raw.endswith("1") and len(raw) > 1 and raw[:-1] in live:
        return raw[:-1]
    return ""


def resolve_vendor(code: str, live: set[str]) -> dict[str, str]:
    """Classify one vendor code against live APMAS accounts.

    linked: the code itself is an account.
    trail: a note or a trailing 1 sits on an account. acctno is that account.
    unknown: blank, or no account to recover.
    """
    raw = str(code or "").strip()
    if raw and raw in live:
        return {"status": "linked", "acctno": raw, "raw": raw}
    parent = trail_parent(raw, live)
    if parent:
        return {"status": "trail", "acctno": parent, "raw": raw}
    return {"status": "unknown", "acctno": "", "raw": raw}


def _codes_to_check(codes: list[str]) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for raw in codes:
        code = str(raw or "").strip()
        candidates = [code]
        if code:
            for suffix in _NOTES:
                if code.endswith(suffix) and len(code) > len(suffix):
                    noted = code[: -len(suffix)]
                    candidates.append(noted)
                    if noted.endswith("1") and len(noted) > 1:
                        candidates.append(noted[:-1])
                    break
            else:
                if code.endswith("1") and len(code) > 1:
                    candidates.append(code[:-1])
        for candidate in candidates:
            if candidate and candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
    return out


def _blocked_pairs(bcodes: list[str]) -> set[tuple[str, str]]:
    from src.hq_po.db import active_blocks_for_bcodes, get_hq_po_supabase_client

    client = get_hq_po_supabase_client()
    return active_blocks_for_bcodes(client, bcodes)


def apply_vendor_blocks(items: list[dict[str, Any]]) -> None:
    """Set vendor_blocked on lines whose product is tagged for that account."""
    bcodes = []
    seen: set[str] = set()
    for item in items:
        bcode = str(item.get("bcode") or "").strip()
        vendor = str(item.get("vendor") or "").strip()
        if bcode and vendor and bcode not in seen:
            seen.add(bcode)
            bcodes.append(bcode)
    if not bcodes:
        return
    try:
        blocked = _blocked_pairs(bcodes)
    except Exception:
        logger.warning("hq po vendor block lookup failed", exc_info=True)
        return
    for item in items:
        bcode = str(item.get("bcode") or "").strip()
        vendor = str(item.get("vendor") or "").strip()
        if bcode and vendor and (bcode, vendor) in blocked:
            item["vendor_blocked"] = True


def settle_waiting_vendors(items: list[dict[str, Any]]) -> None:
    """Resolve HQ waiting vendors. A trail keeps the original account and is tagged.

    ICLOW.VENDOR is rewritten only for a waiting row, and only after the tag
    is stored. A failed lookup leaves the line as PARTS9 wrote it.
    """
    rows = [item for item in items if item.get("iclow_id")]
    if not rows:
        apply_vendor_blocks(items)
        return
    from src.hq_po.iclow_read import fetch_live_vendors

    try:
        live = fetch_live_vendors(
            _codes_to_check([str(item.get("vendor") or "") for item in rows])
        )
    except Exception:
        logger.warning("hq po vendor resolve failed", exc_info=True)
        return
    live_set = set(live)
    trails: list[dict[str, Any]] = []
    for item in rows:
        raw = str(item.get("vendor") or "").strip()
        resolved = resolve_vendor(raw, live_set)
        status = resolved["status"]
        if status == "unknown":
            item["vendor_raw"] = raw
            item["vendor"] = ""
            item["vendor_name"] = None
            item["vendor_blocked"] = False
            continue
        acct = resolved["acctno"]
        item["vendor"] = acct
        item["vendor_name"] = live.get(acct) or item.get("vendor_name") or None
        item["vendor_blocked"] = False
        if status == "trail":
            item["vendor_raw"] = raw
            item["vendor_blocked"] = True
            trails.append(item)
    _persist_trails(trails)
    apply_vendor_blocks(items)


def _persist_trails(trails: list[dict[str, Any]]) -> None:
    if not trails:
        return
    from src.hq_po.config import get_hq_po_settings
    from src.hq_po.db import block_product_vendor, get_hq_po_supabase_client

    try:
        client = get_hq_po_supabase_client()
    except Exception:
        logger.warning("hq po vendor block store unavailable", exc_info=True)
        client = None
    stamp_on = False
    try:
        stamp_on = bool(get_hq_po_settings().stamp_enabled)
    except Exception:
        stamp_on = False
    for item in trails:
        bcode = str(item.get("bcode") or "").strip()
        acct = str(item.get("vendor") or "").strip()
        raw = str(item.get("vendor_raw") or "").strip()
        if client is None or not bcode or not acct or acct == raw:
            continue
        try:
            block_product_vendor(
                client,
                bcode=bcode,
                acctno=acct,
                reason="trail",
                marked_by=None,
            )
        except Exception:
            logger.warning("hq po trail tag failed for %s", bcode, exc_info=True)
            continue
        if not stamp_on:
            continue
        try:
            iclow_id = int(item.get("iclow_id") or 0)
        except (TypeError, ValueError):
            continue
        if iclow_id <= 0:
            continue
        try:
            from src.hq_po.stamp import rewrite_waiting_vendor

            rewrite_waiting_vendor(iclow_id, acct)
        except Exception:
            logger.warning("hq po trail rewrite failed for %s", iclow_id, exc_info=True)


def annotate_markable(rows: list[dict[str, Any]], *, vendor_of) -> None:
    """Set can_mark_unavailable when the code is an account or a trail on one."""
    from src.hq_po.iclow_read import fetch_live_vendors

    codes = _codes_to_check([str(vendor_of(row) or "") for row in rows])
    try:
        live = set(fetch_live_vendors(codes))
    except Exception:
        logger.warning("hq po markable vendor lookup failed", exc_info=True)
        for row in rows:
            row["can_mark_unavailable"] = False
        return
    for row in rows:
        resolved = resolve_vendor(str(vendor_of(row) or ""), live)
        row["can_mark_unavailable"] = resolved["status"] != "unknown"

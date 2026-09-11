from __future__ import annotations

from datetime import datetime, timezone
from functools import lru_cache
from typing import Any

from supabase import Client, create_client

from src.substitutes.config import get_substitutes_settings
from src.substitutes.models import (
    BcodeConflictError,
    GroupDict,
    MemberDict,
    NotFoundError,
    SubstituteError,
)

CATALOG_SCHEMA = "catalog"


@lru_cache
def get_substitutes_supabase_client() -> Client:
    settings = get_substitutes_settings()
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def _table(client: Client, name: str):
    return client.schema(CATALOG_SCHEMA).from_(name)


def _first_row(resp) -> dict[str, Any]:
    data = resp.data
    if data is None:
        return {}
    if isinstance(data, list):
        return dict(data[0]) if data else {}
    return dict(data)


def _rows(resp) -> list[dict[str, Any]]:
    return [dict(r) for r in (resp.data or [])]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _attach_members(client: Client, groups: list[dict[str, Any]]) -> list[GroupDict]:
    ids = [g["group_id"] for g in groups if g.get("group_id")]
    by_gid: dict[str, list[MemberDict]] = {gid: [] for gid in ids}
    if ids:
        resp = (
            _table(client, "substitute_members")
            .select("*")
            .in_("group_id", ids)
            .order("sort_rank")
            .order("bcode")
            .execute()
        )
        for row in _rows(resp):
            gid = row.get("group_id")
            if gid:
                by_gid.setdefault(gid, []).append(row)  # type: ignore[arg-type]
    out: list[GroupDict] = []
    for g in groups:
        row = dict(g)
        row["members"] = by_gid.get(g["group_id"], [])
        out.append(row)  # type: ignore[arg-type]
    return out


def list_groups(client: Client, *, q: str | None = None, limit: int = 100) -> list[GroupDict]:
    if q and q.strip():
        needle = q.strip()
        member_resp = (
            _table(client, "substitute_members")
            .select("group_id")
            .eq("bcode", needle)
            .execute()
        )
        gids = [r["group_id"] for r in _rows(member_resp) if r.get("group_id")]
        if gids:
            resp = (
                _table(client, "substitute_groups")
                .select("*")
                .in_("group_id", gids)
                .order("updated_at", desc=True)
                .limit(max(1, min(limit, 500)))
                .execute()
            )
            return _attach_members(client, _rows(resp))
        resp = (
            _table(client, "substitute_groups")
            .select("*")
            .ilike("name", f"%{needle}%")
            .order("updated_at", desc=True)
            .limit(max(1, min(limit, 500)))
            .execute()
        )
        return _attach_members(client, _rows(resp))

    resp = (
        _table(client, "substitute_groups")
        .select("*")
        .order("updated_at", desc=True)
        .limit(max(1, min(limit, 500)))
        .execute()
    )
    return _attach_members(client, _rows(resp))


def get_group(client: Client, group_id: str) -> GroupDict | None:
    resp = (
        _table(client, "substitute_groups")
        .select("*")
        .eq("group_id", group_id)
        .limit(1)
        .execute()
    )
    row = _first_row(resp)
    if not row:
        return None
    return _attach_members(client, [row])[0]


def get_by_bcode(client: Client, bcode: str) -> GroupDict | None:
    code = (bcode or "").strip()
    if not code:
        return None
    resp = (
        _table(client, "substitute_members")
        .select("group_id")
        .eq("bcode", code)
        .limit(1)
        .execute()
    )
    row = _first_row(resp)
    if not row.get("group_id"):
        return None
    return get_group(client, row["group_id"])


def list_peers(client: Client, bcode: str) -> list[MemberDict]:
    group = get_by_bcode(client, bcode)
    if not group:
        return []
    code = bcode.strip()
    return [m for m in group.get("members", []) if m.get("bcode") != code]


def bulk_peers(client: Client, bcodes: list[str]) -> dict[str, list[MemberDict]]:
    """Map each input bcode → peer members (same group, exclude self), sorted."""
    codes = sorted({(c or "").strip() for c in bcodes if (c or "").strip()})
    if not codes:
        return {}
    resp = (
        _table(client, "substitute_members")
        .select("group_id,bcode")
        .in_("bcode", codes)
        .execute()
    )
    code_to_gid: dict[str, str] = {}
    for row in _rows(resp):
        code = str(row.get("bcode") or "").strip()
        gid = row.get("group_id")
        if code and gid:
            code_to_gid[code] = str(gid)
    gids = sorted(set(code_to_gid.values()))
    by_gid: dict[str, list[MemberDict]] = {gid: [] for gid in gids}
    if gids:
        mem_resp = (
            _table(client, "substitute_members")
            .select("*")
            .in_("group_id", gids)
            .order("sort_rank")
            .order("bcode")
            .execute()
        )
        for row in _rows(mem_resp):
            gid = row.get("group_id")
            if gid:
                by_gid.setdefault(str(gid), []).append(row)  # type: ignore[arg-type]
    out: dict[str, list[MemberDict]] = {}
    for code in codes:
        gid = code_to_gid.get(code)
        if not gid:
            out[code] = []
            continue
        out[code] = [m for m in by_gid.get(gid, []) if m.get("bcode") != code]
    return out


def _require_bcode_free(client: Client, bcode: str) -> None:
    code = (bcode or "").strip()
    if not code:
        raise SubstituteError("bcode required")
    resp = (
        _table(client, "substitute_members")
        .select("group_id,bcode")
        .eq("bcode", code)
        .limit(1)
        .execute()
    )
    row = _first_row(resp)
    if not row:
        return
    raise BcodeConflictError(code, row.get("group_id") or "")


def create_group(
    client: Client,
    *,
    name: str | None = None,
    note: str | None = None,
    created_by: str | None = None,
    members: list[dict[str, Any]] | None = None,
) -> GroupDict:
    member_rows = members or []
    codes = [(m.get("bcode") or "").strip() for m in member_rows]
    codes = [c for c in codes if c]
    if len(codes) != len(set(codes)):
        raise SubstituteError("duplicate bcode in members payload")
    for code in codes:
        _require_bcode_free(client, code)

    payload = {
        "name": name,
        "note": note,
        "created_by": created_by,
        "updated_at": _now(),
    }
    resp = _table(client, "substitute_groups").insert(payload).select("*").execute()
    group = _first_row(resp)
    if not group.get("group_id"):
        raise SubstituteError("failed to create group")
    gid = group["group_id"]
    for m in member_rows:
        code = (m.get("bcode") or "").strip()
        if not code:
            continue
        _table(client, "substitute_members").insert(
            {
                "group_id": gid,
                "bcode": code,
                "sort_rank": int(m.get("sort_rank") or 0),
                "note": m.get("note"),
            }
        ).execute()
    found = get_group(client, gid)
    if not found:
        raise SubstituteError("failed to load created group")
    return found


def delete_group(client: Client, group_id: str) -> None:
    existing = get_group(client, group_id)
    if not existing:
        raise NotFoundError(f"group {group_id}")
    _table(client, "substitute_groups").delete().eq("group_id", group_id).execute()


def update_group(
    client: Client,
    group_id: str,
    *,
    name: str | None = None,
    note: str | None = None,
) -> GroupDict:
    existing = get_group(client, group_id)
    if not existing:
        raise NotFoundError(f"group {group_id}")
    payload: dict[str, Any] = {"updated_at": _now()}
    if name is not None:
        payload["name"] = name
    if note is not None:
        payload["note"] = note
    _table(client, "substitute_groups").update(payload).eq("group_id", group_id).execute()
    found = get_group(client, group_id)
    if not found:
        raise NotFoundError(f"group {group_id}")
    return found


def add_member(
    client: Client,
    group_id: str,
    bcode: str,
    *,
    sort_rank: int = 0,
    note: str | None = None,
) -> MemberDict:
    group = get_group(client, group_id)
    if not group:
        raise NotFoundError(f"group {group_id}")
    code = (bcode or "").strip()
    if not code:
        raise SubstituteError("bcode required")
    _require_bcode_free(client, code)
    resp = (
        _table(client, "substitute_members")
        .insert(
            {
                "group_id": group_id,
                "bcode": code,
                "sort_rank": int(sort_rank or 0),
                "note": note,
            }
        )
        .select("*")
        .execute()
    )
    _table(client, "substitute_groups").update({"updated_at": _now()}).eq(
        "group_id", group_id
    ).execute()
    return _first_row(resp)  # type: ignore[return-value]


def remove_member(client: Client, group_id: str, bcode: str) -> None:
    code = (bcode or "").strip()
    group = get_group(client, group_id)
    if not group:
        raise NotFoundError(f"group {group_id}")
    members = group.get("members") or []
    if not any(m.get("bcode") == code for m in members):
        raise NotFoundError(f"member {code} in group {group_id}")
    (
        _table(client, "substitute_members")
        .delete()
        .eq("group_id", group_id)
        .eq("bcode", code)
        .execute()
    )
    _table(client, "substitute_groups").update({"updated_at": _now()}).eq(
        "group_id", group_id
    ).execute()

"""In-memory substitute catalog for unit tests (no Supabase)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.substitutes.models import (
    BcodeConflictError,
    GroupDict,
    MemberDict,
    NotFoundError,
    SubstituteError,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemorySubstitutes:
    def __init__(self) -> None:
        self.groups: dict[str, dict[str, Any]] = {}
        self.members: dict[str, dict[str, Any]] = {}  # bcode -> row

    def _group_with_members(self, gid: str) -> GroupDict:
        g = dict(self.groups[gid])
        mems = sorted(
            [dict(m) for m in self.members.values() if m["group_id"] == gid],
            key=lambda m: (m.get("sort_rank", 0), m.get("bcode") or ""),
        )
        g["members"] = mems
        return g  # type: ignore[return-value]

    def list_groups(self, *, q: str | None = None, limit: int = 100) -> list[GroupDict]:
        items = list(self.groups.values())
        items.sort(key=lambda g: g.get("updated_at") or "", reverse=True)
        if q and q.strip():
            needle = q.strip()
            if needle in self.members:
                gid = self.members[needle]["group_id"]
                items = [self.groups[gid]] if gid in self.groups else []
            else:
                items = [
                    g
                    for g in items
                    if needle.lower() in ((g.get("name") or "").lower())
                ]
        return [self._group_with_members(g["group_id"]) for g in items[:limit]]

    def get_group(self, group_id: str) -> GroupDict | None:
        if group_id not in self.groups:
            return None
        return self._group_with_members(group_id)

    def get_by_bcode(self, bcode: str) -> GroupDict | None:
        code = (bcode or "").strip()
        row = self.members.get(code)
        if not row:
            return None
        return self.get_group(row["group_id"])

    def list_peers(self, bcode: str) -> list[MemberDict]:
        group = self.get_by_bcode(bcode)
        if not group:
            return []
        code = bcode.strip()
        return [m for m in group.get("members", []) if m.get("bcode") != code]

    def bulk_peers(self, bcodes: list[str]) -> dict[str, list[MemberDict]]:
        codes = sorted({(c or "").strip() for c in bcodes if (c or "").strip()})
        return {code: self.list_peers(code) for code in codes}

    def create_group(
        self,
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
            if code in self.members:
                raise BcodeConflictError(code, self.members[code]["group_id"])
        gid = str(uuid4())
        ts = _now()
        self.groups[gid] = {
            "group_id": gid,
            "name": name,
            "note": note,
            "created_by": created_by,
            "created_at": ts,
            "updated_at": ts,
        }
        for m in member_rows:
            code = (m.get("bcode") or "").strip()
            if not code:
                continue
            self.members[code] = {
                "group_id": gid,
                "bcode": code,
                "sort_rank": int(m.get("sort_rank") or 0),
                "note": m.get("note"),
            }
        return self._group_with_members(gid)

    def delete_group(self, group_id: str) -> None:
        if group_id not in self.groups:
            raise NotFoundError(f"group {group_id}")
        for code, row in list(self.members.items()):
            if row["group_id"] == group_id:
                del self.members[code]
        del self.groups[group_id]

    def update_group(
        self,
        group_id: str,
        *,
        name: str | None = None,
        note: str | None = None,
    ) -> GroupDict:
        if group_id not in self.groups:
            raise NotFoundError(f"group {group_id}")
        if name is not None:
            self.groups[group_id]["name"] = name
        if note is not None:
            self.groups[group_id]["note"] = note
        self.groups[group_id]["updated_at"] = _now()
        return self._group_with_members(group_id)

    def add_member(
        self,
        group_id: str,
        bcode: str,
        *,
        sort_rank: int = 0,
        note: str | None = None,
    ) -> MemberDict:
        if group_id not in self.groups:
            raise NotFoundError(f"group {group_id}")
        code = (bcode or "").strip()
        if not code:
            raise SubstituteError("bcode required")
        if code in self.members:
            raise BcodeConflictError(code, self.members[code]["group_id"])
        row = {
            "group_id": group_id,
            "bcode": code,
            "sort_rank": int(sort_rank or 0),
            "note": note,
        }
        self.members[code] = row
        self.groups[group_id]["updated_at"] = _now()
        return row  # type: ignore[return-value]

    def remove_member(self, group_id: str, bcode: str) -> None:
        if group_id not in self.groups:
            raise NotFoundError(f"group {group_id}")
        code = (bcode or "").strip()
        row = self.members.get(code)
        if not row or row["group_id"] != group_id:
            raise NotFoundError(f"member {code} in group {group_id}")
        del self.members[code]
        self.groups[group_id]["updated_at"] = _now()

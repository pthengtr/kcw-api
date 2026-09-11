"""Substitute catalog API mounted on PARTS9 Explorer (`/parts9/api/substitutes/...`)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.routers.parts9_explorer import _require, _set_session
from src.parts9_explorer.ui import substitutes_manage_page
from src.substitutes import db as sub_db
from src.substitutes.enrich import bcode_exists_any_site, enrich_group, enrich_member_rows
from src.substitutes.models import (
    BcodeConflictError,
    NotFoundError,
    SubstituteError,
    UnknownBcodeError,
)

router = APIRouter(tags=["parts9-substitutes"])
api = APIRouter(prefix="/parts9/api/substitutes", tags=["parts9-substitutes"])


def _client():
    return sub_db.get_substitutes_supabase_client()


def _err(exc: Exception, status: int = 400) -> JSONResponse:
    body: dict[str, Any] = {"detail": str(exc), "error": type(exc).__name__}
    if isinstance(exc, BcodeConflictError):
        body["bcode"] = exc.bcode
        body["existing_group_id"] = exc.existing_group_id
        status = 409
    elif isinstance(exc, UnknownBcodeError):
        body["bcode"] = exc.bcode
        status = 400
    elif isinstance(exc, NotFoundError):
        status = 404
    return JSONResponse(body, status_code=status)


def _ensure_bcodes_exist(bcodes: list[str]) -> None:
    for code in bcodes:
        c = (code or "").strip()
        if not c:
            continue
        if not bcode_exists_any_site(c):
            raise UnknownBcodeError(c)


def _pack_group(group: dict[str, Any] | None) -> dict[str, Any] | None:
    return enrich_group(group)


class CreateGroupBody(BaseModel):
    name: str | None = None
    note: str | None = None
    members: list[dict[str, Any]] = Field(default_factory=list)


class UpdateGroupBody(BaseModel):
    name: str | None = None
    note: str | None = None


class AddMemberBody(BaseModel):
    bcode: str
    sort_rank: int = 0
    note: str | None = None


@router.get("/parts9/substitutes", response_class=HTMLResponse)
def substitutes_manage(request: Request, bcode: str | None = None):
    ident, err = _require(request)
    if err:
        return err
    html = substitutes_manage_page(user_name=ident.display_name, bcode=(bcode or "").strip())
    resp = HTMLResponse(html)
    _set_session(resp, ident)
    return resp


@api.get("/by-bcode/{bcode}")
def api_by_bcode(request: Request, bcode: str):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    code = bcode.strip()
    group = _pack_group(sub_db.get_by_bcode(_client(), code))
    if not group:
        return {"bcode": code, "group": None, "peers": []}
    peers = [m for m in group.get("members", []) if m.get("bcode") != code]
    return {"bcode": code, "group": group, "peers": peers}


@api.get("/suggest/{bcode}")
def api_suggest(
    request: Request,
    bcode: str,
    ship_branch: str | None = None,
    need_qty: float | None = None,
):
    """Live ICMAS suggestions only — not catalog; does not authorize ส่งแทน."""
    from src.substitutes.peers import needs_substitute_hint
    from src.substitutes.suggest import suggest_for_bcode

    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    code = bcode.strip()
    branch = (ship_branch or "").strip().upper() or None
    # Optional gate: if need_qty + stock provided via query, still always return
    # suggestions for Explorer; Transfer applies needs_substitute_hint server-side.
    _ = need_qty
    _ = needs_substitute_hint
    suggestions = suggest_for_bcode(code, ship_branch=branch)
    return {
        "bcode": code,
        "ship_branch": branch,
        "suggestions": suggestions,
    }


@api.get("/groups")
def api_list_groups(request: Request, q: str | None = None, limit: int = 100):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    groups = [_pack_group(g) for g in sub_db.list_groups(_client(), q=q, limit=limit)]
    return {"groups": groups}


@api.get("/groups/{group_id}")
def api_get_group(request: Request, group_id: str):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    group = _pack_group(sub_db.get_group(_client(), group_id))
    if not group:
        return JSONResponse({"detail": "not found"}, status_code=404)
    return {"group": group}


@api.post("/groups")
def api_create_group(request: Request, body: CreateGroupBody):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    try:
        codes = [(m.get("bcode") or "").strip() for m in body.members]
        _ensure_bcodes_exist(codes)
        group = sub_db.create_group(
            _client(),
            name=body.name,
            note=body.note,
            created_by=getattr(ident, "display_name", None) or getattr(ident, "line_user_id", None),
            members=body.members,
        )
        return {"group": _pack_group(group)}
    except SubstituteError as exc:
        return _err(exc)


@api.patch("/groups/{group_id}")
def api_update_group(request: Request, group_id: str, body: UpdateGroupBody):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    try:
        group = sub_db.update_group(_client(), group_id, name=body.name, note=body.note)
        return {"group": _pack_group(group)}
    except SubstituteError as exc:
        return _err(exc)


@api.delete("/groups/{group_id}")
def api_delete_group(request: Request, group_id: str):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    try:
        sub_db.delete_group(_client(), group_id)
        return {"ok": True, "group_id": group_id}
    except SubstituteError as exc:
        return _err(exc)


@api.post("/groups/{group_id}/members")
def api_add_member(request: Request, group_id: str, body: AddMemberBody):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    try:
        _ensure_bcodes_exist([body.bcode])
        member = sub_db.add_member(
            _client(),
            group_id,
            body.bcode,
            sort_rank=body.sort_rank,
            note=body.note,
        )
        enriched = enrich_member_rows([member])[0]
        return {"member": enriched}
    except SubstituteError as exc:
        return _err(exc)


@api.delete("/groups/{group_id}/members/{bcode}")
def api_remove_member(request: Request, group_id: str, bcode: str):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    try:
        sub_db.remove_member(_client(), group_id, bcode)
        return {"ok": True, "group_id": group_id, "bcode": bcode.strip()}
    except SubstituteError as exc:
        return _err(exc)


router.include_router(api)

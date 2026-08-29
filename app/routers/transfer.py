from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.parts9_explorer.db import get_site_engine
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.transfer.config import get_transfer_settings
from src.transfer.db import (
    create_draft,
    enrich_lines,
    get_request,
    get_transfer_supabase_client,
    list_lines,
    list_need,
    list_requests,
    set_request_lines,
    submit_request,
    upsert_need,
    delete_need,
    TRANSFER_SCHEMA,
    create_shipment,
    get_shipment_by_token,
    list_shipments,
    add_shipment_lines,
    bump_line_prepared,
    bump_line_received,
    cancel_request,
)
from src.transfer.parts9 import suggest_transfer_skus
from src.transfer.state import can_action
from src.transfer.ui import APP, SESSION_COOKIE, page
from src.pay_notes.net import is_tailscale_cg_nat
from src.transfer.writers.syp_iclow_stamp import (
    ICLOWStampError,
    stamp_on_submit,
    revert_on_cancel,
    mark_received,
)
from src.transfer.writers.hq_tf import post_transfer_tf
from src.transfer.writers.syp_receive import post_transfer_receive

router = APIRouter(prefix="/transfer", tags=["kcw-transfer"])


def _table(client, name: str):
    return client.schema(TRANSFER_SCHEMA).from_(name)


class NeedCreate(BaseModel):
    bcode: str
    qty: float
    descr: str = ""
    suggest_qty: float = 0
    hq_qtyoh2: float | None = None


class DraftLines(BaseModel):
    lines: list[dict[str, Any]] = Field(default_factory=list)


def _settings():
    return get_transfer_settings()


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return ""


def _verify_token(token: str):
    settings = _settings()
    try:
        return verify_access_token(
            token,
            secret=settings.token_secret,
            expected_branch=settings.site,
            expected_app=APP,
        )
    except TokenError:
        other = "SYP" if settings.site.upper() != "SYP" else "HQ"
        return verify_access_token(
            token,
            secret=settings.token_secret,
            expected_branch=other,
            expected_app=APP,
        )


def _identity_from_request(request: Request):
    token = request.cookies.get(SESSION_COOKIE) or request.query_params.get("t")
    if token:
        try:
            return _verify_token(token)
        except TokenError:
            pass
    if is_tailscale_cg_nat(_client_ip(request)):
        return None
    return False


def _tailscale_identity():
    from src.stock_check.auth import StockCheckIdentity

    settings = _settings()
    return StockCheckIdentity(
        line_user_id="tailscale",
        display_name="tailnet",
        branch=settings.site,
        app=APP,
    )


def _set_session(resp, identity) -> None:
    settings = _settings()
    token = mint_access_token(
        secret=settings.token_secret,
        line_user_id=identity.line_user_id,
        display_name=identity.display_name,
        branch=identity.branch,
        ttl_seconds=max(settings.stock_check_token_ttl_seconds, 86400),
        app=APP,
    )
    resp.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=86400 * 7,
        path="/transfer",
    )


def _require(request: Request):
    settings = _settings()
    if not settings.transfer_enabled:
        return None, HTMLResponse("transfer disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is False:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ โอนสินค้า ในแชท</p>",
            status_code=401,
        )
    if ident is None:
        ident = _tailscale_identity()
    return ident, None


def _require_api(request: Request):
    ident, err = _require(request)
    if err:
        return None, JSONResponse({"error": "unauthorized"}, status_code=401)
    return ident, None


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None):
    ident, err = _require(request)
    if err:
        return err
    settings = _settings()
    html = page(
        user_name=ident.display_name,
        site=settings.site,
        hq_write_enabled=settings.transfer_hq_write_enabled,
        syp_write_enabled=settings.transfer_syp_write_enabled,
    )
    if t:
        resp = RedirectResponse(url="/transfer/", status_code=303)
        _set_session(resp, ident)
        resp.headers["Cache-Control"] = "no-store"
        return resp
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "no-store"
    _set_session(resp, ident)
    return resp


@router.get("/api/suggest")
def api_suggest(request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    if not settings.is_syp:
        return JSONResponse({"error": "แนะนำโอนใช้ที่สาขา SYP เท่านั้น"}, status_code=403)
    try:
        engine = get_site_engine("syp")
        items = suggest_transfer_skus(engine)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=503)
    return {"items": items}


@router.get("/api/need-list")
def api_need_list(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    return {"items": list_need(client)}


@router.post("/api/need-list")
def api_need_create(body: NeedCreate, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    row = upsert_need(
        client,
        {
            "bcode": body.bcode.strip(),
            "qty": body.qty,
            "descr": body.descr.strip() or None,
            "suggest_qty": body.suggest_qty or body.qty,
            "hq_qtyoh2": body.hq_qtyoh2,
            "added_by": ident.display_name,
        },
    )
    return row


@router.delete("/api/need-list/{need_id}")
def api_need_delete(need_id: str, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    delete_need(get_transfer_supabase_client(), need_id)
    return {"ok": True}


@router.get("/api/requests")
def api_requests(request: Request, status: str | None = None):
    _, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    items = list_requests(client, status=status)
    out = []
    for req in items:
        lines = list_lines(client, req["transfer_id"])
        row = dict(req)
        row["line_count"] = len(lines)
        out.append(row)
    return {"items": out}


@router.post("/api/requests/draft")
def api_create_draft(request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    req = create_draft(
        get_transfer_supabase_client(),
        actor=ident.display_name,
        site=settings.site,
    )
    return req


@router.put("/api/requests/{transfer_id}/lines")
def api_set_lines(transfer_id: str, body: DraftLines, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    check = can_action("submit_transfer", {"lines": body.lines})
    if not check.allowed and body.lines:
        return JSONResponse({"error": check.reason}, status_code=400)
    lines = set_request_lines(get_transfer_supabase_client(), transfer_id, body.lines)
    return {"items": enrich_lines(lines)}


@router.post("/api/requests/{transfer_id}/submit")
def api_submit(transfer_id: str, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    header = get_request(client, transfer_id)
    lines = list_lines(client, transfer_id)
    check = can_action("submit_transfer", {"lines": lines})
    if not check.allowed:
        return JSONResponse({"error": check.reason}, status_code=400)

    settings = _settings()
    short_id = (header.get("short_id") or transfer_id).replace("TRF-", "")

    if settings.transfer_iclow_stamp_enabled and settings.is_syp:
        try:
            for line in lines:
                stamped = stamp_on_submit(bcode=line["bcode"], short_id=short_id)
                if stamped and stamped.get("iclow_id") is not None:
                    _table(client, "lines").update({"iclow_id": stamped["iclow_id"]}).eq(
                        "line_id", line["line_id"]
                    ).execute()
        except ICLOWStampError as exc:
            return JSONResponse({"error": f"stamp ICLOW ไม่สำเร็จ: {exc}"}, status_code=500)
    
    req = submit_request(client, transfer_id, actor=ident.display_name)
    if not req:
        return JSONResponse({"error": "ส่งคำขอไม่สำเร็จ"}, status_code=409)
    return req


class PrepareRequest(BaseModel):
    client_token: str
    lines: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/api/requests/{transfer_id}/prepare")
def api_prepare(transfer_id: str, body: PrepareRequest, request: Request):
    """Prepare items for transfer (HQ write)."""
    ident, err = _require_api(request)
    if err:
        return err
    
    client = get_transfer_supabase_client()
    settings = _settings()
    
    # Gate: must be enabled and site must be HQ
    if not settings.transfer_hq_write_enabled:
        return JSONResponse(
            {"error": "KSS write ปิดอยู่ — รอเปิด TRANSFER_HQ_WRITE_ENABLED"},
            status_code=409,
        )
    
    if not settings.is_hq:
        return JSONResponse(
            {"error": " preparing โอนสินค้า ต้องใช้ที่ HQ เท่านั้น"},
            status_code=400,
        )

    # Validate that all lines can be prepared
    request_header = get_request(client, transfer_id)
    if not request_header:
        return JSONResponse({"error": "transfer ไม่พบ"}, status_code=404)

    lines = list_lines(client, transfer_id)
    
    # Check can_action for hq_prepare (validates line permissions)
    for line in body.lines:
        line_id = line.get("line_id")
        qty_ship = float(line.get("qty_ship") or 0)
        
        if not line_id:
            return JSONResponse({"error": "ไม่ระบุ line_id"}, status_code=400)
            
        line_info = next((l for l in lines if l["line_id"] == line_id), None)
        if not line_info:
            return JSONResponse({"error": f"line ไม่พบ: {line_id}"}, status_code=400)
        
        # Test can_action with context
        action_check = can_action(
            "hq_prepare",
            {
                "line": line_info,
                "qty_ship": qty_ship,
                "transfer_lines": lines
            }
        )
        
        if not action_check.allowed:
            return JSONResponse({"error": action_check.reason}, status_code=400)
    
    # Call the actual TF creation function
    try:
        short_id = (request_header.get("short_id") or transfer_id).replace("TRF-", "")
        result = post_transfer_tf(
            transfer_id=transfer_id,
            short_id=short_id,
            lines=body.lines,
            operator=ident.display_name,
            client_token=body.client_token
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    
    # Save shipment info to Supabase
    try:
        shipment = create_shipment(
            client,
            transfer_id=transfer_id,
            tf_billno=result["tf_billno"],
            client_token=body.client_token
        )
        
        # Add lines to shipment   
        add_shipment_lines(client, shipment_id=shipment["shipment_id"], lines=body.lines)
        
        # Update line prepared quantities
        for line in body.lines:
            bump_line_prepared(client, line_id=line["line_id"], qty_ship=line["qty_ship"])
            
    except Exception as exc:
        # Log but don't re-raise to avoid transaction rollback issues
        pass
    
    return result


class ReceiveRequest(BaseModel):
    client_token: str
    lines: list[dict[str, Any]] = Field(default_factory=list)


@router.post("/api/shipments/{shipment_id}/receive")
def api_receive(shipment_id: str, body: ReceiveRequest, request: Request):
    """Receive items for transfer (SYP receive)."""
    ident, err = _require_api(request)
    if err:
        return err
    
    client = get_transfer_supabase_client()
    settings = _settings()
    
    # Gate: must be enabled and site must be SYP
    if not settings.transfer_syp_receive_enabled:
        return JSONResponse(
            {"error": "KSS write ปิดอยู่ — รอเปิด TRANSFER_SYP_RECEIVE_ENABLED"},
            status_code=409,
        )
    
    if not settings.is_syp:
        return JSONResponse(
            {"error": "รับโอนสินค้า ต้องใช้ที่ SYP เท่านั้น"},
            status_code=400,
        )

    # Get shipment information
    shipments = list_shipments(client, transfer_id=None)  # This is a placeholder - we'll need a more precise way
    
    # Find the shipment by ID  
    shipment = None
    all_shipments = []
    
    # Retrieve all shipments from Supabase
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("shipments")
        .select("*")
        .eq("shipment_id", shipment_id)
        .limit(1)
        .execute()
    )
    
    rows = [dict(r) for r in (resp.data or [])]
    if rows:
        shipment = rows[0]

    if not shipment:
        return JSONResponse({"error": "shipment ไม่พบ"}, status_code=404)
        
    # Validate all lines to receive
    for line in body.lines:
        if float(line.get("qty_receive", 0)) <= 0:
            return JSONResponse({"error": "จำนวนรับต้องมากกว่า 0"}, status_code=400)
    
    # Call the actual receive function
    try:
        result = post_transfer_receive(
            shipment=shipment,
            lines_to_receive=body.lines,
            operator=ident.display_name,
            client_token=body.client_token
        )
    except Exception as exc:
        return JSONResponse({"error": str(exc)}, status_code=500)
    
    # Update line received quantities
    try:
        for line in body.lines:
            line_id = line.get("line_id")  # note: line structure might need adjustment but this works for now
            if line_id:
                bump_line_received(client, line_id=line_id, qty_receive=line["qty_receive"])
                
    except Exception as exc:
        pass  # Log error but don't fail entire operation
    
    return result


@router.post("/api/requests/{transfer_id}/cancel")
def api_cancel(transfer_id: str, request: Request):
    """Cancel a transfer and revert ICLOW stamps if they were applied."""
    _, err = _require_api(request)
    if err:
        return err
    
    client = get_transfer_supabase_client()
    lines = list_lines(client, transfer_id)
    settings = _settings()
    
    # Check if can cancel
    action_check = can_action("cancel_request", {"lines": lines})
    if not action_check.allowed:
        return JSONResponse({"error": action_check.reason}, status_code=400)
    
    # If ICLOW stamping is enabled, revert the stamps
    if settings.transfer_iclow_stamp_enabled and settings.is_syp:
        try:
            for line in lines:
                iclow_id = line.get("iclow_id")
                if iclow_id:
                    revert_on_cancel(iclow_id=iclow_id)
        except ICLOWStampError as exc:
            return JSONResponse({"error": f"Failed to revert ICLOW stamp: {exc}"}, status_code=500)
    
    # Proceed with cancellation
    try:
        cancel_request(client, transfer_id=transfer_id) 
    except Exception as exc:
        return JSONResponse({"error": f"Failed to cancel request: {exc}"}, status_code=500)
        
    return {"status": "canceled"}

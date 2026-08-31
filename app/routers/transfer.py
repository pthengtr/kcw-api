from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, Field

from src.stock_check.auth import TokenError, mint_access_token, verify_access_token
from src.transfer.config import get_transfer_settings
from src.transfer.db import (
    TRANSFER_SCHEMA,
    BumpError,
    add_shipment_lines,
    bump_line_prepared,
    bump_line_received,
    bump_shipment_line_received,
    cancel_request,
    create_draft,
    create_receipt,
    create_shipment,
    delete_draft,
    delete_need,
    enrich_lines,
    get_receipt_by_token,
    get_request,
    get_shipment_by_token,
    get_transfer_supabase_client,
    list_lines,
    list_need,
    list_receive_queue,
    list_requests,
    list_shipment_lines,
    list_shipments,
    refresh_request_status,
    set_request_lines,
    shipment_has_lines,
    submit_request,
    upsert_need,
)
from src.transfer.direction import (
    branches_for_direction,
    can_prepare_at_site,
    can_receive_at_site,
    can_submit_at_site,
    direction_label,
    should_stamp_iclow,
)
from src.transfer.parts9 import enrich_transfer_lines, lookup_transfer_product, suggest_transfer_skus
from src.transfer.state import can_action, shipment_lines_fully_received, summarize_request_progress
from src.transfer.ui import APP, SESSION_COOKIE, page
from src.pay_notes.net import is_tailscale_cg_nat
from src.transfer.writers.syp_iclow_stamp import (
    ICLOWStampError,
    mark_received,
    revert_on_cancel,
    stamp_on_submit,
)
from src.transfer.writers.receive_pimas import TransferReceiveError, post_transfer_receive
from src.transfer.writers.ship_simas import TransferShipError, post_transfer_ship

router = APIRouter(prefix="/transfer", tags=["kcw-transfer"])


def _table(client, name: str):
    return client.schema(TRANSFER_SCHEMA).from_(name)


class NeedCreate(BaseModel):
    bcode: str
    qty: float
    descr: str = ""
    suggest_qty: float = 0
    hq_qtyoh2: float | None = None


class DraftCreate(BaseModel):
    direction: str = "to_syp"


class DraftLines(BaseModel):
    lines: list[dict[str, Any]] = Field(default_factory=list)


class PrepareRequest(BaseModel):
    client_token: str = ""
    lines: list[dict[str, Any]] = Field(default_factory=list)


class ReceiveRequest(BaseModel):
    client_token: str = ""
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


def _ship_write_enabled(from_branch: str) -> bool:
    s = _settings()
    return s.hq_ship_write_enabled if from_branch.upper() == "HQ" else s.syp_ship_write_enabled


def _receive_write_enabled(to_branch: str) -> bool:
    s = _settings()
    return s.hq_receive_write_enabled if to_branch.upper() == "HQ" else s.syp_receive_write_enabled


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None):
    ident, err = _require(request)
    if err:
        return err
    settings = _settings()
    html = page(
        user_name=ident.display_name,
        site=settings.site,
        hq_ship_enabled=settings.hq_ship_write_enabled,
        syp_ship_enabled=settings.syp_ship_write_enabled,
        hq_receive_enabled=settings.hq_receive_write_enabled,
        syp_receive_enabled=settings.syp_receive_write_enabled,
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
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    try:
        items = suggest_transfer_skus(site=settings.site)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=503)
    return {"items": items}


@router.get("/api/product")
def api_product(bcode: str, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    code = (bcode or "").strip()
    if not code:
        return JSONResponse({"error": "ระบุรหัสสินค้า"}, status_code=400)
    try:
        product = lookup_transfer_product(bcode=code)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=503)
    if not product:
        return JSONResponse({"error": f"ไม่พบรหัส {code} ใน ICMAS"}, status_code=404)
    return product


@router.get("/api/need-list")
def api_need_list(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    items = enrich_transfer_lines(list_need(get_transfer_supabase_client()))
    return {"items": items}


@router.post("/api/need-list")
def api_need_create(body: NeedCreate, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    payload = {
        "bcode": body.bcode.strip(),
        "qty": body.qty,
        "descr": body.descr.strip() or None,
        "suggest_qty": body.suggest_qty or body.qty,
        "hq_qtyoh2": body.hq_qtyoh2,
        "added_by": ident.display_name,
    }
    if not payload["descr"]:
        try:
            product = lookup_transfer_product(bcode=payload["bcode"])
        except Exception:
            product = None
        if product:
            payload["descr"] = product.get("descr") or None
            if payload["hq_qtyoh2"] is None:
                payload["hq_qtyoh2"] = product.get("hq_qtyoh2")
    row = upsert_need(get_transfer_supabase_client(), payload)
    return row


@router.delete("/api/need-list/{need_id}")
def api_need_delete(need_id: str, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    delete_need(get_transfer_supabase_client(), need_id)
    return {"ok": True}


@router.get("/api/receive-lines")
def api_receive_lines(request: Request):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    items = list_receive_queue(get_transfer_supabase_client(), site=settings.site)
    return {"items": items}


@router.get("/api/requests")
def api_requests(
    request: Request,
    status: str | None = None,
    role: str | None = None,
):
    _, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    client = get_transfer_supabase_client()
    items = list_requests(client, status=status, role=role, site=settings.site)
    out = []
    for req in items:
        lines = enrich_lines(list_lines(client, req["transfer_id"]))
        row = dict(req)
        row["line_count"] = len(lines)
        row.update(summarize_request_progress(lines))
        fb = row.get("from_branch") or "HQ"
        tb = row.get("to_branch") or "SYP"
        row["direction_label"] = direction_label(fb, tb)
        out.append(row)
    return {"items": out}


@router.get("/api/requests/{transfer_id}/lines")
def api_request_lines(transfer_id: str, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    header = get_request(client, transfer_id)
    if not header:
        return JSONResponse({"error": "transfer ไม่พบ"}, status_code=404)
    lines = enrich_transfer_lines(
        enrich_lines(list_lines(client, transfer_id)),
        from_branch=header.get("from_branch"),
        to_branch=header.get("to_branch"),
    )
    shipments = list_shipments(client, transfer_id=transfer_id)
    for ship in shipments:
        ship["lines"] = list_shipment_lines(client, shipment_id=ship["shipment_id"])
        ship["fully_received"] = shipment_lines_fully_received(ship["lines"])
    progress = summarize_request_progress(lines)
    return {
        "header": header,
        "items": lines,
        "lines": lines,
        "shipments": shipments,
        **progress,
        **header,
    }


@router.post("/api/requests/draft")
def api_create_draft(body: DraftCreate, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    settings = _settings()
    from_b, to_b = branches_for_direction(body.direction)
    req = create_draft(
        get_transfer_supabase_client(),
        actor=ident.display_name,
        site=settings.site,
        from_branch=from_b,
        to_branch=to_b,
    )
    req["direction_label"] = direction_label(from_b, to_b)
    return req


@router.put("/api/requests/{transfer_id}/lines")
def api_set_lines(transfer_id: str, body: DraftLines, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    header = get_request(client, transfer_id)
    if not header:
        return JSONResponse({"error": "transfer ไม่พบ"}, status_code=404)
    check = can_action("edit_draft", {"status": header.get("status")})
    if not check.allowed:
        return JSONResponse({"error": check.reason}, status_code=400)
    check = can_action("submit_transfer", {"lines": body.lines})
    if not check.allowed and body.lines:
        return JSONResponse({"error": check.reason}, status_code=400)
    lines = set_request_lines(client, transfer_id, body.lines)
    return {"items": enrich_lines(lines)}


@router.delete("/api/requests/{transfer_id}")
def api_delete_draft(transfer_id: str, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    header = get_request(client, transfer_id)
    if not header:
        return JSONResponse({"error": "transfer ไม่พบ"}, status_code=404)
    check = can_action("delete_draft", {"status": header.get("status")})
    if not check.allowed:
        return JSONResponse({"error": check.reason}, status_code=400)
    if not delete_draft(client, transfer_id=transfer_id):
        return JSONResponse({"error": "ลบร่างไม่สำเร็จ"}, status_code=409)
    return {"ok": True}


@router.post("/api/requests/{transfer_id}/submit")
def api_submit(transfer_id: str, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    header = get_request(client, transfer_id)
    if not header:
        return JSONResponse({"error": "transfer ไม่พบ"}, status_code=404)
    settings = _settings()
    to_branch = (header.get("to_branch") or "SYP").upper()
    if not can_submit_at_site(settings.site, to_branch):
        return JSONResponse({"error": "ส่งคำขอได้เฉพาะสาขาที่ขอรับสินค้า"}, status_code=400)
    lines = list_lines(client, transfer_id)
    check = can_action("submit_transfer", {"lines": lines})
    if not check.allowed:
        return JSONResponse({"error": check.reason}, status_code=400)
    short_id = (header.get("short_id") or transfer_id).replace("TRF-", "")
    from_branch = (header.get("from_branch") or "HQ").upper()
    req = submit_request(client, transfer_id, actor=ident.display_name)
    if not req:
        return JSONResponse({"error": "ส่งคำขอไม่สำเร็จ"}, status_code=409)
    stamped_ids: list[str] = []
    if should_stamp_iclow(
        enabled=settings.transfer_iclow_stamp_enabled,
        site=settings.site,
        from_branch=from_branch,
        to_branch=to_branch,
    ):
        try:
            for line in lines:
                stamped = stamp_on_submit(bcode=line["bcode"], short_id=short_id)
                if stamped and stamped.get("iclow_id") is not None:
                    stamped_ids.append(str(stamped["iclow_id"]))
                    _table(client, "lines").update({"iclow_id": stamped["iclow_id"]}).eq(
                        "line_id", line["line_id"]
                    ).execute()
        except ICLOWStampError as exc:
            for iclow_id in stamped_ids:
                try:
                    revert_on_cancel(iclow_id=iclow_id)
                except ICLOWStampError:
                    pass
            return JSONResponse(
                {"error": f"stamp ICLOW ไม่สำเร็จ: {exc}"},
                status_code=403 if exc.code == "iclow_permission_denied" else 500,
            )
    return req


@router.post("/api/requests/{transfer_id}/prepare")
def api_prepare(transfer_id: str, body: PrepareRequest, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    settings = _settings()
    header = get_request(client, transfer_id)
    if not header:
        return JSONResponse({"error": "transfer ไม่พบ"}, status_code=404)
    from_branch = (header.get("from_branch") or "HQ").upper()
    if not can_prepare_at_site(settings.site, from_branch):
        return JSONResponse({"error": "จัดสินค้าได้เฉพาะสาขาต้นทาง"}, status_code=400)
    if not _ship_write_enabled(from_branch):
        return JSONResponse(
            {"error": "PARTS9 ship write ปิดอยู่ — เปิด TRANSFER_*_SHIP_WRITE_ENABLED"},
            status_code=409,
        )
    client_token = body.client_token or str(uuid4())
    existing_shipment = get_shipment_by_token(
        client, transfer_id=transfer_id, client_token=client_token
    )
    if existing_shipment:
        billno = existing_shipment.get("ship_billno") or existing_shipment.get("tf_billno")
        if billno:
            return {
                "ship_billno": billno,
                "tf_billno": billno,
                "shipment_id": existing_shipment["shipment_id"],
            }
    lines = enrich_lines(list_lines(client, transfer_id))
    header_status = header.get("status") or "requested"
    for line in body.lines:
        line_id = line.get("line_id")
        qty_ship = float(line.get("qty_ship") or 0)
        if not line_id:
            return JSONResponse({"error": "ไม่ระบุ line_id"}, status_code=400)
        line_info = next((ln for ln in lines if ln["line_id"] == line_id), None)
        if not line_info:
            return JSONResponse({"error": f"line ไม่พบ: {line_id}"}, status_code=400)
        check = can_action(
            "prepare_ship",
            {
                "status": header_status,
                "qty_ship": qty_ship,
                "qty_requested": line_info.get("qty_requested", 0),
                "qty_prepared": line_info.get("qty_prepared", 0),
            },
        )
        if not check.allowed:
            return JSONResponse({"error": check.reason}, status_code=400)
        if not line.get("bcode"):
            line["bcode"] = line_info.get("bcode")
        if not line.get("descr"):
            line["descr"] = line_info.get("descr")
    short_id = (header.get("short_id") or transfer_id).replace("TRF-", "")
    try:
        result = post_transfer_ship(
            from_branch=from_branch,
            transfer_id=transfer_id,
            short_id=short_id,
            lines=body.lines,
            operator=ident.display_name,
            client_token=client_token,
        )
    except TransferShipError as exc:
        code = 403 if exc.code == "permission_denied" else 500
        return JSONResponse({"error": str(exc)}, status_code=code)
    billno = result.get("ship_billno") or result.get("tf_billno")
    shipment_id = result.get("shipment_id")
    try:
        if not shipment_id:
            shipment = create_shipment(
                client, transfer_id=transfer_id, tf_billno=billno, client_token=client_token
            )
            shipment_id = shipment["shipment_id"]
        if not shipment_has_lines(client, shipment_id):
            add_shipment_lines(client, shipment_id=shipment_id, lines=body.lines)
        for line in body.lines:
            bump_line_prepared(client, line_id=line["line_id"], qty_ship=line["qty_ship"])
        refresh_request_status(client, transfer_id)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"error": str(exc), "billno": billno, "reconcile": True},
            status_code=500,
        )
    return {**result, "shipment_id": shipment_id}


@router.post("/api/shipments/{shipment_id}/receive")
def api_receive(shipment_id: str, body: ReceiveRequest, request: Request):
    ident, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    settings = _settings()
    resp = (
        client.schema(TRANSFER_SCHEMA)
        .from_("shipments")
        .select("*")
        .eq("shipment_id", shipment_id)
        .limit(1)
        .execute()
    )
    shipment = dict(resp.data[0]) if resp.data else None
    if not shipment:
        return JSONResponse({"error": "shipment ไม่พบ"}, status_code=404)
    header = get_request(client, shipment["transfer_id"])
    if not header:
        return JSONResponse({"error": "transfer ไม่พบ"}, status_code=404)
    from_branch = (header.get("from_branch") or "HQ").upper()
    to_branch = (header.get("to_branch") or "SYP").upper()
    if not can_receive_at_site(settings.site, to_branch):
        return JSONResponse({"error": "รับสินค้าได้เฉพาะสาขาปลายทาง"}, status_code=400)
    if not _receive_write_enabled(to_branch):
        return JSONResponse(
            {"error": "PARTS9 receive write ปิดอยู่ — เปิด TRANSFER_*_RECEIVE_WRITE_ENABLED"},
            status_code=409,
        )
    ship_billno = shipment.get("ship_billno") or shipment.get("tf_billno") or ""
    if not ship_billno:
        return JSONResponse({"error": "ยังไม่มีใบ TF — รอสาขาต้นทางจัดส่งก่อน"}, status_code=400)
    transfer_lines = {ln["line_id"]: ln for ln in enrich_lines(list_lines(client, shipment["transfer_id"]))}
    ship_lines = {
        sl["shipment_line_id"]: sl
        for sl in list_shipment_lines(client, shipment_id=shipment_id)
    }
    for line in body.lines:
        qty_recv = float(line.get("qty_receive") or 0)
        shipment_line_id = line.get("shipment_line_id")
        sl = ship_lines.get(shipment_line_id) if shipment_line_id else None
        if not sl:
            for candidate in ship_lines.values():
                if candidate.get("line_id") == line.get("line_id") or candidate.get("bcode") == line.get("bcode"):
                    sl = candidate
                    shipment_line_id = candidate.get("shipment_line_id")
                    break
        if not sl:
            return JSONResponse({"error": "ไม่พบรายการในใบจัด"}, status_code=400)
        line_id = line.get("line_id") or sl.get("line_id")
        line_info = transfer_lines.get(line_id, {})
        check = can_action(
            "syp_receive",
            {
                "tf_billno": ship_billno,
                "qty_receive": qty_recv,
                "qty_on_shipment": float(sl.get("qty_shipped") or 0) - float(sl.get("qty_received") or 0),
                "qty_received": float(line_info.get("qty_received") or 0),
                "qty_prepared": float(line_info.get("qty_prepared") or 0),
            },
        )
        if not check.allowed:
            return JSONResponse({"error": check.reason}, status_code=400)
        if not line.get("bcode"):
            line["bcode"] = sl.get("bcode")
        line["shipment_line_id"] = shipment_line_id
        line["line_id"] = line_id
        if not line.get("iclow_id"):
            line["iclow_id"] = line_info.get("iclow_id")
    client_token = body.client_token or str(uuid4())
    existing_receipt = get_receipt_by_token(client, client_token)
    if existing_receipt:
        return {
            "status": "received",
            "receive_billno": existing_receipt["receive_billno"],
            "ship_billno": ship_billno,
            "client_token": client_token,
            "warnings": [],
        }
    try:
        result = post_transfer_receive(
            to_branch=to_branch,
            from_branch=from_branch,
            shipment=shipment,
            lines_to_receive=body.lines,
            operator=ident.display_name,
            client_token=client_token,
        )
    except TransferReceiveError as exc:
        code = 403 if exc.code == "permission_denied" else 500
        return JSONResponse({"error": str(exc)}, status_code=code)
    receive_billno = result.get("receive_billno")
    warnings: list[str] = []
    try:
        create_receipt(
            client,
            shipment_id=shipment_id,
            client_token=client_token,
            receive_billno=receive_billno,
        )
        for line in body.lines:
            line_id = line.get("line_id")
            qty_recv = float(line.get("qty_receive") or 0)
            if line_id:
                bump_line_received(client, line_id=line_id, qty_receive=qty_recv)
            shipment_line_id = line.get("shipment_line_id")
            if shipment_line_id:
                bump_shipment_line_received(
                    client, shipment_line_id=str(shipment_line_id), qty_receive=qty_recv
                )
            line_id = line.get("line_id")
            line_info = transfer_lines.get(line_id, {}) if line_id else {}
            new_recv = float(line_info.get("qty_received") or 0) + qty_recv
            req_qty = float(line_info.get("qty_requested") or 0)
            iclow_id = line.get("iclow_id")
            if (
                iclow_id
                and new_recv >= req_qty
                and should_stamp_iclow(
                    enabled=settings.transfer_iclow_stamp_enabled,
                    site=settings.site,
                    from_branch=(header.get("from_branch") or "HQ"),
                    to_branch=to_branch,
                )
            ):
                ship_bill = shipment.get("ship_billno") or shipment.get("tf_billno")
                try:
                    mark_received(iclow_id=str(iclow_id), tf_billno=ship_bill or "")
                except ICLOWStampError as exc:
                    warnings.append(str(exc))
        ship_lines_after = list_shipment_lines(client, shipment_id=shipment_id)
        if shipment_lines_fully_received(ship_lines_after):
            _table(client, "shipments").update({
                "posted_at": datetime.now(timezone.utc).isoformat(),
            }).eq("shipment_id", shipment_id).execute()
        refresh_request_status(client, shipment["transfer_id"])
    except BumpError as exc:
        return JSONResponse({"error": str(exc)}, status_code=409)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse(
            {"error": str(exc), "receive_billno": receive_billno, "reconcile": True},
            status_code=500,
        )
    return {**result, "warnings": warnings}


@router.post("/api/requests/{transfer_id}/cancel")
def api_cancel(transfer_id: str, request: Request):
    _, err = _require_api(request)
    if err:
        return err
    client = get_transfer_supabase_client()
    header = get_request(client, transfer_id)
    lines = list_lines(client, transfer_id)
    has_shipments = bool(list_shipments(client, transfer_id=transfer_id))
    check = can_action(
        "cancel_request",
        {"has_shipments": has_shipments, "status": header.get("status")},
    )
    if not check.allowed:
        return JSONResponse({"error": check.reason}, status_code=400)
    settings = _settings()
    if should_stamp_iclow(
        enabled=settings.transfer_iclow_stamp_enabled,
        site=settings.site,
        from_branch=(header.get("from_branch") or "HQ"),
        to_branch=(header.get("to_branch") or "SYP"),
    ):
        try:
            for line in lines:
                iclow_id = line.get("iclow_id")
                if iclow_id:
                    revert_on_cancel(iclow_id=str(iclow_id))
        except ICLOWStampError as exc:
            return JSONResponse({"error": f"Failed to revert ICLOW stamp: {exc}"}, status_code=500)
    cancel_request(client, transfer_id=transfer_id)
    return {"status": "canceled"}

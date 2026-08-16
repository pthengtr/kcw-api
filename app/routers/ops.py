from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from src.ops.config import get_ops_settings
from src.ops.net import is_tailscale_cg_nat
from src.ops.po import get_po_lines, health_probes, list_pending_receive, list_purchase_orders
from src.ops.prepare import fetch_prepare_headers, fetch_prepare_lines, upsert_prepare_header
from src.ops.ui import APP, SESSION_COOKIE, page
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token

router = APIRouter(prefix="/ops", tags=["kcw-ops"])


def _settings():
    return get_ops_settings()


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
    settings = _settings()
    from src.stock_check.auth import StockCheckIdentity

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
        path="/ops",
    )


def _require(request: Request):
    settings = _settings()
    if not settings.kcw_ops_enabled:
        return None, HTMLResponse("kcw-ops disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is False:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ สถานะใบสั่งซื้อ ในแชท</p>",
            status_code=401,
        )
    if ident is None:
        ident = _tailscale_identity()
    return ident, None


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None, site: str | None = None):
    settings = _settings()
    ident, err = _require(request)
    if err and t:
        try:
            ident = _verify_token(t)
            err = None
        except TokenError as exc:
            return HTMLResponse(f"<h1>ลิงก์ไม่ถูกต้อง</h1><p>{exc}</p>", status_code=401)
    if err and is_tailscale_cg_nat(_client_ip(request)):
        ident = _tailscale_identity()
        err = None
    if err:
        return err
    html = page(
        user_name=ident.display_name,
        site=(site or settings.site).lower(),
        probes=health_probes(),
    )
    if t:
        redir = RedirectResponse(url="/ops/", status_code=303)
        _set_session(redir, ident)
        return redir
    resp = HTMLResponse(html)
    _set_session(resp, ident)
    return resp


@router.get("/api/health")
def api_health():
    return {"status": "ok", "service": "kcw-ops", "sites": health_probes()}


def _auth_json(request: Request):
    ident, err = _require(request)
    if err:
        return None, JSONResponse({"detail": "unauthorized"}, status_code=401)
    return ident, None


def _attach_prepare(data: dict) -> dict:
    if (data.get("site") or "").upper() != "SYP" or not data.get("rows"):
        return data
    prep = fetch_prepare_headers([r["docno"] for r in data["rows"]])
    for row in data["rows"]:
        info = prep.get(row["docno"]) or {}
        row["prepared"] = bool(info.get("prepared"))
        row["prepared_at"] = str(info.get("prepared_at") or "") or None
        row["note"] = info.get("note")
    return data


@router.get("/api/po")
def api_po_list(
    request: Request,
    site: str = "hq",
    status: str = "open",
    q: str = "",
    limit: int = 50,
    offset: int = 0,
):
    ident, err = _auth_json(request)
    if err:
        return err
    _ = ident
    try:
        data = list_purchase_orders(
            site=site,
            status=status,
            q=q or None,
            dfrom=request.query_params.get("from"),
            dto=request.query_params.get("to"),
            limit=limit,
            offset=offset,
        )
        return _attach_prepare(data)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/po/pending")
def api_po_pending(
    request: Request,
    site: str = "hq",
    q: str = "",
    limit: int = 50,
    offset: int = 0,
):
    ident, err = _auth_json(request)
    if err:
        return err
    _ = ident
    try:
        return list_pending_receive(
            site=site,
            q=q or None,
            dfrom=request.query_params.get("from"),
            dto=request.query_params.get("to"),
            limit=limit,
            offset=offset,
        )
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/po/{docno}")
def api_po_detail(request: Request, docno: str, site: str = "hq"):
    ident, err = _auth_json(request)
    if err:
        return err
    _ = ident
    try:
        data = get_po_lines(site=site, docno=docno)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)
    if site.lower() == "syp":
        headers = fetch_prepare_headers([data.get("docno") or docno])
        info = headers.get(data.get("docno") or docno) or {}
        data["prepared"] = bool(info.get("prepared"))
        data["note"] = info.get("note")
        lines_prep = fetch_prepare_lines(docno)
        for ln in data.get("lines") or []:
            p = lines_prep.get(str(ln.get("line") or "").strip()) or {}
            ln["prepared"] = bool(p.get("prepared"))
    return data


@router.post("/api/po/{docno}/prepare")
async def api_po_prepare(request: Request, docno: str, site: str = "syp"):
    ident, err = _auth_json(request)
    if err:
        return err
    if site.lower() != "syp":
        return JSONResponse({"error": "prepare overlay is SYP only"}, status_code=400)
    body = await request.json()
    prepared = bool(body.get("prepared"))
    note = ident.display_name if ident else None
    try:
        row = upsert_prepare_header(docno=docno, prepared=prepared, note=note)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)
    return {"ok": True, "row": row}

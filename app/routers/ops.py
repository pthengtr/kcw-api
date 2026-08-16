from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from src.ops.config import get_ops_settings
from src.ops.net import is_tailscale_cg_nat
from src.ops.iclow import list_iclow
from src.ops.po import get_po_lines, health_probes, list_purchase_orders
from src.ops.tf_prepare import attach_header_prepare, attach_line_prepare
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
        redir.headers["Cache-Control"] = "no-store"
        _set_session(redir, ident)
        return redir
    resp = HTMLResponse(html)
    resp.headers["Cache-Control"] = "no-store"
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


def _attach_prepare(data: dict, prepare_filter: str = "all", *, limit: int = 50, offset: int = 0) -> dict:
    if (data.get("site") or "").upper() != "SYP" or not data.get("rows"):
        return data
    attach_header_prepare(data["rows"])
    wanted = (prepare_filter or "all").strip().lower()
    rows = data["rows"]
    if wanted in ("prepared", "partially_prepared", "not_prepared"):
        rows = [r for r in rows if (r.get("prepare_status") or "not_prepared") == wanted]
        data["count"] = len(rows)
        data["rows"] = rows[max(0, offset) : max(0, offset) + max(1, limit)]
    return data


@router.get("/api/po")
def api_po_list(
    request: Request,
    site: str = "hq",
    status: str = "all",
    q: str = "",
    limit: int = 50,
    offset: int = 0,
):
    ident, err = _auth_json(request)
    if err:
        return err
    _ = ident
    prepare = request.query_params.get("prepare") or "all"
    scan = 2000 if site.lower() == "syp" and prepare not in ("", "all") else None
    try:
        data = list_purchase_orders(
            site=site,
            status=status,
            q=q or None,
            dfrom=request.query_params.get("from"),
            dto=request.query_params.get("to"),
            limit=limit,
            offset=0 if scan else offset,
            scan_limit=scan,
        )
        return _attach_prepare(data, prepare, limit=limit, offset=offset if scan else 0)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)


@router.get("/api/po/pending")
def api_po_pending(
    request: Request,
    site: str = "hq",
    status: str = "pending_receive",
    q: str = "",
    limit: int = 50,
    offset: int = 0,
):
    ident, err = _auth_json(request)
    if err:
        return err
    _ = ident
    try:
        return list_iclow(
            site=site,
            status=status,
            q=q or None,
            dfrom=request.query_params.get("from"),
            dto=request.query_params.get("to"),
            prepare=request.query_params.get("prepare") or "all",
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
        info = attach_line_prepare(data.get("docno") or docno, data.get("lines") or [])
        data["prepare_status"] = info.get("prepare_status") or "not_prepared"
        data["prepared"] = bool(info.get("prepared"))
        data["tf_billnos"] = info.get("tf_billnos")
        data["prepared_line_count"] = info.get("prepared_line_count")
        data["prepare_line_count"] = info.get("line_count")
    return data


@router.post("/api/po/{docno}/prepare")
async def api_po_prepare(request: Request, docno: str, site: str = "syp"):
    ident, err = _auth_json(request)
    if err:
        return err
    _ = ident
    return JSONResponse(
        {
            "error": "prepare status comes from HQ TF/TFV bills (SIMas.REMARKS), not a manual overlay",
            "docno": docno,
            "site": site,
        },
        status_code=409,
    )

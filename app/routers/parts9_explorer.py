from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse

from src.parts9_explorer.config import get_explorer_settings
from src.parts9_explorer.net import is_tailscale_cg_nat
from src.parts9_explorer.query import maybe_document_query, parse_query
from src.parts9_explorer.search import (
    get_product,
    iclow_summary,
    lookup_documents,
    probe_sites,
    recent_for_product,
    search_products,
)
from src.parts9_explorer.ui import APP, SESSION_COOKIE, page
from src.stock_check.auth import TokenError, mint_access_token, verify_access_token

router = APIRouter(prefix="/parts9", tags=["parts9-explorer"])


def _settings():
    return get_explorer_settings()


def _client_ip(request: Request) -> str:
    if request.client and request.client.host:
        return request.client.host
    return ""


def _identity_from_request(request: Request):
    settings = _settings()
    token = request.cookies.get(SESSION_COOKIE) or request.query_params.get("t")
    if token:
        try:
            return verify_access_token(
                token,
                secret=settings.token_secret,
                expected_branch=settings.site,
                expected_app=APP,
            )
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
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, samesite="lax", max_age=86400 * 7, path="/parts9")


def _require(request: Request):
    settings = _settings()
    if not settings.parts9_explorer_enabled:
        return None, HTMLResponse("parts9 explorer disabled", status_code=404)
    if not settings.token_secret:
        return None, HTMLResponse("token secret missing", status_code=500)
    ident = _identity_from_request(request)
    if ident is False:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ parts9 หรือ ค้นหา ในแชท</p>",
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
            ident = verify_access_token(
                t, secret=settings.token_secret, expected_branch=settings.site, expected_app=APP
            )
            err = None
        except TokenError as exc:
            return HTMLResponse(f"<h1>ลิงก์ไม่ถูกต้อง</h1><p>{exc}</p>", status_code=401)
    if err and is_tailscale_cg_nat(_client_ip(request)):
        ident = _tailscale_identity()
        err = None
    if err:
        return err
    html = page(user_name=ident.display_name, site=(site or settings.site).lower(), probes=probe_sites())
    if t:
        redir = RedirectResponse(url="/parts9/", status_code=303)
        _set_session(redir, ident)
        return redir
    resp = HTMLResponse(html)
    _set_session(resp, ident)
    return resp


@router.get("/api/search")
def api_search(
    request: Request,
    q: str = "",
    site: str = "hq",
    include_skip: str = "0",
    kind: str = "all",
    category: str = "",
):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    mode = (kind or "all").strip().lower()
    parsed = parse_query((mode + " " + q).strip() if mode not in ("all", "product", "code_size") and q else q)
    if mode == "product":
        parsed = parse_query("สินค้า " + q) if q else parsed
    products, errp = ([], None)
    documents, errd = ([], None)
    summary, errs = (None, None)
    want_products = mode in ("product", "code_size") or (mode == "all" and parsed.want_product)
    if want_products and q.strip():
        products, errp = search_products(
            q,
            site=site,
            include_skip=include_skip in ("1", "true", "yes"),
            mode="code_size" if mode == "code_size" else None,
            category=category.strip() or None,
        )
    want_docs = mode in ("si", "pi", "po", "pv", "rv", "iclow") or (
        mode == "all" and q.strip() and (parsed.kind == "document" or not parsed.want_product)
    )
    if want_docs and q.strip():
        lookup_kind = None if mode == "all" else mode
        documents, errd = lookup_documents(q, site=site, kind=lookup_kind)
    elif (
        mode == "all"
        and q.strip()
        and parsed.kind == "product"
        and maybe_document_query(q)
    ):
        documents, errd = lookup_documents(q, site=site, kinds=("pi", "pv"))
    if mode == "iclow":
        summary, errs = iclow_summary(site)
    document = documents[0] if documents else None
    return {
        "q": q,
        "kind": mode,
        "category": category.strip() or None,
        "parsed": parsed.kind,
        "doc_kind": parsed.doc_kind,
        "products": products,
        "document": document,
        "documents": documents,
        "iclow_summary": summary,
        "error": errp or errd or errs,
    }


@router.get("/api/iclow/summary")
def api_iclow_summary(request: Request, site: str = "hq"):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    data, err_s = iclow_summary(site)
    if err_s:
        return {"site": site.upper(), "error": err_s, "iclow_summary": None}
    return {"site": site.upper(), "iclow_summary": data, "error": None}


@router.get("/api/product/{bcode}")
def api_product(request: Request, bcode: str, site: str = "hq"):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    product, errp = get_product(bcode, site=site)
    other = "syp" if site.lower() == "hq" else "hq"
    other_p, _ = get_product(bcode, site=other)
    movement = recent_for_product(bcode, site=site)
    return {"product": product, "other_site": other_p, "movement": movement, "error": errp}


@router.get("/api/health")
def api_health():
    return {"status": "ok", "service": "parts9-explorer", "sites": probe_sites()}

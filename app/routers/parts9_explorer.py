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
from src.parts9_explorer.ap_reorder import ap_detail, search_ap
from src.parts9_explorer.cost_access import (
    can_see_explorer_cost,
    redact_ap,
    redact_documents,
    redact_iclow_summary,
    redact_insight,
    redact_movement,
)
from src.parts9_explorer.fifo import fifo_for_product, insight_avg_buy
from src.parts9_explorer.insights import lookup_insight
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


def _see_cost(ident) -> bool:
    return can_see_explorer_cost(getattr(ident, "line_user_id", None))


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
    html = page(
        user_name=ident.display_name,
        site=(site or settings.site).lower(),
        probes=probe_sites(),
        can_see_cost=_see_cost(ident),
    )
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
    sort: str = "",
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
            sort=sort.strip() or None,
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
    see_cost = _see_cost(ident)
    if not see_cost:
        documents = redact_documents(documents)
        summary = redact_iclow_summary(summary)
    document = documents[0] if documents else None
    return {
        "q": q,
        "kind": mode,
        "category": category.strip() or None,
        "sort": sort.strip() or "relevance",
        "parsed": parsed.kind,
        "doc_kind": parsed.doc_kind,
        "products": products,
        "document": document,
        "documents": documents,
        "iclow_summary": summary,
        "can_see_cost": see_cost,
        "error": errp or errd or errs,
    }


@router.get("/api/iclow/summary")
def api_iclow_summary(request: Request, site: str = "hq"):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    data, err_s = iclow_summary(site)
    see_cost = _see_cost(ident)
    if not see_cost:
        data = redact_iclow_summary(data)
    if err_s:
        return {"site": site.upper(), "error": err_s, "iclow_summary": None, "can_see_cost": see_cost}
    return {"site": site.upper(), "iclow_summary": data, "error": None, "can_see_cost": see_cost}


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
    insight = lookup_insight(site, bcode)
    see_cost = _see_cost(ident)
    fifo = None
    if see_cost:
        fifo, fifo_sales = fifo_for_product(
            bcode,
            site=site,
            sales=movement.get("sales") or [],
            insight_avg_buy=insight_avg_buy(insight),
        )
        if fifo and fifo.get("found"):
            movement = {**movement, "sales": fifo_sales}
    else:
        movement = redact_movement(movement)
        insight = redact_insight(insight)
    return {
        "product": product,
        "other_site": other_p,
        "movement": movement,
        "insight": insight,
        "fifo": fifo,
        "can_see_cost": see_cost,
        "error": errp,
    }


@router.get("/api/insight/{bcode}")
def api_insight(request: Request, bcode: str, site: str = "hq"):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    see_cost = _see_cost(ident)
    insight = lookup_insight(site, bcode)
    if not see_cost:
        insight = redact_insight(insight)
    if isinstance(insight, dict):
        insight = {**insight, "can_see_cost": see_cost}
    return insight


@router.get("/api/ap/search")
def api_ap_search(request: Request, q: str = "", site: str = "hq"):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    accounts, err_a = search_ap(q, site=site)
    return {"q": q, "site": (site or "hq").lower(), "accounts": accounts, "can_see_cost": _see_cost(ident), "error": err_a}


@router.get("/api/ap/{acctno}")
def api_ap_detail(request: Request, acctno: str, site: str = "hq", days: int = 365):
    ident, err = _require(request)
    if err:
        return JSONResponse({"detail": "unauthorized"}, status_code=401)
    _ = ident
    code = (acctno or "").strip()
    if not code:
        return JSONResponse({"detail": "acctno required"}, status_code=400)
    detail = ap_detail(code, site=site, days=max(30, min(int(days or 365), 1825)))
    see_cost = _see_cost(ident)
    if not see_cost:
        detail = redact_ap(detail)
    if isinstance(detail, dict):
        detail = {**detail, "can_see_cost": see_cost}
    return detail


@router.get("/api/health")
def api_health():
    return {"status": "ok", "service": "parts9-explorer", "sites": probe_sites()}

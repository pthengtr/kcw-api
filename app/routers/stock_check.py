from __future__ import annotations

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from urllib.parse import quote

from src.barcode import (
    BarcodeDecodeUnavailable,
    decode_barcodes_from_image,
    pick_best_barcode,
    sanitize_barcode,
)
from src.stock_check.audit_mirror import flush_audit_outbox
from src.stock_check.auth import TokenError, build_entry_url, mint_access_token, verify_access_token
from src.stock_check.config import get_stock_check_settings
from src.stock_check.service import StockCheckService
from src.stock_check import ui

router = APIRouter(prefix="/stock-check", tags=["stock-check"])

SESSION_COOKIE = "kcw_stock_check_session"


def _q(msg: str) -> str:
    return quote(str(msg), safe="")



def _service() -> StockCheckService:
    return StockCheckService()


def _settings():
    return get_stock_check_settings()


def _browser_entry_url(user: dict) -> str:
    """Fresh ?t= link for opening outside LINE (LINE's own open-in-browser drops the token)."""
    settings = _settings()
    try:
        token = mint_access_token(
            secret=settings.stock_check_token_secret,
            line_user_id=user["line_user_id"],
            display_name=user.get("display_name") or "",
            branch=settings.stock_check_branch,
            ttl_seconds=settings.stock_check_token_ttl_seconds,
        )
    except TokenError:
        return ""
    return build_entry_url(settings.resolved_public_base_url, token)


def _user_from_request(request: Request, service: StockCheckService) -> dict | None:
    session_id = request.cookies.get(SESSION_COOKIE)
    if not session_id:
        return None
    session = service.store.get_session(session_id)
    if not session:
        return None
    service.store.touch_session(session_id)
    # Re-evaluate from live config so STOCK_CHECK_APPROVER_LINE_USER_IDS
    # updates apply without forcing users to open a fresh LINE link.
    user = dict(session)
    user["is_approver"] = 1 if user.get("line_user_id") in _settings().approver_ids else 0
    return user


def _require_user(request: Request, service: StockCheckService):
    user = _user_from_request(request, service)
    if not user:
        return None, HTMLResponse(
            "<h1>ต้องเปิดลิงก์จาก LINE</h1><p>พิมพ์ เช็คสต็อก ในแชทแล้วกดลิงก์สาขา</p>",
            status_code=401,
        )
    return user, None


@router.get("/", response_class=HTMLResponse)
def home(request: Request, t: str | None = None):
    settings = _settings()
    if not settings.stock_check_enabled:
        return HTMLResponse("stock check disabled", status_code=404)
    service = _service()
    service.expire()
    flush_audit_outbox(service.store, branch=settings.stock_check_branch)

    if t:
        try:
            identity = verify_access_token(
                t,
                secret=settings.stock_check_token_secret,
                expected_branch=settings.stock_check_branch,
                approver_ids=settings.approver_ids,
            )
        except TokenError as exc:
            return HTMLResponse(f"<h1>ลิงก์ไม่ถูกต้อง</h1><p>{exc}</p>", status_code=401)
        session_id = service.store.create_session(
            line_user_id=identity.line_user_id,
            display_name=identity.display_name,
            is_approver=identity.is_approver,
        )
        resp = RedirectResponse(url="/stock-check/", status_code=303)
        resp.set_cookie(
            SESSION_COOKIE,
            session_id,
            httponly=True,
            samesite="lax",
            max_age=max(settings.lease_idle_seconds * 48, 86_400),
        )
        return resp

    user, err = _require_user(request, service)
    if err:
        return err
    flash = request.query_params.get("ok")
    error = request.query_params.get("err")
    items = service.leased_list(user["id"])
    return HTMLResponse(
        ui.home_page(
            user=user,
            items=items,
            flash=flash,
            error=error,
            browser_entry_url=_browser_entry_url(user),
        )
    )


@router.post("/take")
def take(request: Request, count: int = Form(10)):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    try:
        claimed = service.take_n(user["id"], count)
        msg = f"รับงาน {len(claimed)} รายการ"
        return RedirectResponse(url=f"/stock-check/?ok={_q(msg)}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(url=f"/stock-check/?err={_q(exc)}", status_code=303)


@router.post("/heartbeat")
def heartbeat(request: Request):
    """Keep unfinished leases alive while the operator is actively counting."""
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return JSONResponse({"ok": False, "error": "unauthorized"}, status_code=401)
    n = service.bump_leases(user["id"])
    return JSONResponse(
        {
            "ok": True,
            "extended": n,
            "idle_seconds": service.settings.lease_idle_seconds,
        }
    )


@router.get("/ondemand", response_class=HTMLResponse)
def ondemand(request: Request, q: str = ""):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    results = service.lookup(q, session_id=user["id"]) if q.strip() else []
    return HTMLResponse(
        ui.ondemand_page(
            user=user,
            results=results,
            q=q,
            flash=request.query_params.get("ok"),
            error=request.query_params.get("err"),
            browser_entry_url=_browser_entry_url(user),
        )
    )


@router.post("/ondemand/upload", response_class=HTMLResponse)
def ondemand_upload(request: Request, image: UploadFile = File(...)):
    """Photo / camera-roll barcode decode — same idea as LINE upload scan."""
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    try:
        # Sync route so PARTS9/sqlite work does not block the event loop.
        raw = image.file.read()
        if not raw:
            raise ValueError("ไม่พบไฟล์รูป")
        if len(raw) > 12 * 1024 * 1024:
            raise ValueError("ไฟล์ใหญ่เกินไป (สูงสุด 12MB)")
        try:
            codes = decode_barcodes_from_image(raw)
        except BarcodeDecodeUnavailable as exc:
            raise ValueError(str(exc)) from exc
        cleaned: list[str] = []
        for code in codes:
            safe = sanitize_barcode(code)
            if safe:
                cleaned.append(safe)        # de-dupe preserve order
        seen: set[str] = set()
        decoded = []
        for code in cleaned:
            if code not in seen:
                seen.add(code)
                decoded.append(code)
        if not decoded:
            return HTMLResponse(
                ui.ondemand_page(
                    user=user,
                    error="อ่านบาร์โค้ดจากรูปไม่ได้ — ลองใหม่ให้ชัดขึ้น หรือพิมพ์รหัส",
                    browser_entry_url=_browser_entry_url(user),
                )
            )
        best = pick_best_barcode(decoded) or decoded[0]
        # Prefer single hit → product page; multiple → list
        if len(decoded) == 1:
            return RedirectResponse(
                url=f"/stock-check/product/{_q(best)}?source=ondemand",
                status_code=303,
            )
        results = []
        for code in decoded:
            results.extend(service.lookup(code))
        # unique by bcode
        by_b: dict[str, dict] = {}
        for row in results:
            by_b[row["bcode"]] = row
        return HTMLResponse(
            ui.ondemand_page(
                user=user,
                results=list(by_b.values()),
                decoded=decoded,
                flash=f"พบ {len(decoded)} รหัสในรูป",
                browser_entry_url=_browser_entry_url(user),
            )
        )
    except Exception as exc:  # noqa: BLE001
        return HTMLResponse(
            ui.ondemand_page(
                user=user,
                error=str(exc),
                browser_entry_url=_browser_entry_url(user),
            )
        )


@router.get("/product/{bcode}", response_class=HTMLResponse)
def product(request: Request, bcode: str, source: str = "batch"):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    item = service.product_detail(bcode, session_id=user["id"])
    if not item:
        return HTMLResponse("ไม่พบสินค้า", status_code=404)
    return HTMLResponse(
        ui.product_page(
            user=user,
            item=item,
            source=source,
            browser_entry_url=_browser_entry_url(user),
        )
    )


@router.post("/product/{bcode}/submit")
def submit_product(
    request: Request,
    bcode: str,
    source: str = Form("batch"),
    counted_qty: str = Form(""),
    difference: str = Form(""),
    diff_amount: str = Form(""),
    diff_dir: str = Form(""),
    notes: str = Form(""),
    mark_correct: str = Form(""),
):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    try:
        kwargs = {
            "session": user,
            "bcode": bcode,
            "source": source if source in {"batch", "ondemand", "manual"} else "ondemand",
            "notes": notes or None,
            "mark_correct": mark_correct == "1",
        }
        if not kwargs["mark_correct"]:
            counted_raw = counted_qty.strip().replace(",", ".")
            diff_raw = difference.strip().replace(",", ".")
            amount_raw = diff_amount.strip().replace(",", ".")
            if counted_raw:
                kwargs["counted_qty"] = float(counted_raw)
            elif amount_raw:
                abs_amt = abs(float(amount_raw))
                sign = -1.0 if (diff_dir or "minus").lower() in {"minus", "-", "dec", "ลด"} else 1.0
                kwargs["difference"] = sign * abs_amt
            elif diff_raw:
                kwargs["difference"] = float(diff_raw)
            else:
                raise ValueError("กรอกจำนวนนับหรือส่วนต่าง")
        result = service.submit_count(**kwargs)
        if result["status"] == "completed":
            msg = "บันทึกถูกต้อง (auto)"
        else:
            msg = f"ส่งรออนุมัติ ต่าง {result['variance']:+.3g}"
        return RedirectResponse(url=f"/stock-check/?ok={_q(msg)}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(url=f"/stock-check/?err={_q(exc)}", status_code=303)


@router.post("/product/{bcode}/skip")
def skip_product(request: Request, bcode: str):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    service.skip_item(user["id"], bcode)
    return RedirectResponse(url=f"/stock-check/?ok={_q('ข้ามแล้ว')}", status_code=303)


@router.get("/approve", response_class=HTMLResponse)
def approve_list(request: Request):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    drafts = service.store.list_pending_drafts()
    return HTMLResponse(
        ui.approve_page(
            user=user,
            drafts=drafts,
            flash=request.query_params.get("ok"),
            error=request.query_params.get("err"),
            browser_entry_url=_browser_entry_url(user),
        )
    )


@router.post("/approve/{draft_id}")
def approve_one(request: Request, draft_id: str, confirm_drift: str = Form("")):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    try:
        result = service.approve_draft(
            draft_id=draft_id,
            approver_session=user,
            confirm_drift=confirm_drift == "1",
        )
        if not result.get("ok"):
            return RedirectResponse(
                url=f"/stock-check/approve?err={_q(result.get('message') or result.get('code'))}",
                status_code=303,
            )
        bill = result.get("billno")
        msg = f"โพสต์แล้ว {bill}" if bill else "เสร็จสิ้น"
        flush_audit_outbox(service.store, branch=service.settings.stock_check_branch)
        return RedirectResponse(url=f"/stock-check/approve?ok={_q(msg)}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(url=f"/stock-check/approve?err={_q(exc)}", status_code=303)


@router.post("/reject/{draft_id}")
def reject_one(request: Request, draft_id: str):
    service = _service()
    user, err = _require_user(request, service)
    if err:
        return err
    try:
        service.reject_draft(draft_id=draft_id, approver_session=user)
        return RedirectResponse(url=f"/stock-check/approve?ok={_q('ปฏิเสธแล้ว')}", status_code=303)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(url=f"/stock-check/approve?err={_q(exc)}", status_code=303)


@router.get("/end")
@router.post("/end")
def end_session(request: Request):
    service = _service()
    user = _user_from_request(request, service)
    if user:
        n = service.store.end_session(user["id"])
        msg = f"จบงาน คืนคิว {n} รายการ"
    else:
        msg = "ไม่มีเซสชัน"
    resp = RedirectResponse(url=f"/stock-check/?ok={msg}", status_code=303)
    resp.delete_cookie(SESSION_COOKIE)
    # After deleting cookie, home will 401 — better show a simple goodbye
    return HTMLResponse(
        f"<h1>จบงานแล้ว</h1><p>{msg}</p><p>เปิดลิงก์จาก LINE อีกครั้งเพื่อเริ่มใหม่</p>"
    )


@router.get("/api/health")
def health():
    settings = _settings()
    return {
        "enabled": settings.stock_check_enabled,
        "branch": settings.stock_check_branch,
        "bill_prefix": settings.bill_prefix,
        "public_base_url": settings.resolved_public_base_url,
    }


@router.get("/api/write-access")
def write_access():
    from src.stock_check.sa_writer import describe_write_access

    settings = _settings()
    try:
        return describe_write_access(settings)
    except Exception as exc:  # noqa: BLE001
        return JSONResponse({"error": str(exc)}, status_code=500)

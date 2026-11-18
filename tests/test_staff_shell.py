from __future__ import annotations

from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.staff_shell.auth import (
    STAFF_APP,
    STAFF_COOKIE,
    mint_staff_token,
    verify_staff_token,
)
from src.staff_shell.catalog import (
    WEB_SERVICES,
    can_access_service,
    filter_web_services,
    get_service,
    line_menu_entries,
)
from src.staff_shell.ui import inject_shell, render_shell_html
from src.staff_shell.urls import build_switch_url, rewrite_base_port
from src.staff_shell.wiring import entry_source, wire_shell
from src.stock_check.auth import StockCheckIdentity, verify_access_token
from src.handlers.services_menu import handle_services_menu, services_menu_handlers_match


SECRET = "test-staff-shell-secret"


def test_catalog_has_web_services_and_line_extras():
    ids = {s.id for s in WEB_SERVICES}
    assert {
        "stock-check",
        "companion",
        "parts9-explorer",
        "transfer",
        "hq-po",
        "hq-receive",
        "online-sale",
        "pay-notes",
    } <= ids
    labels = [label for label, _ in line_menu_entries()]
    assert "จัดการรูปสินค้า" in labels
    assert "วิธีใช้ทั้งหมด" in labels
    assert "สถานะใบสั่งซื้อ" not in labels


def test_filter_web_services_by_site():
    hq = {s.id for s in filter_web_services(site="HQ")}
    syp = {s.id for s in filter_web_services(site="SYP")}
    assert "pay-notes" in hq and "hq-po" in hq and "companion" in hq
    assert "pay-notes" not in syp and "hq-po" not in syp and "companion" not in syp
    assert "transfer" in syp and "stock-check" in syp


def test_permissions_open_by_default():
    assert can_access_service("transfer", access_group="staff", is_allowed=True)
    assert can_access_service("pay-notes", access_group="guest", is_allowed=True)
    assert not can_access_service("transfer", access_group="staff", is_allowed=False)
    assert not can_access_service("nope", access_group="admin", is_allowed=True)


def test_staff_token_roundtrip():
    token = mint_staff_token(
        secret=SECRET,
        line_user_id="U1",
        display_name="Ann",
        branch="HQ",
        ttl_seconds=3600,
    )
    ident = verify_staff_token(token, secret=SECRET, expected_branch="HQ")
    assert ident.line_user_id == "U1"
    assert ident.display_name == "Ann"
    assert ident.app == STAFF_APP


def test_entry_source_helpers():
    assert entry_source(had_staff_cookie=False, has_entry_token=True) == ("line", True)
    assert entry_source(had_staff_cookie=True, has_entry_token=True) == ("launcher", True)
    assert entry_source(had_staff_cookie=False, has_entry_token=False) == ("direct", False)


def test_rewrite_and_switch_url():
    assert rewrite_base_port("http://192.168.1.21:8792", 8796) == "http://192.168.1.21:8796"
    target = get_service("online-sale")
    assert target is not None

    class _URL:
        scheme = "http"
        netloc = "192.168.1.21:8792"

    class _Req:
        url = _URL()
        headers = {"host": "192.168.1.21:8792"}

    url = build_switch_url(
        _Req(),  # type: ignore[arg-type]
        target,
        secret=SECRET,
        line_user_id="U1",
        display_name="Ann",
        branch="HQ",
        ttl_seconds=120,
    )
    assert url.startswith("http://192.168.1.21:8796/online-sale/?t=")
    token = url.split("t=", 1)[1]
    ident = verify_access_token(
        token, secret=SECRET, expected_branch="HQ", expected_app="kcw-online-sale"
    )
    assert ident.line_user_id == "U1"


def test_inject_shell_once():
    html = "<html><body><h1>x</h1></body></html>"
    out = inject_shell(
        html, service_id="transfer", api_base="/transfer/_shell", user_name="Ann", branch="HQ"
    )
    assert 'data-kcw-shell="1"' in out
    assert "kcwShellMenuBtn" in out
    assert out.count('data-kcw-shell="1"') == 1
    again = inject_shell(
        out, service_id="transfer", api_base="/transfer/_shell", user_name="Ann", branch="HQ"
    )
    assert again.count('data-kcw-shell="1"') == 1
    shell = render_shell_html(
        service_id="transfer", api_base="/transfer/_shell", user_name="Ann", branch="HQ"
    )
    assert "Ann" in shell
    # Dedicated top strip + body pad so host Service controls are not covered.
    assert "html.kcw-shell-pad" in shell
    assert "syncShellPad" in shell
    assert "--kcw-shell-h" in shell
    assert "padding-top:var(--kcw-shell-h)" in shell


def test_online_sale_page_hosts_shell_slot():
    from src.online_sale.ui import page
    from src.staff_shell.ui import inject_shell

    html = inject_shell(
        page(user_name="Ann", write_enabled=True, to_bill_token="tok"),
        service_id="online-sale",
        api_base="/online-sale/_shell",
        user_name="Ann",
        branch="HQ",
    )
    assert 'id="kcwShellSlot"' in html
    assert "kcwShellSlot" in html
    assert "button.kcw-shell-btn" in html
    assert "kcw-shell-rooted" in html  # mount script references the class
    assert "kcw-shell-pad" in html  # pad CSS exists; rooted mount skips applying it


def test_services_menu_still_matches_handlers():
    msg = handle_services_menu()
    labels = [
        c["action"]["label"]
        for c in msg["contents"]["body"]["contents"]
        if c.get("type") == "button"
    ]
    assert "โอนสินค้า" in labels
    assert "ชำระเจ้าหนี้" in labels
    assert "รับชำระลูกหนี้" in labels
    matched = services_menu_handlers_match()
    assert matched["transfer"] and matched["pay_notes"] and matched["receive_notes"] and matched["image"]


def test_shell_routes_switch_and_logout():
    app = FastAPI()
    from fastapi import APIRouter, Request

    router = APIRouter(prefix="/transfer")
    ident = StockCheckIdentity(
        line_user_id="U1", display_name="Ann", branch="HQ", app="kcw-transfer"
    )

    def get_app_identity(request: Request):
        return ident

    wire_shell(
        router,
        current_service_id="transfer",
        session_cookie="kcw_transfer",
        session_cookie_path="/transfer",
        get_secret=lambda: SECRET,
        get_ttl=lambda: 86400,
        get_site=lambda: "HQ",
        get_app_identity=get_app_identity,
    )
    app.include_router(router)
    client = TestClient(app)

    with patch("src.db.engine.get_engine", side_effect=RuntimeError("no db")):
        # me
        r = client.get("/transfer/_shell/me")
        assert r.status_code == 200
        assert r.json()["display_name"] == "Ann"
        assert r.json()["service_id"] == "transfer"

        # services
        r = client.get("/transfer/_shell/services")
        assert r.status_code == 200
        ids = {s["id"] for s in r.json()["services"]}
        assert "online-sale" in ids and "transfer" in ids

        # switch
        r = client.post("/transfer/_shell/switch", json={"service_id": "online-sale"})
        assert r.status_code == 200
        body = r.json()
        assert body["service_id"] == "online-sale"
        assert "8796/online-sale/?t=" in body["url"]
        assert STAFF_COOKIE in r.cookies

        # reject unknown
        r = client.post("/transfer/_shell/switch", json={"service_id": "nope"})
        assert r.status_code == 404

        # logout
        r = client.post("/transfer/_shell/logout")
        assert r.status_code == 200
        assert r.json()["ok"] is True


def test_log_service_access_swallows_errors():
    from src.staff_shell.access_log import log_service_access

    with patch("src.db.engine.get_engine", side_effect=RuntimeError("boom")):
        log_service_access(
            line_user_id="U1",
            display_name="Ann",
            branch="HQ",
            service_id="transfer",
            source="line",
            action="open",
        )

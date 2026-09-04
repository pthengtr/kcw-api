from src.handlers.services_menu import (
    handle_services_menu,
    is_services_menu_request,
    services_menu_handlers_match,
)
from src.handlers.transfer_entry import _rewrite_worker_transfer_urls, is_transfer_command
from src.transfer.net import rewrite_base_port
from src.transfer.ui import page


def test_transfer_commands():
    assert is_transfer_command("โอนสินค้า")
    assert is_transfer_command("transfer")
    assert is_transfer_command(" โอน ")
    assert not is_transfer_command("โอนเงิน")


def test_services_menu_triggers():
    assert is_services_menu_request("menu")
    assert is_services_menu_request("เมนู")
    assert is_services_menu_request("services")
    assert not is_services_menu_request("help")


def test_services_menu_flex():
    msg = handle_services_menu()
    assert msg["type"] == "flex"
    assert msg["contents"]["type"] == "bubble"


def test_services_menu_handlers():
    m = services_menu_handlers_match()
    assert m["transfer"] and m["stock_check"] and m["pay_notes"]


def test_rewrite_port():
    assert rewrite_base_port("http://100.113.143.97:8788", 8792) == "http://100.113.143.97:8792"


def test_rewrite_worker_transfer_urls_keeps_syp_lan(monkeypatch):
    monkeypatch.setenv("TRANSFER_PUBLIC_BASE_URL", "http://192.168.1.21:8792")
    monkeypatch.setenv("TRANSFER_TAILSCALE_BASE_URL", "http://100.113.143.97:8792")
    workers = [
        {
            "worker_name": "HQ-UBUNTU-SERVER",
            "explorer_public_base_url": "http://192.168.1.21:8788",
        },
        {
            "worker_name": "SYP-UBUNTU-SERVER",
            "transfer_public_base_url": "http://192.168.1.216:8792",
            "transfer_tailscale_base_url": "http://100.94.98.18:8792",
        },
    ]
    out = _rewrite_worker_transfer_urls(workers)
    by_name = {w["worker_name"]: w for w in out}
    assert by_name["HQ-UBUNTU-SERVER"]["transfer_public_base_url"] == "http://192.168.1.21:8792"
    assert by_name["SYP-UBUNTU-SERVER"]["transfer_public_base_url"] == "http://192.168.1.216:8792"
    assert by_name["SYP-UBUNTU-SERVER"]["transfer_tailscale_base_url"] == "http://100.94.98.18:8792"


def test_transfer_page_renders():
    html = page(
        user_name="ทดสอบ",
        site="SYP",
        hq_ship_enabled=False,
        syp_ship_enabled=False,
        hq_receive_enabled=False,
        syp_receive_enabled=False,
    )
    assert "โอนสินค้า · สาขา" in html
    assert 'data-site="SYP"' in html
    assert 'html[data-site="SYP"]' in html
    assert 'html[data-site="HQ"]' in html
    assert "--hdr-bar:#0f766e" in html
    assert 'content="#e6f5f2"' in html
    assert "site-badge" in html
    assert "SYP" in html and "สาขา" in html
    assert 'OTHER_LABEL = "สำนักงานใหญ่"' in html
    assert "ใบจัดสินค้า" in html
    assert "ใบรับสินค้า" in html
    assert "ขอสินค้าจาก" in html
    assert "ส่งสินค้าไป" in html
    assert "ของเข้า" in html
    assert "ของออก" in html
    assert "ไม่สต็อก = L -1" in html
    assert "ยังแสดงยอดคงเหลือจริง" in html
    assert "hq_no_stock" in html or "fmtHqStock" in html
    assert 'ไม่สต็อก</span><br>${qtyHtml}' in html or "ไม่สต็อก</span><br>" in html
    assert "ตรวจสอบสถานะ" in html
    assert "ติดตาม" in html
    assert "ขั้นตอนโอนสินค้า" not in html
    assert "ใบ TF ถูกสร้างเมื่อไหร่" in html
    assert "info-toggle" in html
    assert "ยังไม่ออกใบ TF" in html
    assert "receive-lines" in html
    assert "receiveStepBar" in html or "เลือกคำขอ" in html
    assert "recvSearch" in html
    assert "bindLineSearch" in html
    assert "prepareStepBar" in html
    assert "openPrepareRequest" in html
    assert "@media (max-width:640px)" in html
    assert "max-width:1200px" in html
    assert "view-table" in html
    assert "view-cards" in html
    assert "item-card" in html
    assert "openRequestDetail" in html
    assert "row-clickable" in html
    assert "position:sticky" in html
    assert "border-collapse:separate" in html
    assert "table-wrap--tall" in html
    assert "card-table" in html
    assert "card:has(.view-table)" in html
    assert "th.num,td.num" in html
    assert "openStickerPrint" in html
    assert "openStickerPrintFromTransfer" in html
    assert "chkPrintStickers" in html
    assert "TSC TE310" in html
    assert "ดาวน์โหลดไฟล์ .prn" in html
    assert "downloadStickerPrn" in html
    assert "printStickersBrowser" not in html
    assert "data-stickers=" in html


def test_transfer_hq_page_iclow_not_stamped_on_submit():
    html = page(user_name="ทดสอบ", site="HQ")
    assert 'data-site="HQ"' in html
    assert "--hdr-bar:#2563eb" in html
    assert 'content="#e8eef8"' in html
    assert "ไม่แตะ ICLOW" in html
    assert "เก็บไว้สั่งซื้อจากเจ้าหนี้" in html
    assert "SITE === \"HQ\"" in html
    assert "ไม่ดึง ICLOW รอสั่งซื้อ" in html
    assert "fmtDescr" in html
    assert "fmtLocation" in html
    assert "ที่เก็บ" in html
    assert "printRequestBill" in html
    assert "พิมพ์ใบคำขอ" in html
    assert "canCancelRequest" in html
    assert "hasShipments" in html
    assert "ACCTNO KCW1" in html
    assert "btnCommitPick" in html
    assert "เพิ่มที่เลือก" in html
    assert "suggestPick" in html
    assert "withScrollPreserved" in html
    assert "livePickFromDom" in html
    assert "defaultEntryQty(row)" in html
    # Tick without editing qty must not silently fall back to qty=1
    assert 'suggestPick[bcode] || {checked:false, unit:"small", qty:1}' not in html
    assert 'data-add="' not in html
    assert "รุ่น ${m}" in html or "รุ่น " in html


def test_transfer_syp_page_keeps_iclow_suggest_copy():
    html = page(user_name="ทดสอบ", site="SYP")
    assert "รอสั่ง (ICLOW)" in html
    assert "ตรงกับแท็บรอสั่งซื้อ" in html


def _mint_transfer_token(*, secret: str, ttl_seconds: int = 86400, now: float | None = None, name: str = "Tester"):
    from src.stock_check.auth import mint_access_token
    from src.transfer.ui import APP

    return mint_access_token(
        secret=secret,
        line_user_id="Ulineuser",
        display_name=name,
        branch="HQ",
        ttl_seconds=ttl_seconds,
        app=APP,
        now=now,
    )


def _transfer_client(monkeypatch, secret: str = "transfer-test-secret"):
    from fastapi.testclient import TestClient

    from src.transfer.config import get_transfer_settings

    monkeypatch.setenv("STOCK_CHECK_TOKEN_SECRET", secret)
    monkeypatch.setenv("TRANSFER_TOKEN_SECRET", secret)
    monkeypatch.setenv("TRANSFER_SITE", "HQ")
    monkeypatch.setenv("TRANSFER_ENABLED", "true")
    get_transfer_settings.cache_clear()
    from app.transfer_app import app

    return TestClient(app)


def test_transfer_home_missing_token_asks_for_line(monkeypatch):
    client = _transfer_client(monkeypatch)
    res = client.get("/transfer/", follow_redirects=False)
    assert res.status_code == 401
    assert "ต้องเปิดลิงก์จาก LINE" in res.text


def test_transfer_home_accepts_line_query_token(monkeypatch):
    secret = "transfer-test-secret"
    client = _transfer_client(monkeypatch, secret=secret)
    token = _mint_transfer_token(secret=secret)
    res = client.get("/transfer/", params={"t": token}, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers.get("location") == "/transfer/"
    assert "kcw_transfer" in res.headers.get("set-cookie", "")


def test_transfer_home_prefers_fresh_query_token_over_stale_cookie(monkeypatch):
    """LINE Desktop opens Chrome, which still has yesterday's expired cookie."""
    import time

    secret = "transfer-test-secret"
    client = _transfer_client(monkeypatch, secret=secret)
    stale = _mint_transfer_token(secret=secret, ttl_seconds=60, now=time.time() - 3600)
    fresh = _mint_transfer_token(secret=secret)
    client.cookies.set("kcw_transfer", stale, path="/transfer")
    res = client.get("/transfer/", params={"t": fresh}, follow_redirects=False)
    assert res.status_code == 303
    assert res.headers.get("location") == "/transfer/"
    assert "ต้องเปิดลิงก์จาก LINE" not in res.text


def test_transfer_home_invalid_query_token_explains_failure(monkeypatch):
    client = _transfer_client(monkeypatch)
    res = client.get("/transfer/", params={"t": "not-a-real-token"}, follow_redirects=False)
    assert res.status_code == 401
    assert "ลิงก์ไม่ถูกต้อง" in res.text
    assert "ต้องเปิดลิงก์จาก LINE" not in res.text


def test_transfer_home_expired_query_token_explains_failure(monkeypatch):
    import time

    secret = "transfer-test-secret"
    client = _transfer_client(monkeypatch, secret=secret)
    expired = _mint_transfer_token(secret=secret, ttl_seconds=60, now=time.time() - 3600)
    res = client.get("/transfer/", params={"t": expired}, follow_redirects=False)
    assert res.status_code == 401
    assert "ลิงก์ไม่ถูกต้อง" in res.text
    assert "expired" in res.text.lower()

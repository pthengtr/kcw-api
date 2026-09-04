from pathlib import Path

from fastapi.testclient import TestClient

from app.transfer_app import app
from src.transfer.ui import page

PACKAGE = Path(__file__).resolve().parents[1] / "tools" / "prn-printer"


def test_prn_package_files_exist():
    assert (PACKAGE / "PrintPrn.ps1").is_file()
    assert (PACKAGE / "PrintPrn.cmd").is_file()
    assert (PACKAGE / "Install-PrnPrinter.ps1").is_file()
    assert (PACKAGE / "VERSION.json").is_file()
    assert (PACKAGE / "lib" / "zxing.dll").is_file()
    assert (PACKAGE / "lib" / "zxing.presentation.dll").is_file()
    assert (PACKAGE / "index.html").is_file()


def test_prn_printer_version_endpoint_on_transfer_app():
    client = TestClient(app)
    res = client.get("/tools/prn-printer/version")
    assert res.status_code == 200
    data = res.json()
    assert data.get("name") == "kcw-prn-printer"
    assert data.get("version")


def test_prn_printer_install_page_on_transfer_app():
    client = TestClient(app)
    res = client.get("/tools/prn-printer/")
    assert res.status_code == 200
    assert "ดาวน์โหลดตัวติดตั้ง" in res.text
    assert "install.cmd" in res.text


def test_prn_printer_install_cmd_is_downloadable():
    client = TestClient(app)
    res = client.get("/tools/prn-printer/install.cmd", headers={"host": "192.168.1.216:8792"})
    assert res.status_code == 200
    assert "attachment" in res.headers.get("content-disposition", "")
    assert ".cmd" in res.headers.get("content-disposition", "")
    body = res.content.decode("ascii", errors="replace")
    assert "@echo off" in body
    assert "http://192.168.1.216:8792/tools/prn-printer/install.ps1" in body
    # Regression: never leave '$BaseUrl/...' inside single quotes (does not expand).
    assert "$BaseUrl/tools" not in body
    assert "Invoke-WebRequest" in body


def test_prn_printer_install_ps1_bootstrap():
    client = TestClient(app)
    res = client.get("/tools/prn-printer/install.ps1")
    assert res.status_code == 200
    assert "Install-PrnPrinter" in res.text


def test_prn_printer_download_zip_contains_core_files():
    client = TestClient(app)
    res = client.get("/tools/prn-printer/download.zip")
    assert res.status_code == 200
    assert res.content[:2] == b"PK"
    assert b"PrintPrn.ps1" in res.content


def test_transfer_sticker_ui_offers_one_click_prn_helper():
    html = page(
        user_name="tester",
        site="SYP",
        hq_ship_enabled=False,
        syp_ship_enabled=False,
        hq_receive_enabled=False,
        syp_receive_enabled=False,
    )
    assert "stkPrnHelper" in html
    assert "stk-prn-helper" in html
    assert "/tools/prn-printer/install.cmd" in html
    assert "ดาวน์โหลดตัวติดตั้ง" in html
    assert "btnStkPrnHelperCopy" not in html

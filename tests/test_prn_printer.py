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
    assert "text/html" in res.headers.get("content-type", "")
    assert "KCW PRN Printer" in res.text
    assert "install.ps1" in res.text


def test_prn_printer_install_ps1_bootstrap():
    client = TestClient(app)
    res = client.get("/tools/prn-printer/install.ps1")
    assert res.status_code == 200
    body = res.text
    assert "Install-PrnPrinter" in body
    assert "/tools/prn-printer/files/Install-PrnPrinter.ps1" in body


def test_prn_printer_download_zip_contains_core_files():
    client = TestClient(app)
    res = client.get("/tools/prn-printer/download.zip")
    assert res.status_code == 200
    assert res.headers.get("content-type", "").startswith("application/zip")
    assert "kcw-prn-printer-" in res.headers.get("content-disposition", "")
    assert res.content[:2] == b"PK"
    assert b"PrintPrn.ps1" in res.content
    assert b"zxing.dll" in res.content


def test_transfer_sticker_ui_offers_prn_helper_install():
    html = page(
        user_name="tester",
        site="SYP",
        hq_ship_enabled=False,
        syp_ship_enabled=False,
        hq_receive_enabled=False,
        syp_receive_enabled=False,
    )
    assert "stkPrnHelper" in html
    assert "/tools/prn-printer/" in html
    assert "btnStkPrnHelperCopy" in html
    assert "install.ps1" in html
    assert "อัปเดตหรือแทนที่ของเก่า" in html

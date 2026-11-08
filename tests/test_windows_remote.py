from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app as main_app
from app.transfer_app import app

PACKAGE = Path(__file__).resolve().parents[1] / "tools" / "windows-remote"


def test_windows_remote_package_files_exist():
    assert (PACKAGE / "Install-WindowsRemote.ps1").is_file()
    assert (PACKAGE / "authorized_keys").is_file()
    assert (PACKAGE / "VERSION.json").is_file()
    assert (PACKAGE / "index.html").is_file()
    keys = (PACKAGE / "authorized_keys").read_text(encoding="utf-8")
    assert "ssh-ed25519" in keys
    assert "kcw-windows-remote" in keys
    script = (PACKAGE / "Install-WindowsRemote.ps1").read_text(encoding="utf-8")
    assert "OpenSSH" in script
    assert "Tailscale" in script


def test_windows_remote_version_endpoint():
    client = TestClient(app)
    res = client.get("/tools/windows-remote/version")
    assert res.status_code == 200
    data = res.json()
    assert data.get("name") == "kcw-windows-remote"
    assert data.get("version")


def test_windows_remote_install_page():
    client = TestClient(app)
    res = client.get("/tools/windows-remote/")
    assert res.status_code == 200
    assert "ดาวน์โหลดตัวติดตั้ง" in res.text
    assert "install.cmd" in res.text


def test_windows_remote_install_cmd_is_downloadable():
    client = TestClient(app)
    res = client.get("/tools/windows-remote/install.cmd", headers={"host": "192.168.1.2:8792"})
    assert res.status_code == 200
    assert "attachment" in res.headers.get("content-disposition", "")
    assert ".cmd" in res.headers.get("content-disposition", "")
    body = res.content.decode("ascii", errors="replace")
    assert "@echo off" in body
    assert "Run as administrator" in body
    assert "http://192.168.1.2:8792/tools/windows-remote/install.ps1" in body
    assert "$BaseUrl/tools" not in body


def test_windows_remote_install_ps1_bootstrap():
    client = TestClient(app)
    res = client.get("/tools/windows-remote/install.ps1")
    assert res.status_code == 200
    assert "Install-WindowsRemote" in res.text
    assert "KCW_WINDOWS_REMOTE_BASE" in res.text


def test_windows_remote_authorized_keys_file():
    client = TestClient(app)
    res = client.get("/tools/windows-remote/files/authorized_keys")
    assert res.status_code == 200
    assert "ssh-ed25519" in res.text
    assert "kcw-windows-remote" in res.text


def test_windows_remote_mounted_on_railway_main_app():
    """Railway serves app.main:app — installer must be on that app too."""
    client = TestClient(main_app)
    res = client.get("/tools/windows-remote/version")
    assert res.status_code == 200
    assert res.json().get("name") == "kcw-windows-remote"

    res = client.get(
        "/tools/windows-remote/install.cmd",
        headers={
            "host": "kcw-api-production.up.railway.app",
            "x-forwarded-proto": "https",
            "x-forwarded-host": "kcw-api-production.up.railway.app",
        },
    )
    assert res.status_code == 200
    body = res.content.decode("ascii", errors="replace")
    assert "https://kcw-api-production.up.railway.app/tools/windows-remote/install.ps1" in body

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx
import pytest

from src.tiger_pay.cashbox_discovery import (
    build_api_host,
    find_ip_by_mac,
    maybe_rediscover_cashbox_api_host,
    parse_api_host,
)
from src.tiger_pay.config import TigerPaySettings, persist_tiger_pay_api_host
from src.tiger_pay.env_file import upsert_env_key
from src.tiger_pay.mac_addr import normalize_mac
from src.tiger_pay.open_api import TigerPayOpenApiClient


def test_normalize_mac_accepts_common_forms():
    assert normalize_mac("00:E0:23:7F:90:95") == "00:e0:23:7f:90:95"
    assert normalize_mac("00-e0-23-7f-90-95") == "00:e0:23:7f:90:95"
    assert normalize_mac("00e0237f9095") == "00:e0:23:7f:90:95"


def test_normalize_mac_rejects_invalid():
    with pytest.raises(ValueError):
        normalize_mac("not-a-mac")
    with pytest.raises(ValueError):
        normalize_mac("")


def test_parse_and_build_api_host():
    assert parse_api_host("http://192.168.1.36:6789/") == ("http", "192.168.1.36", 6789)
    assert build_api_host(scheme="http", ip="192.168.1.40", port=6789) == (
        "http://192.168.1.40:6789/"
    )


def test_upsert_env_key_updates_and_appends(tmp_path: Path):
    path = tmp_path / ".env"
    path.write_text("FOO=1\nTIGER_PAY_API_HOST=http://old/\nBAR=2\n", encoding="utf-8")
    assert upsert_env_key(path, "TIGER_PAY_API_HOST", "http://new/") is True
    text = path.read_text(encoding="utf-8")
    assert "TIGER_PAY_API_HOST=http://new/" in text
    assert "FOO=1" in text
    assert upsert_env_key(path, "TIGER_PAY_API_HOST", "http://new/") is False
    assert upsert_env_key(path, "NEW_KEY", "x") is True
    assert "NEW_KEY=x" in path.read_text(encoding="utf-8")


def test_find_ip_by_mac_uses_neighbor_table():
    with patch(
        "src.tiger_pay.cashbox_discovery._read_neighbor_table",
        return_value={"00:e0:23:7f:90:95": "192.168.1.36"},
    ):
        assert find_ip_by_mac("00:e0:23:7f:90:95", sweep=False) == "192.168.1.36"


def test_maybe_rediscover_updates_host(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    env_path = tmp_path / ".env"
    env_path.write_text(
        "TIGER_PAY_API_HOST=http://192.168.1.10:6789/\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("TIGER_PAY_API_HOST", "http://192.168.1.10:6789/")
    settings = MagicMock()
    settings.tiger_pay_cashbox_mac = "00:e0:23:7f:90:95"
    settings.tiger_pay_api_host = "http://192.168.1.10:6789/"
    settings.tiger_pay_cashbox_rediscover_cooldown_seconds = 0.0

    with (
        patch(
            "src.tiger_pay.cashbox_discovery.find_ip_by_mac",
            return_value="192.168.1.36",
        ),
        patch(
            "src.tiger_pay.cashbox_discovery.tcp_port_open",
            return_value=True,
        ),
        patch("src.tiger_pay.cashbox_discovery.ENV_FILE", env_path),
        patch(
            "src.tiger_pay.cashbox_discovery.persist_tiger_pay_api_host",
            side_effect=lambda host, env_file=None: persist_tiger_pay_api_host(
                host, env_file=env_path
            ),
        ),
        patch("src.tiger_pay.cashbox_discovery.clear_tiger_pay_settings_cache"),
        patch("src.tiger_pay.cashbox_discovery._clear_open_api_client_cache"),
    ):
        new_host = maybe_rediscover_cashbox_api_host(settings=settings, force=True)

    assert new_host == "http://192.168.1.36:6789/"
    assert "TIGER_PAY_API_HOST=http://192.168.1.36:6789/" in env_path.read_text(
        encoding="utf-8"
    )


def test_open_api_retries_after_rediscover():
    settings = MagicMock()
    settings.tiger_pay_client_id = "id"
    settings.tiger_pay_client_secret = "secret"
    settings.tiger_pay_api_host = "http://192.168.1.10:6789/"
    settings.tiger_pay_cashbox_mac = "00:e0:23:7f:90:95"

    client = TigerPayOpenApiClient(settings=settings)
    http = MagicMock()
    http.request.side_effect = [
        httpx.ConnectError("down"),
        MagicMock(status_code=200, json=lambda: {"data": []}, text=""),
    ]
    client._http = http

    refreshed = MagicMock()
    refreshed.tiger_pay_client_id = "id"
    refreshed.tiger_pay_client_secret = "secret"
    refreshed.tiger_pay_api_host = "http://192.168.1.36:6789/"
    refreshed.tiger_pay_cashbox_mac = "00:e0:23:7f:90:95"

    with (
        patch(
            "src.tiger_pay.cashbox_discovery.maybe_rediscover_cashbox_api_host",
            return_value="http://192.168.1.36:6789/",
        ),
        patch(
            "src.tiger_pay.open_api.get_tiger_pay_settings",
            return_value=refreshed,
        ),
    ):
        status, payload = client._request("GET", "api/open/v2/payment/cash")

    assert status == 200
    assert payload == {"data": []}
    assert http.request.call_count == 2


def test_settings_normalize_cashbox_mac(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("TIGER_PAY_CLIENT_SECRET", "secret")
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    monkeypatch.setenv("SUPABASE_SERVICE_ROLE_KEY", "key")
    monkeypatch.setenv("TIGER_PAY_CASHBOX_MAC", "00-E0-23-7F-90-95")
    settings = TigerPaySettings(_env_file=None)
    assert settings.tiger_pay_cashbox_mac == "00:e0:23:7f:90:95"

"""Tailscale + elevated-access branch tool links."""

from __future__ import annotations

from src.bot.branch_link_buttons import branch_uri_buttons
from src.handlers.branch_tool_links import (
    collect_branch_tool_links,
    is_elevated_access,
)
from src.stock_check.net import is_tailscale_cg_nat


def test_is_elevated_access_admin_exec_only():
    assert is_elevated_access({"access_group": "admin"})
    assert is_elevated_access({"access_group": "exec"})
    assert not is_elevated_access({"access_group": "staff"})
    assert not is_elevated_access({"access_group": "user"})
    assert not is_elevated_access(None)


def test_is_tailscale_cg_nat():
    assert is_tailscale_cg_nat("100.64.1.2")
    assert is_tailscale_cg_nat("100.127.0.1")
    assert not is_tailscale_cg_nat("192.168.1.10")
    assert not is_tailscale_cg_nat("10.0.0.1")


def test_collect_branch_tool_links_adds_tailscale_for_elevated(monkeypatch):
    def fake_mint(**kwargs):
        return f"tok-{kwargs['branch']}-{kwargs.get('app') or 'stock'}"

    def fake_build(base, token, path="/stock-check/"):
        return f"{base}{path}?t={token}"

    monkeypatch.setattr(
        "src.handlers.branch_tool_links.mint_access_token",
        fake_mint,
    )
    monkeypatch.setattr(
        "src.handlers.branch_tool_links.build_entry_url",
        fake_build,
    )

    workers = [
        {
            "worker_name": "HQ-PC",
            "online_status": "online",
            "public_base_url": "http://192.168.1.10:8787",
            "tailscale_public_base_url": "http://100.64.1.10:8787",
        },
        {
            "worker_name": "SYP-UBUNTU-SERVER",
            "online_status": "online",
            "public_base_url": "http://192.168.2.10:8787",
            "tailscale_public_base_url": "http://100.64.2.10:8787",
        },
    ]

    staff_links = collect_branch_tool_links(
        workers,
        line_user_id="U1",
        display_name="Staff",
        secret="secret",
        ttl_seconds=900,
        path="/stock-check/",
        lan_url_key="public_base_url",
        tailscale_url_key="tailscale_public_base_url",
        include_tailscale=False,
    )
    assert len(staff_links) == 2
    assert all(len(x) == 3 for x in staff_links)

    admin_links = collect_branch_tool_links(
        workers,
        line_user_id="U1",
        display_name="Boss",
        secret="secret",
        ttl_seconds=900,
        path="/stock-check/",
        lan_url_key="public_base_url",
        tailscale_url_key="tailscale_public_base_url",
        include_tailscale=True,
    )
    assert len(admin_links) == 4
    labels = [x[3] for x in admin_links if len(x) == 4]
    assert labels == ["สนญ · Tailscale", "สี่แยก · Tailscale"]
    assert "100.64.1.10" in admin_links[1][1]
    assert "100.64.2.10" in admin_links[3][1]

    msg = branch_uri_buttons(
        title="ตรวจนับสต็อก",
        alt_text="ตรวจนับสต็อก",
        links=admin_links,
        wifi_hint="Wi‑Fi หรือ Tailscale",
    )
    buttons = [c for c in msg["contents"]["body"]["contents"] if c.get("type") == "button"]
    assert [b["action"]["label"] for b in buttons] == [
        "สำนักงานใหญ่",
        "สนญ · Tailscale",
        "สาขาสี่แยกพัฒนา",
        "สี่แยก · Tailscale",
    ]

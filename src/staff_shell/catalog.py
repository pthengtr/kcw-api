"""Single catalog for LINE Flex menu + in-app service launcher."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any


# Phase A: open to every known access_group used in ops.line_access.
OPEN_GROUPS = frozenset({"admin", "exec", "staff", "user", "guest"})


def _port(env_key: str, default: int) -> int:
    raw = (os.getenv(env_key) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


@dataclass(frozen=True)
class ServiceDef:
    id: str
    label: str
    line_command: str
    app: str
    path: str
    port: int
    hosts: frozenset[str]
    web: bool = True
    icon: str = "app"


# Web services shown in the waffle launcher (and also in LINE menu).
WEB_SERVICES: tuple[ServiceDef, ...] = (
    ServiceDef(
        id="stock-check",
        label="เช็คสต็อก",
        line_command="เช็คสต็อก",
        app="stock-check",
        path="/stock-check/",
        port=_port("STOCK_CHECK_LISTEN_PORT", 8787),
        hosts=frozenset({"HQ", "SYP"}),
        icon="stock",
    ),
    ServiceDef(
        id="companion",
        label="ไทเกอร์เพย์",
        line_command="ไทเกอร์",
        app="companion",
        path="/companion/",
        port=_port("COMPANION_LISTEN_PORT", 8000),
        hosts=frozenset({"HQ"}),
        icon="pay",
    ),
    ServiceDef(
        id="parts9-explorer",
        label="ค้นหา PARTS9",
        line_command="ค้นหา",
        app="parts9-explorer",
        path="/parts9/",
        port=_port("PARTS9_EXPLORER_LISTEN_PORT", 8788),
        hosts=frozenset({"HQ", "SYP"}),
        icon="search",
    ),
    ServiceDef(
        id="transfer",
        label="โอนสินค้า",
        line_command="โอนสินค้า",
        app="kcw-transfer",
        path="/transfer/",
        port=_port("TRANSFER_LISTEN_PORT", 8792),
        hosts=frozenset({"HQ", "SYP"}),
        icon="transfer",
    ),
    ServiceDef(
        id="hq-po",
        label="สั่งซื้อ",
        line_command="สั่งซื้อ",
        app="kcw-hq-po",
        path="/hq-po/",
        port=_port("HQ_PO_LISTEN_PORT", 8793),
        hosts=frozenset({"HQ"}),
        icon="po",
    ),
    ServiceDef(
        id="hq-receive",
        label="รับสินค้าเข้า",
        line_command="รับสินค้า",
        app="kcw-hq-receive",
        path="/hq-receive/",
        port=_port("HQ_RECEIVE_LISTEN_PORT", 8795),
        hosts=frozenset({"HQ"}),
        icon="receive",
    ),
    ServiceDef(
        id="online-sale",
        label="ขายออนไลน์",
        line_command="ขายออนไลน์",
        app="kcw-online-sale",
        path="/online-sale/",
        port=_port("ONLINE_SALE_LISTEN_PORT", 8796),
        hosts=frozenset({"HQ"}),
        icon="sale",
    ),
    ServiceDef(
        id="pay-notes",
        label="ชำระเจ้าหนี้",
        line_command="ชำระเจ้าหนี้",
        app="pay-notes",
        path="/pay-notes/",
        port=_port("PAY_NOTES_LISTEN_PORT", 8791),
        hosts=frozenset({"HQ"}),
        icon="notes",
    ),
    ServiceDef(
        id="receive-notes",
        label="รับชำระลูกหนี้",
        line_command="รับชำระลูกหนี้",
        app="receive-notes",
        path="/receive-notes/",
        port=_port("RECEIVE_NOTES_LISTEN_PORT", 8797),
        hosts=frozenset({"HQ"}),
        icon="notes",
    ),
)

# Chat-only / help entries for LINE Flex (not in waffle).
_LINE_ONLY: tuple[tuple[str, str], ...] = (
    ("จัดการรูปสินค้า", "รูป"),
    ("วิธีใช้ทั้งหมด", "help"),
)

SERVICE_PERMISSIONS: dict[str, frozenset[str]] = {
    svc.id: OPEN_GROUPS for svc in WEB_SERVICES
}


def get_service(service_id: str) -> ServiceDef | None:
    sid = (service_id or "").strip()
    for svc in WEB_SERVICES:
        if svc.id == sid:
            return svc
    return None


def get_service_by_app(app: str) -> ServiceDef | None:
    claim = (app or "").strip()
    for svc in WEB_SERVICES:
        if svc.app == claim:
            return svc
    return None


def can_access_service(
    service_id: str,
    *,
    access_group: str | None,
    is_allowed: bool = True,
) -> bool:
    """Phase A: any allowed LINE user may use every catalogued web service."""
    if not is_allowed:
        return False
    svc = get_service(service_id)
    if not svc:
        return False
    allowed = SERVICE_PERMISSIONS.get(service_id, OPEN_GROUPS)
    group = (access_group or "guest").strip().lower() or "guest"
    # Unknown groups still pass while the map stays open.
    return group in allowed or allowed >= OPEN_GROUPS


def filter_web_services(
    *,
    site: str,
    access_group: str | None = None,
    is_allowed: bool = True,
) -> list[ServiceDef]:
    site_u = (site or "").strip().upper() or "HQ"
    out: list[ServiceDef] = []
    for svc in WEB_SERVICES:
        if site_u not in svc.hosts:
            continue
        if not can_access_service(
            svc.id, access_group=access_group, is_allowed=is_allowed
        ):
            continue
        out.append(svc)
    return out


def line_menu_entries() -> list[tuple[str, str]]:
    """(label, message) pairs for the LINE Flex services card."""
    entries = [(svc.label, svc.line_command) for svc in WEB_SERVICES]
    entries.extend(_LINE_ONLY)
    return entries


def service_public_dict(svc: ServiceDef, *, current: bool = False) -> dict[str, Any]:
    return {
        "id": svc.id,
        "label": svc.label,
        "path": svc.path,
        "port": svc.port,
        "icon": svc.icon,
        "current": current,
    }

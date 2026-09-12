"""Unit tests for catalog substitute groups (mock store — no live Supabase)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.substitutes.enrich import enrich_member_rows, fetch_dual_stock
from src.substitutes.memory import MemorySubstitutes
from src.substitutes.models import BcodeConflictError, NotFoundError


def test_create_add_remove_by_bcode():
    store = MemorySubstitutes()
    g = store.create_group(
        name="axle bolts",
        members=[{"bcode": "01050076", "sort_rank": 0}, {"bcode": "01050082", "sort_rank": 1}],
    )
    assert g["group_id"]
    assert len(g["members"]) == 2

    by = store.get_by_bcode("01050082")
    assert by is not None
    assert by["group_id"] == g["group_id"]
    peers = store.list_peers("01050082")
    assert [p["bcode"] for p in peers] == ["01050076"]

    store.add_member(g["group_id"], "09050639", sort_rank=2)
    assert store.get_by_bcode("09050639")["group_id"] == g["group_id"]

    store.remove_member(g["group_id"], "01050082")
    assert store.get_by_bcode("01050082") is None
    assert store.get_group(g["group_id"]) is not None
    assert len(store.get_group(g["group_id"])["members"]) == 2


def test_unique_bcode_conflict():
    store = MemorySubstitutes()
    g1 = store.create_group(members=[{"bcode": "11111111"}])
    g2 = store.create_group(members=[{"bcode": "22222222"}])
    with pytest.raises(BcodeConflictError) as ei:
        store.add_member(g2["group_id"], "11111111")
    assert ei.value.bcode == "11111111"
    assert ei.value.existing_group_id == g1["group_id"]

    with pytest.raises(BcodeConflictError):
        store.create_group(members=[{"bcode": "22222222"}, {"bcode": "33333333"}])


def test_delete_group_frees_bcodes():
    store = MemorySubstitutes()
    g = store.create_group(members=[{"bcode": "AAAAAAAA"}, {"bcode": "BBBBBBBB"}])
    store.delete_group(g["group_id"])
    assert store.get_by_bcode("AAAAAAAA") is None
    g2 = store.create_group(members=[{"bcode": "AAAAAAAA"}])
    assert g2["group_id"] != g["group_id"]


def test_remove_missing_raises():
    store = MemorySubstitutes()
    g = store.create_group(members=[{"bcode": "01050076"}])
    with pytest.raises(NotFoundError):
        store.remove_member(g["group_id"], "99999999")
    with pytest.raises(NotFoundError):
        store.delete_group("00000000-0000-0000-0000-000000000000")


def test_update_group_note():
    store = MemorySubstitutes()
    g = store.create_group(name="a", note="old", members=[{"bcode": "01050076"}])
    updated = store.update_group(g["group_id"], name="b", note="new note")
    assert updated["name"] == "b"
    assert updated["note"] == "new note"


class _FakeConn:
    def __init__(self, rows):
        self._rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, params):
        class _R:
            def __init__(self, rows):
                self._rows = rows

            def mappings(self):
                return self

            def all(self):
                return self._rows

        return _R(self._rows)


class _FakeEngine:
    def __init__(self, rows):
        self._rows = rows

    def connect(self):
        return _FakeConn(self._rows)


def test_enrich_member_rows_dual_stock():
    hq_rows = [
        {"BCODE": "01050076", "DESCR": "BOLT A", "QTYOH2": 12, "QTYMIN": -1},
        {"BCODE": "01050082", "DESCR": "BOLT B", "QTYOH2": 3, "QTYMIN": 0},
    ]
    syp_rows = [
        {"BCODE": "01050076", "DESCR": "BOLT A", "QTYOH2": 1, "QTYMIN": 0},
        {"BCODE": "01050082", "DESCR": "BOLT B", "QTYOH2": 0, "QTYMIN": -1},
    ]

    def get_engine(site: str):
        return _FakeEngine(hq_rows if site == "hq" else syp_rows)

    stock = fetch_dual_stock(["01050076", "01050082"], get_engine=get_engine)
    assert stock["01050076"]["hq_qtyoh2"] == 12.0
    assert stock["01050076"]["hq_qtymin"] == -1.0
    assert stock["01050076"]["syp_qtyoh2"] == 1.0
    assert stock["01050082"]["syp_qtymin"] == -1.0

    enriched = enrich_member_rows(
        [
            {"bcode": "01050076", "sort_rank": 0, "note": None},
            {"bcode": "01050082", "sort_rank": 1, "note": "alt"},
        ],
        get_engine=get_engine,
    )
    assert enriched[0]["descr"] == "BOLT A"
    assert enriched[0]["hq_l1"] is True
    assert enriched[0]["syp_l1"] is False
    assert enriched[1]["syp_l1"] is True
    assert enriched[1]["sort_rank"] == 1
    for key in ("bcode", "descr", "hq_qtyoh2", "hq_qtymin", "syp_qtyoh2", "syp_qtymin", "sort_rank"):
        assert key in enriched[0]


def test_api_routes_mounted_and_crud(monkeypatch):
    from app.parts9_explorer_app import app

    store = MemorySubstitutes()

    class _Ident:
        display_name = "tester"
        line_user_id = "u1"

    def fake_require(request):
        return _Ident(), None

    monkeypatch.setattr("app.routers.parts9_substitutes._require", fake_require)
    monkeypatch.setattr(
        "app.routers.parts9_substitutes._client",
        lambda: store,
    )
    monkeypatch.setattr(
        "app.routers.parts9_substitutes.bcode_exists_any_site",
        lambda bcode, get_engine=None: True,
    )

    def passthrough_enrich(group, get_engine=None):
        if not group:
            return None
        out = dict(group)
        out["members"] = passthrough_members(list(group.get("members") or []))
        return out

    def passthrough_members(members, get_engine=None):
        out = []
        for m in members:
            row = dict(m)
            row.setdefault("descr", "")
            row.setdefault("hq_qtyoh2", None)
            row.setdefault("hq_qtymin", None)
            row.setdefault("syp_qtyoh2", None)
            row.setdefault("syp_qtymin", None)
            row.setdefault("hq_l1", False)
            row.setdefault("syp_l1", False)
            out.append(row)
        return out

    monkeypatch.setattr("app.routers.parts9_substitutes.enrich_group", passthrough_enrich)
    monkeypatch.setattr("app.routers.parts9_substitutes.enrich_member_rows", passthrough_members)

    import app.routers.parts9_substitutes as routes

    monkeypatch.setattr(
        routes.sub_db,
        "get_by_bcode",
        lambda _c, bcode: store.get_by_bcode(bcode),
    )
    monkeypatch.setattr(
        routes.sub_db,
        "list_groups",
        lambda _c, q=None, limit=100: store.list_groups(q=q, limit=limit),
    )
    monkeypatch.setattr(
        routes.sub_db,
        "get_group",
        lambda _c, gid: store.get_group(gid),
    )
    monkeypatch.setattr(
        routes.sub_db,
        "create_group",
        lambda _c, **kw: store.create_group(**kw),
    )
    monkeypatch.setattr(
        routes.sub_db,
        "update_group",
        lambda _c, gid, name=None, note=None: store.update_group(gid, name=name, note=note),
    )
    monkeypatch.setattr(
        routes.sub_db,
        "delete_group",
        lambda _c, gid: store.delete_group(gid),
    )
    monkeypatch.setattr(
        routes.sub_db,
        "add_member",
        lambda _c, gid, bcode, sort_rank=0, note=None: store.add_member(
            gid, bcode, sort_rank=sort_rank, note=note
        ),
    )
    monkeypatch.setattr(
        routes.sub_db,
        "remove_member",
        lambda _c, gid, bcode: store.remove_member(gid, bcode),
    )

    client = TestClient(app)

    openapi_paths = client.get("/openapi.json").json()["paths"]
    assert "/parts9/api/substitutes/by-bcode/{bcode}" in openapi_paths
    assert "/parts9/api/substitutes/groups" in openapi_paths
    assert "/parts9/substitutes" in openapi_paths

    empty = client.get("/parts9/api/substitutes/by-bcode/01050076")
    assert empty.status_code == 200
    assert empty.json()["group"] is None

    created = client.post(
        "/parts9/api/substitutes/groups",
        json={
            "name": "seed",
            "members": [{"bcode": "01050076"}, {"bcode": "01050082"}],
        },
    )
    assert created.status_code == 200
    gid = created.json()["group"]["group_id"]

    conflict = client.post(
        "/parts9/api/substitutes/groups",
        json={"members": [{"bcode": "01050076"}]},
    )
    assert conflict.status_code == 409
    assert conflict.json()["bcode"] == "01050076"

    by = client.get("/parts9/api/substitutes/by-bcode/01050082")
    assert by.status_code == 200
    assert by.json()["group"]["group_id"] == gid
    assert len(by.json()["peers"]) == 1
    peer = by.json()["peers"][0]
    assert "hq_qtyoh2" in peer
    assert "sort_rank" in peer

    patched = client.patch(
        f"/parts9/api/substitutes/groups/{gid}",
        json={"note": "reviewed"},
    )
    assert patched.status_code == 200
    assert patched.json()["group"]["note"] == "reviewed"

    add = client.post(
        f"/parts9/api/substitutes/groups/{gid}/members",
        json={"bcode": "09050639", "sort_rank": 2},
    )
    assert add.status_code == 200

    rm = client.delete(f"/parts9/api/substitutes/groups/{gid}/members/01050082")
    assert rm.status_code == 200
    assert store.get_by_bcode("01050082") is None

    listed = client.get("/parts9/api/substitutes/groups")
    assert listed.status_code == 200
    assert len(listed.json()["groups"]) == 1

    deleted = client.delete(f"/parts9/api/substitutes/groups/{gid}")
    assert deleted.status_code == 200
    assert store.get_group(gid) is None


def test_api_rejects_unknown_bcode(monkeypatch):
    from app.parts9_explorer_app import app

    store = MemorySubstitutes()

    class _Ident:
        display_name = "tester"
        line_user_id = "u1"

    monkeypatch.setattr(
        "app.routers.parts9_substitutes._require",
        lambda request: (_Ident(), None),
    )
    monkeypatch.setattr("app.routers.parts9_substitutes._client", lambda: store)
    monkeypatch.setattr(
        "app.routers.parts9_substitutes.bcode_exists_any_site",
        lambda bcode, get_engine=None: False,
    )
    monkeypatch.setattr(
        "app.routers.parts9_substitutes.enrich_group",
        lambda g, get_engine=None: g,
    )

    client = TestClient(app)
    resp = client.post(
        "/parts9/api/substitutes/groups",
        json={"members": [{"bcode": "NOPE0001"}]},
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "UnknownBcodeError"


def test_api_unauthorized_without_session(monkeypatch):
    from app.parts9_explorer_app import app

    monkeypatch.setenv("PARTS9_EXPLORER_ENABLED", "1")
    monkeypatch.setenv("PARTS9_EXPLORER_TOKEN_SECRET", "test-secret")
    from src.parts9_explorer.config import get_explorer_settings

    get_explorer_settings.cache_clear()

    def deny(request):
        from fastapi.responses import HTMLResponse

        return None, HTMLResponse("no", status_code=401)

    monkeypatch.setattr("app.routers.parts9_substitutes._require", deny)
    client = TestClient(app)
    resp = client.get("/parts9/api/substitutes/groups")
    assert resp.status_code == 401


def test_manage_page_smoke(monkeypatch):
    from app.parts9_explorer_app import app

    class _Ident:
        display_name = "tester"
        line_user_id = "u1"

    monkeypatch.setattr(
        "app.routers.parts9_substitutes._require",
        lambda request: (_Ident(), None),
    )
    monkeypatch.setattr(
        "app.routers.parts9_substitutes._set_session",
        lambda resp, ident: None,
    )
    client = TestClient(app)
    resp = client.get("/parts9/substitutes?bcode=01050076")
    assert resp.status_code == 200
    html = resp.text
    assert "กลุ่มทดแทน" in html
    assert 'id="loadForm"' in html
    assert "01050076" in html
    assert "/parts9/api/substitutes/by-bcode/" in html


def test_needs_substitute_hint_l1_and_weak_stock():
    from src.substitutes.peers import needs_substitute_hint

    l1 = {"hq_no_stock": True, "hq_qtyoh2": 5, "hq_qtymin": -1}
    assert needs_substitute_hint(l1, ship_branch="HQ", need_qty=1) is True

    weak = {"hq_no_stock": False, "hq_qtyoh2": 2, "hq_qtymin": 1}
    assert needs_substitute_hint(weak, ship_branch="HQ", need_qty=5) is True
    assert needs_substitute_hint(weak, ship_branch="HQ", need_qty=1) is False

    syp_weak = {"syp_qtyoh2": 0, "syp_qtymin": 2}
    assert needs_substitute_hint(syp_weak, ship_branch="SYP", need_qty=3) is True


def test_attach_substitute_hints_for_l1(monkeypatch):
    from src.substitutes.peers import attach_live_suggestions

    items = [
        {
            "bcode": "L1SKU",
            "hq_no_stock": True,
            "hq_qtyoh2": 0,
            "hq_qtymin": -1,
            "suggest_qty": 2,
        },
        {
            "bcode": "OKSKU",
            "hq_no_stock": False,
            "hq_qtyoh2": 20,
            "hq_qtymin": 1,
            "suggest_qty": 2,
        },
    ]

    def fake_map(bcodes):
        return {
            "L1SKU": [
                {"bcode": "ALT002", "source": "remarks", "source_label": "REMARKS"},
                {"bcode": "ALT001", "source": "pcode", "source_label": "PCODE"},
            ]
        }

    out = attach_live_suggestions(
        items,
        ship_branch="HQ",
        need_qty_for=lambda r: r.get("suggest_qty"),
        suggest_map_fn=fake_map,
    )
    assert [p["bcode"] for p in out[0]["suggestions"]] == ["ALT002", "ALT001"]
    assert out[0]["substitutes"] == out[0]["suggestions"]
    assert out[1]["suggestions"] == []


def test_attach_live_suggestions_respects_max_codes():
    from src.substitutes.peers import attach_live_suggestions

    items = [
        {
            "bcode": "WEAK1",
            "hq_qtyoh2": 0,
            "hq_qtymin": 1,
            "suggest_qty": 5,
        },
        {
            "bcode": "L1FIRST",
            "hq_no_stock": True,
            "hq_qtyoh2": 0,
            "hq_qtymin": -1,
            "suggest_qty": 2,
        },
        {
            "bcode": "WEAK2",
            "hq_qtyoh2": 1,
            "hq_qtymin": 1,
            "suggest_qty": 4,
        },
    ]
    seen: list[str] = []

    def fake_map(bcodes):
        seen.extend(bcodes)
        return {b: [{"bcode": f"P-{b}", "source": "pcode"}] for b in bcodes}

    out = attach_live_suggestions(
        items,
        ship_branch="HQ",
        need_qty_for=lambda r: r.get("suggest_qty"),
        suggest_map_fn=fake_map,
        max_codes=1,
    )
    assert seen == ["L1FIRST"]
    by = {r["bcode"]: r for r in out}
    assert by["L1FIRST"]["suggestions"]
    assert by["WEAK1"]["suggestions"] == []
    assert by["WEAK2"]["suggestions"] == []



def test_enrich_transfer_lines_attaches_substitutes():
    from unittest.mock import patch

    from src.transfer.parts9 import enrich_transfer_lines

    lines = [{"bcode": "L1SKU", "qty_requested": 3, "qty_prepared": 0, "descr": ""}]

    def fake_meta(engine, bcodes, include_blocked=False):
        if engine is hq_engine:
            return {
                "L1SKU": {
                    "qtyoh2": 0.0,
                    "qtymin": -1.0,
                    "blocked": True,
                    "descr": "L-1 item",
                    "ui1": "ชิ้น",
                    "ui2": "",
                    "mtp2": 1.0,
                }
            }
        return {
            "L1SKU": {
                "qtyoh2": 5.0,
                "qtymin": 2.0,
                "blocked": False,
                "descr": "L-1 item",
                "ui1": "ชิ้น",
                "ui2": "",
                "mtp2": 1.0,
            }
        }

    hq_engine = object()
    syp_engine = object()

    def fake_engine(site):
        return hq_engine if site == "hq" else syp_engine

    def fake_map(bcodes):
        return {"L1SKU": [{"bcode": "PEER9", "source": "code_size", "descr": "peer"}]}

    with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=False):
        with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
            with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
                out = enrich_transfer_lines(
                    lines,
                    from_branch="HQ",
                    to_branch="SYP",
                    suggest_map_fn=fake_map,
                )

    assert out[0]["hq_no_stock"] is True
    assert len(out[0]["suggestions"]) == 1
    assert out[0]["suggestions"][0]["bcode"] == "PEER9"


def test_resolve_ship_as_ok_clash_and_not_in_group():
    from src.substitutes.memory import MemorySubstitutes
    from src.substitutes.ship_as import resolve_ship_as

    store = MemorySubstitutes()
    store.create_group(
        members=[{"bcode": "REQ001"}, {"bcode": "ALT001"}]
    )

    def meta(bcode):
        return {"descr": f"d-{bcode}", "qtyoh2": 9} if bcode == "ALT001" else None

    ok = resolve_ship_as(
        request_bcode="REQ001",
        ship_as_bcode="ALT001",
        other_request_bcodes={"OTHER9"},
        get_by_bcode=store.get_by_bcode,
        ship_from_meta=meta,
    )
    assert ok.is_substitute is True
    assert ok.ship_bcode == "ALT001"
    assert ok.requested_bcode == "REQ001"
    assert ok.error is None

    clash = resolve_ship_as(
        request_bcode="REQ001",
        ship_as_bcode="OTHER9",
        other_request_bcodes={"OTHER9"},
        get_by_bcode=store.get_by_bcode,
        ship_from_meta=lambda _b: {"descr": "x"},
    )
    assert clash.error
    assert "clash" in clash.error.lower() or "รายการขออื่น" in clash.error

    bad = resolve_ship_as(
        request_bcode="REQ001",
        ship_as_bcode="NOPE",
        other_request_bcodes=set(),
        get_by_bcode=store.get_by_bcode,
        ship_from_meta=lambda _b: {"descr": "x"},
    )
    assert bad.error
    assert "กลุ่ม" in bad.error

    same = resolve_ship_as(
        request_bcode="REQ001",
        ship_as_bcode=None,
        other_request_bcodes=set(),
        get_by_bcode=store.get_by_bcode,
        ship_from_meta=meta,
    )
    assert same.is_substitute is False
    assert same.ship_bcode == "REQ001"


def test_api_prepare_ship_as_passes_alt_bcode_to_writer():
    from unittest.mock import MagicMock, patch

    from app.routers.transfer import PrepareRequest, api_prepare
    from src.substitutes.memory import MemorySubstitutes

    store = MemorySubstitutes()
    store.create_group(members=[{"bcode": "REQ001"}, {"bcode": "ALT001"}])

    ident = MagicMock(display_name="op")
    settings = MagicMock()
    settings.site = "HQ"
    settings.hq_ship_write_enabled = True
    settings.syp_ship_write_enabled = False

    body = PrepareRequest(
        client_token="tok-ship-as",
        lines=[
            {
                "line_id": "line-1",
                "qty_ship": 2,
                "ship_as_bcode": "ALT001",
            }
        ],
    )
    request = MagicMock()

    with (
        patch("app.routers.transfer._require_api", return_value=(ident, None)),
        patch("app.routers.transfer._settings", return_value=settings),
        patch("app.routers.transfer.get_transfer_supabase_client", return_value=MagicMock()),
        patch(
            "app.routers.transfer.get_request",
            return_value={
                "transfer_id": "t1",
                "from_branch": "HQ",
                "to_branch": "SYP",
                "status": "requested",
                "short_id": "TRF-abc",
            },
        ),
        patch("app.routers.transfer.get_shipment_by_token", return_value=None),
        patch(
            "app.routers.transfer.list_lines",
            return_value=[
                {
                    "line_id": "line-1",
                    "bcode": "REQ001",
                    "descr": "requested",
                    "qty_requested": 5,
                    "qty_prepared": 0,
                    "qty_received": 0,
                },
                {
                    "line_id": "line-2",
                    "bcode": "OTHER9",
                    "descr": "other",
                    "qty_requested": 1,
                    "qty_prepared": 0,
                    "qty_received": 0,
                },
            ],
        ),
        patch(
            "app.routers.transfer._fetch_dual_icmas",
            return_value=(
                {
                    "REQ001": {"qtyoh2": 0, "qtymin": -1, "blocked": True, "descr": "req"},
                    "ALT001": {"qtyoh2": 8, "qtymin": 1, "blocked": False, "descr": "alt peer"},
                },
                {},
            ),
        ),
        patch(
            "app.routers.transfer.resolve_ship_as",
            wraps=__import__(
                "src.substitutes.ship_as", fromlist=["resolve_ship_as"]
            ).resolve_ship_as,
        ),
        patch("app.routers.transfer.post_transfer_ship") as mock_ship,
        patch(
            "app.routers.transfer.create_shipment",
            return_value={"shipment_id": "ship-1"},
        ),
        patch("app.routers.transfer.shipment_has_lines", return_value=False),
        patch("app.routers.transfer.add_shipment_lines") as mock_add,
        patch("app.routers.transfer.bump_line_prepared") as mock_bump,
        patch("app.routers.transfer.insert_event") as mock_event,
        patch("app.routers.transfer.refresh_request_status"),
        patch(
            "src.substitutes.config.get_substitutes_settings",
            return_value=MagicMock(supabase_url="http://x", supabase_service_role_key="k"),
        ),
        patch(
            "src.substitutes.db.get_substitutes_supabase_client",
            return_value=store,
        ),
        patch("src.substitutes.db.get_by_bcode", side_effect=lambda _c, b: store.get_by_bcode(b)),
    ):
        mock_ship.return_value = {"ship_billno": "TF6808-009", "tf_billno": "TF6808-009"}
        result = api_prepare("t1", body, request)

    assert result["ship_billno"] == "TF6808-009"
    shipped = mock_ship.call_args.kwargs["lines"]
    assert shipped[0]["bcode"] == "ALT001"
    assert shipped[0]["requested_bcode"] == "REQ001"
    assert shipped[0]["descr"] == "alt peer"
    mock_add.assert_called_once()
    assert mock_add.call_args.kwargs["lines"][0]["bcode"] == "ALT001"
    assert mock_bump.call_args.kwargs["line_id"] == "line-1"
    assert mock_bump.call_args.kwargs["qty_ship"] == 2
    mock_event.assert_called_once()
    assert mock_event.call_args.kwargs["event_type"] == "substitute_ship"
    assert mock_event.call_args.kwargs["payload"]["to_bcode"] == "ALT001"


def test_api_prepare_ship_as_clash_rejects():
    from unittest.mock import MagicMock, patch

    from app.routers.transfer import PrepareRequest, api_prepare
    from src.substitutes.memory import MemorySubstitutes

    store = MemorySubstitutes()
    store.create_group(members=[{"bcode": "REQ001"}, {"bcode": "OTHER9"}])

    ident = MagicMock(display_name="op")
    settings = MagicMock()
    settings.site = "HQ"
    settings.hq_ship_write_enabled = True

    body = PrepareRequest(
        client_token="tok-clash",
        lines=[{"line_id": "line-1", "qty_ship": 1, "ship_as_bcode": "OTHER9"}],
    )

    with (
        patch("app.routers.transfer._require_api", return_value=(ident, None)),
        patch("app.routers.transfer._settings", return_value=settings),
        patch("app.routers.transfer.get_transfer_supabase_client", return_value=MagicMock()),
        patch(
            "app.routers.transfer.get_request",
            return_value={
                "transfer_id": "t1",
                "from_branch": "HQ",
                "to_branch": "SYP",
                "status": "requested",
                "short_id": "TRF-abc",
            },
        ),
        patch("app.routers.transfer.get_shipment_by_token", return_value=None),
        patch(
            "app.routers.transfer.list_lines",
            return_value=[
                {
                    "line_id": "line-1",
                    "bcode": "REQ001",
                    "qty_requested": 5,
                    "qty_prepared": 0,
                    "qty_received": 0,
                },
                {
                    "line_id": "line-2",
                    "bcode": "OTHER9",
                    "qty_requested": 1,
                    "qty_prepared": 0,
                    "qty_received": 0,
                },
            ],
        ),
        patch(
            "app.routers.transfer._fetch_dual_icmas",
            return_value=(
                {
                    "REQ001": {"qtyoh2": 0, "qtymin": -1, "blocked": True, "descr": "req"},
                    "OTHER9": {"qtyoh2": 8, "qtymin": 1, "blocked": False, "descr": "other"},
                },
                {},
            ),
        ),
        patch(
            "src.substitutes.config.get_substitutes_settings",
            return_value=MagicMock(supabase_url="http://x", supabase_service_role_key="k"),
        ),
        patch("src.substitutes.db.get_substitutes_supabase_client", return_value=store),
        patch("src.substitutes.db.get_by_bcode", side_effect=lambda _c, b: store.get_by_bcode(b)),
        patch("app.routers.transfer.post_transfer_ship") as mock_ship,
    ):
        resp = api_prepare("t1", body, MagicMock())

    assert resp.status_code == 400
    assert "clash" in resp.body.decode().lower() or "รายการขออื่น" in resp.body.decode()
    mock_ship.assert_not_called()


def test_live_suggest_remarks_code_size_pcode_mcode_merge():
    from src.substitutes.suggest import (
        collect_suggestion_hits,
        extract_remarks_peers,
        is_clean_part_number,
        merge_suggestion_hits,
        suggest_for_bcode,
    )

    assert extract_remarks_peers("11111111", "ใช้รหัส 22222222 แทน") == ["22222222"]
    # no transitive merge — only directed from source remarks
    assert extract_remarks_peers("11111111", "ใช้รหัส 33333333 แทน") == ["33333333"]
    assert is_clean_part_number("203-07150B") is True
    assert is_clean_part_number("ราคา 09/2008") is False
    assert is_clean_part_number("") is False

    source = {
        "bcode": "10000001",
        "remarks": "ใช้รหัส 20000001 แทน",
        "code1": "C",
        "size1": "31",
        "size2": "46",
        "size3": "7",
        "pcode": "OEM-12345",
        "mcode": "FAC-99999",
    }

    def find_cs(**kw):
        assert kw["code1"] == "C"
        assert kw["size1"] == "31"
        return [{"bcode": "30000001", "source": "code_size", "evidence": "size"}]

    def find_pc(**kw):
        assert kw["value"] == "OEM-12345"
        return [{"bcode": "40000001", "source": "pcode", "evidence": "PCODE"}]

    def find_mc(**kw):
        return [{"bcode": "50000001", "source": "mcode", "evidence": "MCODE"}]

    hits = collect_suggestion_hits(
        source, find_code_size=find_cs, find_pcode=find_pc, find_mcode=find_mc
    )
    by = {h["bcode"]: h for h in hits}
    assert "20000001" in by and by["20000001"]["source"] == "remarks"
    assert "30000001" in by and by["30000001"]["source"] == "code_size"
    assert "40000001" in by and by["40000001"]["source"] == "pcode"
    assert "50000001" in by and by["50000001"]["source"] == "mcode"

    # remarks wins when same bcode hit by two signals
    merged = merge_suggestion_hits(
        [
            {"bcode": "X1", "source": "pcode", "evidence": "p"},
            {"bcode": "X1", "source": "remarks", "evidence": "r"},
        ]
    )
    assert merged[0]["source"] == "remarks"
    assert set(merged[0]["sources"]) == {"remarks", "pcode"}

    def fake_source(b):
        return source if b == "10000001" else None

    def fake_engine(_site):
        raise RuntimeError("no sql")

    out = suggest_for_bcode(
        "10000001",
        fetch_source=fake_source,
        find_code_size=find_cs,
        find_pcode=find_pc,
        find_mcode=find_mc,
        get_engine=fake_engine,
    )
    assert {p["bcode"] for p in out} >= {"20000001", "30000001", "40000001", "50000001"}


def test_ship_as_rejects_live_only_peer_not_in_catalog():
    from src.substitutes.memory import MemorySubstitutes
    from src.substitutes.ship_as import resolve_ship_as

    store = MemorySubstitutes()
    # catalog empty — live suggestion ALT999 must not authorize ส่งแทน
    bad = resolve_ship_as(
        request_bcode="REQ001",
        ship_as_bcode="ALT999",
        other_request_bcodes=set(),
        get_by_bcode=store.get_by_bcode,
        ship_from_meta=lambda b: {"descr": "x", "qtyoh2": 5},
    )
    assert bad.error
    assert "กลุ่ม" in bad.error


def test_api_suggest_endpoint(monkeypatch):
    from app.parts9_explorer_app import app

    class _Ident:
        display_name = "tester"
        line_user_id = "u1"

    monkeypatch.setattr(
        "app.routers.parts9_substitutes._require",
        lambda request: (_Ident(), None),
    )
    monkeypatch.setattr(
        "src.substitutes.suggest.suggest_for_bcode",
        lambda bcode, ship_branch=None, **kw: [
            {"bcode": "PEER01", "source": "remarks", "source_label": "REMARKS"}
        ],
    )
    client = TestClient(app)
    resp = client.get("/parts9/api/substitutes/suggest/SRC00001")
    assert resp.status_code == 200
    body = resp.json()
    assert body["bcode"] == "SRC00001"
    assert body["suggestions"][0]["bcode"] == "PEER01"

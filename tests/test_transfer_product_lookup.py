from unittest.mock import MagicMock, patch

from src.transfer.parts9 import (
    _fetch_site_icmas,
    enrich_transfer_lines,
    lookup_transfer_product,
)


def test_lookup_transfer_product_merges_hq_and_syp():
    def fake_meta(engine, bcodes, include_blocked=False):
        if engine is hq_engine:
            return {
                "02050663": {
                    "qtyoh2": 3.0,
                    "qtymin": 2.0,
                    "blocked": False,
                    "descr": "สะดือแหนบหน้า",
                    "ui1": "หน่วย",
                    "ui2": "",
                    "mtp2": 1.0,
                }
            }
        return {
            "02050663": {
                "qtyoh2": 1.0,
                "qtymin": 1.0,
                "blocked": False,
                "descr": "สะดือแหนบหน้า",
                "ui1": "หน่วย",
                "ui2": "",
                "mtp2": 1.0,
            }
        }

    hq_engine = object()
    syp_engine = object()

    def fake_engine(site):
        return hq_engine if site == "hq" else syp_engine

    with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=False):
        with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
            with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
                product = lookup_transfer_product(bcode="02050663")

    assert product is not None
    assert product["descr"] == "สะดือแหนบหน้า"
    assert product["hq_qtyoh2"] == 3.0
    assert product["syp_qtyoh2"] == 1.0
    assert product["hq_no_stock"] is False
    assert product["hq_qtymin"] == 2.0


def test_lookup_transfer_product_hq_l1_no_stock():
    def fake_meta(engine, bcodes, include_blocked=False):
        if engine is hq_engine:
            return {
                "L1SKU": {
                    "qtyoh2": 0.0,
                    "qtymin": -1.0,
                    "blocked": True,
                    "descr": "ไม่เก็บสต็อก",
                    "ui1": "ชิ้น",
                    "ui2": "",
                    "mtp2": 1.0,
                }
            }
        return {
            "L1SKU": {
                "qtyoh2": 2.0,
                "qtymin": 1.0,
                "blocked": False,
                "descr": "ไม่เก็บสต็อก",
                "ui1": "ชิ้น",
                "ui2": "",
                "mtp2": 1.0,
            }
        }

    hq_engine = object()
    syp_engine = object()

    def fake_engine(site):
        return hq_engine if site == "hq" else syp_engine

    with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=False):
        with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
            with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
                product = lookup_transfer_product(bcode="L1SKU")

    assert product is not None
    assert product["hq_no_stock"] is True
    assert product["hq_qtymin"] == -1.0
    assert product["syp_qtyoh2"] == 2.0


def test_enrich_transfer_lines_marks_hq_no_stock():
    lines = [{"bcode": "L1SKU", "qty": 1, "descr": ""}]

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

    with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=False):
        with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
            with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
                out = enrich_transfer_lines(lines, from_branch="HQ", to_branch="SYP")

    assert out[0]["hq_no_stock"] is True
    assert out[0]["hq_qtymin"] == -1.0
    assert out[0]["hq_qtyoh2"] == 0.0
    assert out[0]["syp_qtyoh2"] == 5.0


def test_lookup_uses_peer_when_sql_hosts_collide():
    peer_hq = {
        "02050663": {
            "qtyoh2": 9.0,
            "qtymin": 1.0,
            "blocked": False,
            "descr": "from peer HQ",
            "ui1": "หน่วย",
            "ui2": "",
            "mtp2": 1.0,
        }
    }
    local_syp = {
        "02050663": {
            "qtyoh2": 2.0,
            "qtymin": 1.0,
            "blocked": False,
            "descr": "local SYP",
            "ui1": "หน่วย",
            "ui2": "",
            "mtp2": 1.0,
        }
    }

    settings = MagicMock()
    settings.site = "SYP"
    settings.is_syp = True
    settings.peer_base_url = "http://hq-ubuntu-server:8792"

    def fake_meta(engine, bcodes, include_blocked=False):
        return dict(local_syp)

    with patch("src.transfer.parts9.get_transfer_settings", return_value=settings):
        with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=True):
            with patch("src.transfer.parts9.get_site_engine", return_value=MagicMock()):
                with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
                    with patch(
                        "src.transfer.parts9._fetch_icmas_via_peer", return_value=peer_hq
                    ) as peer:
                        product = lookup_transfer_product(bcode="02050663")

    assert product is not None
    assert product["hq_qtyoh2"] == 9.0
    assert product["syp_qtyoh2"] == 2.0
    peer.assert_called()


def test_fetch_site_icmas_falls_back_to_peer_on_sql_error():
    peer = {
        "A1": {
            "qtyoh2": 4.0,
            "qtymin": 0.0,
            "blocked": False,
            "descr": "x",
            "ui1": "",
            "ui2": "",
            "mtp2": 1.0,
        }
    }
    settings = MagicMock()
    settings.site = "HQ"
    settings.is_syp = False
    settings.peer_base_url = "http://syp-ubuntu-server:8792"

    with patch("src.transfer.parts9.get_transfer_settings", return_value=settings):
        with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=False):
            with patch("src.transfer.parts9.get_site_engine", return_value=MagicMock()):
                with patch(
                    "src.transfer.parts9._fetch_icmas_meta",
                    side_effect=ConnectionError("down"),
                ):
                    with patch(
                        "src.transfer.parts9._fetch_icmas_via_peer", return_value=peer
                    ) as peer_fn:
                        out = _fetch_site_icmas("syp", ["A1"])

    assert out["A1"]["qtyoh2"] == 4.0
    peer_fn.assert_called_once()


def test_enrich_transfer_lines_fills_missing_descr_and_live_stock():
    lines = [{"bcode": "02050663", "qty": 2, "descr": ""}]

    def fake_meta(engine, bcodes, include_blocked=False):
        if engine is hq_engine:
            return {
                "02050663": {
                    "qtyoh2": 3.0,
                    "qtymin": 1.0,
                    "blocked": False,
                    "descr": "สะดือแหนบหน้า",
                    "ui1": "หน่วย",
                    "ui2": "",
                    "mtp2": 1.0,
                }
            }
        return {
            "02050663": {
                "qtyoh2": 1.0,
                "qtymin": 1.0,
                "blocked": False,
                "descr": "สะดือแหนบหน้า",
                "ui1": "หน่วย",
                "ui2": "",
                "mtp2": 1.0,
            }
        }

    hq_engine = object()
    syp_engine = object()

    def fake_engine(site):
        return hq_engine if site == "hq" else syp_engine

    with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=False):
        with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
            with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
                out = enrich_transfer_lines(lines, from_branch="HQ", to_branch="SYP")

    assert out[0]["descr"] == "สะดือแหนบหน้า"
    assert out[0]["hq_qtyoh2"] == 3.0
    assert out[0]["syp_qtyoh2"] == 1.0
    assert out[0]["from_qtyoh2"] == 3.0
    assert out[0]["to_qtyoh2"] == 1.0
    assert out[0]["hq_no_stock"] is False
    assert out[0]["hq_qtymin"] == 1.0

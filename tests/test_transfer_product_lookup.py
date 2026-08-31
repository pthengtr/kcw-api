from unittest.mock import patch

from src.transfer.parts9 import enrich_transfer_lines, lookup_transfer_product


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

    with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
        with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
            product = lookup_transfer_product(bcode="02050663")

    assert product is not None
    assert product["descr"] == "สะดือแหนบหน้า"
    assert product["hq_qtyoh2"] == 3.0
    assert product["syp_qtyoh2"] == 1.0


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

    with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
        with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_meta):
            out = enrich_transfer_lines(lines, from_branch="HQ", to_branch="SYP")

    assert out[0]["descr"] == "สะดือแหนบหน้า"
    assert out[0]["hq_qtyoh2"] == 3.0
    assert out[0]["syp_qtyoh2"] == 1.0
    assert out[0]["from_qtyoh2"] == 3.0
    assert out[0]["to_qtyoh2"] == 1.0

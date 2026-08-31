from unittest.mock import MagicMock, patch

from src.transfer.parts9 import suggest_transfer_skus


def _meta(qtyoh2, *, blocked=False, ui1="ชิ้น", ui2="", mtp2=1.0, descr=""):
    return {
        "qtyoh2": qtyoh2,
        "qtymin": -1.0 if blocked else 4.0,
        "blocked": blocked,
        "descr": descr,
        "ui1": ui1,
        "ui2": ui2,
        "mtp2": mtp2,
    }


def test_suggest_transfer_skus_from_iclow_to_be_ordered():
    iclow_rows = {
        "rows": [
            {
                "bcode": "A001",
                "descr": "Widget A",
                "qty": 3,
                "ordered_qty": 3,
            },
            {
                "bcode": "A001",
                "descr": "Widget A",
                "qty": 2,
                "ordered_qty": 2,
            },
            {
                "bcode": "B002",
                "descr": "Widget B",
                "qty": 5,
                "ordered_qty": 5,
            },
        ],
        "count": 3,
    }

    def fake_icmas_meta(engine, bcodes):
        if engine is hq_engine:
            return {
                "A001": _meta(10.0, descr="Widget A HQ"),
                "B002": _meta(3.0, descr="Widget B HQ"),
            }
        return {
            "A001": _meta(1.0, descr="Widget A SYP"),
            "B002": _meta(0.0, descr="Widget B SYP"),
        }

    hq_engine = MagicMock(name="hq")
    syp_engine = MagicMock(name="syp")

    def fake_engine(site):
        return hq_engine if site == "hq" else syp_engine

    with patch("src.transfer.parts9.list_iclow", return_value=iclow_rows) as mock_list:
        with patch("src.transfer.parts9.get_site_engine", side_effect=fake_engine):
            with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_icmas_meta):
                items = suggest_transfer_skus(site="SYP", limit=50)

    mock_list.assert_called_once_with(site="syp", status="to_be_ordered", limit=200, offset=0)
    assert len(items) == 2
    a = next(i for i in items if i["bcode"] == "A001")
    assert a["suggest_qty"] == 5.0
    assert a["qtyoh2"] == 1.0
    assert a["hq_qtyoh2"] == 10.0
    assert a["syp_qtyoh2"] == 1.0
    b = next(i for i in items if i["bcode"] == "B002")
    assert b["suggest_qty"] == 5.0


def test_suggest_transfer_skus_skips_do_not_restock():
    iclow_rows = {
        "rows": [
            {"bcode": "NR01", "descr": "No restock", "qty": 1, "ordered_qty": 1},
            {"bcode": "OK01", "descr": "OK", "qty": 2, "ordered_qty": 2},
        ],
        "count": 2,
    }

    def fake_icmas_meta(engine, bcodes):
        return {
            "NR01": _meta(0.0, blocked=True),
            "OK01": _meta(1.0, ui1="ea", ui2="กล่อง", mtp2=12.0),
        }

    with patch("src.transfer.parts9.list_iclow", return_value=iclow_rows):
        with patch("src.transfer.parts9.get_site_engine", return_value=MagicMock()):
            with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_icmas_meta):
                items = suggest_transfer_skus(site="hq")

    assert [i["bcode"] for i in items] == ["OK01"]
    assert items[0]["ui1"] == "ea"
    assert items[0]["ui2"] == "กล่อง"
    assert items[0]["mtp2"] == 12.0


def test_suggest_transfer_skus_includes_icmas_low_stock_without_iclow():
    iclow_rows = {"rows": [], "count": 0}
    icmas_low = {
        "02050663": {
            "bcode": "02050663",
            "descr": "สะดือแหนบหน้า",
            "suggest_qty": 1.0,
            "qtyoh2": 1.0,
            "qtymin": 1.0,
            "ui1": "หน่วย",
            "ui2": "",
            "mtp2": 1.0,
            "source": "icmas",
        }
    }

    def fake_icmas_meta(engine, bcodes, include_blocked=False):
        return {
            "02050663": _meta(1.0, descr="สะดือแหนบหน้า", ui1="หน่วย"),
        }

    with patch("src.transfer.parts9.list_iclow", return_value=iclow_rows):
        with patch("src.transfer.parts9.get_site_engine", return_value=MagicMock()):
            with patch("src.transfer.parts9._suggest_from_icmas_low_stock", return_value=icmas_low):
                with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_icmas_meta):
                    items = suggest_transfer_skus(site="SYP", limit=50)

    assert len(items) == 1
    assert items[0]["bcode"] == "02050663"
    assert items[0]["descr"] == "สะดือแหนบหน้า"
    assert items[0]["source"] == "icmas"

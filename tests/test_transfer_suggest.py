from unittest.mock import MagicMock, patch

from src.transfer.parts9 import suggest_transfer_skus


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
        return {
            "A001": {"qtyoh2": 1.0, "qtymin": 4.0, "blocked": False},
            "B002": {"qtyoh2": 0.0, "qtymin": 2.0, "blocked": False},
        }

    with patch("src.transfer.parts9.list_iclow", return_value=iclow_rows) as mock_list:
        with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_icmas_meta):
            items = suggest_transfer_skus(site="SYP", limit=50)

    mock_list.assert_called_once_with(site="syp", status="to_be_ordered", limit=200, offset=0)
    assert len(items) == 2
    a = next(i for i in items if i["bcode"] == "A001")
    assert a["suggest_qty"] == 5.0
    assert a["qtyoh2"] == 1.0
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
            "NR01": {"qtyoh2": 0.0, "qtymin": -1.0, "blocked": True},
            "OK01": {"qtyoh2": 1.0, "qtymin": 3.0, "blocked": False},
        }

    with patch("src.transfer.parts9.list_iclow", return_value=iclow_rows):
        with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_icmas_meta):
            items = suggest_transfer_skus(site="hq")

    assert [i["bcode"] for i in items] == ["OK01"]

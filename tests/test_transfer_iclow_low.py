from __future__ import annotations

from contextlib import contextmanager
from datetime import date
from unittest.mock import MagicMock, patch

from src.transfer.writers.iclow_low import ensure_hq_low_stock_iclow, low_stock_reorder_qty
from src.transfer.writers.ship_simas import post_transfer_ship


def test_reorder_qty_skips_qtylo_zero_minus_one_and_not_below():
    assert low_stock_reorder_qty(qtyget=4, qtymin=-1, qtyoh=0) is None
    assert low_stock_reorder_qty(qtyget=2, qtymin=0, qtyoh=0) is None
    assert low_stock_reorder_qty(qtyget=4, qtymin=None, qtyoh=0) is None
    assert low_stock_reorder_qty(qtyget=4, qtymin=2, qtyoh=3) is None


def test_reorder_qty_uses_lot_when_on_hand_reaches_qtylo():
    assert low_stock_reorder_qty(qtyget=6, qtymin=4, qtyoh=4) == 6
    assert low_stock_reorder_qty(qtyget=6, qtymin=4, qtyoh=3) == 6
    assert low_stock_reorder_qty(qtyget=0, qtymin=4, qtyoh=1) == 3
    assert low_stock_reorder_qty(qtyget=0, qtymin=4, qtyoh=4) == 1


class _Result:
    def __init__(self, row=None, scalar=None):
        self._row = row
        self._scalar = scalar

    def mappings(self):
        return self

    def first(self):
        return self._row

    def scalar(self):
        return self._scalar


class _Conn:
    def __init__(self, product, open_id=None):
        self.product = product
        self.open_id = open_id
        self.inserted = None

    def execute(self, sql, params=None):
        statement = str(sql)
        if "FROM dbo.ICMAS" in statement:
            return _Result(row=self.product)
        if "FROM dbo.ICLOW" in statement:
            return _Result(scalar=self.open_id)
        if "INSERT INTO dbo.ICLOW" in statement:
            self.inserted = params
            return _Result(scalar=501)
        raise AssertionError(statement)


def test_ensure_inserts_waiting_row_when_on_hand_is_below_qtylo():
    conn = _Conn(
        {
            "QTYMIN": 2,
            "QTYGET": 4,
            "COSTLAST": 10,
            "DESCR": "bolt",
            "VENDOR": "7POP",
            "UI1": "หน่วย",
            "MCODE": "M1",
        }
    )
    iclow_id = ensure_hq_low_stock_iclow(conn, bcode="03010575", qtyoh=1, on=date(2026, 10, 19))
    assert iclow_id == 501
    assert conn.inserted["qty"] == 4
    assert conn.inserted["qtyoh"] == 1
    assert conn.inserted["price"] == 10
    assert conn.inserted["amount"] == 40
    assert conn.inserted["bcode"] == "03010575"
    assert conn.inserted["vendor"] == "7POP"
    assert conn.inserted["billdate"] == date(2026, 10, 19)


def test_ensure_skips_when_an_unreceived_row_is_already_open():
    conn = _Conn({"QTYMIN": 2, "QTYGET": 4, "COSTLAST": 10}, open_id=9)
    assert ensure_hq_low_stock_iclow(conn, bcode="03010575", qtyoh=0) is None
    assert conn.inserted is None


def test_ensure_inserts_when_on_hand_lands_on_qtylo():
    conn = _Conn({"QTYMIN": 8, "QTYGET": 10, "COSTLAST": 12, "BCODE": "03053151"})
    iclow_id = ensure_hq_low_stock_iclow(conn, bcode="03053151", qtyoh=8, on=date(2026, 10, 19))
    assert iclow_id == 501
    assert conn.inserted["qty"] == 10
    assert conn.inserted["qtyoh"] == 8


def test_ensure_skips_when_still_above_qtylo():
    conn = _Conn({"QTYMIN": 2, "QTYGET": 4})
    assert ensure_hq_low_stock_iclow(conn, bcode="03010575", qtyoh=3) is None
    assert conn.inserted is None
    assert ensure_hq_low_stock_iclow(_Conn({"QTYMIN": 0, "QTYGET": 4}), bcode="03010575", qtyoh=0) is None
    assert ensure_hq_low_stock_iclow(_Conn({"QTYMIN": -1, "QTYGET": 4}), bcode="03010575", qtyoh=0) is None


@patch("src.transfer.writers.ship_simas.ensure_hq_low_stock_iclow")
@patch("src.transfer.writers.ship_simas.get_transfer_supabase_client")
@patch("src.transfer.writers.ship_simas.writer_engine_for_branch")
@patch("src.transfer.writers.ship_simas.get_shipment_by_token")
def test_hq_ship_opens_iclow_after_qty_update(mock_get_shipment, mock_engine, _client, mock_low):
    mock_get_shipment.return_value = None
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = {
        "ACCTNAME": "สาขาสี่แยกพัฒนา",
        "MCODE": "M",
        "PCODE": "P",
        "UI1": "หน่วย",
        "LOCATION1": "A1",
        "QTYOH2": 3,
    }

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    with patch("src.transfer.writers.ship_simas.next_simas_billno", return_value="TF6910-0999"):
        post_transfer_ship(
            from_branch="HQ",
            to_branch="SYP",
            transfer_id="tid",
            short_id="ABCD",
            lines=[{"bcode": "03010575", "qty_ship": 2, "descr": "bolt"}],
            operator="op",
            client_token="tok",
        )
    mock_low.assert_called_once()
    assert mock_low.call_args.kwargs["bcode"] == "03010575"
    assert mock_low.call_args.kwargs["qtyoh"] == 1


@patch("src.transfer.writers.ship_simas.ensure_hq_low_stock_iclow")
@patch("src.transfer.writers.ship_simas.get_transfer_supabase_client")
@patch("src.transfer.writers.ship_simas.writer_engine_for_branch")
@patch("src.transfer.writers.ship_simas.get_shipment_by_token")
def test_syp_ship_does_not_open_hq_iclow(mock_get_shipment, mock_engine, _client, mock_low):
    mock_get_shipment.return_value = None
    mock_conn = MagicMock()
    mock_conn.execute.return_value.mappings.return_value.first.return_value = {
        "ACCTNAME": "สำนักงานใหญ่",
        "QTYOH2": 1,
        "UI1": "หน่วย",
    }

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    with patch("src.transfer.writers.ship_simas.next_simas_billno", return_value="3TF6910-0009"):
        post_transfer_ship(
            from_branch="SYP",
            to_branch="HQ",
            transfer_id="tid",
            short_id="ABCD",
            lines=[{"bcode": "03010575", "qty_ship": 1, "descr": "bolt"}],
            operator="op",
            client_token="tok",
        )
    mock_low.assert_not_called()

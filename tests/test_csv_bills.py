from decimal import Decimal
from pathlib import Path

from src.companion.config import CompanionBillSettings, get_companion_bill_settings
from src.companion.csv_bills import get_csv_bill, list_csv_bills
from src.companion.bills import list_open_bills, get_open_bill

FIXTURE = Path(__file__).parent / "fixtures" / "raw_hq_simas_sales_bills_sample.csv"


def _settings(**overrides) -> CompanionBillSettings:
    get_companion_bill_settings.cache_clear()
    base = {
        "pos_bill_source": "csv",
        "pos_bills_csv_path": str(FIXTURE),
        "pos_bills_mode": "latest",
        "pos_bills_limit": 10,
    }
    base.update(overrides)
    return CompanionBillSettings(**base)


def test_list_csv_bills_filters_cashed_y_and_orders_latest():
    bills = list_csv_bills(_settings(pos_bills_limit=10))
    # CASHED=N (104) and TF/TFV bill nos (106/107) excluded → 4 cash bills
    assert len(bills) == 4
    assert [b.bill_number for b in bills] == [
        "B2607140001",
        "B2607130002",
        "B2607120003",
        "B2607100005",
    ]
    assert bills[0].amount == Decimal("250.00")
    assert bills[0].pos_status == "N"
    assert bills[0].salesperson == "alice"


def test_list_csv_bills_excludes_tf_and_tfv_prefixes():
    bills = list_csv_bills(_settings(pos_bills_limit=20))
    bill_numbers = [b.bill_number for b in bills]
    assert "TF2607140006" not in bill_numbers
    assert "TFV2607140007" not in bill_numbers
    assert get_csv_bill("106", _settings()) is None
    assert get_csv_bill("107", _settings()) is None


def test_list_csv_bills_limit():
    bills = list_csv_bills(_settings(pos_bills_limit=2))
    assert len(bills) == 2
    assert bills[0].bill_number == "B2607140001"
    assert bills[1].bill_number == "B2607130002"


def test_get_csv_bill_by_id():
    bill = get_csv_bill("103", _settings())
    assert bill is not None
    assert bill.bill_number == "B2607120003"
    assert bill.pos_status == "Y"
    assert bill.salesperson == "carol"


def test_bills_dispatcher_uses_csv_source(monkeypatch):
    monkeypatch.setenv("POS_BILL_SOURCE", "csv")
    monkeypatch.setenv("POS_BILLS_CSV_PATH", str(FIXTURE))
    monkeypatch.setenv("POS_BILLS_MODE", "latest")
    monkeypatch.setenv("POS_BILLS_LIMIT", "2")
    get_companion_bill_settings.cache_clear()

    bills = list_open_bills()
    assert len(bills) == 2
    assert get_open_bill(bills[0].id) is not None
    get_companion_bill_settings.cache_clear()

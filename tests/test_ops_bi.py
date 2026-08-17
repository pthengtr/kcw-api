from datetime import date

import pytest

from src.ops.bi_filters import (
    MAX_LIVE_DAYS,
    billtype_std,
    excluded_from_revenue,
    reporting_branch,
    resolve_range,
    sales_type,
)
from src.ops.bi_ui import page


def test_revenue_excludes_transfers_and_stock_check():
    assert excluded_from_revenue("TF6908-046")
    assert excluded_from_revenue("TFV6908-069")
    assert excluded_from_revenue("3TF6908-001")
    assert excluded_from_revenue("TAR6902-001")
    assert excluded_from_revenue("CNTF6908-001")
    assert excluded_from_revenue("3CNTF6908-001")
    assert excluded_from_revenue("SA6908-001")
    assert excluded_from_revenue("3SA6908-001")
    assert not excluded_from_revenue("TAD6908-001")
    assert not excluded_from_revenue("TR6908-001")
    assert not excluded_from_revenue("CNTAD6908-001")
    assert not excluded_from_revenue("33K69-0006257")


def test_billtype_and_online_branch():
    assert billtype_std("TAD6908-001") == "TAD"
    assert billtype_std("3TR6908-001") == "TR"
    assert billtype_std("CNTAD6908-001") == "CN"
    assert billtype_std("33K69-0006257") == "UNKNOWN"
    assert reporting_branch(site="hq", billno="TAD6908-001") == "ONLINE"
    assert reporting_branch(site="hq", billno="CNTAD6908-001") == "ONLINE"
    assert reporting_branch(site="hq", billno="TR6908-001") == "HQ"
    assert reporting_branch(site="syp", billno="3TR6908-001") == "SYP"
    assert sales_type("TAD", "TAD6908-001", 0) == "VAT"
    assert sales_type("UNKNOWN", "33K69-1", 0) == "NON_VAT"


def test_live_range_cap():
    start, end = resolve_range("2026-08-01", "2026-08-17")
    assert start == date(2026, 8, 1)
    assert end == date(2026, 8, 17)
    with pytest.raises(ValueError):
        resolve_range("2026-01-01", "2026-08-17")
    assert MAX_LIVE_DAYS == 92


def test_bi_page_labels():
    html = page(probes={"hq": {"ok": True}, "syp": {"ok": True}})
    assert "ภาพรวมยอดขาย" in html
    assert "อันดับลูกค้า" in html
    assert "การเคลื่อนไหวสินค้า" in html
    assert "PARTS9" in html
    assert "92" in html

from datetime import date

from src.handlers.hq_receive_entry import is_hq_receive_command
from src.handlers.services_menu import services_menu_handlers_match
from src.hq_receive.docno import bn_prefix, buddhist_yymm, format_bn
from src.hq_receive.invoice_ai import _normalize_structured, _score_match
from src.hq_receive.net import is_private_lan
from src.hq_receive.rules import (
    RULES_SUMMARY,
    assert_confirmable,
    classify_line,
    cost_mismatch,
)
from src.hq_receive.service import _normalize_lines, _totals
from src.hq_receive.guards import HqReceiveError
import pytest


def test_docno_bn_sequence():
    assert buddhist_yymm(date(2026, 11, 7)) == "6911"
    assert bn_prefix(date(2026, 11, 7)) == "BN6911"
    assert format_bn(450, date(2026, 11, 7)) == "BN691100450"


def test_private_lan():
    assert is_private_lan("127.0.0.1")
    assert is_private_lan("192.168.1.21")
    assert not is_private_lan("8.8.8.8")


def test_normalize_and_totals():
    lines = _normalize_lines(
        [
            {"bcode": "A1", "qty": 2, "cost": 100, "discount": 10, "status": "ok"},
            {"bcode": "B2", "qty": 1, "cost": 50, "status": "hold"},
        ]
    )
    assert len(lines) == 2
    assert lines[0]["amount"] == 190
    totals = _totals(lines, {"discount": 20, "vat_rate": 7})
    assert totals["subtotal"] == 190
    assert totals["discount"] == 20
    assert totals["tax"] == 11.9
    assert totals["net"] == 181.9


def test_line_commands_and_menu():
    assert is_hq_receive_command("รับสินค้า")
    assert is_hq_receive_command("hq receive")
    assert not is_hq_receive_command("สั่งซื้อ")
    matched = services_menu_handlers_match()
    assert matched["hq_receive"] is True
    assert matched["hq_po"] is True


def test_rules_partial_and_over_po():
    under = classify_line(open_qty=10, receive_qty=4, known_product=True)
    assert under["status"] == "ok"
    assert "under_po" in under["flags"]
    over = classify_line(open_qty=10, receive_qty=12, known_product=True)
    assert over["status"] == "mismatch"
    assert "over_po" in over["flags"]
    assert cost_mismatch(100, 105) is True
    assert cost_mismatch(100, 101) is False
    assert "Confirm required" in RULES_SUMMARY or "confirm" in RULES_SUMMARY.lower()


def test_assert_confirmable_skips_hold_and_blocks_mismatch():
    ready = assert_confirmable(
        {
            "lines": [
                {"bcode": "A", "qty": 1, "status": "ok"},
                {"bcode": "B", "qty": 2, "status": "hold"},
            ]
        }
    )
    assert len(ready) == 1
    with pytest.raises(HqReceiveError):
        assert_confirmable(
            {"lines": [{"bcode": "X", "qty": 1, "status": "mismatch"}]}
        )


def test_invoice_normalize_and_score():
    structured = _normalize_structured(
        {
            "vendor_billno": "IV-1",
            "bill_date": "2026-11-07",
            "lines": [
                {
                    "raw_code": "07051647",
                    "raw_name": "ไส้กรอง",
                    "qty": 2,
                    "cost": 50,
                    "confidence": 0.9,
                }
            ],
        }
    )
    assert structured["vendor_billno"] == "IV-1"
    assert structured["lines"][0]["amount"] == 100
    score = _score_match(
        {"raw_code": "07051647", "raw_name": "ไส้กรอง", "qty": 2},
        {"bcode": "07051647", "descr": "ไส้กรองเครื่อง", "qty": 2},
    )
    assert score >= 0.7

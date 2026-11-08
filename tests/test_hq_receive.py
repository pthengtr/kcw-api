from datetime import date

from src.handlers.hq_receive_entry import is_hq_receive_command
from src.handlers.services_menu import services_menu_handlers_match
from src.hq_receive.docno import bn_prefix, buddhist_yymm, format_bn, format_cn, cn_prefix
from src.hq_receive.invoice_ai import _normalize_structured, _score_match
from src.hq_receive.net import is_private_lan
from src.hq_receive.rules import (
    RULES_SUMMARY,
    assert_confirmable,
    classify_line,
    cost_mismatch,
    credit_note_lines,
    line_cn_qty,
    line_pi_qty,
    line_sticker_qty,
)
from src.hq_receive.service import _normalize_lines, _totals
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.writers.credit_note_pimas import plan_credit_note, receipt_is_vat
import pytest


def test_docno_bn_sequence():
    assert buddhist_yymm(date(2026, 11, 7)) == "6911"
    assert bn_prefix(date(2026, 11, 7)) == "BN6911"
    assert format_bn(450, date(2026, 11, 7)) == "BN691100450"
    assert cn_prefix(is_vat=False, when=date(2026, 11, 7)) == "KCCN6911-"
    assert cn_prefix(is_vat=True, when=date(2026, 11, 7)) == "7KCCN6911-"
    assert format_cn(3, is_vat=False, when=date(2026, 11, 7)) == "KCCN6911-003"
    assert format_cn(1, is_vat=True, when=date(2026, 11, 7)) == "7KCCN6911-001"


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
    assert lines[0]["bill_qty"] == 2
    assert lines[0]["received_qty"] == 2
    totals = _totals(lines, {"discount": 20, "vat_rate": 7})
    assert totals["subtotal"] == 190
    assert totals["discount"] == 20
    assert totals["tax"] == 11.9
    assert totals["net"] == 181.9


def test_normalize_variance_and_change_product_holds():
    lines = _normalize_lines(
        [
            {
                "bcode": "A1",
                "bill_qty": 10,
                "received_qty": 9,
                "cost": 100,
                "variance_action": "credit_note",
                "status": "ok",
            },
            {
                "bcode": "B2",
                "bill_qty": 5,
                "received_qty": 4,
                "cost": 50,
                "variance_action": "change_product",
            },
        ]
    )
    assert lines[0]["variance_action"] == "credit_note"
    assert lines[0]["amount"] == 1000  # bill qty for money
    assert lines[1]["status"] == "hold"
    assert line_pi_qty(lines[0]) == 10
    assert line_cn_qty(lines[0]) == 1
    assert line_sticker_qty(lines[0]) == 9


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


def test_variance_requires_action_and_credit_note_plan():
    with pytest.raises(HqReceiveError) as exc:
        assert_confirmable(
            {
                "lines": [
                    {
                        "bcode": "A",
                        "bill_qty": 10,
                        "received_qty": 9,
                        "cost": 100,
                        "status": "ok",
                    }
                ]
            }
        )
    assert exc.value.code == "variance_unresolved"

    receipt = {
        "vendor_acctno": "V1",
        "tax": 0,
        "lines": [
            {
                "bcode": "A",
                "bill_qty": 10,
                "received_qty": 9,
                "cost": 100,
                "status": "ok",
                "variance_action": "credit_note",
            }
        ],
    }
    ready = assert_confirmable(receipt)
    assert ready[0]["qty"] == 10
    cn_lines = credit_note_lines(receipt)
    assert len(cn_lines) == 1
    assert cn_lines[0]["qty"] == 1
    assert cn_lines[0]["amount"] == 100
    plan = plan_credit_note(receipt, source_billno="BN691100001")
    assert plan is not None
    assert plan["is_vat"] is False
    assert plan["status"] == "completed"
    assert plan["beforetax"] == -100
    assert receipt_is_vat({"tax": 7}) is True
    vat_plan = plan_credit_note({**receipt, "tax": 7}, source_billno="BN691100001")
    assert vat_plan["is_vat"] is True
    assert vat_plan["status"] == "awaiting_vendor_doc"
    assert vat_plan["prefix"].startswith("7KCCN")

    wait_receipt = {
        "lines": [
            {
                "bcode": "A",
                "bill_qty": 10,
                "received_qty": 9,
                "cost": 100,
                "status": "ok",
                "variance_action": "wait_rest",
            }
        ]
    }
    ready_wait = assert_confirmable(wait_receipt)
    assert ready_wait[0]["qty"] == 9
    assert credit_note_lines(wait_receipt) == []


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

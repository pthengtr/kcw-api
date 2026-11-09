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
from src.hq_receive.icmas_create import _main_from_bcode
from src.hq_receive.iclow_open import _po_key
from src.hq_receive.service import _normalize_lines, _totals
from src.hq_receive.guards import HqReceiveError
from src.hq_receive.ui import page
from src.hq_receive.writers.credit_note_pimas import plan_credit_note, receipt_is_vat
from src.hq_receive.writers.receive_pimas import _apply_iclow_receive
import pytest
from unittest.mock import MagicMock


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


def test_ui_po_first_and_typed_cost():
    html = page(user_name="tester", write_enabled=False)
    assert "ดึงรายการจาก PO ที่เลือก" in html
    assert "สร้างสินค้าใหม่" in html
    assert "AI Match ค้างรับ" not in html
    assert 'inputmode="decimal"' in html
    assert "/open-pos" in html
    assert "/products" in html
    assert "renderPoLines" in html
    assert "แก้ไขข้อมูลสินค้า" in html
    assert 'id="npLoc1"' in html
    assert 'id="npCode1"' in html
    assert 'id="npPrice"' in html
    assert ">ค่า<" in html
    assert "PUT" in html and "/products/" in html


def test_main_from_bcode_and_po_key():
    assert _main_from_bcode("07051647") == 7
    assert _main_from_bcode("AB") is None
    assert _po_key({"hq_po_docno": "HP6911-AAAA", "docno": "X"}) == "HP6911-AAAA"
    assert _po_key({"docno": "DOC1"}) == "DOC1"


def test_line_preview_and_open_pos_shape():
    from src.hq_receive.iclow_open import _line_preview

    preview = _line_preview(
        {
            "bcode": "07051647",
            "descr": "ไส้กรอง",
            "model": "M1",
            "brand": "B1",
            "pcode": "P1",
            "mcode": "F1",
            "photo": "https://example/x.jpg",
            "qty": 3,
            "ui": "ชิ้น",
        }
    )
    assert preview["bcode"] == "07051647"
    assert preview["pcode"] == "P1"
    assert preview["photo"].endswith(".jpg")
    assert preview["qty"] == 3.0


def _iclow_select_then(update_rowcount: int = 1):
    select_result = MagicMock()
    select_result.mappings.return_value.first.return_value = {"ID": 9, "QTY": 10.0}
    update_result = MagicMock(rowcount=update_rowcount)
    conn = MagicMock()
    conn.execute.side_effect = [select_result, update_result]
    return conn


def test_apply_iclow_receive_reduces_on_wait_rest():
    conn = _iclow_select_then()
    result = _apply_iclow_receive(
        conn,
        iclow_id=9,
        line={
            "bcode": "A",
            "bill_qty": 10,
            "received_qty": 4,
            "variance_action": "wait_rest",
        },
        rcvdno="BN691100001",
        rcvddate=date(2026, 11, 9),
    )
    assert result == "reduced"
    assert conn.execute.call_count == 2
    reduce_sql = str(conn.execute.call_args_list[1].args[0])
    assert "SET QTY" in reduce_sql
    assert conn.execute.call_args_list[1].args[1]["qty"] == 6.0


def test_apply_iclow_receive_stamps_on_full():
    conn = _iclow_select_then()
    result = _apply_iclow_receive(
        conn,
        iclow_id=9,
        line={"bcode": "A", "bill_qty": 10, "received_qty": 10},
        rcvdno="BN691100001",
        rcvddate=date(2026, 11, 9),
    )
    assert result == "received"
    stamp_sql = str(conn.execute.call_args_list[1].args[0])
    assert "RECEIVED" in stamp_sql


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

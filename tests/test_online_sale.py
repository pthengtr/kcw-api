from __future__ import annotations

from contextlib import contextmanager
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from src.handlers.online_sale_entry import is_online_sale_command
from src.handlers.services_menu import services_menu_handlers_match
from src.handlers.to_bill_entry import handle_to_bill_command, is_to_bill_command
from src.online_sale.docno import buddhist_yymm, format_cntad, format_tad
from src.online_sale.errors import OnlineSaleError
from src.online_sale.net import is_private_lan
from src.online_sale.shops import bill_acctname, detect_platform, shop_display_name
from src.online_sale.ui import page
from src.online_sale.vat import split_inclusive, totals_from_amounts
from src.online_sale.sheets.cntad import render_cntad_sheet
from src.online_sale.staff import issuer_full_name, match_staff
from src.online_sale.writers.cntad_simas import post_cntad
from src.online_sale.writers.tad_simas import post_tad, update_tad


def test_line_commands_and_menu():
    assert is_online_sale_command("ขายออนไลน์")
    assert is_online_sale_command("tad")
    assert is_to_bill_command("ใบเต็มออนไลน์")
    matched = services_menu_handlers_match()
    assert matched["online_sale"] is True
    assert "to_bill" not in matched
    from src.handlers.services_menu import handle_services_menu

    labels = [
        c["action"]["label"]
        for c in handle_services_menu()["contents"]["body"]["contents"]
        if c.get("type") == "button"
    ]
    assert "ขายออนไลน์" in labels
    assert "ใบเต็มออนไลน์" not in labels


def test_docno_format():
    yymm = buddhist_yymm()
    assert format_tad(1).startswith(f"TAD{yymm}-")
    assert format_tad(393) == f"TAD{yymm}-393"
    assert format_cntad(12) == f"CNTAD{yymm}-012"
    assert len(format_tad(999)) <= 15


def test_vat_split_matches_live_tad():
    before, tax, after = split_inclusive(1970)
    assert after == Decimal("1970.00")
    assert tax == Decimal("128.88")
    assert before == Decimal("1841.12")
    totals = totals_from_amounts([1250, 720])
    assert totals["aftertax"] == Decimal("1970.00")


def test_shop_helpers():
    assert detect_platform("คุณลูกค้าทั่วไป SHOPEE (PNT TRACTOR)", "7SPNT") == "shopee"
    assert detect_platform("คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)", "7LAZ1") == "lazada"
    assert detect_platform("คุณลูกค้าทั่วไป TIKTOK (ICE TIKTOK SHOP)", "7ICE") == "tiktok"
    assert detect_platform("LINE MY SHOP", "7LINE") == "line"
    assert detect_platform("บริษัท ส.บุญรักษา จำกัด (สำนักงานใหญ่)", "7SB") == ""
    assert shop_display_name("คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)") == "KC INDUSTRY"
    assert "LAZADA" in bill_acctname("lazada", "KC INDUSTRY")


def test_ui_page_placeholders():
    html = page(user_name="ทดสอบ", write_enabled=True)
    assert "ขายออนไลน์" in html
    assert "true" in html
    assert "ทดสอบ" in html
    assert 'data-tab="to"' in html
    assert "stockWarn" in html
    assert "status-cancel" in html
    assert "data-edit" in html
    assert "cancelEdit" in html


def test_staff_roster_and_cntad_signers():
    assert match_staff("เมย์")["full_name"] == "ปิยะนุช นันตาบุตร"
    assert issuer_full_name("Nu") == "อานนท์ ชูสวัสดิ์"
    assert issuer_full_name("Boss") == "สุริยะ โกศัลยกุล"
    html = render_cntad_sheet(
        {
            "billno": "CNTAD6911-001",
            "bill_date": "2026-11-15",
            "sale": "เมย์",
            "acctname": "ลูกค้า",
            "lines": [],
            "aftertax": 0,
            "tax": 0,
        }
    )
    assert "ผู้ออกเอกสาร" in html
    assert "ผู้อนุมัติเอกสาร" in html
    assert "ผู้รับเอกสาร" in html
    assert "ปิยะนุช นันตาบุตร" in html


def test_update_tad_validation():
    with pytest.raises(OnlineSaleError, match="TAD"):
        update_tad(
            billno="CNTAD6911-001",
            acctno="7LAZ1",
            acctname="x",
            online_po="PO1",
            remarks="##0000000000001",
            operator="tester",
            lines=[{"bcode": "A", "qty": 1, "price": 10}],
        )
    with pytest.raises(OnlineSaleError, match="อย่างน้อย"):
        update_tad(
            billno="TAD6911-001",
            acctno="7LAZ1",
            acctname="x",
            online_po="PO1",
            remarks="##0000000000001",
            operator="tester",
            lines=[],
        )


def test_private_lan():
    assert is_private_lan("127.0.0.1")
    assert is_private_lan("192.168.1.2")
    assert not is_private_lan("8.8.8.8")


def test_post_tad_validation():
    with pytest.raises(OnlineSaleError, match="อย่างน้อย"):
        post_tad(
            acctno="7LAZ1",
            acctname="คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)",
            online_po="ORDER1",
            remarks="##0000000000001",
            operator="tester",
            lines=[],
        )
    with pytest.raises(OnlineSaleError, match="15"):
        post_tad(
            acctno="7LAZ1",
            acctname="x",
            online_po="1234567890123456",
            remarks="##0000000000001",
            operator="tester",
            lines=[{"bcode": "A", "qty": 1, "price": 10}],
        )


@patch("src.online_sale.writers.tad_simas._fetch_icmas_row")
@patch("src.online_sale.writers.tad_simas.writer_engine_for_branch")
def test_post_tad_blocks_duplicate_po_and_stock(mock_engine, mock_icmas):
    mock_conn = MagicMock()

    def first_side_effect():
        # First SELECT in TX = duplicate PO check; return an existing bill.
        return {"billno": "TAD6911-001"}

    mock_conn.execute.return_value.mappings.return_value.first.side_effect = first_side_effect

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
    with pytest.raises(OnlineSaleError) as exc:
        post_tad(
            acctno="7LAZ1",
            acctname="คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)",
            online_po="DUPORDER",
            remarks="##0000000000001",
            operator="tester",
            lines=[{"bcode": "03053231", "qty": 1, "price": 100, "detail": "x"}],
        )
    assert exc.value.code == "duplicate_po"

    # No duplicate; stock too low.
    mock_conn.execute.return_value.mappings.return_value.first.side_effect = lambda: None
    mock_icmas.return_value = {
        "PCODE": "P",
        "MCODE": "M",
        "UI1": "หน่วย",
        "LOCATION1": "A1",
        "QTYOH2": 0,
        "DESCR": "item",
    }
    with pytest.raises(OnlineSaleError) as stock_exc:
        post_tad(
            acctno="7LAZ1",
            acctname="คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)",
            online_po="NEWORDER",
            remarks="##0000000000001",
            operator="tester",
            lines=[{"bcode": "03053231", "qty": 2, "price": 100, "detail": "x"}],
        )
    assert stock_exc.value.code == "stock"


def test_post_cntad_requires_tad_ref():
    with pytest.raises(OnlineSaleError, match="TAD"):
        post_cntad(
            tad_billno="TAR6911-001",
            acctno="7LAZ1",
            acctname="x",
            remarks="##0000000000001",
            operator="tester",
            lines=[{"bcode": "A", "qty": 1, "price": 10}],
        )


def test_to_bill_line_redirects_to_online_sale(monkeypatch):
    captured = {}

    def fake_handle(engine, **kwargs):
        captured.update(kwargs)
        return {"type": "text", "text": "ok"}

    monkeypatch.setattr(
        "src.handlers.to_bill_entry.handle_online_sale_command",
        fake_handle,
    )
    out = handle_to_bill_command(None, line_user_id="u1", display_name="A")
    assert out["type"] == "text"
    assert captured["path"] == "/online-sale/?tab=to"
    assert captured["title"] == "ใบเต็มออนไลน์"

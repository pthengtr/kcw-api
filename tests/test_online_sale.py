from __future__ import annotations

from decimal import Decimal

from src.handlers.online_sale_entry import is_online_sale_command
from src.handlers.services_menu import services_menu_handlers_match
from src.handlers.to_bill_entry import is_to_bill_command
from src.online_sale.docno import buddhist_yymm, format_cntad, format_tad
from src.online_sale.shops import bill_acctname, detect_platform, shop_display_name
from src.online_sale.ui import page
from src.online_sale.vat import split_inclusive, totals_from_amounts


def test_line_commands_and_menu():
    assert is_online_sale_command("ขายออนไลน์")
    assert is_online_sale_command("tad")
    assert is_to_bill_command("ใบเต็มออนไลน์")
    matched = services_menu_handlers_match()
    assert matched["online_sale"] is True
    assert matched["to_bill"] is True


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

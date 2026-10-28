from datetime import date
from decimal import Decimal

from src.to_bill.buyers import armas_prefill, is_generic_party, parse_buyer, usable_tax_id, validate_buyer
from src.to_bill.kss import LiveBill, LiveLine, like_prefix
from src.to_bill.net import is_private_lan
from src.to_bill.numbering import buddhist_yymm, format_docno, month_bounds
from src.to_bill.service import changed_from_kss
from src.to_bill.sheet import build_sheet
from src.handlers.to_bill_entry import is_to_bill_command
from src.handlers.services_menu import services_menu_handlers_match


def test_docno_padding_and_overflow():
    assert format_docno("6910", 1) == "TO6910-001"
    assert format_docno("6910", 999) == "TO6910-999"
    assert format_docno("6910", 1000) == "TO6910-1000"


def test_buddhist_month_and_bounds():
    assert buddhist_yymm(date(2026, 10, 28)) == "6910"
    start, end = month_bounds("6910")
    assert start.isoformat().startswith("2026-10-01")
    assert end.isoformat().startswith("2026-11-01")


def test_generic_party_and_tax_id():
    assert is_generic_party("คุณลูกค้าทั่วไป LAZADA ( PNT TRACTOR)")
    assert is_generic_party("เงินสด")
    assert not is_generic_party("หจก. สมชายอะไหล่")
    assert usable_tax_id("0000000000001") == ""
    assert usable_tax_id("0000-000-00000-1") == ""
    assert usable_tax_id("1234567890123") == "1234567890123"


def test_buyer_validation_and_branch():
    buyer = parse_buyer(
        {
            "customer_name": "บริษัท ทดสอบ จำกัด",
            "address": "1 ถนนทดสอบ",
            "tax_id": "1234567890123",
            "branch_label": "สาขาที่",
            "branch_no": "2",
            "phone": "0812345678",
        }
    )
    assert buyer.branch_label == "สาขาที่ 2"
    assert validate_buyer(buyer) is None
    assert validate_buyer(parse_buyer({"customer_name": "A", "address": "B", "tax_id": "123"}))


def test_armas_prefill_skips_marketplace():
    assert armas_prefill({"acctname": "คุณลูกค้าทั่วไป SHOPEE", "tax_id": "0000000000003"}) is None
    filled = armas_prefill(
        {
            "acctname": "หจก. สมชาย",
            "addr1": "99 หมู่ 2",
            "addr2": "=DONE=",
            "phone": "038-000000",
            "tax_id": "1234567890123",
            "email": "a@example.com",
        }
    )
    assert filled["address"] == "99 หมู่ 2"
    assert filled["tax_id"] == "1234567890123"


def test_like_prefix_escapes():
    assert like_prefix("TAD_69%") == "TAD[_]69[%]%"


def test_private_lan():
    assert is_private_lan("192.168.1.21")
    assert is_private_lan("127.0.0.1")
    assert is_private_lan("10.1.1.1")
    assert not is_private_lan("100.113.10.32")
    assert not is_private_lan("8.8.8.8")


def test_changed_from_kss_detects_amount():
    live = LiveBill(
        billno="TAD6910-014",
        bill_date=date(2026, 10, 1),
        acctno="7LPNT",
        acctname="คุณลูกค้าทั่วไป LAZADA",
        online_po="123",
        beforetax=Decimal("100.00"),
        tax=Decimal("7.00"),
        aftertax=Decimal("107.00"),
        discount=Decimal("0.00"),
        canceled=False,
        lines=[
            LiveLine(10, "A", "น็อต", Decimal("1"), "หน่วย", Decimal("107.00"), Decimal("107.00"))
        ],
    )
    saved = {
        "tad_billno": "TAD6910-014",
        "beforetax": 100,
        "tax": 7,
        "aftertax": 107,
        "discount": 0,
        "kss_canceled": False,
        "lines": [{"bcode": "A", "detail": "น็อต", "qty": 1, "amount": 107}],
    }
    assert changed_from_kss(saved, live) is False
    saved["aftertax"] = 200
    assert changed_from_kss(saved, live) is True


def test_sheet_names_the_tad_and_buyer():
    html = build_sheet(
        {
            "status": "issued",
            "docno": "TO6910-001",
            "tad_billno": "TAD6910-014",
            "bill_date": "2026-10-27",
            "issued_at": "2026-10-28",
            "customer_name": "บริษัท ทดสอบ จำกัด",
            "address": "1 ถนนทดสอบ",
            "tax_id": "1234567890123",
            "branch_label": "สำนักงานใหญ่",
            "phone": "0812345678",
            "beforetax": 100,
            "tax": 7,
            "aftertax": 107,
            "discount": 0,
            "online_po": "9988",
            "lines": [{"bcode": "12053560", "detail": "แหวน", "qty": 1, "ui": "หน่วย", "price": 107, "amount": 107}],
        },
        seller_tax_id="0105537000000",
    )
    assert "ใบกำกับภาษี/ใบเสร็จรับเงิน" in html
    assert "ใบกำกับภาษีเต็มรูป" not in html
    assert "FULL TAX INVOICE" not in html
    assert html.count("(ต้นฉบับ)") == 1
    assert html.count("(สำเนา)") == 1
    assert "เลขที่เอกสาร" in html
    assert "TO6910-001" in html
    assert "27 ตุลาคม 2569" in html
    assert "27/10/2569" in html
    assert "ลูกค้า" in html
    assert "ผู้ซื้อ" not in html
    assert "ที่อยู่" in html
    assert "เลขคำสั่งซื้อ" in html
    assert "เลขออเดอร์" not in html
    assert "9988" in html
    assert "ออกแทนใบกำกับภาษีอย่างย่อ TAD6910-014" in html
    assert "วันที่ 27/10/2569 ซึ่งยกเลิกแล้ว" in html
    assert html.count("ผู้ออกเอกสาร (ผู้ขาย)") == 2
    assert html.count("ผู้อนุมัติเอกสาร (ผู้ขาย)") == 2
    assert html.count("ผู้รับเอกสาร (ลูกค้า)") == 2
    assert "ลายมือชื่อ" in html
    assert "TAD6910-014" in html
    assert "บริษัท ทดสอบ จำกัด" in html
    assert "1234567890123" in html
    assert "0105537000000" in html
    assert "class='void'" not in html


def test_void_sheet_has_watermark():
    html = build_sheet(
        {
            "status": "void",
            "docno": "TO6910-001",
            "tad_billno": "TAD6910-014",
            "customer_name": "ทดสอบ",
            "address": "1",
            "tax_id": "1234567890123",
            "branch_label": "สำนักงานใหญ่",
            "beforetax": 0,
            "tax": 0,
            "aftertax": 0,
            "void_reason": "พิมพ์ผิด",
            "lines": [],
        },
        seller_tax_id="0105537000000",
    )
    assert html.count("class='void'>ยกเลิก") == 2
    assert "พิมพ์ผิด" in html
    assert "(ต้นฉบับ)" in html and "(สำเนา)" in html


def test_line_command_and_menu():
    assert is_to_bill_command("ใบเต็ม")
    assert is_to_bill_command("ใบเต็มออนไลน์")
    assert is_to_bill_command("TO Bill")
    assert not is_to_bill_command("สั่งซื้อ")
    assert services_menu_handlers_match()["to_bill"]

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
from src.online_sale.shops import (
    bill_acctname,
    channel_label,
    customer_name_without_shop,
    detect_platform,
    shop_display_name,
    tax_id_from_remarks,
    validate_online_po,
)
from src.online_sale.ui import page
from src.online_sale.vat import split_inclusive, totals_from_amounts
from src.online_sale.sheets.cntad import credit_note_summary, render_cntad_sheet
from src.online_sale.sheets.pick import render_pick_sheet
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

    from src.handlers.services_menu import iter_services_menu_buttons

    labels = [
        c["action"]["label"] for c in iter_services_menu_buttons(handle_services_menu())
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
    assert customer_name_without_shop(
        "คุณลูกค้าทั่วไป LAZADA ( PNT TRACTOR)"
    ) == "คุณลูกค้าทั่วไป LAZADA"
    assert channel_label("lazada", "PNT TRACTOR") == "Lazada (PNT TRACTOR)"
    assert tax_id_from_remarks("##0000000000001") == "0000000000001"
    assert tax_id_from_remarks("โอน##0105524009949") == "0105524009949"
    assert tax_id_from_remarks("") == ""


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
    assert "qtyUnit" in html
    assert "unit-select" in html
    assert "print/pick?drafts=" in html
    assert "พิมพ์ใบจัดสินค้ารวม" in html
    assert "พิมพ์ TAD" in html
    assert "บันทึกฉบับร่าง" in html
    assert "pick-draft" in html
    assert "printPick" in html
    assert "saveDraft" in html
    assert "qKind" in html
    # Search results: compact TAD / CNTAD / net summary above pick print.
    assert "searchBillSummary" in html
    assert "renderSearchSummaryHtml" in html
    assert 'class="search-sum"' in html
    assert "บิลขาย" in html
    assert "บิลคืน" in html
    assert "ยอดสุทธิ" in html
    assert "searchBillSummary(bills)" in html
    # After a successful draft save, clear the form for the next order
    # instead of staying in edit mode (editDraftId + syncEditBanner).
    assert "clearSaleForm();" in html
    draft_save = html.split("$('saveDraft').onclick", 1)[1].split("$('saveSale').onclick", 1)[0]
    assert "clearSaleForm();" in draft_save
    assert "state.editDraftId = draft.draft_id" not in draft_save
    # Sale page must not offer pick-sheet after save.
    assert "print/pick/${encodeURIComponent(billno)}" not in html
    # Pick is from drafts only — no TAD checkbox class.
    assert "pick-bill" not in html


def test_pick_sheet_sorted_no_price():
    html = render_pick_sheet(
        {
            "billno": "TAD6911-010",
            "bill_date": "2026-11-16",
            "platform": "shopee",
            "shop_name": "PNT TRACTOR",
            "online_po": "251116ABC",
            "lines": [
                {
                    "bcode": "B2",
                    "detail": "สินค้า B",
                    "qty": 2,
                    "ui": "ลัง",
                    "mtp": 10,
                    "qtyoh2": 50,
                    "location1": "Z-9",
                    "price": 999,
                    "amount": 1998,
                    "photo": "https://example.com/b2.jpg",
                    "brand": "KUBOTA",
                    "model": "L3408",
                    "pcode": "1G888-11111",
                    "mcode": "HH123",
                },
                {
                    "bcode": "B1",
                    "detail": "สินค้า A",
                    "qty": 1,
                    "ui": "ขวด",
                    "mtp": 1,
                    "qtyoh2": 3,
                    "location1": "A-1",
                    "price": 100,
                    "amount": 100,
                },
            ],
        }
    )
    assert "ใบจัดสินค้า" in html
    # Packing refs use order id, not TAD.
    assert "251116ABC" in html
    assert "เลขคำสั่งซื้อ" in html
    assert "Shopee" in html
    assert "PNT TRACTOR" in html
    assert "ผู้จัดสินค้า" in html
    assert "ผู้ตรวจสินค้า" in html
    assert "ที่เก็บ" in html
    assert "คงเหลือ" in html
    # B2: qtyoh2 50 / mtp 10 = 5 ลัง; B1: 3 ขวด
    assert ">5<" in html or ">5</td>" in html
    assert ">3<" in html or ">3</td>" in html
    assert "☐" in html
    assert html.index("A-1") < html.index("Z-9")
    assert "999" not in html
    assert "1,998" not in html
    assert "ราคา" not in html
    assert "https://example.com/b2.jpg" in html
    # Name extras under ชื่อสินค้า; omit blank fields (B1 has none).
    assert "ยี่ห้อ KUBOTA" in html
    assert "รุ่น L3408" in html
    assert "เบอร์แท้ 1G888-11111" in html
    assert "เบอร์โรงงาน HH123" in html
    assert html.count("ยี่ห้อ ") == 1
    assert html.count("รุ่น ") == 1


def test_pick_sheet_merges_multi_bill_same_sku_unit():
    from src.online_sale.sheets.pick import merge_pick_lines

    merged = merge_pick_lines(
        [
            {
                "billno": "TAD6911-001",
                "online_po": "PO1",
                "lines": [
                    {
                        "bcode": "B1",
                        "detail": "สินค้า A",
                        "qty": 2,
                        "ui": "ขวด",
                        "location1": "A-1",
                    },
                    {
                        "bcode": "B2",
                        "detail": "สินค้า B",
                        "qty": 1,
                        "ui": "ลัง",
                        "location1": "Z-9",
                    },
                ],
            },
            {
                "billno": "TAD6911-002",
                "online_po": "PO2",
                "lines": [
                    {
                        "bcode": "B1",
                        "detail": "สินค้า A",
                        "qty": 3,
                        "ui": "ขวด",
                        "location1": "A-1",
                    },
                    {
                        "bcode": "B1",
                        "detail": "สินค้า A",
                        "qty": 1,
                        "ui": "ลัง",
                        "location1": "A-1",
                    },
                ],
            },
        ]
    )
    by_key = {(r["bcode"], r["ui"]): r for r in merged}
    assert by_key[("B1", "ขวด")]["qty"] == 5
    assert {x["billno"]: x["qty"] for x in by_key[("B1", "ขวด")]["bill_qtys"]} == {
        "PO1": 2,
        "PO2": 3,
    }
    assert by_key[("B1", "ลัง")]["qty"] == 1
    html = render_pick_sheet(
        bills=[
            {
                "billno": "TAD6911-001",
                "online_po": "PO1",
                "lines": [
                    {
                        "bcode": "B1",
                        "detail": "สินค้า A",
                        "qty": 2,
                        "ui": "ขวด",
                        "location1": "A-1",
                    }
                ],
            },
            {
                "billno": "TAD6911-002",
                "online_po": "PO2",
                "lines": [
                    {
                        "bcode": "B1",
                        "detail": "สินค้า A",
                        "qty": 3,
                        "ui": "ขวด",
                        "location1": "A-1",
                    }
                ],
            },
        ]
    )
    assert "จำนวนออเดอร์" in html
    assert "PO1" in html
    assert "PO2" in html
    assert "PO1: 2" in html
    assert "PO2: 3" in html
    assert "TAD6911-001" not in html
    assert ">5<" in html or ">5</td>" in html


def test_line_mtp_resolves_large_unit():
    from src.online_sale.writers.tad_simas import _line_mtp, _stock_units

    product = {"UI1": "หลอด", "UI2": "ลัง", "MTP2": 20}
    assert _line_mtp(product, "ลัง") == 20
    assert _line_mtp(product, "หลอด") == 1
    assert _stock_units(2, 20) == 40


def test_tad_sheet_matches_cntad_meta_layout():
    from src.online_sale.sheets.tad import render_tad_sheet

    html = render_tad_sheet(
        {
            "billno": "TAD6911-001",
            "bill_date": "2026-11-02",
            "acctname": "คุณลูกค้าทั่วไป TIKTOK (ICE TIKTOK SHOP)",
            "customer_name": "คุณลูกค้าทั่วไป TIKTOK (ICE TIKTOK SHOP)",
            "customer_address": "305 หมู่1 ต.ชุมแสง อ.วังจันทร์ จ.ระยอง 21210",
            "customer_tax_id": "0000000000002",
            "platform": "tiktok",
            "shop_name": "ICE TIKTOK SHOP",
            "online_po": "913101322028564",
            "issuer_label": "ปิยะนุช นันตาบุตร (เมย์)",
            "lines": [
                {
                    "bcode": "30050024",
                    "detail": "สีส้ม",
                    "price": 360,
                    "qty": 1,
                    "ui": "หน่วย",
                    "amount": 360,
                }
            ],
        }
    )
    assert "ใบกำกับภาษีอย่างย่อ/ใบส่งสินค้า" in html
    assert "class='side'" in html
    assert "ลูกค้า:" in html
    assert "คุณลูกค้าทั่วไป TIKTOK" in html
    assert "ICE TIKTOK SHOP)" not in html.split("ลูกค้า:")[1].split("</div>")[0]
    assert "ที่อยู่:" in html
    assert "เลขประจำตัวผู้เสียภาษี:" in html
    assert "0000000000002" in html
    assert "ช่องทาง:" in html
    assert "TikTok (ICE TIKTOK SHOP)" in html
    assert "เลขคำสั่งซื้อ:" in html
    assert "913101322028564" in html
    assert "แพลตฟอร์ม" not in html
    assert "ชื่อร้านค้า" not in html
    assert "ยอดก่อน VAT" in html
    assert "พนักงานขาย:" in html


def test_staff_roster_and_cntad_signers():
    assert match_staff("เมย์")["full_name"] == "ปิยะนุช นันตาบุตร"
    assert issuer_full_name("Nu") == "อานนท์ ชูสวัสดิ์ (นุ)"
    assert issuer_full_name("Boss") == "สุริยะ โกศัลยกุล (บอส)"
    # POS SALE stamps on older CNTAD/TAD.
    assert issuer_full_name("MIAW") == "ธนวรรณ เดชกุญชร (มะเหมี่ยว)"
    assert issuer_full_name("MIAW ICE") == "ธนวรรณ เดชกุญชร (มะเหมี่ยว)"
    assert issuer_full_name("AUM SPNT") == "จิตติมา ทิมเทศ (อุ้ม)"
    assert issuer_full_name("peung") == "นฤมล วิทยผโลทัย (ผึ้ง)"
    assert issuer_full_name("PHU Nattapon W.") == "ณัฐพล วิทยผโลทัย (ภู่)"
    assert issuer_full_name("January Ice") == "มกรา มณีกุล (ไอซ์)"
    html = render_cntad_sheet(
        {
            "billno": "CNTAD6911-001",
            "bill_date": "2026-11-15",
            "sale": "เมย์",
            "acctname": "ลูกค้า",
            "customer_name": "คุณลูกค้าทั่วไป LAZADA ( PNT TRACTOR)",
            "customer_address": "ที่อยู่ทดสอบ",
            "customer_tax_id": "0000000000001",
            "tad_billno": "TAD6910-611",
            "tad_bill_date": "2026-10-23",
            "platform": "lazada",
            "shop_name": "PNT TRACTOR",
            "order_id": "33210966075295",
            "reason": "คืนสินค้า",
            "lines": [],
            "beforetax": 0,
            "aftertax": 0,
            "tax": 0,
        }
    )
    assert "ผู้ออกเอกสาร" in html
    assert "ผู้อนุมัติเอกสาร" in html
    assert "ผู้รับเอกสาร" in html
    assert "ปิยะนุช นันตาบุตร (เมย์)" in html
    assert "ลูกค้า:" in html
    assert "คุณลูกค้าทั่วไป LAZADA" in html
    assert "PNT TRACTOR)" not in html.split("ลูกค้า:")[1].split("</div>")[0]
    assert "ที่อยู่:" in html
    assert "ที่อยู่ทดสอบ" in html
    assert "เลขประจำตัวผู้เสียภาษี:" in html
    assert "0000000000001" in html
    assert "เลขที่:" in html
    assert "CNTAD6911-001" in html
    assert "อ้างอิง:" in html
    assert "TAD6910-611" in html
    assert "วันที่บิลอ้างอิง:" in html
    assert "ช่องทาง:" in html
    assert "Lazada (PNT TRACTOR)" in html
    assert "แพลตฟอร์ม" not in html
    assert "ชื่อร้านค้า" not in html
    assert "เลขคำสั่งซื้อ:" in html
    assert "33210966075295" in html
    assert "เหตุผลที่ออกใบลดหนี้" in html
    assert "คืนสินค้า" in html
    assert "มูลค่าตามใบกำกับภาษีเดิม (ก่อน VAT)" in html
    assert "มูลค่าที่ถูกต้อง (ก่อน VAT)" in html
    assert "ผลต่างที่ลดหนี้ (ก่อน VAT)" in html
    # Single money summary — no duplicate totals_block.
    assert html.count("รวมยอดลดหนี้ (รวม VAT)") == 1
    assert "ยอดก่อน VAT" not in html


def test_credit_note_summary_full_and_partial_return():
    original = {"beforetax": 1841.12, "tax": 128.88, "aftertax": 1970.00}

    full = credit_note_summary(
        {"beforetax": -1841.12, "tax": -128.88, "aftertax": -1970.00, "lines": []},
        original,
    )
    assert full["original_before"] == Decimal("1841.12")
    assert full["credit_before"] == Decimal("1841.12")
    assert full["correct_before"] == Decimal("0.00")
    assert full["credit_tax"] == Decimal("128.88")
    assert full["credit_after"] == Decimal("1970.00")

    # Partial: return one inclusive line of 720 from a 1970 bill.
    partial = credit_note_summary(
        {
            "beforetax": -672.90,
            "tax": -47.10,
            "aftertax": -720.00,
            "lines": [{"amount": -720}],
        },
        original,
    )
    assert partial["original_before"] == Decimal("1841.12")
    assert partial["credit_before"] == Decimal("672.90")
    assert partial["correct_before"] == Decimal("1168.22")
    assert partial["credit_tax"] == Decimal("47.10")
    assert partial["credit_after"] == Decimal("720.00")

    # Live-shaped partial sample: TAD 6500 / CNTAD 4875.
    live = credit_note_summary(
        {"beforetax": -4556.07, "tax": -318.93, "aftertax": -4875.00, "lines": []},
        {"beforetax": 6074.77, "tax": 425.23, "aftertax": 6500.00},
    )
    assert live["correct_before"] == Decimal("1518.70")


def test_update_tad_validation():
    with pytest.raises(OnlineSaleError, match="TAD"):
        update_tad(
            billno="CNTAD6911-001",
            acctno="7LAZ1",
            acctname="คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)",
            online_po="1234567890123456",
            remarks="##0000000000001",
            operator="tester",
            lines=[{"bcode": "A", "qty": 1, "price": 10}],
        )
    with pytest.raises(OnlineSaleError, match="อย่างน้อย"):
        update_tad(
            billno="TAD6911-001",
            acctno="7LAZ1",
            acctname="คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)",
            online_po="1234567890123456",
            remarks="##0000000000001",
            operator="tester",
            lines=[],
        )


def test_private_lan():
    assert is_private_lan("127.0.0.1")
    assert is_private_lan("192.168.1.2")
    assert not is_private_lan("8.8.8.8")


def test_online_po_length_by_platform():
    assert validate_online_po("shopee", "12345678901234") == "12345678901234"
    assert validate_online_po("lazada", "1234567890123456") == "1234567890123456"
    assert validate_online_po("tiktok", "123456789012345678") == "123456789012345678"
    # Always string — numeric inputs must not lose precision / leading zeros.
    assert validate_online_po("shopee", 12345678901234) == "12345678901234"
    with pytest.raises(OnlineSaleError, match="14"):
        validate_online_po("shopee", "1234567890123")
    with pytest.raises(OnlineSaleError, match="16"):
        validate_online_po("lazada", "123456789012345")
    with pytest.raises(OnlineSaleError, match="18"):
        validate_online_po("tiktok", "12345678901234567")


def test_post_tad_validation():
    with pytest.raises(OnlineSaleError, match="อย่างน้อย"):
        post_tad(
            acctno="7LAZ1",
            acctname="คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)",
            online_po="1234567890123456",
            remarks="##0000000000001",
            operator="tester",
            lines=[],
        )
    with pytest.raises(OnlineSaleError, match="16"):
        post_tad(
            acctno="7LAZ1",
            acctname="คุณลูกค้าทั่วไป LAZADA (KC INDUSTRY)",
            online_po="123456789012345",
            remarks="##0000000000001",
            operator="tester",
            lines=[{"bcode": "A", "qty": 1, "price": 10}],
        )


@patch("src.online_sale.service.draft_store.find_duplicate_draft_po", return_value=[])
@patch(
    "src.online_sale.service.parts9.find_duplicate_po",
    return_value=[{"billno": "TAD6911-001", "bill_date": "2026-11-27", "online_po": "1234567890123456"}],
)
def test_check_po_duplicate_is_warning_only(mock_find_po, mock_find_draft):
    from src.online_sale.service import check_po_payload

    out = check_po_payload("7LAZ1", "1234567890123456", platform="lazada")
    assert out["ok"] is True
    assert out["duplicates"][0]["billno"] == "TAD6911-001"
    assert out["warning"]
    assert "TAD6911-001" in out["warning"]
    mock_find_po.assert_called_once()
    mock_find_draft.assert_called_once()


@patch("src.online_sale.writers.tad_simas._fetch_icmas_row")
@patch("src.online_sale.writers.tad_simas.writer_engine_for_branch")
def test_post_tad_allows_duplicate_po_but_blocks_stock(mock_engine, mock_icmas):
    mock_conn = MagicMock()
    # Next billno lookup may return an existing max seq; stock check uses ICMAS mock.
    mock_conn.execute.return_value.mappings.return_value.first.return_value = {
        "max_seq": 1
    }

    @contextmanager
    def fake_begin():
        yield mock_conn

    mock_engine.return_value.begin = fake_begin
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
            online_po="1234567890123456",
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

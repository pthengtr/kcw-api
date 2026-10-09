from datetime import date

import pytest

from src.hq_po.guards import HqPoError
from src.hq_po.sheet import build_sheet_forms


def _forms(monkeypatch, groups):
    from src.hq_po import iclow_read

    def cards(acctnos):
        assert "SM" in acctnos
        return {
            "SM": {
                "acctno": "SM",
                "name": "บริษัท ส.มิตรอะไหล่ยาง (1985) จำกัด",
                "addr1": "สำนักงานใหญ่",
                "addr2": "กรุงเทพฯ",
                "phone": "02-2215865",
                "tax_id": "0105530000000",
                "fax": "02-2243659",
                "contact": "คุณสมชาย",
                "term": "30",
            }
        }

    def products(bcodes):
        assert "13051964" in bcodes
        return {
            "13051964": {
                "descr": "ยางปูพื้นรถ เล็ก ลายสี่เหลี่ยม",
                "model": "RF",
                "brand": "SMA",
                "pcode": "RF008",
                "mcode": "RF008",
                "ui": "แผ่น",
                "costlast": 45,
                "costnet": 40,
            },
            "13050473": {
                "descr": "ยางปูพื้นลาดหน้า ลายใหญ่",
                "model": "Grande",
                "brand": "Grande",
                "pcode": "RF001",
                "mcode": "RF001",
                "ui": "คู่",
                "costlast": 178,
                "costnet": None,
            },
        }

    monkeypatch.setattr(iclow_read, "fetch_vendor_cards", cards)
    monkeypatch.setattr(iclow_read, "fetch_sheet_products", products)
    return build_sheet_forms(groups)


def test_simple_sheet_includes_vendor_and_part_columns(monkeypatch):
    forms = _forms(
        monkeypatch,
        [
            {
                "vendor": "SM",
                "docno": "",
                "docdate": "2026-10-09",
                "lines": [
                    {"bcode": "13051964", "qty": 6, "ui": "แผ่น"},
                    {"bcode": "13050473", "qty": 5, "ui": "คู่"},
                ],
            }
        ],
    )
    simple = forms["simple_html"]
    text = forms["simple_text"]
    for blob in (simple, text):
        assert "ผู้ขาย / SUPPLIER" in blob
        assert "บริษัท ส.มิตรอะไหล่ยาง (1985) จำกัด" in blob
        assert "02-2215865" in blob
        assert "02-2243659" in blob
        assert "0105530000000" in blob
        assert "คุณสมชาย" in blob
        assert "สำนักงานใหญ่ กรุงเทพฯ" in blob
        assert "เลขประจำตัวผู้เสียภาษี" in blob
        assert "NO.1" in blob
        assert "NO.2" in blob
        assert "RF008" in blob
        assert "ยี่ห้อ" in blob
        assert "ราคา/หน่วย" in blob
        assert "9 ตุลาคม 2026" in blob
    assert "45.-" in simple or "45.00" in simple
    assert "178.-" in text


def test_full_sheet_matches_purchase_order_totals(monkeypatch):
    forms = _forms(
        monkeypatch,
        [
            {
                "vendor": "SM",
                "vendor_name": "ชื่อที่ส่งมา",
                "docno": "PO6910-0171",
                "docdate": "2026-10-09",
                "lines": [
                    {"bcode": "13051964", "qty": 6},
                    {"bcode": "13050473", "qty": 5},
                ],
            }
        ],
    )
    full = forms["full_html"]
    text = forms["full_text"]
    for blob in (full, text):
        assert "ใบสั่งซื้อ" in blob
        assert "PURCHASE ORDER" in blob
        assert "PO6910-0171" in blob
        assert "09/10/2026" in blob
        assert "บริษัท เกียรติชัยอะไหล่ยนต์ 2007 จำกัด" in blob
        assert "ผู้ขาย / SUPPLIER" in blob
        assert "เลขประจำตัวผู้เสียภาษี" in blob
        assert "1,160.00" in blob
        assert "81.20" in blob
        assert "1,241.20" in blob
        assert "หนึ่งพันสองร้อยสี่สิบเอ็ดบาทยี่สิบสตางค์" in blob
        assert "ผู้ขายยืนยันรับคำสั่งซื้อ" in blob or "ผู้ขายยืนยันรับคำสั่งซื้อ" in text
    assert "ยอดสุทธิ" in full
    assert "ภาษีมูลค่าเพิ่ม 7%" in full
    assert "เครดิต 30 วัน" in full
    assert "ชื่อที่ส่งมา" not in full


def test_sheet_keeps_vendor_labels_when_card_is_missing(monkeypatch):
    from src.hq_po import iclow_read

    monkeypatch.setattr(iclow_read, "fetch_vendor_cards", lambda _codes: {})
    monkeypatch.setattr(iclow_read, "fetch_sheet_products", lambda _codes: {})
    forms = build_sheet_forms(
        [
            {
                "vendor": "V9",
                "vendor_name": "ร้านทดสอบ",
                "docdate": date(2026, 10, 8).isoformat(),
                "lines": [{"bcode": "30050719", "descr": "ลูกปืนคลัช", "qty": 10, "ui": "หน่วย"}],
            }
        ]
    )
    simple = forms["simple_text"]
    assert "ร้านทดสอบ" in simple
    assert "รหัสเจ้าหนี้: V9" in simple
    assert "ที่อยู่: —" in simple
    assert "โทรศัพท์: —" in simple
    assert "เลขประจำตัวผู้เสียภาษี: —" in simple
    assert "ผู้ติดต่อ: —" in simple
    assert "ลูกปืนคลัช" in simple
    assert "ยังไม่ออกเลข" in simple


def test_sheet_rejects_empty_lines():
    with pytest.raises(HqPoError) as caught:
        build_sheet_forms([{"vendor": "V1", "lines": [{"bcode": "A", "qty": 0}]}])
    assert caught.value.code == "empty"

from unittest.mock import patch

from fastapi.testclient import TestClient

from src.transfer.sticker import (
    BARCODE_HEIGHT_MM,
    BARCODE_LEFT_MM,
    FOOT_H_MM,
    LABEL_HEIGHT_MM,
    LABEL_PAD_MM,
    LABEL_WIDTH_MM,
    StickerLabel,
    build_batch_tspl,
    build_label_tspl,
    clamp_sticker_qty,
    count_copies,
    decode_price_letters,
    encode_price_digits,
    format_footer_line,
    format_header_line,
    format_meta_line,
    format_price_code,
    format_unit_line,
    is_lan_printer_host,
    label_from_icmas,
    normalize_printer_model,
    normalize_site,
    page_width_mm,
    printer_profile,
    render_label_image,
    render_label_png,
    resolve_sticker_labels,
    sticker_config_payload,
    sticker_name_lines,
    validate_batch,
    _image_to_bitmap_bytes,
)
from src.transfer.ui import page


SAMPLE = StickerLabel(
    bcode="12052328",
    descr="ชุดยางไฮปั๊มขาว",
    location="14F-5-2.2",
    brand="นอกแท้",
    unit="ชุด",
    company="7MCP",
    model="F/6600",
    factory_no="SK0013",
    genuine_no="EDPN500B",
    price_code="OTSMXLTM",
    site="HQ",
    qty=3,
)


def test_price_cipher_matches_shop_legend():
    assert encode_price_digits(270) == "TSM"
    assert encode_price_digits(420) == "LTM"
    assert encode_price_digits("1,250") == "PTBM"
    assert decode_price_letters("TSM") == 270
    assert decode_price_letters("LTM") == 420
    assert format_price_code(cost=270, sell=420) == "OTSMXLTM"
    assert format_price_code(cost=270) == "OTSM"
    assert format_price_code(sell=420) == "XLTM"
    assert format_price_code() == ""


def test_printer_model_aliases():
    assert normalize_printer_model("TE310") == "te310"
    assert normalize_printer_model("244 Pro") == "ttp244pro"
    assert normalize_printer_model("ttp-244-pro") == "ttp244pro"
    assert normalize_printer_model("unknown") == "te310"


def test_label_from_icmas_and_qty_merge():
    row = {
        "BCODE": "12052328",
        "DESCR": "ชุดยางไฮปั๊มขาว",
        "LOCATION1": "14F-5-2.2",
        "BRAND": "นอกแท้",
        "UI1": "ชุด",
        "VENDOR": "7MCP",
        "MODEL": "F/6600",
        "MCODE": "SK0013",
        "PCODE": "EDPN500B",
        "COSTNET": 270,
        "PRICE1": 420,
    }
    label = label_from_icmas(row, qty=4, site="HQ")
    assert label.price_code == "OTSMXLTM"
    assert label.location == "14F-5-2.2"
    assert label.abbreviation == ""
    assert label.factory_no == "SK0013"
    assert label.genuine_no == "EDPN500B"
    assert label.site == "HQ"
    merged = resolve_sticker_labels(
        [
            {"bcode": "12052328", "qty": 2, "descr": "ชุดยางไฮปั๊มขาว"},
            {"bcode": "12052328", "qty_receive": 3},
            {"bcode": "999", "qty": 0},
        ],
        {"12052328": row},
        site="SYP",
    )
    assert len(merged) == 1
    assert merged[0].qty == 5
    assert merged[0].price_code == "OTSMXLTM"
    assert merged[0].site == "SYP"


def test_qty_caps_and_validate():
    assert clamp_sticker_qty(3.6) == 4
    assert clamp_sticker_qty(-2) == 0
    assert clamp_sticker_qty(9999) == 200
    assert validate_batch([]) == "ไม่มีรายการที่เลือกพิมพ์"
    labels = [SAMPLE]
    assert validate_batch(labels) is None
    assert count_copies(labels) == 3


def test_lan_printer_host_guard():
    assert is_lan_printer_host("127.0.0.1")
    assert is_lan_printer_host("192.168.1.50")
    assert is_lan_printer_host("10.0.0.8")
    assert is_lan_printer_host("100.94.98.18")
    assert is_lan_printer_host("syp-label-printer")
    assert not is_lan_printer_host("8.8.8.8")
    assert not is_lan_printer_host("example.com/x")
    assert not is_lan_printer_host("http://192.168.1.50")
    assert not is_lan_printer_host("")


SHOP_REF = StickerLabel(
    bcode="13010754",
    descr="30 มิล เหล็ก ตาน้ำถ้วย",
    location="19P-1-3",
    brand="SAK",
    unit="ตนถ",
    factory_no="SAK-03010",
    price_code="OPMXTM2605",
    qty=2,
)


def test_unit_line_matches_shop_prefix():
    assert format_unit_line("ตนถ") == "หน่วย ตนถ"
    assert format_unit_line("ชุด") == "หน่วย ชุด"
    assert format_unit_line("หน่วย ชุด") == "หน่วย ชุด"
    assert format_unit_line("  ") == ""


def test_layout_line_helpers():
    assert normalize_site("hq") == "HQ"
    assert normalize_site("syp") == "SYP"
    assert normalize_site("other") == ""
    assert format_header_line("14F-5-2.2", "HQ") == "14F-5-2.2 | HQ SYP"
    assert format_header_line("14F-5-2.2", "") == "14F-5-2.2 | HQ SYP"
    assert format_header_line("", "syp") == "HQ SYP"
    assert format_header_line("19P-1-3", "SYP") == "19P-1-3 | HQ SYP"
    assert format_meta_line("นอกแท้", "ชุด", "7MCP") == "นอกแท้ • ชุด • 7MCP"
    assert format_meta_line("นอกแท้", "", "") == "นอกแท้"
    assert format_footer_line("SK0013", "EDPN500B", "OTSMXLTM") == "SK0013 | EDPN500B | OTSMXLTM"
    assert format_footer_line("", "", "ONMMMMMM") == "ONMMMMMM"
    assert SAMPLE.as_preview_dict()["site"] == "HQ"


def test_name_uses_full_width():
    assert sticker_name_lines(SAMPLE.descr, printer_model="te310") == [SAMPLE.descr]
    assert sticker_name_lines(SAMPLE.descr, printer_model="ttp244pro") == [SAMPLE.descr]
    # Shop-era wrap ("30 มิล เหล็ก" / "ตาน้ำถ้วย") is gone — name is full width.
    assert sticker_name_lines(SHOP_REF.descr, printer_model="te310") == [SHOP_REF.descr]
    long_name = "สายพานหน้าเครื่องปรับอากาศรถยนต์รุ่นพิเศษยาวมากเกินหนึ่งบรรทัด"
    lines = sticker_name_lines(long_name, printer_model="te310")
    assert 1 <= len(lines) <= 2
    assert all(lines)


def test_shop_reference_label_renders():
    img = render_label_image(SHOP_REF, printer_model="te310")
    assert img.size == (600, 420)
    # Ink in the top-right barcode band and bottom-left factory code.
    px = img.load()
    barcode_x = int(600 * BARCODE_LEFT_MM / LABEL_WIDTH_MM) + 8
    assert any(px[x, y] == 0 for x in range(barcode_x, 580) for y in range(20, 140))
    assert any(px[x, y] == 0 for x in range(10, 140) for y in range(330, 415))


def test_tspl_job_uses_received_qty_and_label_size():
    # qty=3 on 2-across → one full row (PRINT 1,1) + one leftover (PRINT 1,1)
    raw = build_label_tspl(SAMPLE, printer_model="te310")
    assert b"SIZE 102 mm,35 mm" in raw
    assert b"GAP 2 mm,0 mm" in raw
    assert b"BITMAP 0,0," in raw
    assert raw.count(b"PRINT 1,") == 2
    assert b"PRINT 1,1" in raw
    batch = build_batch_tspl(
        [SAMPLE, StickerLabel(bcode="22010585", descr="test", qty=2)],
        printer_model="te310",
    )
    # SAMPLE qty=3 → 2 pages; qty=2 → 1 page (one full pair)
    assert batch.count(b"PRINT 1,") == 3
    assert b"SIZE 102 mm,35 mm" in batch


def test_244_pro_two_up_and_inverted_bitmap():
    from PIL import Image

    assert page_width_mm(printer_profile("ttp244pro")) == 102.0
    assert page_width_mm(printer_profile("te310")) == 102.0
    assert printer_profile("ttp244pro")["invert_bitmap"] is True
    assert printer_profile("te310")["invert_bitmap"] is True
    assert printer_profile("ttp244pro")["columns"] == 2
    assert printer_profile("te310")["columns"] == 2

    white = Image.new("1", (8, 1), 1)
    _, _, raw = _image_to_bitmap_bytes(white, invert=False)
    _, _, flipped = _image_to_bitmap_bytes(white, invert=True)
    assert raw == b"\x00"
    assert flipped == b"\xff"

    pair = build_label_tspl(SHOP_REF, printer_model="ttp244pro")  # qty=2
    assert b"SIZE 102 mm,35 mm" in pair
    assert b"REM kcw_tspl_bit0_prints" in pair
    assert pair.count(b"PRINT 1,") == 1
    assert b"PRINT 1,1" in pair

    odd = build_label_tspl(SAMPLE, printer_model="ttp244pro")  # qty=3
    assert odd.count(b"SIZE 102 mm,35 mm") == 2
    assert odd.count(b"PRINT 1,") == 2
    assert b"PRINT 1,1" in odd

    # TE310 uses the same 2-across stock + 0=printed polarity as 244 Pro.
    te = build_label_tspl(SHOP_REF, printer_model="te310")  # qty=2
    assert b"SIZE 102 mm,35 mm" in te
    assert b"SIZE 50 mm,35 mm" not in te
    assert b"REM kcw_tspl_bit0_prints" in te
    assert te.count(b"PRINT 1,") == 1
    assert b"PRINT 1,1" in te


def test_price_lives_in_footer_not_on_barcode():
    short = StickerLabel(
        bcode="70010300",
        descr="เทิร์นแบตเก่า (300.-)",
        unit="ลูก",
        company="KCW1",
        model="N50 , DIN LN 3",
        price_code="ONMMMMMM",
        site="HQ",
        qty=1,
    )
    img = render_label_image(short, printer_model="ttp244pro")
    dots_mm = 8
    barcode_top = int(round(LABEL_PAD_MM * dots_mm))
    barcode_bottom = barcode_top + int(round(BARCODE_HEIGHT_MM * dots_mm))
    barcode_left = int(round(BARCODE_LEFT_MM * dots_mm))
    footer_top = img.height - int(round(FOOT_H_MM * dots_mm))
    px = img.load()
    assert any(
        px[x, y] == 0
        for y in range(barcode_top, barcode_bottom)
        for x in range(barcode_left, img.width - 6)
    )
    assert any(
        px[x, y] == 0
        for y in range(footer_top + 4, img.height - 2)
        for x in range(6, img.width - 6)
    )


def test_render_label_native_dpi():
    te = render_label_image(SAMPLE, printer_model="te310")
    pro = render_label_image(SAMPLE, printer_model="ttp244pro")
    assert te.size == (600, 420)  # 50×35 mm at 12 dot/mm
    assert pro.size == (400, 280)  # 50×35 mm at 8 dot/mm
    png = render_label_png(SAMPLE, printer_model="te310")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    cfg = sticker_config_payload(model="244 Pro", host="192.168.1.50")
    assert cfg["default_model"] == "ttp244pro"
    assert cfg["label_width_mm"] == LABEL_WIDTH_MM
    assert cfg["label_height_mm"] == LABEL_HEIGHT_MM


def test_transfer_page_has_sticker_print_flow():
    html = page(user_name="ทดสอบ", site="SYP", sticker_printer_model="te310")
    assert "openStickerPrint" in html
    assert "openStickerPrintFromTransfer" in html
    assert "renderStickerComposer" in html
    assert "downloadStickerPrn" in html
    assert "printStickersBrowser" not in html
    assert "fireStickerWindowPrint" not in html
    assert "busyDepth" in html
    assert "reuseSuggest" in html
    assert "lastPreviewKey" in html
    assert "visibleDualPane" in html
    assert "stkSelectedCount" in html
    assert "chkPrintStickers" in html
    assert "พิมพ์สติ๊กเกอร์บาร์โค้ด" in html
    assert "data-stickers=" in html
    assert "พิมพ์บาร์โค้ดที่เลือก" in html
    assert "เลือกสินค้าทั้งหมด" in html
    assert ">บาร์โค้ด<" in html
    assert 'view==="stickers"' in html
    assert "/transfer/api/stickers/preview" in html
    assert "/transfer/api/stickers/print" in html
    assert "TSC TE310" in html
    assert "244 Pro" in html
    assert "2 คอลัมน์" in html
    assert "1 ชิ้น = 1 ดวง" in html
    assert "stk-prn-helper" in html
    assert "ดาวน์โหลดไฟล์ .prn" in html
    assert "พิมพ์ผ่าน LAN" in html
    assert "รุ่นเครื่องพิมพ์" in html
    assert "stkPrnHelper" in html
    assert "/tools/prn-printer/install.cmd" in html
    assert "ดาวน์โหลดตัวติดตั้ง" in html
    assert 'action:"download"' in html
    assert "print-sticker-mode" not in html
    assert "stk-row" not in html
    assert "101.6mm" not in html
    assert "กดพิมพ์อีกครั้ง" not in html
    assert "stickerPrintPage" not in html
    assert "btnDetailStickers" in html
    assert "เลือกทั้งหมด" in html
    assert "btnStkAll" in html
    assert "kcw-stickers-" in html
    assert 'id="btnStkDownload"' in html
    assert "btnStkPrint" not in html
    # Bill print still uses window.print; sticker flow must not.
    assert "window.print()" in html
    assert "printRequestBill" in html
    assert "left:-10000px" in html

def test_sticker_preview_and_download_api():
    from app.transfer_app import app

    catalog = {
        "12052328": {
            "bcode": "12052328",
            "descr": "ชุดยางไฮปั๊มขาว",
            "brand": "นอกแท้",
            "ui1": "ชุด",
            "vendor": "7MCP",
            "model": "F/6600",
            "location1": "14F-5-2.2",
            "mcode": "SK0013",
            "pcode": "EDPN500B",
            "costnet": 270,
            "price1": 420,
        }
    }

    def _ok_ident(request):
        return object(), None

    with (
        patch("app.routers.transfer._require_api", side_effect=_ok_ident),
        patch("app.routers.transfer.fetch_sticker_catalog", return_value=catalog),
    ):
        client = TestClient(app)
        preview = client.post(
            "/transfer/api/stickers/preview",
            json={"lines": [{"bcode": "12052328", "qty": 4}], "printer_model": "te310"},
        )
        assert preview.status_code == 200
        body = preview.json()
        assert body["copies"] == 4
        assert body["labels"][0]["price_code"] == "OTSMXLTM"
        assert body["labels"][0]["site"] in {"HQ", "SYP"}
        assert body["preview_png_b64"]
        assert body["labels"][0]["preview_png_b64"]
        assert body["labels"][0]["preview_png_b64"] == body["preview_png_b64"]

        all_prev = client.post(
            "/transfer/api/stickers/preview",
            json={
                "lines": [{"bcode": "12052328", "qty": 4}],
                "printer_model": "te310",
                "all_previews": True,
            },
        )
        assert all_prev.status_code == 200
        assert all_prev.json()["labels"][0]["preview_png_b64"]

        prn = client.post(
            "/transfer/api/stickers/print",
            json={
                "lines": [{"bcode": "12052328", "qty": 4}],
                "printer_model": "ttp244pro",
                "action": "download",
            },
        )
        assert prn.status_code == 200
        assert prn.content.startswith(b"SIZE 102 mm,35 mm")
        assert prn.content.count(b"PRINT 1,") == 2
        assert b"PRINT 1,4" not in prn.content
        assert "kcw-stickers.prn" in prn.headers.get("content-disposition", "")


def test_batch_packs_two_single_skus_on_one_row():
    left = StickerLabel(bcode="31050663", descr="ชุดหมุนไดเเมสซี่", location="0M-0-1", qty=1)
    right = StickerLabel(bcode="31050239", descr="ฝาถังโซล่า", location="3M-3-5.1", qty=1)
    raw = build_batch_tspl([left, right], printer_model="te310")
    assert raw.count(b"SIZE 102 mm,35 mm") == 1
    assert raw.count(b"PRINT 1,") == 1
    # 102 mm at 12 dot/mm = 1224 dots → 153 bytes/row
    assert b"BITMAP 0,0,153," in raw

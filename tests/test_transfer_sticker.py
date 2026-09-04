from unittest.mock import patch

from fastapi.testclient import TestClient

from src.transfer.sticker import (
    LABEL_HEIGHT_MM,
    LABEL_WIDTH_MM,
    StickerLabel,
    build_batch_tspl,
    build_label_tspl,
    clamp_sticker_qty,
    count_copies,
    decode_price_letters,
    encode_price_digits,
    format_price_code,
    is_lan_printer_host,
    label_from_icmas,
    normalize_printer_model,
    render_label_image,
    render_label_png,
    resolve_sticker_labels,
    sticker_config_payload,
    validate_batch,
)
from src.transfer.ui import page


SAMPLE = StickerLabel(
    bcode="12052328",
    descr="ชุดยางไฮปั๊มขาว",
    location="14F-5-2.2",
    brand="นอกแท้",
    unit="ชุด",
    abbreviation="ยฮปป",
    company="7MCP",
    model="F/6600",
    factory_no="SK0013",
    genuine_no="EDPN500B",
    price_code="OTSMXLTM",
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
        "ACODE": "ยฮปป",
        "VENDOR": "7MCP",
        "MODEL": "F/6600",
        "MCODE": "SK0013",
        "PCODE": "EDPN500B",
        "COSTNET": 270,
        "PRICE1": 420,
    }
    label = label_from_icmas(row, qty=4)
    assert label.price_code == "OTSMXLTM"
    assert label.location == "14F-5-2.2"
    assert label.abbreviation == "ยฮปป"
    assert label.factory_no == "SK0013"
    assert label.genuine_no == "EDPN500B"
    merged = resolve_sticker_labels(
        [
            {"bcode": "12052328", "qty": 2, "descr": "ชุดยางไฮปั๊มขาว"},
            {"bcode": "12052328", "qty_receive": 3},
            {"bcode": "999", "qty": 0},
        ],
        {"12052328": row},
    )
    assert len(merged) == 1
    assert merged[0].qty == 5
    assert merged[0].price_code == "OTSMXLTM"


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


def test_tspl_job_uses_received_qty_and_label_size():
    raw = build_label_tspl(SAMPLE, printer_model="te310")
    assert raw.startswith(b"SIZE 50 mm,35 mm")
    assert b"GAP 2 mm,0 mm" in raw
    assert b"BITMAP 0,0," in raw
    assert b"PRINT 1,3" in raw
    batch = build_batch_tspl(
        [SAMPLE, StickerLabel(bcode="22010585", descr="test", qty=2)],
        printer_model="ttp244pro",
    )
    assert batch.count(b"PRINT 1,") == 2
    assert b"PRINT 1,2" in batch


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
    assert "printStickersBrowser" in html
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
    assert "1 ชิ้นที่รับ = 1 ดวง" in html
    assert "ตั้งค่าไฟล์พิมพ์" in html
    assert "ดาวน์โหลดไฟล์พิมพ์" in html
    assert "print-stickers" in html
    assert "window.print()" in html
    assert "btnDetailStickers" in html
    assert "เลือกทั้งหมด" in html
    assert "btnStkAll" in html
    assert "kcw-stickers-" in html
    assert 'id="btnStkPrint"' in html
    assert ">พิมพ์<" in html or ">พิมพ์</button>" in html

def test_sticker_preview_and_download_api():
    from app.transfer_app import app

    catalog = {
        "12052328": {
            "bcode": "12052328",
            "descr": "ชุดยางไฮปั๊มขาว",
            "brand": "นอกแท้",
            "ui1": "ชุด",
            "acode": "ยฮปป",
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
        assert body["preview_png_b64"]
        assert body["labels"][0]["preview_png_b64"]
        assert body["labels"][0]["preview_png_b64"] == body["preview_png_b64"]

        prn = client.post(
            "/transfer/api/stickers/print",
            json={
                "lines": [{"bcode": "12052328", "qty": 4}],
                "printer_model": "ttp244pro",
                "action": "download",
            },
        )
        assert prn.status_code == 200
        assert prn.content.startswith(b"SIZE 50 mm,35 mm")
        assert b"PRINT 1,4" in prn.content
        assert "kcw-stickers.prn" in prn.headers.get("content-disposition", "")

from src.handlers.explorer_entry import is_explorer_command
from src.parts9_explorer.net import is_tailscale_cg_nat
from src.parts9_explorer.query import (
    format_size_line,
    infer_doc_kind,
    maybe_document_query,
    parse_query,
    size_labels,
)
from src.parts9_explorer.search import _DOC_SPECS, _pack_doc, product_image_urls
from src.parts9_explorer.config import get_explorer_settings
from src.parts9_explorer.ui import page


def test_parse_code_size_query():
    from src.parts9_explorer.query import code_size_query_valid, parse_code_size_query, parse_query

    seal = parse_code_size_query("ซีล 31×46×7")
    assert seal.code1 == "C"
    assert seal.size1 == "31"
    assert seal.size2 == "46"
    assert seal.size3 == "7"
    assert code_size_query_valid(seal)

    bearing = parse_code_size_query("I นอก 72 หนา 17")
    assert bearing.code1 == "I"
    assert bearing.size2 == "72"
    assert bearing.size3 == "17"
    assert code_size_query_valid(bearing)

    cvjoint = parse_code_size_query("G ปลอก 1 ยาว 24")
    assert cvjoint.code1 == "G"
    assert cvjoint.size1 == "1"
    assert cvjoint.size2 == "24"
    assert cvjoint.size3 is None
    assert code_size_query_valid(cvjoint)

    hose = parse_code_size_query("L หัวสาย 1 NN12 หัวสาย 2 NS17 ยาว 24")
    assert hose.code1 == "L"
    assert hose.size1 == "NN12"
    assert hose.size2 == "NS17"
    assert hose.size3 == "24"
    assert code_size_query_valid(hose)

    oring = parse_code_size_query("O ใน 35 หนา 3")
    assert oring.code1 == "O"
    assert oring.size1 == "35"
    assert oring.size2 == "3"
    assert oring.size3 is None

    prefixed = parse_query("รหัสขนาด C 31 46 7")
    assert prefixed.search_mode == "code_size"
    assert prefixed.code1 == "C"

    assert not code_size_query_valid(parse_code_size_query("ซีล"))


def test_explorer_page_has_code_size_mode():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert 'data-k="code_size"' in html
    assert "รหัส+ขนาด" in html


def test_explorer_page_has_code_size_panel():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert 'id="codeSizePanel"' in html
    assert 'id="code1"' in html
    assert 'id="sizeFields"' in html
    assert 'id="searchBtn"' in html
    assert 'class="search-form"' in html
    assert 'class="search-actions"' in html
    assert "code-size-fields" in html
    assert "buildCodeSizeQuery" in html
    assert "mode-code-size" in html
    assert "resetCodeSizeForm" in html
    assert "--field-h" in html
    assert ">สำนักงานใหญ่</option>" in html
    assert ">สาขาสี่แยกพัฒนา</option>" in html
    assert 'id="searchPanel"' in html
    assert 'id="searchToggle"' in html
    assert "collapseSearchPanelIfMobile" in html
    assert "Live typing must not auto-hide the mobile search panel." in html
    assert "go(null, { collapse: false })" in html
    assert "opts && opts.collapse" in html
    assert '"C": ["ใน", "นอก", "หนา"]' in html
    assert '"C": "ซีล"' in html
    assert "กรอกบางช่องก็ค้นได้" in html


def test_format_size_line_by_code1():
    assert format_size_line("C", "31", "46", "7", compact=True) == "ใน 31 / นอก 46 / หนา 7"
    assert format_size_line("O", "35", "3", None, compact=True) == "ใน 35 / หนา 3"
    assert format_size_line("I", None, "72", "17", compact=True) == "นอก 72 / หนา 17"
    assert format_size_line("C", "", "", "") == ""
    assert "ขนาด:" in format_size_line("C", "31", "46", "7")
    assert size_labels("Q") == ("เตเปอร์", "แกนโต", None)


def test_size_labels_match_icmas_dictionary():
    """SIZE_LABELS A–P must match kcw-docs ICMAS dictionary §7."""
    from src.parts9_explorer.query import CODE1_LABELS, SIZE_LABELS

    dictionary = {
        "A": ("สูง", "กว้าง", None),
        "C": ("ใน", "นอก", "หนา"),
        "D": ("ใน", "นอก", "หนา"),
        "E": ("ใน", "นอก", "หนา"),
        "F": ("ใน", "นอก", "สูง"),
        "G": ("ปลอก", "ยาว", None),
        "I": ("ใน", "นอก", "หนา"),
        "K": ("ยาว(นิ้ว)", "ฟัน", "ขนาดรูเฟือง"),
        "L": ("หัวสาย 1", "หัวสาย 2", "ยาว"),
        "O": ("ใน", "หนา", None),
        "P": ("ใน", "นอก", "สูง"),
    }
    for code, expected in dictionary.items():
        assert code in CODE1_LABELS
        assert SIZE_LABELS[code] == expected


def test_code_size_ui_queries_for_all_dictionary_codes():
    from src.parts9_explorer.query import SIZE_LABELS, code_size_query_valid, parse_code_size_query

    samples = {
        "A": ("10", "20", None),
        "C": ("31", "46", "7"),
        "D": ("20", "30", "5"),
        "E": ("15", "25", "3"),
        "F": ("100", "200", "50"),
        "G": ("1", "24", None),
        "I": ("20", "47", "14"),
        "K": ("10", "22", "100"),
        "L": ("NN12", "NS17", '24"'),
        "O": ("35", "3", None),
        "P": ("50", "60", "80"),
    }
    for code, (v1, v2, v3) in samples.items():
        labels = SIZE_LABELS[code]
        parts = [code]
        for idx, lbl in enumerate(labels):
            val = (v1, v2, v3)[idx]
            if lbl and val is not None:
                parts.extend([lbl, str(val)])
        parsed = parse_code_size_query(" ".join(parts))
        assert parsed.code1 == code
        assert parsed.size1 == v1
        assert parsed.size2 == v2
        assert parsed.size3 == v3
        assert code_size_query_valid(parsed)


def test_explorer_commands():
    assert is_explorer_command("parts9")
    assert is_explorer_command("ค้นหา")
    assert is_explorer_command("สำรวจ")
    assert not is_explorer_command("สินค้า 22010585")
    assert not is_explorer_command("เช็คสต็อก")


def test_tailscale_cgnat():
    assert is_tailscale_cg_nat("100.113.143.97")
    assert is_tailscale_cg_nat("100.64.0.1")
    assert is_tailscale_cg_nat("100.127.255.1")
    assert not is_tailscale_cg_nat("192.168.1.21")
    assert not is_tailscale_cg_nat("100.63.0.1")
    assert not is_tailscale_cg_nat("127.0.0.1")
    assert is_tailscale_cg_nat("fd7a:115c:a1e0::7b3a:8f62")


def test_parse_bcode_and_seal_sizes():
    p = parse_query("22010585")
    assert p.kind == "product"
    assert p.bcode_prefix == "22010585"
    s = parse_query("ซีล 31 46 7")
    assert s.code1 == "C"
    assert s.sizes == ["31", "46", "7"]
    d = parse_query("KCPN6901-12")
    assert d.kind == "document"
    assert d.docno.startswith("KCPN")
    assert d.doc_kind == "pv"
    po = parse_query("PO6905-392")
    assert po.doc_kind == "po"
    assert po.want_product is False
    pi = parse_query("pi 254929")
    assert pi.doc_kind == "pi"
    assert pi.docno == "254929"
    thai = parse_query("ค้างรับ PO6905-392")
    assert thai.doc_kind == "iclow"
    assert infer_doc_kind("8K69-0013225") == "si"
    assert infer_doc_kind("RC6907-001") == "rv"
    note = parse_query("โน้ต 103772300")
    assert note.doc_kind == "pv"
    assert note.docno == "103772300"
    assert parse_query("note BA25656").doc_kind == "pv"
    assert maybe_document_query("103772300")
    assert maybe_document_query("PACO4-260700251")
    assert not maybe_document_query("ซีล 31 46")


def test_product_image_urls(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://example.supabase.co")
    get_explorer_settings.cache_clear()
    urls = product_image_urls("ABC")
    assert urls[0].endswith("/pictures/product/ABC/ABC.jpg")
    get_explorer_settings.cache_clear()


def test_pv_sql_matches_note_and_voucher():
    sql = _DOC_SPECS["pv"]["header"]
    assert "NOTENO" in sql
    assert "VOUCNO" in sql
    assert "NOTENO" in _DOC_SPECS["pi"]["header"]


def test_explorer_page_has_theme_toggle():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert 'id="themeBtn"' in html
    assert 'data-theme' in html
    assert "kcw.parts9.theme" in html
    assert 'html[data-theme="light"]' in html
    assert 'html[data-theme="dark"]' in html


def test_parse_oem_mcode_and_code1():
    oem = parse_query("12371-0L040")
    assert oem.kind == "product"
    assert oem.want_product is True
    assert oem.bcode_prefix is None
    assert oem.text_terms == ["12371-0L040"]

    mfr = parse_query("ME201571")
    assert mfr.kind == "product"
    assert mfr.want_product is True
    assert mfr.text_terms == ["ME201571"]

    labeled = parse_query("oem 90915-YZZD3")
    assert labeled.kind == "product"
    assert labeled.text_terms == ["90915-YZZD3"]
    assert parse_query("mcode MD075760").text_terms == ["MD075760"]
    assert parse_query("เบอร์แท้ 12371-0L040").text_terms == ["12371-0L040"]

    assert parse_query("I").code1 == "I"
    assert parse_query("K").code1 == "K"
    assert parse_query("code1 I").code1 == "I"
    assert parse_query("ประเภท K").code1 == "K"
    combo = parse_query("I 6201")
    assert combo.kind == "product"
    assert combo.code1 == "I"
    assert combo.sizes == ["6201"]

    # Known bill prefixes stay documents
    assert parse_query("KCPN6901-12").kind == "document"
    assert parse_query("PO6905-392").want_product is False


def test_product_search_matches_pcode_mcode_and_code1():
    from src.parts9_explorer.search import _term_match_sql

    sql = _term_match_sql("t0")
    assert "PCODE LIKE :t0" in sql
    assert "MCODE LIKE :t0" in sql
    assert "ACODE LIKE :t0" in sql
    assert "CODE1" in sql
    sized = _term_match_sql("sz1", include_size_slot=1)
    assert "SIZE1" in sized
    assert "PCODE LIKE :sz1" in sized


def test_product_search_includes_acode_column():
    from src.parts9_explorer.search import PRODUCT_COLS

    assert "ACODE" in PRODUCT_COLS


def test_serialize_product_includes_acode():
    from src.parts9_explorer.search import _serialize_product

    row = {
        "BCODE": "15001234",
        "DESCR": "ลูกปืน",
        "PCODE": "",
        "MCODE": "",
        "BRAND": "",
        "MODEL": "",
        "ACODE": "ลป",
        "CODE1": "I",
        "SIZE1": "20",
        "SIZE2": "47",
        "SIZE3": "14",
        "UI1": "ลูก",
        "UI2": "",
        "MTP2": None,
        "QTYOH2": 5,
        "QTYMIN": 0,
        "LOCATION1": "13P-4-13",
        "LOCATION2": "B",
        "CANCELED": "N",
    }
    out = _serialize_product(row, site="hq")
    assert out["acode"] == "ลป"
    assert out["location1"] == "13P-4-13"
    assert out["location2"] == "B"
    assert out["location"] == "13P-4-13 / B"
    assert out["location_hq"] == "13P-4-13 / B"
    assert out["location_syp"] == ""


def test_enrich_with_peer_location_fills_other_site(monkeypatch):
    from src.parts9_explorer import search as search_mod

    products = [
        {
            "bcode": "01010023",
            "location": "13P-4-13",
            "qtyoh2": 6.0,
        }
    ]
    monkeypatch.setattr(
        search_mod,
        "_fetch_peer_locations",
        lambda bcodes, *, peer: {
            "01010023": {
                "location1": "T0-4-4",
                "location2": "",
                "location": "T0-4-4",
                "qtyoh2": 3.0,
            }
        },
    )
    out = search_mod._enrich_with_peer_location(products, site="hq")
    assert out[0]["location_hq"] == "13P-4-13"
    assert out[0]["location_syp"] == "T0-4-4"
    assert out[0]["qtyoh2_hq"] == 6.0
    assert out[0]["qtyoh2_syp"] == 3.0


def test_explorer_page_shows_location_bits():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True}, "syp": {}})
    assert "function locBits(p)" in html
    assert "locBits(p)" in html
    assert "ที่เก็บ สนญ" in html
    assert "location_hq" in html
    assert "location_syp" in html


def test_search_products_applies_category_filter(monkeypatch):
    from sqlalchemy import text

    from src.parts9_explorer.search import search_products

    captured: dict = {}

    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params):
            captured["sql"] = str(sql)
            captured["params"] = dict(params)
            return FakeResult()

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(
        "src.parts9_explorer.search.get_site_engine",
        lambda site: FakeEngine(),
    )
    search_products("6207", site="hq", category="15")
    assert "LEFT(LTRIM(RTRIM(BCODE)), 2) = :category" in captured["sql"]
    assert captured["params"]["category"] == "15"


def test_search_products_sort_by_price_and_bcode(monkeypatch):
    from src.parts9_explorer.search import search_products

    captured: dict = {}

    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params):
            captured["sql"] = str(sql)
            captured["params"] = dict(params)
            return FakeResult()

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(
        "src.parts9_explorer.search.get_site_engine",
        lambda site: FakeEngine(),
    )
    search_products("6207", site="hq", sort="price")
    assert "PRICE1" in captured["sql"]
    assert "ISNUMERIC" in captured["sql"]
    assert "TRY_CONVERT" not in captured["sql"]
    assert "ASC" in captured["sql"]
    assert "exact" not in captured["params"]

    search_products("6207", site="hq", sort="bcode_desc")
    assert "ORDER BY BCODE DESC" in captured["sql"]

    search_products("6207", site="hq", sort="relevance")
    assert ":exact" in captured["sql"]
    assert captured["params"]["exact"] == "6207"


def test_product_order_sql_keys():
    from src.parts9_explorer.search import PRODUCT_SORT_KEYS, _product_order_sql

    assert "price" in PRODUCT_SORT_KEYS
    assert "bcode" in PRODUCT_SORT_KEYS
    sql, needs = _product_order_sql("price_desc")
    assert "DESC" in sql
    assert "ISNUMERIC" in sql
    assert "TRY_CONVERT" not in sql
    assert needs is False
    sql, needs = _product_order_sql("bogus")
    assert needs is True
    assert ":exact" in sql


def test_search_products_ignores_invalid_category(monkeypatch):
    from src.parts9_explorer.search import search_products

    captured: dict = {}

    class FakeResult:
        def mappings(self):
            return self

        def all(self):
            return []

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def execute(self, sql, params):
            captured["sql"] = str(sql)
            captured["params"] = dict(params)
            return FakeResult()

    class FakeEngine:
        def connect(self):
            return FakeConn()

    monkeypatch.setattr(
        "src.parts9_explorer.search.get_site_engine",
        lambda site: FakeEngine(),
    )
    search_products("6207", site="hq", category="99")
    assert "category" not in captured["params"]


def test_explorer_page_has_category_select():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert 'id="category"' in html
    assert 'id="categoryField"' in html
    assert "initCategorySelect" in html
    assert "mode-product" in html
    assert "isProductMode" in html
    assert '"15": "ลูกปืน"' in html
    assert "ชื่อย่อ" in html
    assert "นมฮPT" in html


def test_explorer_page_has_sort_select():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert 'id="sort"' in html
    assert 'id="sortField"' in html
    assert 'id="productFilters"' in html
    assert 'value="price"' in html
    assert 'value="bcode"' in html
    assert "เรียงตาม" in html
    assert "SORT_LABELS" in html
    assert "&sort=" in html


def test_explorer_page_mentions_oem_and_code1():
    html = page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})
    assert "เบอร์แท้" in html
    assert "เบอร์โรงงาน" in html
    assert "PCODE" in html
    assert "MCODE" in html
    assert "p.model" in html
    assert "function sizeBits" in html


def test_pack_note_only_pv_uses_noteno():
    packed = _pack_doc(
        "pv",
        "hq",
        {"VOUCNO": "", "NOTENO": "103772300", "ACCTNAME": "STATE"},
        [],
    )
    assert packed["docno"] == "103772300"
    assert packed["kind_label"] == "โน้ตจ่าย NP"


def test_explorer_page_hides_pyodbc_timeout():
    html = page(
        user_name="t",
        site="hq",
        probes={
            "hq": {"ok": True, "server": "KSS"},
            "syp": {
                "ok": False,
                "error": "(pyodbc.OperationalError) ('HYT00', 'Login timeout expired')",
            },
        },
    )
    assert "สำนักงานใหญ่ SQL KSS" in html
    assert "สาขาสี่แยกพัฒนา SQL down" in html
    assert "HYT00" not in html
    assert "pyodbc" not in html


def test_format_sql_timeout_is_short():
    from src.parts9_explorer.db import format_sql_error

    msg = format_sql_error(
        Exception("(pyodbc.OperationalError) ('HYT00', '[HYT00] Login timeout expired')"),
        site="syp",
    )
    assert "HYT00" not in msg
    assert "pyodbc" not in msg
    assert "SYP SQL" in msg
    assert "ไม่เชื่อมต่อ" in msg


def _explorer_html():
    return page(user_name="t", site="hq", probes={"hq": {"ok": True, "server": "KSS"}, "syp": {}})


def test_explorer_page_uses_thai_headers_and_formats_billamt():
    html = _explorer_html()
    assert 'BILLAMT:"ยอดบิล"' in html
    assert 'JOURTYPE:"ประเภทสมุด"' in html
    assert 'NOTENO:"เลขโน้ต"' in html
    assert 'LINE:"ลำดับ"' in html
    assert 'BCODE:"รหัสสินค้า"' in html
    assert 'DETAIL:"รายละเอียด"' in html
    assert 'QTY:"จำนวน"' in html
    assert 'UI:"หน่วย"' in html
    assert 'PRICE:"ราคา"' in html
    assert 'AMOUNT:"จำนวนเงิน"' in html
    assert "MONEY_KEYS.has(k) ? money(obj[k])" in html
    assert 'if (c === "LINE") return "<td>"+(i+1)+"</td>"' in html
    assert 'minimumFractionDigits: 2' in html


def test_explorer_js_renders_comma_billamt_and_sequential_lines(tmp_path):
    import json
    import shutil
    import subprocess

    node = shutil.which("node")
    if not node:
        raise AssertionError("node is required to verify explorer money/LINE rendering")
    html = _explorer_html()
    start = html.index("const STATUS_TH")
    end = html.index("function jumpProduct")
    helpers = html[start:end]
    script = helpers + r"""
const header = {
  JOURTYPE: "NP", VOUCED: "N", NOTED: "Y", NOTEDATE: "2026-08-22",
  NOTENO: "ABC7/69", ACCTNO: "123", ACCTNAME: "บจก. ทดสอบ",
  BILLCNT: "5", BILLAMT: "31809.14", CANCELED: "N"
};
const lines = [
  {LINE:"10", BCODE:"2201", DETAIL:"สายพาน", QTY:"2", UI:"เส้น", PRICE:"1000.5", AMOUNT:"2001"},
  {LINE:"20", BCODE:"2202", DETAIL:"สายพาน 2", QTY:"1", UI:"เส้น", PRICE:"50", AMOUNT:"50"},
];
process.stdout.write(JSON.stringify({
  kv: kvTable(header),
  table: lineTable(lines, ["LINE","BCODE","DETAIL","QTY","UI","PRICE","AMOUNT"]),
  money: money("31809.14"),
  lineLabel: colTh("LINE"),
}));
"""
    script_path = tmp_path / "render_explorer.js"
    script_path.write_text(script, encoding="utf-8")
    result = subprocess.run([node, str(script_path)], capture_output=True, text=True, check=True)
    out = json.loads(result.stdout)
    assert "31,809.14" in out["money"]
    assert "ยอดบิล" in out["kv"]
    assert "ประเภทสมุด" in out["kv"]
    assert "เลขโน้ต" in out["kv"]
    assert "ชื่อบัญชี" in out["kv"]
    assert "BILLAMT" not in out["kv"]
    assert "JOURTYPE" not in out["kv"]
    assert "31,809.14" in out["kv"]
    assert "31809.14" not in out["kv"]
    assert out["lineLabel"] == "ลำดับ"
    assert "<th>ลำดับ</th>" in out["table"]
    assert "<th>รหัสสินค้า</th>" in out["table"]
    assert "<th>รายละเอียด</th>" in out["table"]
    assert "<th>LINE</th>" not in out["table"]
    assert "<th>BCODE</th>" not in out["table"]
    assert "<td>1</td>" in out["table"]
    assert "<td>2</td>" in out["table"]
    assert "<td>10</td>" not in out["table"]
    assert "<td>20</td>" not in out["table"]

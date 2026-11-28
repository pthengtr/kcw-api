from src.hq_po.guards import HqPoError
from src.hq_po.pdf import (
    build_sheet_pdf,
    content_disposition,
    sheet_pdf_filename,
    wrap_sheet_document,
)


def test_sheet_pdf_filename_uses_po_number():
    assert sheet_pdf_filename([{"docno": "HP6911-CD8B"}]) == "HP6911-CD8B.pdf"
    assert sheet_pdf_filename([{"docno": ""}, {"docno": "HP6910-A1B2"}]) == "HP6910-A1B2.pdf"
    assert sheet_pdf_filename([{"docno": "../evil name"}]) == "evil-name.pdf"
    assert sheet_pdf_filename([{"docno": ""}]) == "PO.pdf"


def test_content_disposition_inline_ascii():
    assert content_disposition("HP6911-CD8B.pdf") == 'inline; filename="HP6911-CD8B.pdf"'


def test_wrap_sheet_document_is_printable_html():
    html = wrap_sheet_document('<article class="pos">ใบสั่งซื้อ</article>')
    assert "<!DOCTYPE html>" in html
    assert 'lang="th"' in html
    assert "ใบสั่งซื้อ" in html
    assert "Prompt" in html


def test_build_sheet_pdf_uses_selected_variant(monkeypatch):
    from src.hq_po import pdf as pdf_mod

    captured = {}

    monkeypatch.setattr(
        pdf_mod,
        "build_sheet_forms",
        lambda _groups: {
            "simple_html": "<div id='simple'>ย่อ</div>",
            "full_html": "<div id='full'>เต็ม</div>",
        },
    )

    def fake_html_to_pdf(html):
        captured["html"] = html
        return b"%PDF-1.4 fake"

    monkeypatch.setattr(pdf_mod, "html_to_pdf", fake_html_to_pdf)

    groups = [{"docno": "HP6911-CD8B", "vendor": "SM", "lines": [{"bcode": "1", "qty": 1}]}]
    pdf, name = build_sheet_pdf(groups, "simple")
    assert pdf.startswith(b"%PDF")
    assert name == "HP6911-CD8B.pdf"
    assert "ย่อ" in captured["html"]
    assert "เต็ม" not in captured["html"]

    pdf, name = build_sheet_pdf(groups, "full")
    assert name == "HP6911-CD8B.pdf"
    assert "เต็ม" in captured["html"]


def test_build_sheet_pdf_rejects_empty(monkeypatch):
    from src.hq_po import pdf as pdf_mod
    from src.hq_po.sheet import build_sheet_forms as real_build

    def boom(groups):
        raise HqPoError("empty", "ไม่มีรายการสำหรับใบสั่งซื้อ")

    monkeypatch.setattr(pdf_mod, "build_sheet_forms", boom)
    try:
        build_sheet_pdf([{"vendor": "V1", "lines": []}])
        assert False, "expected HqPoError"
    except HqPoError as exc:
        assert exc.code == "empty"
    monkeypatch.setattr(pdf_mod, "build_sheet_forms", real_build)


def test_html_to_pdf_with_chrome_when_available():
    from src.hq_po.pdf import _chrome_bin, html_to_pdf

    if not _chrome_bin():
        return
    pdf = html_to_pdf(
        wrap_sheet_document(
            "<style>@page{size:A4 portrait;margin:10mm}body{font-family:sans-serif}</style>"
            "<h1>ใบสั่งซื้อ HP6911-CD8B</h1><p>ทดสอบ</p>"
        )
    )
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 500

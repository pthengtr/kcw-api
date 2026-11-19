from __future__ import annotations

from src.online_sale.bill_sheets import reason_from_sheet_html, strip_autoprint


def test_strip_autoprint_removes_window_print():
    html = """<!doctype html><script>
window.onload=function(){
  setTimeout(function(){ window.print(); }, 200);
};
</script>"""
    out = strip_autoprint(html)
    assert "window.print" not in out
    assert "setTimeout" not in out or "print" not in out


def test_reason_from_sheet_html_recovers_credit_note_reason():
    html = (
        "<div class='cn-box'><div class='reason'>"
        "<span class='k'>เหตุผลที่ออกใบลดหนี้</span>"
        "<span class='v'>คืนสินค้า</span></div></div>"
    )
    assert reason_from_sheet_html(html) == "คืนสินค้า"
    assert reason_from_sheet_html(html.replace("คืนสินค้า", "—")) == ""
    assert reason_from_sheet_html("") == ""

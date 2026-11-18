from __future__ import annotations

from src.online_sale.bill_sheets import strip_autoprint


def test_strip_autoprint_removes_window_print():
    html = """<!doctype html><script>
window.onload=function(){
  setTimeout(function(){ window.print(); }, 200);
};
</script>"""
    out = strip_autoprint(html)
    assert "window.print" not in out
    assert "setTimeout" not in out or "print" not in out

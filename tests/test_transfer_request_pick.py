"""Request pick-list Continue must work when products are ticked (cart still empty)."""

from src.transfer.ui import page


def test_request_continue_enabled_when_products_are_selected():
    html = page(user_name="ทดสอบ", site="SYP")
    assert "request-dock" in html
    assert "request-picking" in html
    assert "commitPicked" in html
    assert "collectPicks" in html
    assert "visibleDualPane(el)" in html
    assert "function escText" in html
    assert '${nPicked||cartItems.length?"":"disabled"}' in html
    assert "next.disabled = n===0 && !cartItems.length" in html
    # Old gate: Continue stayed disabled until items were already in the cart.
    assert 'id="btnReqNext2" ${cartItems.length?"":"disabled"}' not in html
    assert "ติ๊กจากรายการแนะนำแล้วกดถัดไป" in html
    assert "แล้วกด <strong>ถัดไป</strong>" in html


def test_request_pick_reads_visible_qty_and_escapes_descr():
    html = page(user_name="ทดสอบ", site="HQ")
    assert "livePickFromDom" in html
    assert "pane.querySelector(`[data-qty=" in html
    assert 'escText((row && row.descr) || "")' in html
    assert "function pickKey" in html

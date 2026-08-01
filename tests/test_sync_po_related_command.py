from src.handlers.job import (
    is_job_request,
    is_sync_po_related_request,
    is_sync_pomas_podet_request,
)


def test_sync_po_related_aliases_en_and_thai():
    for text in (
        "sync po related",
        "sync-po-related",
        "Sync PO Related",
        "update po related",
        "po related sync",
        "po-related sync",
        "อัปเดตporelated",
        "อัพเดตporelated",
        "อัปเดทporelated",
        "syncporelated",
        "updateporelated",
    ):
        assert is_sync_po_related_request(text), text
        assert is_job_request(text), text
        assert not is_sync_pomas_podet_request(text), text


def test_sync_po_related_does_not_match_unrelated_text():
    for text in (
        "sync",
        "sync po",
        "อัปเดตpo",
        "อัปเดตใบสั่งซื้อ",
        "sync pomas",
        "อัปเดตiclow",
        "สินค้า 22010585",
    ):
        assert not is_sync_po_related_request(text), text

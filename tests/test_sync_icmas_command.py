from src.handlers.job import is_job_request, is_sync_icmas_request


def test_sync_icmas_aliases_en_and_thai():
    for text in (
        "sync icmas",
        "sync-icmas",
        "Sync ICMAS",
        "update icmas",
        "icmas sync",
        "update product master",
        "sync product master",
        "อัปเดตicmas",
        "อัพเดตicmas",
        "อัปเดทicmas",
        "syncicmas",
        "updateicmas",
        "อัปเดตข้อมูลสินค้า",
        "อัพเดตข้อมูลสินค้า",
    ):
        assert is_sync_icmas_request(text), text
        assert is_job_request(text), text


def test_sync_icmas_does_not_match_unrelated_text():
    for text in (
        "sync",
        "icmas",
        "อัปเดต",
        "อัปเดตสต็อก",
        "อัปเดตสินค้า",
        "อัปเดตiclow",
        "อัปเดตใบสั่งซื้อ",
        "sync pomas",
        "สินค้า 22010585",
    ):
        assert not is_sync_icmas_request(text), text

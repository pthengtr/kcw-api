from src.handlers.job import is_job_request, is_sync_iclow_request


def test_sync_iclow_aliases_en_and_thai():
    for text in (
        "sync iclow",
        "sync-iclow",
        "Sync iClow",
        "update iclow",
        "iclow sync",
        "อัปเดตiclow",
        "อัพเดตiclow",
        "อัปเดทiclow",
        "synciclow",
        "updateiclow",
    ):
        assert is_sync_iclow_request(text), text
        assert is_job_request(text), text


def test_sync_iclow_does_not_match_unrelated_text():
    for text in (
        "sync",
        "iclow",
        "อัปเดต",
        "อัปเดตสต็อก",
        "อัปเดตใบสั่งซื้อ",
        "sync pomas",
        "สินค้า 22010585",
    ):
        assert not is_sync_iclow_request(text), text

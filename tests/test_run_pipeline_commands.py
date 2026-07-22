from src.handlers.job import (
    is_hq_full_request,
    is_hq_raw_request,
    is_job_request,
    is_syp_raw_request,
)


def test_syp_raw_aliases_en_and_thai():
    for text in (
        "run syp",
        "run syp raw",
        "Run SYP Raw",
        "รัน syp",
        "รัน syp raw",
        "รัน สาขา",
        "รัน สาขา raw",
        "run สาขา",
        "runsypraw",
        "รันสาขาraw",
    ):
        assert is_syp_raw_request(text), text
        assert is_job_request(text), text


def test_hq_raw_aliases_en_and_thai():
    for text in (
        "run hq a",
        "run hq raw",
        "รัน hq a",
        "รัน hq raw",
        "รัน สนญ a",
        "รัน สนญ raw",
        "run สนญ a",
        "runhqa",
        "รันhqraw",
        "รันสนญraw",
    ):
        assert is_hq_raw_request(text), text
        assert is_job_request(text), text
        assert not is_hq_full_request(text), text


def test_hq_full_aliases_en_and_thai():
    for text in (
        "run hq b",
        "run hq full",
        "รัน hq b",
        "รัน hq full",
        "รัน สนญ b",
        "รัน สนญ full",
        "run สนญ b",
        "runhqb",
        "รันhqfull",
        "รันสนญfull",
    ):
        assert is_hq_full_request(text), text
        assert is_job_request(text), text
        assert not is_hq_raw_request(text), text


def test_run_commands_do_not_match_unrelated_text():
    for text in (
        "run",
        "run hq",
        "hq raw",
        "syp raw",
        "อัปเดตสต็อก",
        "สินค้า 22010585",
    ):
        assert not is_syp_raw_request(text), text
        assert not is_hq_raw_request(text), text
        assert not is_hq_full_request(text), text

from unittest.mock import MagicMock, patch

from src.handlers.job import (
    is_hq_full_request,
    is_hq_raw_request,
    is_job_request,
    is_syp_raw_request,
)
from src.jobs.tasks import (
    enqueue_hq_full_jobs,
    enqueue_hq_raw_jobs,
    enqueue_syp_raw_jobs,
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


def test_syp_raw_targets_only_syp_pc():
    engine = MagicMock()
    with patch("src.jobs.tasks.enqueue_job") as enqueue_job:
        enqueue_job.return_value = {
            "id": 1,
            "job_type": "syp_raw",
            "payload": {"site": "SYP", "task": "syp_raw"},
            "worker_name": "SYP-PC",
        }
        jobs = enqueue_syp_raw_jobs(
            engine,
            allowed_workers={"SYP-PC", "HQ-PC"},
        )

    assert len(jobs) == 1
    enqueue_job.assert_called_once()
    kwargs = enqueue_job.call_args.kwargs
    assert kwargs["job_type"] == "syp_raw"
    assert kwargs["worker_name"] == "SYP-PC"
    assert kwargs["payload"]["site"] == "SYP"


def test_hq_jobs_target_only_hq_pc():
    engine = MagicMock()
    with patch("src.jobs.tasks.enqueue_job") as enqueue_job:
        enqueue_job.side_effect = [
            {
                "id": 2,
                "job_type": "hq_raw",
                "payload": {"site": "HQ", "task": "hq_raw"},
                "worker_name": "HQ-PC",
            },
            {
                "id": 3,
                "job_type": "hq_full",
                "payload": {"site": "HQ", "task": "hq_full"},
                "worker_name": "HQ-PC",
            },
        ]
        raw_jobs = enqueue_hq_raw_jobs(
            engine,
            allowed_workers={"SYP-PC", "HQ-PC"},
        )
        full_jobs = enqueue_hq_full_jobs(
            engine,
            allowed_workers={"SYP-PC", "HQ-PC"},
        )

    assert len(raw_jobs) == 1
    assert len(full_jobs) == 1
    assert enqueue_job.call_count == 2
    for call in enqueue_job.call_args_list:
        assert call.kwargs["worker_name"] == "HQ-PC"
        assert call.kwargs["payload"]["site"] == "HQ"


def test_syp_job_skipped_when_only_hq_online():
    engine = MagicMock()
    with patch("src.jobs.tasks.enqueue_job") as enqueue_job:
        jobs = enqueue_syp_raw_jobs(engine, allowed_workers={"HQ-PC"})

    assert jobs == []
    enqueue_job.assert_not_called()


def test_hq_job_skipped_when_only_syp_online():
    engine = MagicMock()
    with patch("src.jobs.tasks.enqueue_job") as enqueue_job:
        raw_jobs = enqueue_hq_raw_jobs(engine, allowed_workers={"SYP-PC"})
        full_jobs = enqueue_hq_full_jobs(engine, allowed_workers={"SYP-PC"})

    assert raw_jobs == []
    assert full_jobs == []
    enqueue_job.assert_not_called()

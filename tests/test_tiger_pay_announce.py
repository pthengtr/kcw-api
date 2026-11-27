from unittest.mock import MagicMock, patch

from src.tiger_pay.announce_tts import (
    cloud_qr_success_phrase,
    format_amount_for_speech,
)
from src.tiger_pay.announce_worker import run_once
from src.tiger_pay import cloud_qr_repos


def test_format_amount_for_speech_strips_whole_baht():
    assert format_amount_for_speech(100) == "100"
    assert format_amount_for_speech(100.0) == "100"
    assert format_amount_for_speech("250.00") == "250"
    assert format_amount_for_speech(99.5) == "99.50"


def test_cloud_qr_success_phrase_prefers_paid_amount():
    phrase = cloud_qr_success_phrase(
        {"amount": 100, "paid_amount": 120.0, "pos_bill_number": "B1"}
    )
    assert phrase == "ชำระเงินผ่าน QR สำเร็จ จำนวน 120 บาท"


def test_claim_next_cloud_qr_announce_sql_and_params():
    engine = MagicMock()
    conn = MagicMock()
    engine.begin.return_value.__enter__.return_value = conn
    engine.begin.return_value.__exit__.return_value = None
    row = MagicMock()
    row._mapping = {
        "id": "cloudqr001",
        "pos_bill_id": "bill-1",
        "pos_bill_number": "B1",
        "amount": 50,
        "paid_amount": 50,
        "status": "C",
        "announced_at": "2026-11-27T06:00:00+00:00",
        "announced_by": "till-pc",
    }
    conn.execute.return_value.first.return_value = row

    claimed = cloud_qr_repos.claim_next_cloud_qr_announce(
        engine, worker_id="till-pc", lookback_hours=12
    )
    assert claimed is not None
    assert claimed["id"] == "cloudqr001"
    assert claimed["announced_by"] == "till-pc"
    args = conn.execute.call_args
    sql_text = str(args.args[0])
    assert "announced_at is null" in sql_text
    assert "for update skip locked" in sql_text.lower()
    assert args.args[1]["worker_id"] == "till-pc"
    assert args.args[1]["lookback_hours"] == 12.0


def test_run_once_speaks_claimed_row():
    engine = MagicMock()
    row = {
        "id": "cloudqr001",
        "pos_bill_number": "B1",
        "amount": 80,
        "paid_amount": 80,
        "status": "C",
    }
    with (
        patch(
            "src.tiger_pay.announce_worker.cloud_qr_repos.claim_next_cloud_qr_announce",
            return_value=row,
        ) as claim,
        patch("src.tiger_pay.announce_worker.speak_thai") as speak,
    ):
        assert run_once(
            engine, worker_id="w1", lookback_hours=24, dry_run=False
        ) is True
        claim.assert_called_once()
        speak.assert_called_once()
        assert "80" in speak.call_args.args[0]
        assert speak.call_args.kwargs["dry_run"] is False


def test_run_once_idle_when_nothing_to_claim():
    engine = MagicMock()
    with (
        patch(
            "src.tiger_pay.announce_worker.cloud_qr_repos.claim_next_cloud_qr_announce",
            return_value=None,
        ),
        patch("src.tiger_pay.announce_worker.speak_thai") as speak,
    ):
        assert run_once(
            engine, worker_id="w1", lookback_hours=24, dry_run=True
        ) is False
        speak.assert_not_called()

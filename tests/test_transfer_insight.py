from datetime import datetime, timedelta, timezone

from src.transfer.insight import (
    ai_recommendation,
    annotate_iclow_items,
    clean_propose_meta,
    insight_only_lines,
    pack_gap,
)


NOW = datetime(2026, 10, 5, 2, 0, tzinfo=timezone.utc)
FRESH = "2026-10-03T10:00:00+07:00"


def _policy(**kwargs):
    row = {
        "bcode": "A1",
        "generated_at": FRESH,
        "dead_stock": "no",
        "syp_safe_holding": 10,
        "syp_monthly": 4,
        "rec_transfer_qty_to_syp": 12,
        "rec_transfer_reason": "",
    }
    row.update(kwargs)
    return row


def test_pack_gap_rounds_up_to_mtp2():
    assert pack_gap(5, 12) == 12
    assert pack_gap(0, 12) == 0
    assert pack_gap(1.2, 1) == 2


def test_ai_qty_is_live_gap_capped_by_hq():
    advice = ai_recommendation(
        _policy(),
        live_syp=3,
        live_hq=4,
        syp_blocked=False,
        mtp2=1,
        now=NOW,
    )
    assert advice is not None
    assert advice["ai_qty"] == 4
    assert advice["reason"].startswith("สาขา 3 / เป้า 10")


def test_ai_skips_stale_blocked_dead_and_enough_stock():
    stale = (NOW - timedelta(days=30)).isoformat()
    assert ai_recommendation(_policy(generated_at=stale), live_syp=0, live_hq=5, syp_blocked=False, mtp2=1, now=NOW) is None
    assert ai_recommendation(_policy(), live_syp=0, live_hq=5, syp_blocked=True, mtp2=1, now=NOW) is None
    assert ai_recommendation(_policy(dead_stock="yes"), live_syp=0, live_hq=5, syp_blocked=False, mtp2=1, now=NOW) is None
    assert ai_recommendation(_policy(), live_syp=10, live_hq=5, syp_blocked=False, mtp2=1, now=NOW) is None
    assert ai_recommendation(_policy(), live_syp=1, live_hq=0, syp_blocked=False, mtp2=1, now=NOW) is None


def test_annotate_keeps_iclow_qty():
    items = [
        {
            "bcode": "A1",
            "source": "iclow",
            "suggest_qty": 2,
            "syp_qtyoh2": 1,
            "hq_qtyoh2": 20,
            "qtymin": 4,
            "mtp2": 1,
        }
    ]
    annotate_iclow_items(items, {"A1": _policy()}, now=NOW)
    assert items[0]["suggest_qty"] == 2
    assert items[0]["source"] == "iclow"
    assert items[0]["propose_meta"]["source"] == "both"
    assert items[0]["propose_meta"]["ai_qty"] == 9
    assert items[0]["propose_meta"]["generated_at"] == FRESH


def test_insight_only_skips_iclow_bcode_and_ranks():
    policies = {
        "A1": _policy(bcode="A1", syp_monthly=1),
        "B2": _policy(bcode="B2", syp_safe_holding=6, syp_monthly=10),
    }
    hq = {
        "A1": {"qtyoh2": 20, "blocked": False, "mtp2": 1, "descr": "A"},
        "B2": {"qtyoh2": 20, "blocked": False, "mtp2": 1, "descr": "B"},
    }
    syp = {
        "A1": {"qtyoh2": 0, "blocked": False, "mtp2": 1, "qtymin": 1, "descr": "A"},
        "B2": {"qtyoh2": 0, "blocked": False, "mtp2": 1, "qtymin": 1, "descr": "B"},
    }
    lines = insight_only_lines(
        policies, iclow_bcodes={"A1"}, hq_icmas=hq, syp_icmas=syp, now=NOW
    )
    assert [row["bcode"] for row in lines] == ["B2"]
    assert lines[0]["source"] == "insight"
    assert lines[0]["suggest_qty"] == lines[0]["propose_meta"]["ai_qty"]
    assert lines[0]["propose_meta"]["source"] == "insight"


def test_suggest_keeps_iclow_and_appends_insight_only():
    from unittest.mock import patch

    from src.transfer.parts9 import transfer_insight_overlay

    iclow_rows = [{"bcode": "A1", "descr": "From ICLOW", "qty": 2, "ordered_qty": 2}]

    def fake_icmas(engine, bcodes, include_blocked=False):
        return {
            code: {
                "qtyoh2": 8.0 if "hq" in getattr(engine, "name", "") else 1.0,
                "qtymin": 2.0,
                "blocked": False,
                "descr": code,
                "model": "",
                "ui1": "ชิ้น",
                "ui2": "",
                "mtp2": 1.0,
                "location1": "",
                "location2": "",
                "location": "",
            }
            for code in bcodes
        }

    hq = type("E", (), {"name": "hq"})()
    syp = type("E", (), {"name": "syp"})()

    def fake_chunked(site_key, bcodes):
        qty = 8.0 if site_key == "hq" else 0.0
        return {
            code: {
                "qtyoh2": qty,
                "qtymin": 1.0,
                "blocked": False,
                "descr": "Only AI",
                "model": "",
                "brand": "",
                "pcode": "",
                "mcode": "",
                "ui1": "ชิ้น",
                "ui2": "",
                "mtp2": 1.0,
                "location": "",
            }
            for code in bcodes
        }

    policies = {
        "A1": _policy(bcode="A1"),
        "B2": _policy(bcode="B2", syp_safe_holding=5, syp_monthly=2),
    }
    with patch("src.transfer.parts9._fetch_all_iclow_to_be_ordered", return_value=iclow_rows):
        with patch("src.transfer.parts9.site_sql_hosts_collide", return_value=False):
            with patch("src.transfer.parts9.get_site_engine", side_effect=lambda site: hq if site == "hq" else syp):
                with patch("src.transfer.parts9._fetch_icmas_meta", side_effect=fake_icmas):
                    with patch("src.transfer.parts9._suggest_from_icmas_low_stock", return_value={}):
                        with patch("src.transfer.insight.load_insight_policies", return_value=policies):
                            with patch("src.transfer.parts9._fetch_icmas_chunked", side_effect=fake_chunked):
                                with patch("src.transfer.parts9._insight_only_cache", None):
                                    overlay = transfer_insight_overlay(
                                        [
                                            {
                                                "bcode": "A1",
                                                "source": "iclow",
                                                "suggest_qty": 2,
                                                "syp_qtyoh2": 1,
                                                "hq_qtyoh2": 8,
                                                "qtymin": 2,
                                                "mtp2": 1,
                                            }
                                        ],
                                        site_key="syp",
                                    )

    assert overlay["updates"][0]["bcode"] == "A1"
    assert overlay["updates"][0]["propose_meta"]["source"] == "both"
    insight = overlay["insight_only"]
    assert [row["bcode"] for row in insight] == ["B2"]
    assert insight[0]["source"] == "insight"
    assert insight[0]["propose_meta"]["source"] == "insight"


def test_clean_propose_meta_drops_plain_iclow():
    assert clean_propose_meta({"source": "iclow", "ai_qty": 1}) is None
    kept = clean_propose_meta(
        {"source": "both", "ai_qty": 3, "generated_at": FRESH, "reason": "สาขา 1 / เป้า 4", "extra": 1}
    )
    assert kept == {
        "source": "both",
        "reason": "สาขา 1 / เป้า 4",
        "ai_qty": 3.0,
        "generated_at": FRESH,
    }

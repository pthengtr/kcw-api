"""Tests for pay-notes AI vision helpers (no OpenAI calls)."""

from src.pay_notes.ai_vision import (
    amounts_match,
    compare_payment_amounts,
    dedupe_extracted_lines,
    extract_bill_lines_from_images,
    match_bill_lines,
    normalize_billno,
)


def test_normalize_billno_strips_separators():
    assert normalize_billno("INV-2401/001") == normalize_billno("INV2401001")


def test_extract_bill_lines_from_images_single_image():
    """Test extract_bill_lines_from_images works with single image."""
    assert callable(extract_bill_lines_from_images)


def test_dedupe_extracted_lines_drops_exact_duplicates():
    lines, warnings = dedupe_extracted_lines([
        {"billno": "INV-001", "amount": 100.0},
        {"billno": "INV-001", "amount": 100.0},
        {"billno": "INV-002", "amount": 200.0},
    ])
    assert len(lines) == 2
    assert not warnings


def test_dedupe_extracted_lines_warns_conflicting_amounts():
    lines, warnings = dedupe_extracted_lines([
        {"billno": "INV-001", "amount": 100.0},
        {"billno": "INV-001", "amount": 200.0},
    ])
    assert len(lines) == 2
    assert warnings


def test_match_bill_lines_amount_unique():
    pickable = [
        {"BILLNO": "A1", "AFTERTAX": 100.0},
        {"BILLNO": "B2", "AFTERTAX": 200.0},
    ]
    result = match_bill_lines([{"billno": "X", "amount": 200.0}], pickable)
    assert result["auto_selected_billnos"] == ["B2"]
    assert result["lines"][0]["matched"]["match"] == "amount"


def test_match_bill_lines_amount_and_billno():
    pickable = [{"BILLNO": "2401-001", "AFTERTAX": 12500.0}]
    result = match_bill_lines([{"billno": "INV-2401-001", "amount": 12500.0}], pickable)
    assert result["auto_selected_billnos"] == ["2401-001"]
    assert result["lines"][0]["matched"]["match"] in ("amount+billno", "amount")


def test_match_bill_lines_ambiguous_same_amount():
    pickable = [
        {"BILLNO": "A1", "AFTERTAX": 500.0},
        {"BILLNO": "A2", "AFTERTAX": 500.0},
    ]
    result = match_bill_lines([{"billno": "?", "amount": 500.0}], pickable)
    assert result["auto_selected_billnos"] == []
    assert result["lines"][0]["status"] in ("ambiguous", "unmatched")


def test_match_bill_lines_greedy_no_double_assign():
    pickable = [
        {"BILLNO": "B1", "AFTERTAX": 100.0},
        {"BILLNO": "B2", "AFTERTAX": 200.0},
    ]
    result = match_bill_lines(
        [
            {"billno": "B1", "amount": 100.0},
            {"billno": "B2", "amount": 200.0},
        ],
        pickable,
    )
    assert sorted(result["auto_selected_billnos"]) == ["B1", "B2"]


def test_payment_amount_match_tolerance():
    assert amounts_match(100.0, 100.009)
    assert not amounts_match(100.0, 100.02)
    cmp = compare_payment_amounts(99.99, 100.0)
    assert cmp["match"] is True
    cmp2 = compare_payment_amounts(50.0, 100.0)
    assert cmp2["match"] is False
    assert cmp2["difference"] == -50.0

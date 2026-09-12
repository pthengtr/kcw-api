"""Tests for pay-notes AI vision helpers (no OpenAI calls)."""

from src.pay_notes.ai_vision import (
    BILL_LINES_SYSTEM_PROMPT,
    amounts_match,
    compare_payment_amounts,
    dedupe_extracted_lines,
    drop_statement_total_rows,
    extract_bill_lines_from_images,
    match_bill_lines,
    merge_page_extractions,
    normalize_billno,
    normalize_extracted_page,
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


def test_prompt_asks_for_table_rows_not_statement_header():
    assert "เลขที่ใบส่งของ" in BILL_LINES_SYSTEM_PROMPT
    assert "ใบวางบิล" in BILL_LINES_SYSTEM_PROMPT
    assert "Do NOT use the document header number" in BILL_LINES_SYSTEM_PROMPT
    assert "เงินคงค้าง" in BILL_LINES_SYSTEM_PROMPT


def test_drop_statement_total_rows_removes_header_when_other_rows_exist():
    lines, warnings = drop_statement_total_rows(
        [
            {"billno": "BO690011221", "amount": 82566.0},
            {"billno": "IVE6932639", "amount": 5200.0},
            {"billno": "IVE6932746", "amount": 3371.0},
        ],
        82566.0,
    )
    assert [ln["billno"] for ln in lines] == ["IVE6932639", "IVE6932746"]
    assert warnings


def test_drop_statement_total_rows_keeps_single_invoice_page():
    lines, warnings = drop_statement_total_rows(
        [{"billno": "IVE6932639", "amount": 5200.0}],
        5200.0,
    )
    assert len(lines) == 1
    assert not warnings


def test_normalize_extracted_page_drops_footer_total_row():
    page = normalize_extracted_page(
        {
            "lines": [
                {"billno": "IVE1", "amount": 100.0},
                {"billno": "IVE2", "amount": 200.0},
                {"billno": "BO1", "amount": 300.0},
            ],
            "total_amount": 300.0,
            "warnings": [],
        }
    )
    assert [ln["billno"] for ln in page["lines"]] == ["IVE1", "IVE2"]
    assert page["total_amount"] == 300.0


def test_merge_page_extractions_concats_rows_and_sums_totals():
    merged = merge_page_extractions(
        [
            {
                "lines": [{"billno": "IVE1", "amount": 100.0}],
                "total_amount": 100.0,
                "warnings": [],
                "usage": {"input_tokens": 10, "output_tokens": 4, "total_tokens": 14},
            },
            {
                "lines": [{"billno": "IVE2", "amount": 200.0}],
                "total_amount": 200.0,
                "warnings": ["blurry row"],
                "usage": {"input_tokens": 20, "output_tokens": 6, "total_tokens": 26},
            },
        ]
    )
    assert [ln["billno"] for ln in merged["lines"]] == ["IVE1", "IVE2"]
    assert merged["total_amount"] == 300.0
    assert merged["usage"]["total_tokens"] == 40
    assert any("page 2" in w and "blurry" in w for w in merged["warnings"])


def test_merge_page_extractions_dedupes_repeated_rows_across_pages():
    merged = merge_page_extractions(
        [
            {
                "lines": [{"billno": "IVE1", "amount": 100.0}],
                "total_amount": 100.0,
                "warnings": [],
                "usage": {},
            },
            {
                "lines": [{"billno": "IVE1", "amount": 100.0}],
                "total_amount": 100.0,
                "warnings": [],
                "usage": {},
            },
        ]
    )
    assert merged["lines"] == [{"billno": "IVE1", "amount": 100.0}]
    assert merged["total_amount"] == 200.0

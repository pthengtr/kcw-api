from src.stock_check.sa_writer import (
    _sa_remarks,
    _sa_sale_name,
    _sql_nvarchar_len,
    _truncate_sql_nvarchar,
)


def test_sql_nvarchar_len_counts_surrogate_pairs():
    may = "🅼🅾🅾🅼🅰🆈"
    assert _sql_nvarchar_len(may) == 2 * len(may)


def test_sa_remarks_fits_may_emoji_approver_with_thai_operator():
    remarks = _sa_remarks("พลอย หมื่นไสยาสน์", "🅼🅾🅾🅼🅰🆈")
    assert _sql_nvarchar_len(remarks) <= 30
    assert remarks.startswith("SC:พลอย")


def test_sa_remarks_fits_bellla_emoji_approver():
    remarks = _sa_remarks("Nok Garage (KCW)", "Bellla 😘😘")
    assert _sql_nvarchar_len(remarks) <= 30
    assert remarks.startswith("SC:Nok")


def test_sa_sale_name_fits_thai_operator():
    sale = _sa_sale_name("พลอย หมื่นไสยาสน์")
    assert _sql_nvarchar_len(sale) <= 15
    assert sale.startswith("พลอย")


def test_truncate_sql_nvarchar_never_exceeds_limit():
    text = "SC:พลอย หมื่นไสยาสน์/🅼🅾🅾🅼🅰🆈"
    cut = _truncate_sql_nvarchar(text, 30)
    assert _sql_nvarchar_len(cut) <= 30
    assert len(cut) < len(text)

from datetime import date

from src.queries import get_daily_sales_summary


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def fetchall(self):
        return self._rows


class _Connection:
    def __init__(self, rows):
        self._rows = rows
        self.sql = None
        self.params = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def execute(self, sql, params):
        self.sql = str(sql)
        self.params = params
        return _Result(self._rows)


class _Engine:
    def __init__(self, rows):
        self.connection = _Connection(rows)

    def connect(self):
        return self.connection


def test_daily_sales_classifies_tad_and_cntad_as_online():
    engine = _Engine(
        [
            ("HQ", 10_000),
            ("SYP", 5_000),
            ("ONLINE", 40_000),
            ("ALL", 55_000),
        ]
    )

    summary = get_daily_sales_summary(engine, "2026-07-27")

    assert summary == {
        "date": "2026-07-27",
        "HQ": 10_000.0,
        "SYP": 5_000.0,
        "ONLINE": 40_000.0,
        "ALL": 55_000.0,
    }
    assert "like 'TAD%'" in engine.connection.sql
    assert "like 'CNTAD%'" in engine.connection.sql
    assert engine.connection.sql.index("like 'CNTAD%'") < engine.connection.sql.index(
        "else upper(trim(coalesce(\"BRANCH\", '')))"
    )
    assert engine.connection.params == {"target_date": date(2026, 7, 27)}

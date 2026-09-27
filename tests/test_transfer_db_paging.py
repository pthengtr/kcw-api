"""Status list must see every line. PostgREST stops at 1000 rows."""

from types import SimpleNamespace

from src.transfer.db import (
    _IN_CHUNK,
    _PAGE_SIZE,
    list_lines_by_transfers,
    list_requests,
)
from src.transfer.state import derive_request_status


class _Query:
    def __init__(self, store: dict):
        self.store = store
        self.ids: list[str] | None = None
        self.start = 0
        self.end = -1

    def select(self, *_args, **_kwargs):
        return self

    def in_(self, _column, ids):
        self.ids = list(ids)
        self.store["in_calls"].append(list(ids))
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def order(self, column, **kwargs):
        self.store.setdefault("orders", []).append((column, kwargs))
        return self

    def range(self, start, end):
        self.start = start
        self.end = end
        return self

    def execute(self):
        if self.ids is None:
            matched = list(self.store["rows"])
        else:
            matched = [row for row in self.store["rows"] if row["transfer_id"] in self.ids]
        data = matched[self.start : self.end + 1]
        self.store["pages"].append((self.start, self.end, len(data)))
        return SimpleNamespace(data=data)


class _Client:
    def __init__(self, rows):
        self.store = {"rows": rows, "in_calls": [], "pages": [], "orders": []}

    def schema(self, _name):
        return self

    def from_(self, _name):
        return _Query(self.store)


def test_list_lines_reads_past_the_postgrest_cap():
    """A received bill past row 1000 must still be attached to its request."""
    received_id = "received-late"
    rows = [
        {
            "transfer_id": "older",
            "line_id": f"old-{i}",
            "qty_prepared": 1,
            "qty_received": 1,
        }
        for i in range(_PAGE_SIZE)
    ]
    rows.append(
        {
            "transfer_id": received_id,
            "line_id": "late-1",
            "qty_prepared": 4,
            "qty_received": 4,
        }
    )
    client = _Client(rows)
    grouped = list_lines_by_transfers(client, ["older", received_id])

    assert len(grouped["older"]) == _PAGE_SIZE
    assert len(grouped[received_id]) == 1
    assert client.store["pages"][0][0:2] == (0, _PAGE_SIZE - 1)
    assert client.store["pages"][1][0] == _PAGE_SIZE
    assert derive_request_status(
        header_status="complete",
        lines=grouped[received_id],
        has_shipments=True,
    ) == "received"


def test_missing_lines_with_a_shipment_is_what_the_list_used_to_show():
    """Documents the mismatch: no lines + a shipment derives as prepared."""
    assert (
        derive_request_status(header_status="complete", lines=[], has_shipments=True)
        == "prepared"
    )


def test_in_filter_is_chunked():
    ids = [f"t-{i}" for i in range(_IN_CHUNK + 1)]
    rows = [{"transfer_id": tid, "line_id": tid} for tid in ids]
    client = _Client(rows)
    grouped = list_lines_by_transfers(client, ids)

    assert [len(chunk) for chunk in client.store["in_calls"]] == [_IN_CHUNK, 1]
    assert set(grouped) == set(ids)
    assert all(len(lines) == 1 for lines in grouped.values())


def test_ignored_offset_does_not_loop(monkeypatch):
    monkeypatch.setattr("src.transfer.db._PAGE_SIZE", 2)
    client = _Client([])

    class _Stuck(_Query):
        def execute(self):
            self.store["pages"].append((self.start, self.end, 2))
            return SimpleNamespace(
                data=[
                    {"transfer_id": "r", "status": "complete"},
                    {"transfer_id": "s", "status": "complete"},
                ]
            )

    client.from_ = lambda _name: _Stuck(client.store)  # type: ignore[method-assign]
    items = list_requests(client)
    assert [row["transfer_id"] for row in items] == ["r", "s"]
    assert len(client.store["pages"]) == 2


def test_list_requests_pages_when_headers_exceed_the_cap():
    rows = [{"transfer_id": f"r-{i}", "status": "complete"} for i in range(_PAGE_SIZE + 3)]
    client = _Client(rows)
    items = list_requests(client)

    assert len(items) == _PAGE_SIZE + 3
    assert client.store["pages"][0][0:2] == (0, _PAGE_SIZE - 1)
    assert client.store["pages"][1][0] == _PAGE_SIZE
    assert ("created_at", {"desc": True}) in client.store["orders"]
    assert ("transfer_id", {}) in client.store["orders"]

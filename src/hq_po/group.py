from __future__ import annotations

from typing import Any


def vendor_key(item: dict[str, Any]) -> str:
    return str(item.get("vendor") or "").strip()


def group_by_vendor(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Vendor buckets. Unassigned vendor is last. Lines inside a vendor sort by product."""
    buckets: dict[str, dict[str, Any]] = {}
    for item in items:
        key = vendor_key(item)
        bucket = buckets.get(key)
        if bucket is None:
            name = str(item.get("vendor_name") or "").strip()
            bucket = {
                "vendor": key,
                "vendor_name": name or None,
                "lines": [],
            }
            buckets[key] = bucket
        elif not bucket.get("vendor_name"):
            name = str(item.get("vendor_name") or "").strip()
            if name:
                bucket["vendor_name"] = name
        bucket["lines"].append(item)

    def vendor_sort(row: dict[str, Any]) -> tuple:
        key = row["vendor"]
        name = (row.get("vendor_name") or key or "").strip()
        return (1 if not key else 0, name.casefold(), key)

    groups = list(buckets.values())
    groups.sort(key=vendor_sort)
    for group in groups:
        group["lines"] = sort_products(group["lines"])
        group["line_count"] = len(group["lines"])
        group["confirmable_count"] = sum(1 for line in group["lines"] if line.get("confirmable"))
    return groups


def sort_products(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Flat product list: confirmable ICLOW rows first, then description."""

    def key(item: dict[str, Any]) -> tuple:
        descr = str(item.get("descr") or "").strip().casefold()
        bcode = str(item.get("bcode") or "").strip()
        iclow_id = item.get("iclow_id")
        try:
            iclow_n = int(iclow_id) if iclow_id is not None else 0
        except (TypeError, ValueError):
            iclow_n = 0
        return (0 if item.get("confirmable") else 1, descr, bcode, iclow_n)

    return sorted(items, key=key)

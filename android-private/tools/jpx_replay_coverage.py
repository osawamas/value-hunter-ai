"""Strict replay of two dated JPX close sets; no raw data is published.

Input JSON: previous_date, latest_date, previous_closes, latest_closes,
financial_codes, listed_codes, split_verified_free_codes,
dividend_verified_free_codes. Prices are strings, code sets are arrays.
"""
import json
import sys
from datetime import date
from decimal import Decimal


def _codes(value):
    if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
        raise ValueError("code lists must contain nonempty strings")
    if len(set(value)) != len(value):
        raise ValueError("duplicate code")
    return set(value)


def _prices(value):
    if not isinstance(value, dict):
        raise ValueError("prices must be objects")
    result = {}
    for code, raw in value.items():
        if not isinstance(code, str) or not code or not isinstance(raw, str):
            raise ValueError("invalid code or price")
        price = Decimal(raw)
        if not price.is_finite() or price <= 0:
            raise ValueError("invalid price")
        result[code] = price
    return result


def reconcile(snapshot):
    previous_date = date.fromisoformat(snapshot["previous_date"])
    latest_date = date.fromisoformat(snapshot["latest_date"])
    if previous_date >= latest_date:
        raise ValueError("dates must increase")
    previous = _prices(snapshot["previous_closes"])
    latest = _prices(snapshot["latest_closes"])
    financial = _codes(snapshot["financial_codes"])
    listed = _codes(snapshot["listed_codes"])
    splits = _codes(snapshot["split_verified_free_codes"])
    dividends = _codes(snapshot["dividend_verified_free_codes"])
    if not (set(previous) | set(latest) | financial | splits | dividends) <= listed:
        raise ValueError("codes outside dated listing universe")
    paired = set(previous) & set(latest)
    eligible = paired - financial
    budget = {code for code in eligible
              if previous[code] * 100 > 100000 >= latest[code] * 100}
    event_safe = eligible & splits & dividends
    rapid = {code for code in event_safe
             if abs((latest[code] / previous[code] - 1) * 100) >= 8}
    return {
        "previous_date": str(previous_date),
        "latest_date": str(latest_date),
        "listed_denominator": len(listed),
        "paired_closes": len(paired),
        "financial_registered_total": len(financial),
        "paired_financial_overlap": len(paired & financial),
        "price_only_assessable": len(eligible),
        "price_only_market_coverage_percent":
            str((Decimal(len(eligible)) * 100 / len(listed)).quantize(Decimal("0.01")))
            if listed else "0.00",
        "budget_entries": len(budget),
        "event_verified_intervals": len(event_safe),
        "rapid_moves_verified": len(rapid),
        "rapid_moves_held_unverified": len(eligible - event_safe),
        "new_notifications": None,
        "new_notifications_reason": "requires persisted per-code/day/reason delivery ledger",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: jpx_replay_coverage.py snapshot.json")
    with open(sys.argv[1], encoding="utf-8") as source:
        snapshot = json.load(source)
    print(json.dumps(reconcile(snapshot), ensure_ascii=False, indent=2))

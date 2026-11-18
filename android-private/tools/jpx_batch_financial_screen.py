"""Batch-screen locally verified JP observations without publishing prices.

Input is a local JSON object with trade_date, observations (code, close,
financial_as_of, per, pbr, single_share_supported). Ratios must already
have been independently verified and adjusted to the close's share basis.
No network requests, credentials, or price-bearing output are produced.
"""
import argparse
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from value_candidate_screen import classify


def decimal_or_none(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid numeric field") from exc
    if not result.is_finite():
        raise ValueError("Non-finite numeric field")
    return result


def screen(payload):
    trade_date = date.fromisoformat(payload["trade_date"])
    seen = set()
    counts = {"priority": 0, "reference": 0, "held": 0, "excluded": 0}
    reasons = {}
    processed = 0
    for row in payload["observations"]:
        code = str(row["code"])
        if not (len(code) == 4 and code.isdigit()) or code in seen:
            raise ValueError("Invalid or duplicated JP security code")
        seen.add(code)
        financial_date = row.get("financial_as_of")
        if financial_date is not None and date.fromisoformat(financial_date) > trade_date:
            raise ValueError("Future financial basis date")
        # A financial date alone does not prove price/share-basis comparability.
        # The producer must explicitly attest to independent verification.
        verified = row.get("financial_verified") is True and row.get("share_basis_verified") is True
        close = decimal_or_none(row.get("close"))
        per = decimal_or_none(row.get("per")) if verified else None
        pbr = decimal_or_none(row.get("pbr")) if verified else None
        result = classify(close, Decimal("1"), per, pbr,
                          row.get("single_share_supported") is True)
        counts[result.tier] += 1
        reasons[result.reason] = reasons.get(result.reason, 0) + 1
        processed += 1
    return {"trade_date": trade_date.isoformat(), "market": "JP",
            "processed": processed, "tiers": counts, "reasons": reasons,
            "note": "Counts only; no quotes, candidates or alerts exported"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("local_json", type=Path)
    args = parser.parse_args()
    payload = json.loads(args.local_json.read_text(encoding="utf-8"))
    print(json.dumps(screen(payload), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

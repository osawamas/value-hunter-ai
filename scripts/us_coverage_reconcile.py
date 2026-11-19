"""Reconcile verified US two-session coverage with financial-screened symbols.

Pure offline accounting: never treats a price candidate as notification-eligible.
All inputs must use the same exchange-specific canonical symbol namespace.
"""
from collections import Counter


def reconcile_us_coverage(listed_by_market, paired_by_market, financial_by_market,
                          candidates_by_market):
    """Return per-market counts; reject mismatched or incomplete sets.

    Sets are canonical ordinary-share symbols, not counts or ticker-only
    cross-exchange guesses. Candidate status remains unverified pending
    independent close, FX, class, event and provenance checks.
    """
    markets = ("NYSE", "Nasdaq")
    sources = (listed_by_market, paired_by_market, financial_by_market,
               candidates_by_market)
    if any(not isinstance(source, dict) or set(source) != set(markets)
           for source in sources):
        raise ValueError("NYSE and Nasdaq symbol sets required for all inputs")
    result = {}
    for market in markets:
        listed, paired, financial, candidates = (
            source[market] for source in sources)
        if any(not isinstance(values, (set, frozenset)) for values in
               (listed, paired, financial, candidates)):
            raise ValueError("inputs must be actual symbol sets, not counts")
        if any(not isinstance(s, str) or not s.strip() for values in
               (listed, paired, financial, candidates) for s in values):
            raise ValueError("empty or invalid symbol")
        if not paired <= listed or not financial <= listed or not candidates <= paired:
            raise ValueError("inconsistent listing/paired/candidate membership")
        eligible_price_only = paired - financial
        raw_candidates = candidates - financial
        result[market] = {
            "listed": len(listed),
            "paired_closes": len(paired),
            "paired_coverage_pct": round(100 * len(paired) / len(listed), 2)
                if listed else 0.0,
            "financial_registered": len(financial),
            "price_only_possible_before_provenance": len(eligible_price_only),
            "price_only_coverage_pct": round(100 * len(eligible_price_only) / len(listed), 2)
                if listed else 0.0,
            "crossings_before_provenance": len(raw_candidates),
            "crossings_excluded_financial": len(candidates & financial),
            "notification_verified": None,
        }
    return result

"""Conservative US price-only eligibility; no network access or notifications.

Only call after independently verifying raw regular-session closes, FX fixings,
ordinary-share class, corporate actions and provenance for both trade dates.
"""
from datetime import date
from decimal import Decimal, InvalidOperation

BUDGET_JPY = Decimal("100000")


def _positive(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None
    return number if number.is_finite() and number > 0 else None


def evaluate_budget_entry(previous, current, *, ordinary_share_verified,
                          financials_verified, corporate_actions_verified,
                          source_verified, stale_cache=False):
    """Return (eligible, reason). Inputs are mappings with date, close_usd, usd_jpy.

    Never infer missing data, split adjustments, a single-share brokerage
    entitlement or an alert from a one-day snapshot.
    """
    if financials_verified:
        return False, "financials_use_full_valuation"
    if not ordinary_share_verified:
        return False, "ordinary_share_unverified"
    if not corporate_actions_verified:
        return False, "corporate_actions_unverified"
    if not source_verified or stale_cache:
        return False, "source_unverified_or_stale"
    if not previous or not current:
        return False, "two_closes_required"
    try:
        old_date = date.fromisoformat(previous["date"])
        new_date = date.fromisoformat(current["date"])
    except (KeyError, TypeError, ValueError):
        return False, "invalid_trade_dates"
    if old_date >= new_date:
        return False, "non_increasing_trade_dates"
    prices = [_positive(item.get("close_usd")) for item in (previous, current)]
    rates = [_positive(item.get("usd_jpy")) for item in (previous, current)]
    if None in prices or None in rates:
        return False, "invalid_close_or_fx"
    old_cost = prices[0] * rates[0] * 100
    new_cost = prices[1] * rates[1] * 100
    if old_cost > BUDGET_JPY >= new_cost:
        return True, "entered_100_share_budget"
    return False, "no_budget_crossing"

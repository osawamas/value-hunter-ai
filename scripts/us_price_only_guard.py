"""Conservative US price-only eligibility; no network access or notifications.

Only call after independently verifying raw regular-session closes, FX fixings,
ordinary-share class, corporate actions and provenance for both trade dates.
"""
from datetime import date
from decimal import Decimal, InvalidOperation
from collections.abc import Mapping

BUDGET_JPY = Decimal("100000")


def _positive(value):
    # bool is a subclass of int; True must never become a $1 close or FX rate.
    if isinstance(value, bool):
        return None
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
    if financials_verified is not False:
        return False, "financials_status_unverified" if financials_verified is not True else "financials_use_full_valuation"
    if ordinary_share_verified is not True:
        return False, "ordinary_share_unverified"
    if corporate_actions_verified is not True:
        return False, "corporate_actions_unverified"
    if source_verified is not True or stale_cache is not False:
        return False, "source_unverified_or_stale"
    if not previous or not current:
        return False, "two_closes_required"
    if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
        return False, "invalid_observation"
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


def evaluate_budget_entry_for_sessions(previous, current, *, expected_previous_date,
                                       expected_current_date, **verification):
    """Fail closed unless both observations belong to the requested sessions.

    This prevents a missing same-session close from being silently replaced by
    an older cached close. The caller must derive expected dates from an
    exchange trading calendar, not by subtracting a calendar day.
    """
    if previous is None or current is None:
        return False, "invalid_trade_dates"
    if not isinstance(previous, Mapping) or not isinstance(current, Mapping):
        return False, "invalid_observation"
    try:
        expected_old = date.fromisoformat(expected_previous_date)
        expected_new = date.fromisoformat(expected_current_date)
        observed_old = date.fromisoformat(previous["date"])
        observed_new = date.fromisoformat(current["date"])
    except (KeyError, TypeError, ValueError):
        return False, "invalid_trade_dates"
    if expected_old >= expected_new:
        return False, "invalid_expected_sessions"
    if observed_old != expected_old or observed_new != expected_new:
        return False, "session_close_missing_or_stale"
    return evaluate_budget_entry(previous, current, **verification)


def evaluate_verified_budget_entry(previous, current, *, expected_previous_date,
                                   expected_current_date, **verification):
    """Notification gate requiring per-session price and FX provenance.

    A generic source_verified flag alone cannot distinguish adjusted history
    from the raw regular-session closing price. No alert is emitted unless
    both observations explicitly carry independently checked price bases,
    matching FX fixing dates, and nonempty source references.
    """
    if not previous or not current:
        return False, "two_closes_required"
    for item in (previous, current):
        if not isinstance(item, Mapping):
            return False, "invalid_observation"
        if item.get("price_basis") != "raw_unadjusted_regular_session":
            return False, "raw_close_basis_unverified"
        if item.get("fx_date") != item.get("date"):
            return False, "fx_session_mismatch"
        for key in ("close_source", "fx_source"):
            source = item.get(key)
            if not isinstance(source, str) or not source.strip():
                return False, "missing_source_reference"
    return evaluate_budget_entry_for_sessions(
        previous, current,
        expected_previous_date=expected_previous_date,
        expected_current_date=expected_current_date, **verification)

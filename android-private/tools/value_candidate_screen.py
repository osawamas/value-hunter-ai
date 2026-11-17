"""Prototype for classifying comparable, date-verified stock observations."""
from dataclasses import dataclass
from decimal import Decimal

BUDGET = Decimal("100000")
PER_TARGET = Decimal("15")
PBR_TARGET = Decimal("1")
PER_REFERENCE_LIMIT = Decimal("20")
PBR_REFERENCE_LIMIT = Decimal("1.5")


@dataclass(frozen=True)
class Candidate:
    tier: str
    quantity: int
    yen_cost: Decimal | None
    reason: str


def usable(value):
    return value is not None and value.is_finite() and value > 0


def classify(close, yen_per_unit, per, pbr, single_share_supported):
    """Use a verified close and FX rate, and verified ratios when available.

    None means unavailable. Nonpositive ratios represent unusable or
    explicitly nonpositive fundamentals and require separate review.
    """
    if not usable(close) or not usable(yen_per_unit):
        return Candidate("held", 0, None, "price_or_fx_unavailable")
    price = close * yen_per_unit
    if price * 100 <= BUDGET:
        quantity = 100
    elif price <= BUDGET and single_share_supported:
        quantity = 1
    else:
        return Candidate("excluded", 0, None, "over_budget_or_single_share_unavailable")

    cost = price * quantity
    if any(value is not None and not usable(value) for value in (per, pbr)):
        return Candidate("held", quantity, cost, "nonpositive_or_invalid_fundamentals")
    per_passes = per is not None and per <= PER_TARGET
    pbr_passes = pbr is not None and pbr <= PBR_TARGET
    if per_passes and pbr_passes:
        return Candidate("priority", quantity, cost, "both_ratios_pass")
    if per_passes and (pbr is None or pbr <= PBR_REFERENCE_LIMIT):
        return Candidate("reference", quantity, cost, "per_passes")
    if pbr_passes and (per is None or per <= PER_REFERENCE_LIMIT):
        return Candidate("reference", quantity, cost, "pbr_passes")
    if per is None and pbr is None:
        return Candidate("held", quantity, cost, "fundamentals_unavailable")
    return Candidate("excluded", quantity, cost, "valuation_outside_limits")


def range_position(split_adjusted_close, split_adjusted_history):
    """Return the position within a verified five-year series, as a fraction."""
    if len(split_adjusted_history) < 2 or not usable(split_adjusted_close):
        return None
    if not all(map(usable, split_adjusted_history)):
        return None
    low, high = min(split_adjusted_history), max(split_adjusted_history)
    if low == high:
        return None
    return (split_adjusted_close - low) / (high - low)

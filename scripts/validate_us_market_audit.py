"""Validate saved US coverage evidence without publishing raw quotes."""
import json
from pathlib import Path


def validate(audit):
    errors = []
    markets = audit["listing_market_counts"]
    if set(markets) != {"NYSE", "Nasdaq"}:
        errors.append("unexpected markets")
    covered = sum(v["covered"] for v in markets.values())
    listed = sum(v["listed"] for v in markets.values())
    if any(not isinstance(v[k], int) or isinstance(v[k], bool) or v[k] < 0 for v in markets.values() for k in ("covered", "listed")):
        errors.append("invalid market count")
    if any(v["covered"] > v["listed"] for v in markets.values()):
        errors.append("covered exceeds listed")
    if (covered, listed) != (audit["covered"], audit["listed"]):
        errors.append("market totals disagree")
    if audit["covered"] > audit["listed"]:
        errors.append("overall coverage exceeds listing")
    nasdaq_holds = audit["nasdaq_hold_reason_by_ticker"]
    nyse_holds = audit["nyse_official_pair_unavailable"]
    verified = audit["nasdaq_verified_pair"]
    nyse_history = audit["nyse_nasdaq_public_history_status_by_ticker"]
    if len(nasdaq_holds) != len(set(nasdaq_holds)):
        errors.append("duplicate Nasdaq hold")
    if len(nyse_holds) != len(set(nyse_holds)):
        errors.append("duplicate NYSE hold")
    if len(verified) != len(set(verified)):
        errors.append("duplicate verified Nasdaq symbol")
    if set(verified) & set(nasdaq_holds):
        errors.append("Nasdaq symbol both verified and held")
    if set(nyse_holds) != set(nyse_history):
        errors.append("NYSE evidence missing or extraneous")
    if len(nasdaq_holds) != markets["Nasdaq"]["listed"] - markets["Nasdaq"]["covered"]:
        errors.append("Nasdaq hold count differs from uncovered")
    if len(nyse_holds) != markets["NYSE"]["listed"] - markets["NYSE"]["covered"]:
        errors.append("NYSE hold count differs from uncovered")
    if any(reason not in {"official_pair_unavailable", "split_check_excluded"} for reason in nasdaq_holds.values()):
        errors.append("unknown Nasdaq hold reason")
    if any(status not in {"both_consolidated_dates", "unconfirmed_identity"} for status in nyse_history.values()):
        errors.append("unknown NYSE history status")
    if audit["previous_trading_date"] >= audit["trading_date"]:
        errors.append("trade dates not increasing")
    replay = audit["budget_replay"]
    if any(not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in replay.values()):
        errors.append("invalid replay count")
    return errors


if __name__ == "__main__":
    import sys
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("docs/us-market-audit-20261117.json")
    problems = validate(json.loads(path.read_text(encoding="utf-8")))
    if problems:
        raise SystemExit("; ".join(problems))
    print("US audit consistency OK (not independent price verification)")

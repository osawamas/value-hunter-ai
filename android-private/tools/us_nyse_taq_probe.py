"""Benchmark Dolt closes against the NYSE TAQ public sample's dated Last values."""
import argparse
from collections import Counter
import csv
from datetime import date
from decimal import Decimal, InvalidOperation
from io import StringIO
import json
from pathlib import Path
import re

from us_public_files_probe import MAX_BYTES, dolt_csv, dolt_rows, validated_closes

PLAIN_SYMBOL = re.compile(r"[A-Z]{1,5}")
CENT = Decimal("0.01")


def read_nyse_sample(path, day):
    if path.name != f"EQY_US_NYSE_SUM_CLOSE_{day:%Y%m%d}.txt":
        raise ValueError("Expected the original NYSE TAQ sample filename for the trading date")
    with path.open("rb") as file:
        content = file.read(MAX_BYTES + 1)
    if not 0 < len(content) <= MAX_BYTES:
        raise ValueError("Unexpected NYSE TAQ sample size")
    same_day = day.strftime("%m/%d/%Y")
    totals = Counter()
    prices = {}
    for line in content.decode("ascii").splitlines():
        row = line.split("|")
        if len(row) != 14:
            raise ValueError("Unexpected NYSE TAQ record length")
        if row[13] != "N":
            continue
        totals["nyse_listed_rows"] += 1
        ticker, last, volume, last_date = row[0], row[5], row[7], row[8]
        if not PLAIN_SYMBOL.fullmatch(ticker):
            totals["excluded_non_plain_symbol"] += 1
            continue
        if last_date != same_day:
            totals["excluded_different_or_blank_trade_date"] += 1
            continue
        try:
            close = Decimal(last)
        except InvalidOperation:
            raise ValueError("Invalid NYSE TAQ Last value") from None
        if not close.is_finite() or not re.fullmatch(r"[0-9]+", volume):
            raise ValueError("Invalid NYSE TAQ price or volume")
        if close <= 0 or int(volume) == 0:
            totals["excluded_no_positive_last_or_volume"] += 1
            continue
        if ticker in prices:
            raise ValueError("Duplicate NYSE TAQ symbol")
        prices[ticker] = close
    if not prices:
        raise ValueError("No eligible same-date NYSE TAQ Last values")
    return prices, dict(totals)


def benchmark(day, reference, bars):
    seen, prices = validated_closes(day, bars)
    matched = reference.keys() & prices.keys()
    differences = {symbol: abs(reference[symbol] - Decimal(str(prices[symbol]))) for symbol in matched}
    exact = sum(delta == 0 for delta in differences.values())
    within = sum(delta <= CENT for delta in differences.values())
    above_cent = sorted(symbol for symbol, delta in differences.items() if delta > CENT)
    return {
        "reference_basis": "NYSE TAQ Last, row trade date matches session; NYSE-listed plain symbols",
        "reference_symbols": len(reference),
        "matched_dolt": len(matched),
        "missing_dolt": len(reference) - len(matched),
        "exact_matches": exact,
        "within_one_cent_nonexact": within - exact,
        "differ_over_one_cent": len(above_cent),
        "exceptions": {
            "no_dolt_row": sorted(reference.keys() - seen),
            "dolt_row_without_usable_close": sorted((reference.keys() & seen) - matched),
            "differ_over_one_cent": above_cent,
        },
    }


def follow_missing(directory, day, through, symbols):
    """Find the earliest later positive close in the current mirror for each exception."""
    requested = sorted(set(symbols))
    if through <= day or any(not PLAIN_SYMBOL.fullmatch(symbol) for symbol in requested):
        raise ValueError("Follow-up needs a later date and plain NYSE TAQ symbols")
    found = {}
    if requested:
        literals = ", ".join(f"'{symbol}'" for symbol in requested)
        query = ("SELECT act_symbol AS symbol, MIN(date) AS first_close_date FROM ohlcv "
                 f"WHERE date > '{day}' AND date <= '{through}' AND close > 0 "
                 f"AND act_symbol IN ({literals}) GROUP BY act_symbol")
        reader = csv.DictReader(StringIO(dolt_csv(directory, query).decode("utf-8")))
        if reader.fieldnames != ["symbol", "first_close_date"]:
            raise ValueError("Unexpected Dolt follow-up columns")
        for row in reader:
            symbol = row["symbol"]
            if None in row or symbol not in requested or symbol in found or not row["first_close_date"]:
                raise ValueError("Unexpected Dolt follow-up row")
            observed = date.fromisoformat(row["first_close_date"])
            if not day < observed <= through:
                raise ValueError("Dolt follow-up row was outside the requested window")
            found[symbol] = observed.isoformat()
    return {
        "status": "checked",
        "through": through.isoformat(),
        "first_later_close_date_by_symbol": dict(sorted(found.items())),
        "no_later_close_in_window": sorted(set(requested) - found.keys()),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trading_day", type=date.fromisoformat)
    parser.add_argument("--nyse-sample-file", type=Path, required=True)
    parser.add_argument("--dolt-dir", type=Path, required=True)
    parser.add_argument("--follow-through", type=date.fromisoformat,
                        help="Check missing tickers through this later trading date")
    args = parser.parse_args()
    if args.follow_through is not None and args.follow_through <= args.trading_day:
        parser.error("--follow-through must be later than the TAQ sample date")
    try:
        reference, checks = read_nyse_sample(args.nyse_sample_file, args.trading_day)
        directory = args.dolt_dir.resolve()
        result = benchmark(args.trading_day, reference, dolt_rows(directory, args.trading_day))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"NYSE TAQ benchmark failed: {error}\n")
    if args.follow_through is not None:
        missing = result["exceptions"]
        try:
            result["dolt_follow_up"] = follow_missing(
                directory, args.trading_day, args.follow_through,
                missing["no_dolt_row"] + missing["dolt_row_without_usable_close"],
            )
        except (OSError, ValueError, KeyError) as error:
            result["dolt_follow_up"] = {
                "status": "unavailable", "through": args.follow_through.isoformat(), "error": str(error),
            }
    print(json.dumps(dict(result, trading_date=args.trading_day.isoformat(), reference_checks=checks), indent=2))


if __name__ == "__main__":
    main()

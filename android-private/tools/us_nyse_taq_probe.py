"""Benchmark Dolt closes against the NYSE TAQ public sample's dated Last values."""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re

from us_public_files_probe import MAX_BYTES, dolt_rows, validated_closes

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
    _, prices = validated_closes(day, bars)
    matched = reference.keys() & prices.keys()
    differences = [abs(reference[symbol] - Decimal(str(prices[symbol]))) for symbol in matched]
    exact = differences.count(Decimal(0))
    within = sum(delta <= CENT for delta in differences)
    return {
        "reference_basis": "NYSE TAQ Last, row trade date matches session; NYSE-listed plain symbols",
        "reference_symbols": len(reference),
        "matched_dolt": len(matched),
        "missing_dolt": len(reference) - len(matched),
        "exact_matches": exact,
        "within_one_cent_nonexact": within - exact,
        "differ_over_one_cent": len(matched) - within,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trading_day", type=date.fromisoformat)
    parser.add_argument("--nyse-sample-file", type=Path, required=True)
    parser.add_argument("--dolt-dir", type=Path, required=True)
    args = parser.parse_args()
    try:
        reference, checks = read_nyse_sample(args.nyse_sample_file, args.trading_day)
        result = benchmark(args.trading_day, reference, dolt_rows(args.dolt_dir.resolve(), args.trading_day))
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"NYSE TAQ benchmark failed: {error}\n")
    print(json.dumps(dict(result, trading_date=args.trading_day.isoformat(), reference_checks=checks), indent=2))


if __name__ == "__main__":
    main()

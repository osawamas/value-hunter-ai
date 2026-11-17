"""Measure US listing coverage using public files without an account or API key."""

import argparse
import csv
from datetime import date, datetime
import json
from math import isfinite
from pathlib import Path
import re
import subprocess
from zoneinfo import ZoneInfo

DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/"
SAMPLE = "https://marketparquet.com/api/data/download/stock_daily/"
MAX_BYTES = 4 * 1024 * 1024
CREATED = re.compile(r"File Creation Time: (\d{8}\d{2}:\d{2})\|+")
SYMBOL = re.compile(r"[A-Z0-9.$+^=-]{1,24}")
EQUITY = re.compile(r"\b(?:common|ordinary)\s+(?:stock|shares?)\b", re.I)
OTHER = re.compile(r"\b(?:depositary|depository|preferred|preference|warrants?|rights?|units?|"
                   r"notes?|bonds?|debentures?)\b", re.I)
EXCHANGES = {"A": "NYSE American", "N": "NYSE", "P": "NYSE Arca", "Z": "Cboe BZX",
             "V": "IEX", "M": "NYSE Texas", "F": "Texas Stock Exchange"}


def fetch(url):
    name = url.rsplit("/", 1)[-1]
    try:
        result = subprocess.run(
            ["curl", "--fail", "--silent", "--location", "--max-redirs", "4",
             "--proto", "=https", "--proto-redir", "=https", "--max-time", "25",
             "--max-filesize", str(MAX_BYTES), url],
            capture_output=True, check=False,
        )
    except FileNotFoundError:
        raise ValueError("Install curl to download the public files") from None
    if result.returncode or not result.stdout or len(result.stdout) > MAX_BYTES:
        raise ValueError(f"{name}: public download unavailable (curl {result.returncode})")
    return result.stdout


def read_directory(content, nasdaq):
    if len(content) > MAX_BYTES:
        raise ValueError("Oversized Nasdaq Trader directory file")
    lines = content.decode("utf-8-sig").splitlines()
    footer = CREATED.fullmatch(lines[-1]) if lines else None
    if not footer:
        raise ValueError("Missing Nasdaq Trader file timestamp")
    timestamp = datetime.strptime(footer[1], "%m%d%Y%H:%M")
    reader = csv.DictReader(lines[:-1], delimiter="|")
    ticker_column = "Symbol" if nasdaq else "ACT Symbol"
    expected = {ticker_column, "Security Name", "Test Issue", "ETF",
                "NextShares" if nasdaq else "Exchange"}
    if not expected.issubset(reader.fieldnames or ()):
        raise ValueError("Unexpected Nasdaq Trader directory headers")
    rows = {}
    for row in reader:
        symbol, name = row[ticker_column], row["Security Name"]
        if (None in row or None in row.values() or not SYMBOL.fullmatch(symbol)
                or not name or row["Test Issue"] not in {"Y", "N"} or row["ETF"] not in {"Y", "N"}):
            raise ValueError("Invalid Nasdaq Trader directory row")
        if row["Test Issue"] == "Y" or row["ETF"] == "Y" or row.get("NextShares") == "Y":
            continue
        venue = "Nasdaq" if nasdaq else EXCHANGES.get(row["Exchange"], row["Exchange"])
        if symbol in rows or not venue:
            raise ValueError("Duplicate ticker or missing exchange in Nasdaq directory")
        kind = "other_security" if OTHER.search(name) else (
            "common_or_ordinary_label" if EQUITY.search(name) else "unclassified")
        rows[symbol] = (venue, kind)
    if not rows:
        raise ValueError("Nasdaq Trader directory has no in-scope listings")
    return timestamp, rows


def coverage(day, listings, bars):
    seen = set()
    closes = set()
    for row in bars:
        ticker, close = row["symbol"], row["close"]
        if row["date"] != day or row["asset_type"] != "Stock":
            raise ValueError("Price file contains a different date or asset type")
        if not isinstance(ticker, str) or not SYMBOL.fullmatch(ticker) or ticker in seen:
            raise ValueError("Invalid or duplicate ticker in price file")
        seen.add(ticker)
        if type(close) in (int, float) and isfinite(close) and close > 0:
            closes.add(ticker)
    if not closes or not (closes & listings.keys()):
        raise ValueError("No matching valid prices in the sample")
    groups = {"all_listed_excluding_etfs_and_tests": set(listings)}
    by_exchange = {}
    for symbol, (venue, kind) in listings.items():
        groups.setdefault(kind, set()).add(symbol)
        if kind == "common_or_ordinary_label":
            by_exchange.setdefault(venue, set()).add(symbol)

    def counts(symbols):
        matched = len(closes & symbols)
        return {"listed": len(symbols), "with_close": matched, "without_close": len(symbols) - matched,
                "percent": round(100 * matched / len(symbols), 2)}

    return {"trading_date": day.isoformat(), "sample_price_basis": "split-adjusted",
            "price_rows": len(seen), "valid_close_rows": len(closes),
            "unmatched_price_tickers": len(closes - listings.keys()),
            "groups": {key: counts(value) for key, value in groups.items()},
            "common_or_ordinary_label_by_exchange": {key: counts(value) for key, value in sorted(by_exchange.items())}}


def parquet_rows(content):
    import pyarrow as pa
    import pyarrow.parquet as pq

    if len(content) > MAX_BYTES or not content.startswith(b"PAR1") or not content.endswith(b"PAR1"):
        raise ValueError("Expected a bounded Parquet file; the sample may no longer be available")
    file = pq.ParquetFile(pa.BufferReader(content))
    if not 0 < file.metadata.num_rows <= 50_000:
        raise ValueError("Unexpected row count in daily Parquet file")
    return file.read(columns=["date", "symbol", "asset_type", "close"]).to_pylist()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trading_day", nargs="?", type=date.fromisoformat,
                        help="Date of an evaluation sample; omit to check only the listing files")
    parser.add_argument("--directory-cache", type=Path,
                        help="Replay both original Nasdaq files from this directory")
    parser.add_argument("--sample-file", type=Path, help="Replay an original MarketParquet evaluation sample")
    args = parser.parse_args()
    if args.sample_file and not args.trading_day:
        parser.error("--sample-file requires its trading date")
    if args.trading_day and args.trading_day >= datetime.now(ZoneInfo("America/New_York")).date():
        parser.exit(1, "Use a completed US trading date. The public sample window is limited.\n")
    try:
        observed = {}
        listings = {}
        for name in ("nasdaqlisted.txt", "otherlisted.txt"):
            content = ((args.directory_cache / name).read_bytes() if args.directory_cache
                       else fetch(DIRECTORY + name))
            timestamp, entries = read_directory(content, name == "nasdaqlisted.txt")
            if listings.keys() & entries.keys():
                raise ValueError("Directory files overlap; wait for a consistent refresh")
            listings.update(entries)
            observed[name] = timestamp.isoformat()
        if len({stamp[:10] for stamp in observed.values()}) != 1:
            raise ValueError("Directory files are from different calendar dates")
        result = {"directory_observed_at": observed, "non_etf_non_test_listings": len(listings)}
        if args.trading_day:
            sample = (args.sample_file.read_bytes() if args.sample_file
                      else fetch(SAMPLE + args.trading_day.isoformat() + ".parquet"))
            result.update(coverage(args.trading_day, listings, parquet_rows(sample)))
            result["comparison_basis"] = "observed listings; not a historical listing snapshot"
        print(json.dumps(result, indent=2))
    except ImportError:
        parser.exit(1, "Install pyarrow to read the public price file.\n")
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f"Coverage probe failed: {error}\n")


if __name__ == "__main__":
    main()

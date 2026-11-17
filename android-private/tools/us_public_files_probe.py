"""Measure US listing coverage using public files without an account or API key."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime
import json
from io import BytesIO
from math import isfinite
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from zipfile import BadZipFile
from zoneinfo import ZoneInfo

from us_sec_share_coverage import measure as measure_shares
from us_sec_statement_coverage import measure as measure_statements

DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/"
SEC_DIRECTORY = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_NOTES = "https://www.sec.gov/files/dera/data/financial-statement-notes-data-sets/"
SEC_STATEMENTS = "https://www.sec.gov/files/dera/data/financial-statement-data-sets/"
DIA_HOLDINGS = "https://www.ssga.com/library-content/products/fund-data/etfs/us/holdings-daily-us-en-dia.xlsx"
DOW = "Dow Jones (DIA holdings)"
SAMPLE = "https://marketparquet.com/api/data/download/stock_daily/"
MAX_BYTES = 4 * 1024 * 1024
CREATED = re.compile(r"File Creation Time: (\d{8}\d{2}:\d{2})\|+")
SYMBOL = re.compile(r"[A-Z0-9.$+^=-]{1,24}")
EQUITY = re.compile(r"\b(?:common|ordinary)\s+(?:stock|shares?)\b", re.I)
OTHER = re.compile(r"\b(?:depositary|depository|preferred|preference|warrants?|rights?|units?|"
                   r"notes?|bonds?|debentures?)\b", re.I)
EXCHANGES = {"A": "NYSE American", "N": "NYSE", "P": "NYSE Arca", "Z": "Cboe BZX",
             "V": "IEX", "M": "NYSE Texas", "F": "Texas Stock Exchange"}


def fetch(url, destination=None):
    name = url.rsplit("/", 1)[-1]
    command = ["curl", "--fail", "--silent", "--location", "--max-redirs", "4",
               "--proto", "=https", "--proto-redir", "=https",
               "--max-time", "120" if destination else "25",
               "--max-filesize", str((350_000_000 if url.startswith(SEC_NOTES) else 220_000_000) if destination else MAX_BYTES)]
    if destination:
        command.extend(["--output", str(destination)])
    if url == SEC_DIRECTORY or url.startswith((SEC_STATEMENTS, SEC_NOTES)):
        command.extend(["--user-agent", "VALUE HUNTER AI research https://github.com/osawamas/value-hunter-ai"])
    try:
        result = subprocess.run([*command, url], capture_output=True, check=False)
    except FileNotFoundError:
        raise ValueError("Install curl to download the public files") from None
    if result.returncode or (destination is None and not 0 < len(result.stdout) <= MAX_BYTES):
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


def read_sec_directory(content):
    if len(content) > MAX_BYTES:
        raise ValueError("Oversized SEC company directory")
    payload = json.loads(content)
    if (not isinstance(payload, dict) or payload.get("fields") != ["cik", "name", "ticker", "exchange"]
            or not isinstance(payload.get("data"), list) or not payload["data"]):
        raise ValueError("Unexpected SEC company directory schema")
    rows = defaultdict(set)
    for row in payload["data"]:
        if not isinstance(row, list) or len(row) != 4:
            raise ValueError("Invalid SEC company directory row")
        cik, name, ticker, venue = row
        if (type(cik) is not int or not 0 < cik < 10**10 or not isinstance(name, str) or not name
                or not isinstance(ticker, str) or not SYMBOL.fullmatch(ticker)
                or (venue is not None and not isinstance(venue, str))):
            raise ValueError("Invalid SEC company directory row")
        rows[ticker].add((cik, venue))
    return rows


def read_dia_rows(rows):
    fund, ticker, as_of, _, headers = [next(rows, ()) for _ in range(5)]
    if (not fund or fund[0] != "Fund Name:" or ticker[:2] != ("Ticker Symbol:", "DIA")
            or headers[:2] != ("Name", "Ticker") or headers[6:8] != ("Shares Held", "Local Currency")
            or len(as_of) < 2 or as_of[0] != "Holdings:" or not isinstance(as_of[1], str)):
        raise ValueError("Unexpected State Street DIA holdings layout")
    match = re.fullmatch(r"As of (\d{2})-([A-Z][a-z]{2})-(\d{4})", as_of[1])
    if not match:
        raise ValueError("Missing DIA holdings date")
    day, month, year = match.groups()
    months = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()
    as_of_day = date(int(year), months.index(month) + 1, int(day))
    symbols = set()
    for row in rows:
        if not row or not row[0]:
            break
        name, symbol = row[:2]
        if (name, symbol) == ("US DOLLAR", "-"):
            continue
        if (not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol) or symbol in symbols
                or row[7] != "USD" or type(row[6]) not in (int, float) or not 0 < row[6] < float("inf")):
            raise ValueError("Invalid equity holding in DIA")
        symbols.add(symbol)
    if len(symbols) != 30:
        raise ValueError("Expected 30 equity holdings in DIA")
    return as_of_day, symbols


def load_dia(content):
    from openpyxl import load_workbook

    if not 0 < len(content) <= MAX_BYTES:
        raise ValueError("Unexpected DIA holdings file size")
    workbook = load_workbook(BytesIO(content), read_only=True, data_only=True)
    try:
        return read_dia_rows(iter(workbook["holdings"].iter_rows(max_col=8, values_only=True)))
    finally:
        workbook.close()


def issuers_requiring_class_review(listings, sec):
    symbols_by_issuer = defaultdict(set)
    for ticker, candidates in sec.items():
        symbol = ticker
        if symbol not in listings and re.fullmatch(r"[A-Z]+-[A-Z]", symbol):
            dotted = symbol.replace("-", ".")
            if dotted in listings:
                symbol = dotted
        if symbol in listings and listings[symbol][1] == "other_security":
            continue
        for cik, _ in candidates:
            symbols_by_issuer[cik].add(symbol)
    return {cik for cik, symbols in symbols_by_issuer.items() if len(symbols) > 1}


def filing_join(listings, closes, sec, statement_files=(), day=None, focus=None, notes_files=()):
    # The SEC may label NYSE-group listings simply as NYSE.
    venues = {"Nasdaq": {"Nasdaq"}, "NYSE": {"NYSE"}, "NYSE American": {"NYSE", "NYSE American"},
              "NYSE Arca": {"NYSE", "NYSE Arca"}, "Cboe BZX": {"CBOE"},
              "Texas Stock Exchange": {"TXSE"}}
    focus = focus or {}
    common = {ticker for ticker, (_, kind) in listings.items() if kind == "common_or_ordinary_label"}
    scope = common.union(*(focus.values()))
    matches = {}
    diagnostics = Counter()
    for ticker, (venue, kind) in listings.items():
        if ticker not in scope or kind == "other_security":
            continue
        candidates = sec.get(ticker, set())
        # SEC uses BRK-B where Nasdaq Trader uses BRK.B. Restrict this to share-class suffixes.
        if re.fullmatch(r"[A-Z]+\.[A-Z]", ticker):
            alias = ticker.replace(".", "-")
            if alias not in listings:
                candidates = candidates | sec.get(alias, set())
        compatible = {cik for cik, exchange in candidates if exchange in venues.get(venue, set())}
        if len(compatible) == 1:
            matches[ticker] = next(iter(compatible))
        elif ticker in common:
            reason = ("ambiguous_sec_issuer" if len(compatible) > 1 else
                      "sec_exchange_unconfirmed" if candidates else "no_sec_ticker")
            diagnostics[reason] += 1

    base_matches = common & matches.keys()
    issuer_counts = Counter(matches[ticker] for ticker in base_matches)
    with_both = closes & base_matches
    result = {
        "listed_with_sec_issuer": len(base_matches),
        "listed_with_close_and_sec_issuer": len(with_both),
        "with_close_missing_sec_issuer": sum(
            ticker in closes and ticker not in matches
            for ticker, (_, kind) in listings.items() if kind == "common_or_ordinary_label"
        ),
        "with_sec_issuer_missing_close": len(base_matches - closes),
        "with_both_sharing_issuer_with_another_listed_class": sum(
            issuer_counts[matches[ticker]] > 1 for ticker in with_both
        ),
        "unlinked": dict(sorted(diagnostics.items())),
    }
    grouped = {name: {ticker: matches[ticker] for ticker in symbols & closes & matches.keys()}
               for name, symbols in focus.items()}
    if focus:
        result["with_close_and_sec_issuer_by_market_or_index"] = {
            name: len(tickers) for name, tickers in grouped.items()
        }
    securities = {ticker: matches[ticker] for ticker in with_both}
    share_dates = None
    if notes_files:
        result["cover_share_archive_coverage"], share_dates = measure_shares(
            notes_files, day, securities, grouped, issuers_requiring_class_review(listings, sec)
        )
    if statement_files:
        result["statement_archive_coverage"] = measure_statements(
            statement_files, day, securities, grouped, share_dates
        )
    return result


def coverage(day, listings, bars, sec=None, statement_files=(), dow=None, notes_files=()):
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

    result = {"trading_date": day.isoformat(), "sample_price_basis": "split-adjusted",
            "price_rows": len(seen), "valid_close_rows": len(closes),
            "unmatched_price_tickers": len(closes - listings.keys()),
            "groups": {key: counts(value) for key, value in groups.items()},
            "common_or_ordinary_label_by_exchange": {key: counts(value) for key, value in sorted(by_exchange.items())}}
    focus = {name: by_exchange.get(name, set()) for name in ("NYSE", "Nasdaq")}
    if dow is not None:
        as_of, symbols = dow
        result["dia_holdings_comparison"] = {"as_of": as_of.isoformat(), "symbols": len(symbols)}
        if as_of != day:
            result["dia_holdings_comparison"]["status"] = "Holdings date differs from the trading date"
        else:
            listed = symbols & listings.keys()
            focus[DOW] = listed
            result["dia_holdings_comparison"].update({
                "listed": len(listed),
                "with_close": len(listed & closes),
                "listing_venues": dict(Counter(listings[ticker][0] for ticker in sorted(listed))),
            })
    if sec is not None:
        result["common_or_ordinary_label_sec_join"] = filing_join(listings, closes, sec, statement_files, day, focus, notes_files)
    return result


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
    parser.add_argument("--with-sec", action="store_true", help="Include the SEC issuer directory in the comparison")
    parser.add_argument("--sec-file", type=Path, help="Replay the original SEC issuer directory")
    dow = parser.add_mutually_exclusive_group()
    dow.add_argument("--dow", action="store_true", help="Check the dated State Street DIA holdings")
    dow.add_argument("--dow-file", type=Path, help="Replay the original DIA holdings file")
    statements = parser.add_mutually_exclusive_group()
    statements.add_argument("--sec-quarter", action="append", default=[], help="Download a public SEC statements ZIP, e.g. 2026q3")
    statements.add_argument("--sec-statement-file", type=Path, action="append", default=[], help="Replay the original SEC statements ZIP")
    notes = parser.add_mutually_exclusive_group()
    notes.add_argument("--sec-notes", action="append", default=[], help="Download a public SEC notes ZIP, e.g. 2026-10")
    notes.add_argument("--sec-notes-file", type=Path, action="append", default=[], help="Replay an original SEC notes ZIP")
    args = parser.parse_args()
    check_notes = args.sec_notes or args.sec_notes_file
    if any(not re.fullmatch(r"20[0-9]{2}-(0[1-9]|1[0-2])", month) for month in args.sec_notes):
        parser.error("--sec-notes expects YYYY-MM")
    if len(check_notes) > 4 or len(check_notes) != len(set(check_notes)):
        parser.error("Use up to four distinct monthly notes archives")
    check_statements = args.sec_quarter or args.sec_statement_file
    if any(not re.fullmatch(r"20[0-9]{2}q[1-4]", quarter) for quarter in args.sec_quarter):
        parser.error("--sec-quarter expects YYYYqN")
    if len(check_statements) > 8 or len(check_statements) != len(set(check_statements)):
        parser.error("Use up to eight distinct statement archives")
    if (args.sample_file or args.with_sec or args.sec_file or check_statements
            or args.dow or args.dow_file or check_notes) and not args.trading_day:
        parser.error("The sample, SEC and Dow options require a trading date")
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
            sec = None
            if args.with_sec or args.sec_file or check_statements or check_notes:
                content = args.sec_file.read_bytes() if args.sec_file else fetch(SEC_DIRECTORY)
                sec = read_sec_directory(content)
            holdings = None
            if args.dow or args.dow_file:
                holdings = load_dia(args.dow_file.read_bytes() if args.dow_file else fetch(DIA_HOLDINGS))
            with TemporaryDirectory() as directory:
                statement_files = list(args.sec_statement_file)
                for quarter in args.sec_quarter:
                    filename = quarter + ".zip"
                    destination = Path(directory) / filename
                    fetch(SEC_STATEMENTS + filename, destination)
                    statement_files.append(destination)
                notes_files = list(args.sec_notes_file)
                for month in args.sec_notes:
                    filename = month.replace("-", "_") + "_notes.zip"
                    destination = Path(directory) / filename
                    fetch(SEC_NOTES + filename, destination)
                    notes_files.append(destination)
                result.update(coverage(args.trading_day, listings, parquet_rows(sample),
                                       sec, statement_files, holdings, notes_files))
            if notes_files:
                result["sec_notes_archives"] = [path.name for path in notes_files]
            if statement_files:
                result["sec_statement_archives"] = [path.name for path in statement_files]
            result["comparison_basis"] = "observed listings; not a historical listing snapshot"
        print(json.dumps(result, indent=2))
    except ImportError as error:
        parser.exit(1, f"A file reader dependency is missing: {error.name} (pyarrow for prices, openpyxl for DIA).\n")
    except (OSError, ValueError, KeyError, BadZipFile) as error:
        parser.exit(1, f"Coverage probe failed: {error}\n")


if __name__ == "__main__":
    main()

"""Measure US listing coverage using public files without an account or API key."""

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime
from decimal import Decimal
from email.utils import parsedate_to_datetime
import json
import os
from io import BytesIO, StringIO
from math import isfinite
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit
from xml.etree import ElementTree
from zipfile import BadZipFile
from zoneinfo import ZoneInfo

from us_sec_share_coverage import measure as measure_shares
from us_sec_statement_coverage import measure as measure_statements

DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/"
HALTS = "https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts"
HALT_NS = {"n": "http://www.nasdaqtrader.com/"}
DIRECTORY_FILES = ("nasdaqlisted.txt", "otherlisted.txt")
SEC_DIRECTORY = "https://www.sec.gov/files/company_tickers_exchange.json"
SEC_INDEX = "https://www.sec.gov/Archives/edgar/full-index/"
SEC_ARCHIVES = "https://www.sec.gov/Archives/edgar/"
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


def fetch(url, destination=None, max_bytes=None):
    name = url.rsplit("/", 1)[-1]
    limit = max_bytes or ((350_000_000 if url.startswith(SEC_NOTES) else 220_000_000)
                          if destination else MAX_BYTES)
    command = ["curl", "--fail", "--silent", "--location", "--max-redirs", "4",
               "--proto", "=https", "--proto-redir", "=https",
               "--max-time", "120" if destination else "25",
               "--max-filesize", str(limit)]
    if destination:
        command.extend(["--output", str(destination)])
    if url == SEC_DIRECTORY or url.startswith((SEC_STATEMENTS, SEC_NOTES, SEC_ARCHIVES)):
        command.extend(["--user-agent", "VALUE HUNTER AI research https://github.com/osawamas/value-hunter-ai"])
    try:
        result = subprocess.run([*command, url], capture_output=True, check=False)
    except FileNotFoundError:
        raise ValueError("Install curl to download the public files") from None
    if result.returncode or (destination is None and not 0 < len(result.stdout) <= limit):
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


def filing_join(listings, closes, sec, statement_files=(), day=None, focus=None, notes_files=(), indexes=None):
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
            notes_files, day, securities, grouped, issuers_requiring_class_review(listings, sec), indexes
        )
    if statement_files:
        result["statement_archive_coverage"] = measure_statements(
            statement_files, day, securities, grouped, share_dates
        )
    return result


def validated_closes(day, bars):
    seen = set()
    closes = {}
    for row in bars:
        ticker, close = row["symbol"], row["close"]
        if row["date"] != day or row["asset_type"] != "Stock":
            raise ValueError("Price file contains a different date or asset type")
        if not isinstance(ticker, str) or not SYMBOL.fullmatch(ticker) or ticker in seen:
            raise ValueError("Invalid or duplicate ticker in price file")
        seen.add(ticker)
        if type(close) in (int, float) and isfinite(close) and close > 0:
            closes[ticker] = close
    return seen, closes


def read_halt_notices(content, day):
    """Return notices whose reported date interval strictly contains the session."""
    if len(content) > MAX_BYTES:
        raise ValueError("Oversized Nasdaq Trader halt feed")
    channel = ElementTree.fromstring(content).find("channel")
    if channel is None or channel.findtext("description") != "NASDAQ Trade Halts":
        raise ValueError("Unexpected Nasdaq Trader halt feed")
    published = parsedate_to_datetime(channel.findtext("pubDate", ""))
    if published.tzinfo is None or published.astimezone(ZoneInfo("America/New_York")).date() <= day:
        raise ValueError("Halt feed must be dated after the target US trading date")
    items = channel.findall("item")
    if channel.findtext("n:numItems", namespaces=HALT_NS) != str(len(items)):
        raise ValueError("Incomplete Nasdaq Trader halt feed")
    matches = defaultdict(set)
    for item in items:
        values = [item.findtext(f"n:{key}", namespaces=HALT_NS)
                  for key in ("IssueSymbol", "Market", "HaltDate", "ResumptionDate")]
        if any(value is None for value in values):
            raise ValueError("Incomplete Nasdaq Trader halt item")
        symbol, market, halted, resumed = (value.strip() for value in values)
        start = datetime.strptime(halted, "%m/%d/%Y").date()
        end = datetime.strptime(resumed, "%m/%d/%Y").date() if resumed else None
        if not SYMBOL.fullmatch(symbol) or (end is not None and end < start):
            raise ValueError("Invalid Nasdaq Trader halt item")
        if start < day and (end is None or day < end):
            matches[market].add(symbol)
    return published.isoformat(), matches


def missing_history(missing, history):
    not_seen = set(missing)
    last_seen = {}
    for day, closes in sorted(history.items(), reverse=True):
        matched = not_seen & closes.keys()
        last_seen[day.isoformat()] = len(matched)
        not_seen -= matched
    return {
        "missing_on_target_date": len(missing),
        "last_seen_by_checked_earlier_date": last_seen,
        "missing_on_all_checked_dates": len(not_seen),
    }


def read_listing_events(content):
    """Load sourced listing events for review, without creating ticker aliases."""
    if len(content) > MAX_BYTES:
        raise ValueError("Oversized listing evidence file")
    rows = json.loads(content)
    if not isinstance(rows, list):
        raise ValueError("Listing evidence must be an array")
    events = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid listing evidence row")
        market, symbol, day, kind, source = (row.get(key) for key in
                                             ("market", "symbol", "date", "kind", "source"))
        previous = row.get("previous_symbol")
        if (market not in ("NYSE", "Nasdaq") or not isinstance(symbol, str) or not SYMBOL.fullmatch(symbol)
                or kind not in ("announced_start", "effective_symbol_change") or not isinstance(day, str)
                or not isinstance(source, str)):
            raise ValueError("Invalid listing evidence fields")
        address = urlsplit(source)
        if address.scheme != "https" or not address.hostname or address.username or address.password:
            raise ValueError("Listing evidence needs a public HTTPS source")
        if kind == "effective_symbol_change":
            if not isinstance(previous, str) or not SYMBOL.fullmatch(previous) or previous == symbol:
                raise ValueError("Symbol change needs a distinct previous symbol")
        elif previous is not None:
            raise ValueError("An announced start does not link a previous symbol")
        key = market, symbol
        if key in events:
            raise ValueError("Duplicate listing evidence for a market and ticker")
        events[key] = (date.fromisoformat(day), kind, source, previous)
    return events


def missing_listing_events(day, market, missing, primary, reference, events):
    matches = []
    for symbol in sorted(missing):
        event = events.get((market, symbol))
        if event is None:
            continue
        effective, kind, source, previous = event
        relation = ("after_target" if effective > day else "on_target" if effective == day else "before_target")
        item = {"symbol": symbol, "date": effective.isoformat(), "relation_to_target": relation,
                "kind": kind, "source": source}
        if previous is not None:
            item["previous_symbol"] = previous
            if effective > day:
                item["previous_symbol_has_target_close"] = previous in primary or previous in reference
        matches.append(item)
    return matches


def compare_closes(day, primary, reference_bars, focus, history_bars=None, halt_notices=None, listing_events=None, *, include_missing_symbols=False):
    _, reference = validated_closes(day, reference_bars)
    if not reference:
        raise ValueError("No valid closes in the comparison sample")
    history = {}
    for earlier, bars in (history_bars or {}).items():
        if earlier >= day:
            raise ValueError("Coverage history dates must precede the target date")
        _, closes = validated_closes(earlier, bars)
        if not closes:
            raise ValueError("No valid closes in a historical Dolt session")
        history[earlier] = closes
    common = primary.keys() & reference.keys()
    one_cent = Decimal("0.01")
    within = {ticker for ticker in common
              if abs(Decimal(str(primary[ticker])) - Decimal(str(reference[ticker]))) <= one_cent}

    result = {}
    for name, symbols in focus.items():
        primary_symbols = symbols & primary.keys()
        reference_symbols = symbols & reference.keys()
        union = primary_symbols | reference_symbols
        both = primary_symbols & reference_symbols
        agrees = len(within & symbols)
        result[name] = {
            "listed": len(symbols),
            "only_dolt": len(primary_symbols - reference_symbols),
            "only_marketparquet": len(reference_symbols - primary_symbols),
            "neither": len(symbols - union),
            "both_within_one_cent": agrees,
            "both_differ_over_one_cent": len(both) - agrees,
            "with_either": len(union),
        }
        if include_missing_symbols:
            result[name]["only_marketparquet_symbols"] = sorted(reference_symbols - primary_symbols)
            result[name]["missing_from_both_symbols"] = sorted(symbols - union)
        if listing_events is not None and name in ("NYSE", "Nasdaq"):
            result[name]["missing_listing_events"] = missing_listing_events(
                day, name, symbols - union, primary, reference, listing_events
            )
        if halt_notices is not None and name in ("NYSE", "Nasdaq"):
            published, markets = halt_notices
            missing = symbols - union
            reported = missing & markets.get(name.upper(), set())
            result[name]["missing_halt_notices"] = {
                "feed_published_at": published,
                "with_notice_covering_date": len(reported),
                "symbols_with_notice": sorted(reported),
                "without_matching_notice_in_feed": len(missing - reported),
            }
        if history:
            result[name]["missing_dolt_history"] = missing_history(symbols - union, history)
    return result


def coverage(day, listings, bars, sec=None, statement_files=(), dow=None, notes_files=(), indexes=None, price_basis="split-adjusted",
             comparison_bars=None, history_bars=None, halt_notices=None, listing_events=None, *, include_missing_symbols=False):
    seen, prices = validated_closes(day, bars)
    closes = prices.keys()
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

    result = {"trading_date": day.isoformat(), "sample_price_basis": price_basis,
            "price_rows": len(seen), "valid_close_rows": len(closes),
            "unmatched_price_tickers": len(closes - listings.keys()),
            "groups": {key: counts(value) for key, value in groups.items()},
            "common_or_ordinary_label_by_exchange": {key: counts(value) for key, value in sorted(by_exchange.items())}}
    focus = {name: by_exchange.get(name, set()) for name in ("NYSE", "Nasdaq")}
    if include_missing_symbols:
        result["missing_close_symbols_by_exchange"] = {
            venue: sorted(symbols - closes) for venue, symbols in focus.items()
        }
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
    if comparison_bars is not None:
        result["dolt_marketparquet_comparison"] = compare_closes(
            day, prices, comparison_bars, focus, history_bars, halt_notices, listing_events,
            include_missing_symbols=include_missing_symbols,
        )
    if sec is not None:
        result["common_or_ordinary_label_sec_join"] = filing_join(listings, closes, sec, statement_files, day, focus, notes_files, indexes)
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


def dolt_rows(directory, day):
    if not (directory / ".dolt").is_dir():
        raise ValueError("--dolt-dir must point to a local Dolt clone")
    query = ("SELECT act_symbol AS symbol, date AS trading_date, close "
             f"FROM ohlcv WHERE date = '{day.isoformat()}' ORDER BY act_symbol")
    try:
        result = subprocess.run(["dolt", "sql", "-r", "csv", "-q", query], cwd=directory,
                                capture_output=True, timeout=45, check=False)
    except FileNotFoundError:
        raise ValueError("Install Dolt to read the local price database") from None
    except subprocess.TimeoutExpired:
        raise ValueError("The local Dolt daily query did not finish") from None
    if result.returncode or not 0 < len(result.stdout) <= MAX_BYTES:
        raise ValueError("The local Dolt market query failed")
    return read_dolt_csv(result.stdout)


def read_dolt_csv(content):
    reader = csv.DictReader(StringIO(content.decode("utf-8")))
    if reader.fieldnames != ["symbol", "trading_date", "close"]:
        raise ValueError("Unexpected Dolt daily market columns")
    rows = []
    for row in reader:
        if len(rows) >= 50_000 or None in row or None in row.values():
            raise ValueError("Unexpected row count or format in Dolt daily market data")
        # A corrupt, non-finite or non-positive close is not a usable trading price.
        # Preserve NULL as missing so coverage reports it rather than fabricating a close.
        raw = row["close"]
        try:
            close = float(raw) if raw not in ("", "NULL") else None
            trading_day = date.fromisoformat(row["trading_date"])
        except (ValueError, OverflowError):
            raise ValueError("Invalid Dolt date or close") from None
        if close is not None and (not isfinite(close) or close <= 0):
            raise ValueError("Invalid Dolt close: expected a finite positive price")
        rows.append({"symbol": row["symbol"], "date": trading_day,
                     "close": close, "asset_type": "Stock"})
    return rows



def load_listing_directories(directory=None):
    observed = {}
    listings = {}
    originals = {}
    for name in DIRECTORY_FILES:
        content = (directory / name).read_bytes() if directory is not None else fetch(DIRECTORY + name)
        timestamp, entries = read_directory(content, name == "nasdaqlisted.txt")
        if listings.keys() & entries.keys():
            raise ValueError("Directory files overlap; wait for a consistent refresh")
        listings.update(entries)
        observed[name] = timestamp.isoformat()
        originals[name] = content
    if len({stamp[:10] for stamp in observed.values()}) != 1:
        raise ValueError("Directory files are from different calendar dates")
    return observed, listings, originals


def save_listing_snapshot(root, day, originals):
    root.mkdir(parents=True, exist_ok=True)
    target = root / day.isoformat()
    with TemporaryDirectory(prefix=".listing-", dir=root) as staging:
        snapshot = Path(staging) / "snapshot"
        snapshot.mkdir()
        for name in DIRECTORY_FILES:
            (snapshot / name).write_bytes(originals[name])
        # A complete, nonempty destination directory wins if another capture finished first.
        try:
            os.rename(snapshot, target)
        except OSError:
            if not target.is_dir():
                raise
            observed, _, _ = load_listing_directories(target)
            require_listing_date(day, observed)
            return "already_saved"
    return "saved"


def require_listing_date(day, observed):
    if any(stamp[:10] != day.isoformat() for stamp in observed.values()):
        raise ValueError(f"Nasdaq directory pair does not match requested date {day}")


def listing_snapshot_assessment(trading_day, observed):
    """Flag a later directory snapshot; never treat it as a historical universe."""
    dates = [date.fromisoformat(value[:10]) for value in observed.values()]
    if len(dates) != 2 or dates[0] != dates[1]:
        raise ValueError("Inconsistent directory snapshot dates")
    lag = (dates[0] - trading_day).days
    return {
        "trading_date": trading_day.isoformat(),
        "directory_date": dates[0].isoformat(),
        "calendar_day_offset": lag,
        "historical_universe_verified": False,
        "status": ("future_directory_snapshot" if lag > 0 else
                   "prior_directory_snapshot" if lag < 0 else
                   "same_day_directory_unverified"),
        "note": "Coverage uses an observed directory, not verified point-in-time listings",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trading_day", nargs="?", type=date.fromisoformat,
                        help="Date of an evaluation sample; omit to check only the listing files")
    directories = parser.add_mutually_exclusive_group()
    directories.add_argument("--directory-cache", type=Path,
                             help="Replay both original Nasdaq files from this directory")
    directories.add_argument("--save-directory-to", type=Path,
                             help="Save today's live Nasdaq directory pair under ROOT/YYYY-MM-DD")
    directories.add_argument("--directory-archive", type=Path,
                             help="Read the exact trading day's saved pair from ROOT/YYYY-MM-DD")
    prices = parser.add_mutually_exclusive_group()
    prices.add_argument("--sample-file", type=Path, help="Replay an original MarketParquet evaluation sample")
    prices.add_argument("--dolt-dir", type=Path, help="Read closes from a local post-no-preference/stocks clone")
    comparisons = parser.add_mutually_exclusive_group()
    comparisons.add_argument("--compare-marketparquet", action="store_true",
                             help="Compare Dolt closes with the public split-adjusted sample")
    comparisons.add_argument("--comparison-sample-file", type=Path,
                             help="Compare Dolt closes with a saved original MarketParquet sample")
    parser.add_argument("--history-date", action="append", default=[], type=date.fromisoformat,
                        help="Check missing symbols on an earlier completed Dolt session (repeatable)")
    halts = parser.add_mutually_exclusive_group()
    halts.add_argument("--with-halts", action="store_true", help="Check missing closes against the Nasdaq Trader halt feed")
    halts.add_argument("--halt-feed-file", type=Path, help="Replay a saved Nasdaq Trader halt RSS file")
    parser.add_argument("--listing-evidence-file", type=Path,
                        help="Attach sourced listing events to the two-source missing-price report")
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
    indexes = parser.add_mutually_exclusive_group()
    indexes.add_argument("--sec-index-quarter", action="append", default=[],
                         help="Download an EDGAR filing index by quarter, e.g. 2026q4")
    indexes.add_argument("--sec-index-file", action="append", default=[],
                         help="Replay an original EDGAR index as YYYYqN=FILE")
    args = parser.parse_args()
    if (args.compare_marketparquet or args.comparison_sample_file) and not args.dolt_dir:
        parser.error("Price comparison requires --dolt-dir")
    if (args.with_halts or args.halt_feed_file) and not (args.compare_marketparquet or args.comparison_sample_file):
        parser.error("Halt notice matching requires a price comparison")
    if args.listing_evidence_file and not (args.compare_marketparquet or args.comparison_sample_file):
        parser.error("Listing evidence requires a price comparison")
    if args.history_date and (not (args.compare_marketparquet or args.comparison_sample_file)
                              or not args.trading_day or len(args.history_date) > 5
                              or len(set(args.history_date)) != len(args.history_date)
                              or any(day >= args.trading_day for day in args.history_date)):
        parser.error("History needs a price comparison and up to five distinct earlier dates")
    index_paths = {}
    for item in args.sec_index_file or args.sec_index_quarter:
        name, separator, filename = item.partition("=")
        match = re.fullmatch(r"(20[0-9]{2})q([1-4])", name)
        if not match or (args.sec_index_file and (not separator or not filename)) or (args.sec_index_quarter and separator):
            parser.error("Use YYYYqN for --sec-index-quarter or YYYYqN=FILE for --sec-index-file")
        key = tuple(map(int, match.groups()))
        if key in index_paths:
            parser.error("Each EDGAR quarter can be specified once")
        index_paths[key] = Path(filename) if filename else None
    if len(index_paths) > 4 or (index_paths and not (args.sec_notes or args.sec_notes_file)):
        parser.error("Use up to four EDGAR quarters with at least one SEC notes archive")
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
    if args.directory_archive and not args.trading_day:
        parser.error("--directory-archive requires a trading date")
    if args.save_directory_to and args.trading_day:
        parser.error("--save-directory-to is a directory-only operation; omit the trading date")
    if (args.sample_file or args.dolt_dir or args.with_sec or args.sec_file or check_statements
            or args.dow or args.dow_file or check_notes) and not args.trading_day:
        parser.error("The sample, SEC and Dow options require a trading date")
    ny_day = datetime.now(ZoneInfo("America/New_York")).date()
    if args.trading_day and args.trading_day >= ny_day:
        parser.exit(1, "Use a completed US trading date. The public sample window is limited.\n")
    try:
        directory = args.directory_cache
        archive_status = None
        if args.directory_archive:
            directory = args.directory_archive / args.trading_day.isoformat()
        elif args.save_directory_to:
            target = args.save_directory_to / ny_day.isoformat()
            if target.is_dir():
                directory = target
                archive_status = "already_saved"
        observed, listings, originals = load_listing_directories(directory)
        if args.directory_archive:
            require_listing_date(args.trading_day, observed)
        if args.save_directory_to:
            require_listing_date(ny_day, observed)
            if archive_status is None:
                archive_status = save_listing_snapshot(args.save_directory_to, ny_day, originals)
                if archive_status == "already_saved":
                    observed, listings, _ = load_listing_directories(target)
                    require_listing_date(ny_day, observed)
        result = {"directory_observed_at": observed, "non_etf_non_test_listings": len(listings)}
        if archive_status is not None:
            result["directory_archive_status"] = archive_status
        if args.trading_day:
            if args.dolt_dir:
                bars = dolt_rows(args.dolt_dir.resolve(), args.trading_day)
                price_basis = "Dolt reported close (basis under evaluation)"
            else:
                sample = (args.sample_file.read_bytes() if args.sample_file
                          else fetch(SAMPLE + args.trading_day.isoformat() + ".parquet"))
                bars = parquet_rows(sample)
                price_basis = "split-adjusted"
            comparison_bars = None
            if args.compare_marketparquet or args.comparison_sample_file:
                content = (args.comparison_sample_file.read_bytes() if args.comparison_sample_file
                           else fetch(SAMPLE + args.trading_day.isoformat() + ".parquet"))
                comparison_bars = parquet_rows(content)
            history_bars = {earlier: dolt_rows(args.dolt_dir.resolve(), earlier) for earlier in args.history_date}
            halt_notices = None
            if args.with_halts or args.halt_feed_file:
                feed = args.halt_feed_file.read_bytes() if args.halt_feed_file else fetch(HALTS)
                halt_notices = read_halt_notices(feed, args.trading_day)
            listing_events = None
            if args.listing_evidence_file:
                listing_events = read_listing_events(args.listing_evidence_file.read_bytes())
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
                for (year, part), supplied in index_paths.items():
                    if supplied is None:
                        destination = Path(directory) / f"{year}q{part}-master.idx"
                        fetch(f"{SEC_INDEX}{year}/QTR{part}/master.idx", destination)
                        index_paths[year, part] = destination
                result.update(coverage(args.trading_day, listings, bars,
                                       sec, statement_files, holdings, notes_files, index_paths, price_basis,
                                       comparison_bars, history_bars, halt_notices, listing_events))
            if notes_files:
                result["sec_notes_archives"] = [path.name for path in notes_files]
            if statement_files:
                result["sec_statement_archives"] = [path.name for path in statement_files]
            result["comparison_basis"] = "observed listings; not a historical listing snapshot"
            result["listing_snapshot_assessment"] = listing_snapshot_assessment(args.trading_day, observed)
        print(json.dumps(result, indent=2))
    except ImportError as error:
        parser.exit(1, f"A file reader dependency is missing: {error.name} (pyarrow for prices, openpyxl for DIA).\n")
    except (OSError, ValueError, KeyError, BadZipFile, ElementTree.ParseError) as error:
        parser.exit(1, f"Coverage probe failed: {error}\n")


if __name__ == "__main__":
    main()

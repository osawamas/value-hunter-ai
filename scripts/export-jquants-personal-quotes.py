#!/usr/bin/env python3
"""Export J-Quants daily unadjusted closes for a local market research session."""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ENDPOINT = "https://api.jquants.com/v2/equities/bars/daily"


def code4(value):
    if not re.fullmatch(r"[0-9][0-9A-Z]{3}", value):
        raise argparse.ArgumentTypeError("use a four-character common stock code")
    return value


def trading_date(value):
    try:
        day = date.fromisoformat(value)
        if day.isoformat() == value:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("use YYYY-MM-DD")


def fetch_page(query, api_key):
    request = Request(ENDPOINT + "?" + urlencode(query), headers={"x-api-key": api_key})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def daily_bars(query, api_key, fetch):
    query = dict(query)
    tokens = set()
    while True:
        page = fetch(query, api_key)
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise ValueError("the daily price response lacks a data array")
        yield from page["data"]
        token = page.get("pagination_key")
        if token is None:
            return
        if not isinstance(token, str) or not token or token in tokens:
            raise ValueError("invalid or repeated pagination key")
        tokens.add(token)
        query["pagination_key"] = token


def close_value(item):
    close = item["C"]
    if close is not None and (type(close) not in (int, float) or not math.isfinite(close) or close <= 0):
        raise ValueError("invalid unadjusted close in the response")
    return close


def record_close(closes, key, close):
    if close is None:
        return
    if key in closes and closes[key] != close:
        raise ValueError("conflicting closes for the same code and date")
    closes[key] = close


def collect_quotes(code, start, end, api_key, fetch=fetch_page):
    query = {"code": code, "from": start, "to": end}
    closes = {}
    for item in daily_bars(query, api_key, fetch):
        if item["Code"] not in {code, code + "0"}:
            raise ValueError("the response contained an unexpected stock code")
        day = trading_date(item["Date"])
        if not start <= day <= end:
            raise ValueError("the response contained a date outside the requested interval")
        record_close(closes, day, close_value(item))
    return [(f"JP:{code}", day, "JPY", closes[day]) for day in sorted(closes)]


def collect_session_quotes(codes, day, api_key, fetch=fetch_page):
    # The market-wide endpoint has five-character IDs. A nonzero suffix
    # represents a different security and must not match a common-stock input.
    ids = {code + "0": code for code in codes}
    closes = {}
    for item in daily_bars({"date": day}, api_key, fetch):
        if item["Date"] != day:
            raise ValueError("the response contained an unexpected trading date")
        code = ids.get(item["Code"])
        if code is not None:
            record_close(closes, code, close_value(item))
    return [(f"JP:{code}", day, "JPY", closes[code]) for code in sorted(closes)]


def write_quotes(stream, rows):
    writer = csv.writer(stream, lineterminator="\n")
    writer.writerow(("market_id", "date", "currency", "close"))
    writer.writerows(rows)


def save_snapshot(path, rows):
    temporary_path = None
    try:
        with NamedTemporaryFile(mode="w", encoding="utf-8", newline="", dir=path.parent,
                                prefix=".jquants-", delete=False) as stream:
            temporary_path = Path(stream.name)
            write_quotes(stream, rows)
        digest = hashlib.sha256(temporary_path.read_bytes()).hexdigest()
        temporary_path.replace(path)
        return digest
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


def report_provenance(rows, codes, start, end, sha256, retrieved_at):
    record = {
        "provider": "J-Quants",
        "endpoint": ENDPOINT,
        "purpose": "personal",
        "price_basis": "unadjusted_close",
        "retrieved_at_utc": retrieved_at.isoformat(),
        "requested_period": {"first": start, "last": end},
        "requested_codes": codes,
        "observations": len(rows),
        "csv_sha256": sha256,
    }
    print(json.dumps(record), file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=trading_date, help="Get selected common-stock closes from one market-wide trading session")
    parser.add_argument("--from", dest="from_date", type=trading_date)
    parser.add_argument("--to", dest="to_date", type=trading_date)
    parser.add_argument("--output", type=Path, help="Atomically replace this local CSV after validation")
    parser.add_argument("--require-all", action="store_true", help="Require at least one close for every requested code")
    parser.add_argument("--provenance", action="store_true", help="Write a JSON receipt to stderr with --output")
    parser.add_argument("codes", type=code4, nargs="+")
    args = parser.parse_args()
    if args.date and (args.from_date or args.to_date):
        parser.error("--date cannot be combined with --from or --to")
    if not args.date and not (args.from_date and args.to_date):
        parser.error("provide --date or both --from and --to")
    if args.from_date and args.from_date > args.to_date:
        parser.error("--from must be on or before --to")
    if args.provenance and not args.output:
        parser.error("--provenance requires --output")
    if args.provenance and not args.require_all:
        parser.error("--provenance requires --require-all")
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        parser.error("set JQUANTS_API_KEY using your personal account")
    codes = list(dict.fromkeys(args.codes))
    try:
        if args.date:
            rows = collect_session_quotes(codes, args.date, api_key)
        else:
            rows = [row for code in codes for row in collect_quotes(code, args.from_date, args.to_date, api_key)]
    except HTTPError as error:
        parser.exit(1, f"J-Quants returned HTTP {error.code}. Check your plan, date range and API key.\n")
    except (URLError, TimeoutError, KeyError, TypeError, ValueError, argparse.ArgumentTypeError):
        parser.exit(1, "J-Quants response could not be retrieved or validated.\n")
    if not rows:
        parser.exit(1, "No closes returned for the requested interval.\n")
    retrieved_at = datetime.now(timezone.utc)
    returned = {row[0][3:] for row in rows}
    missing = sorted(set(codes) - returned)
    if missing:
        message = "No close returned for: " + ", ".join(missing)
        if args.require_all:
            parser.exit(1, message + "\n")
        print(message, file=sys.stderr)
    if args.output is None:
        write_quotes(sys.stdout, rows)
    else:
        try:
            digest = save_snapshot(args.output, rows)
        except OSError:
            parser.exit(1, "Could not save the local snapshot. Check the destination directory and permissions.\n")
        if args.provenance:
            report_provenance(rows, codes, args.date or args.from_date, args.date or args.to_date, digest, retrieved_at)


if __name__ == "__main__":
    main()

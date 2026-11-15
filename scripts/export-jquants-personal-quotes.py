#!/usr/bin/env python3
"""Export J-Quants daily unadjusted closes for a local market research session."""

import argparse
import csv
import json
import math
import os
import re
import sys
from datetime import date
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


def collect_quotes(code, start, end, api_key, fetch=fetch_page):
    query = {"code": code, "from": start, "to": end}
    tokens = set()
    closes = {}
    while True:
        page = fetch(query, api_key)
        if not isinstance(page, dict) or not isinstance(page.get("data"), list):
            raise ValueError("the daily price response lacks a data array")
        for item in page["data"]:
            if item["Code"] not in {code, code + "0"}:
                raise ValueError("the response contained an unexpected stock code")
            day = trading_date(item["Date"])
            if not start <= day <= end:
                raise ValueError("the response contained a date outside the requested interval")
            close = item["C"]
            if close is None:
                continue
            if type(close) not in (int, float) or not math.isfinite(close) or close <= 0:
                raise ValueError("invalid unadjusted close in the response")
            if day in closes and closes[day] != close:
                raise ValueError("conflicting closes for the same date")
            closes[day] = close

        token = page.get("pagination_key")
        if token is None:
            return [(f"JP:{code}", day, "JPY", closes[day]) for day in sorted(closes)]
        if not isinstance(token, str) or not token or token in tokens:
            raise ValueError("invalid or repeated pagination key")
        tokens.add(token)
        query["pagination_key"] = token


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from", dest="from_date", required=True, type=trading_date)
    parser.add_argument("--to", dest="to_date", required=True, type=trading_date)
    parser.add_argument("codes", type=code4, nargs="+")
    args = parser.parse_args()
    if args.from_date > args.to_date:
        parser.error("--from must be on or before --to")
    api_key = os.environ.get("JQUANTS_API_KEY", "").strip()
    if not api_key:
        parser.error("set JQUANTS_API_KEY using your personal account")
    rows = []
    try:
        for code in dict.fromkeys(args.codes):
            rows.extend(collect_quotes(code, args.from_date, args.to_date, api_key))
    except HTTPError as error:
        parser.exit(1, f"J-Quants returned HTTP {error.code}. Check your plan, date range and API key.\n")
    except (URLError, TimeoutError, KeyError, TypeError, ValueError, argparse.ArgumentTypeError):
        parser.exit(1, "J-Quants response could not be retrieved or validated.\n")
    if not rows:
        parser.exit(1, "No closes returned for the requested interval.\n")
    writer = csv.writer(sys.stdout, lineterminator="\n")
    writer.writerow(("market_id", "date", "currency", "close"))
    writer.writerows(rows)


if __name__ == "__main__":
    main()

"""Measure Massive's US daily close coverage without exporting quotes."""

import argparse
from datetime import date, datetime
from http.client import HTTPException, HTTPSConnection
import json
import os
import time
from urllib.parse import parse_qs, urlencode, urlsplit
from zoneinfo import ZoneInfo

HOST = "api.massive.com"
TICKERS = "/v3/reference/tickers"
NEW_YORK = ZoneInfo("America/New_York")
MAX_BYTES = 16 * 1024 * 1024


class ProbeError(ValueError):
    pass


def get_json(connection, path, key):
    connection.request("GET", path, headers={"Authorization": f"Bearer {key}"})
    response = connection.getresponse()
    if response.status != 200:
        raise ProbeError(f"Massive returned HTTP {response.status}")
    raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ProbeError("Massive response exceeded the size limit")
    try:
        payload = json.loads(raw)
    except ValueError:
        raise ProbeError("Massive returned invalid JSON") from None
    if not isinstance(payload, dict) or payload.get("status") != "OK":
        raise ProbeError("Massive response did not report success")
    return payload


def coverage(trading_day, payload, symbols):
    rows = payload.get("results", [])
    if (
        payload.get("adjusted") is not False
        or not isinstance(rows, list)
        or payload.get("resultsCount") != len(rows)
    ):
        raise ProbeError("Expected a complete, unadjusted daily summary")
    if not rows:
        raise ProbeError("No bars for that date; use a completed US trading day")

    closes = set()
    seen = set()
    invalid = 0
    for row in rows:
        if not isinstance(row, dict):
            invalid += 1
            continue
        symbol, close, timestamp = row.get("T"), row.get("c"), row.get("t")
        if not isinstance(symbol, str) or not symbol:
            invalid += 1
            continue
        if symbol in seen:
            raise ProbeError("Duplicate symbol in the daily summary")
        seen.add(symbol)
        if type(timestamp) is not int or not 0 <= timestamp <= 253402214399999:
            invalid += 1
            continue
        if datetime.fromtimestamp(timestamp / 1000, NEW_YORK).date() != trading_day:
            raise ProbeError("Daily summary contains a bar from a different New York date")
        if (
            row.get("otc") is True
            or type(close) not in (int, float)
            or not 0 < close < float("inf")
        ):
            invalid += 1
            continue
        closes.add(symbol)

    if not symbols:
        raise ProbeError("No listed common stocks returned for that date")
    matched = len(closes & symbols)
    if matched == 0:
        raise ProbeError("None of the listed common stocks had a valid close")
    return {
        "trading_date_et": trading_day.isoformat(),
        "market_summary_rows": len(rows),
        "invalid_or_otc_rows": invalid,
        "massive_common_stock_universe": len(symbols),
        "common_stocks_with_close": matched,
        "common_stocks_without_close": len(symbols) - matched,
        "common_stock_coverage_percent": round(100 * matched / len(symbols), 2),
    }


def next_page(next_url):
    parsed = urlsplit(next_url)
    cursors = parse_qs(parsed.query).get("cursor", [])
    if (
        parsed.scheme != "https"
        or parsed.netloc != HOST
        or parsed.path != TICKERS
        or parsed.fragment
        or len(cursors) != 1
    ):
        raise ProbeError("Unexpected Massive pagination URL")
    return TICKERS + "?" + urlencode({"cursor": cursors[0]})


def listed_common_stocks(get, trading_day):
    query = urlencode({
        "date": trading_day.isoformat(), "market": "stocks", "locale": "us",
        "active": "true", "type": "CS", "limit": 1000, "sort": "ticker",
    })
    path = TICKERS + "?" + query
    visited = set()
    symbols = set()
    while path:
        if path in visited or len(visited) >= 50:
            raise ProbeError("Ticker pagination did not terminate")
        visited.add(path)
        payload = get(path)
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise ProbeError("Invalid ticker results")
        for row in rows:
            if (
                not isinstance(row, dict)
                or row.get("type") != "CS"
                or row.get("market") != "stocks"
                or row.get("locale") != "us"
                or row.get("active") is not True
                or not isinstance(row.get("ticker"), str)
                or not row["ticker"]
            ):
                raise ProbeError("Unexpected row in the listed common-stock universe")
            if row["ticker"] in symbols:
                raise ProbeError("Duplicate symbol in the listed common-stock universe")
            symbols.add(row["ticker"])
        cursor = payload.get("next_url")
        path = next_page(cursor) if isinstance(cursor, str) and cursor else None
        if cursor is not None and not path:
            raise ProbeError("Invalid ticker pagination cursor")
    return symbols


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trading_day", type=date.fromisoformat)
    args = parser.parse_args()
    if args.trading_day >= datetime.now(NEW_YORK).date():
        parser.exit(1, "Use a prior US trading date (New York time).\n")
    key = os.environ.get("MASSIVE_API_KEY", "").strip()
    if not key or not key.isascii() or any(char.isspace() for char in key):
        parser.exit(1, "Set a valid MASSIVE_API_KEY in the local environment.\n")

    connection = HTTPSConnection(HOST, timeout=30)
    last_request = None

    def get(path):
        nonlocal last_request
        if last_request is not None:
            time.sleep(max(0, 13 - (time.monotonic() - last_request)))
        last_request = time.monotonic()
        return get_json(connection, path, key)

    try:
        summary = get(
            f"/v2/aggs/grouped/locale/us/market/stocks/{args.trading_day.isoformat()}"
            "?adjusted=false&include_otc=false"
        )
        if summary.get("resultsCount") == 0:
            parser.exit(1, "No bars for that date; use a completed US trading day.\n")
        symbols = listed_common_stocks(get, args.trading_day)
        print(json.dumps(coverage(args.trading_day, summary, symbols), indent=2))
    except ProbeError as error:
        parser.exit(1, f"{error}\n")
    except (ValueError, TypeError):
        parser.exit(1, "Invalid Massive response or connection settings.\n")
    except (OSError, HTTPException):
        parser.exit(1, "Could not connect to Massive.\n")
    finally:
        connection.close()


if __name__ == "__main__":
    main()

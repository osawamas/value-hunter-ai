"""Check two published Nasdaq historical closes without credentials."""
import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import re
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from us_public_files_probe import SYMBOL

ENDPOINT = "https://api.nasdaq.com/api/quote/{}/historical"
PRICE = re.compile(r"\$([0-9]+(?:\.[0-9]{1,8})?)")
MAX_BYTES = 65_536


def parse(payload, symbol, days):
    if not isinstance(payload, dict):
        raise ValueError("Invalid Nasdaq response")
    status = payload.get("status")
    data = payload.get("data")
    if not isinstance(status, dict) or status.get("rCode") != 200:
        raise ValueError("Nasdaq did not confirm the request")
    if not isinstance(data, dict) or data.get("symbol") != symbol:
        raise ValueError("Nasdaq response does not identify the requested symbol")
    table = data.get("tradesTable")
    if not isinstance(table, dict):
        raise ValueError("Nasdaq historical close table is missing")
    rows = table.get("rows")
    if rows is None and data.get("totalRecords") == 0:
        return {}
    if not isinstance(rows, list) or data.get("totalRecords") != len(rows) or len(rows) > 8:
        raise ValueError("Incomplete Nasdaq historical close table")
    closes = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("date"), str):
            raise ValueError("Invalid Nasdaq historical row")
        day = datetime.strptime(row["date"], "%m/%d/%Y").date()
        value = row.get("close")
        price = PRICE.fullmatch(value) if isinstance(value, str) else None
        if day not in days or day in closes or price is None or Decimal(price[1]) <= 0:
            raise ValueError("Unexpected date, duplicate row, or invalid Nasdaq close")
        closes[day] = Decimal(price[1])
    return closes


def fetch(symbol, days):
    if not SYMBOL.fullmatch(symbol) or not re.fullmatch(r"[A-Z0-9.-]{1,24}", symbol):
        raise ValueError("Unsupported Nasdaq quote symbol")
    start, end = sorted(days)
    url = ENDPOINT.format(symbol) + "?" + urlencode(
        {"assetclass": "stocks", "fromdate": start, "todate": end, "limit": 8})
    request = Request(url, headers={
        "Accept": "application/json, text/plain, */*",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/135.0.0.0 Safari/537.36",
    })
    with urlopen(request, timeout=15) as response:
        if response.geturl() != url:
            raise ValueError("Nasdaq historical endpoint redirected")
        data = response.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError("Oversized Nasdaq historical response")
    return parse(json.loads(data), symbol, days)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("previous", type=date.fromisoformat)
    parser.add_argument("latest", type=date.fromisoformat)
    parser.add_argument("symbols", nargs="+")
    args = parser.parse_args()
    if (not 1 <= (args.latest - args.previous).days <= 7
            or not 1 <= len(set(args.symbols)) == len(args.symbols) <= 12):
        parser.error("Use two ordered dates within seven days and up to 12 distinct symbols")
    requested = {args.previous, args.latest}
    # Allow intervening sessions in the response, while only scoring the requested dates.
    days = {date.fromordinal(n) for n in range(args.previous.toordinal(), args.latest.toordinal() + 1)}
    complete = 0
    results = {}
    for symbol in args.symbols:
        try:
            rows = fetch(symbol, days)
            found = len(rows.keys() & requested)
            results[symbol] = {"dates_found": found}
            if found == 2:
                complete += 1
        except HTTPError as error:
            results[symbol] = {"dates_found": 0, "error": f"HTTP {error.code}"}
            if error.code == 429:
                break
        except (ValueError, URLError, TimeoutError) as error:
            results[symbol] = {"dates_found": 0, "error": str(error)}
    print(json.dumps({"requested": len(args.symbols), "two_session_closes": complete,
                      "unadjusted_basis_verified": False, "symbols": results}, indent=2))
    return 0 if complete == len(args.symbols) else 1


if __name__ == "__main__":
    raise SystemExit(main())

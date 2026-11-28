"""Verify unadjusted US daily closes from the account-free Market History preview."""
import argparse
from datetime import date, datetime, time
from decimal import Decimal
import json
from urllib.error import HTTPError, URLError
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ENDPOINT = "https://getmarkethistory.com/api/v1/bars/stocks/us/AAPL/1d"
NEW_YORK = ZoneInfo("America/New_York")


def dated_regular_closes(body, symbol):
    closes = {}
    for line in body.splitlines():
        if not line.strip():
            continue
        row = json.loads(line, parse_float=Decimal)
        if row["symbol"] != symbol or row.get("is_gap") is not False:
            raise ValueError("Unexpected symbol or gap-filled bar")
        timestamp = datetime.fromisoformat(row["timestamp"].replace("Z", "+00:00"))
        if timestamp.utcoffset() is None:
            raise ValueError("Missing bar timezone")
        local = timestamp.astimezone(NEW_YORK)
        if local.time() != time(9, 30):
            raise ValueError("Bar did not start at the regular NY session")
        price = row["close"]
        if type(price) not in (int, Decimal) or not Decimal(price).is_finite() or price <= 0:
            raise ValueError("Invalid close")
        if local.date() in closes:
            raise ValueError("Duplicated daily bar")
        closes[local.date()] = Decimal(price)
    return closes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=date.fromisoformat)
    target = parser.parse_args().session
    report = {"source": "market_history_account_free_preview", "symbol": "AAPL",
              "target_session": target.isoformat(), "status": "unavailable"}
    try:
        with urlopen(ENDPOINT, timeout=12) as response:
            if response.geturl() != ENDPOINT:
                raise ValueError("Unexpected redirect")
            body = response.read(256_001)
        if len(body) > 256_000:
            raise ValueError("Preview exceeded its expected size")
        closes = dated_regular_closes(body, "AAPL")
        report.update(status="target_close_available" if target in closes else "target_close_unavailable",
                      verified_sessions=len(closes), newest_session=max(closes).isoformat() if closes else None)
    except HTTPError as error:
        report["http_status"] = error.code
    except (URLError, OSError, ValueError, KeyError, TypeError) as error:
        report["reason"] = type(error).__name__
    print(json.dumps(report))


if __name__ == "__main__":
    main()

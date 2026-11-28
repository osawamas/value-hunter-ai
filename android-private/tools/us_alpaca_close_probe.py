"""Verify dated raw SIP daily bars through Alpaca's historical endpoint."""
import argparse
from datetime import date, datetime
from decimal import Decimal
import json
import os
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from zoneinfo import ZoneInfo

from us_finzdata_probe import NoRedirect

SYMBOLS = ("AAPL", "IBM")
NEW_YORK = ZoneInfo("America/New_York")


def fetch(day, key, secret):
    params = {"symbols": ",".join(SYMBOLS), "timeframe": "1Day", "limit": 10,
              "start": datetime.combine(day, datetime.min.time(), NEW_YORK).isoformat(),
              "end": datetime.combine(day, datetime.max.time().replace(microsecond=0), NEW_YORK).isoformat(),
              "adjustment": "raw",
              "feed": "sip", "asof": day.isoformat()}
    request = Request("https://data.alpaca.markets/v2/stocks/bars?" + urlencode(params),
                      headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
    with build_opener(NoRedirect()).open(request, timeout=12) as response:
        body = response.read(32_769)
    if len(body) > 32_768:
        raise ValueError("Oversized Alpaca sample")
    return json.loads(body, parse_float=Decimal)


def audit(day, key, secret, download=fetch):
    report = {"source": "alpaca_delayed_sip", "trade_date": day.isoformat(), "requested": len(SYMBOLS)}
    if not key or not secret:
        return {**report, "status": "key_unconfigured"}
    try:
        payload = download(day, key, secret)
        bars = payload["bars"]
        if payload.get("next_page_token") or not isinstance(bars, dict) or bars.keys() - set(SYMBOLS):
            raise ValueError("Unexpected symbols or pagination")
        verified = 0
        for rows in bars.values():
            if not isinstance(rows, list) or len(rows) > 1:
                raise ValueError("Unexpected duplicate daily bar")
            if not rows:
                continue
            row = rows[0]
            stamp = datetime.fromisoformat(row["t"])
            close = row["c"]
            if (stamp.tzinfo is None or stamp.astimezone(NEW_YORK).date() != day
                    or type(close) not in (int, Decimal) or not Decimal(close).is_finite() or close <= 0):
                raise ValueError("Invalid date or close")
            verified += 1
        return {**report, "status": "sample_verified" if verified == len(SYMBOLS) else "sample_incomplete",
                "verified": verified}
    except HTTPError as error:
        error.close()
        return {**report, "status": "unavailable", "http_status": error.code}
    except (OSError, ValueError, TypeError, KeyError):
        return {**report, "status": "response_unverified"}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=date.fromisoformat)
    day = parser.parse_args().session
    print(json.dumps(audit(day, os.getenv("ALPACA_PAPER_KEY_ID", ""), os.getenv("ALPACA_PAPER_SECRET_KEY", ""))))

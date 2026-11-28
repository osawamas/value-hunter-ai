"""Verify dated raw SIP daily bars through Alpaca's historical endpoint."""
import argparse
from datetime import date, datetime, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, build_opener
from zoneinfo import ZoneInfo

from us_finzdata_probe import NoRedirect

SYMBOLS = ("AAPL", "IBM")
NEW_YORK = ZoneInfo("America/New_York")


def fetch(day, key, secret):
    return request_bars(day, day, SYMBOLS, "raw", 10, key, secret)


def request_bars(start, end, symbols, adjustment, limit, key, secret, token=None):
    params = {"symbols": ",".join(symbols), "timeframe": "1Day", "limit": limit,
              "start": datetime.combine(start, datetime.min.time(), NEW_YORK).isoformat(),
              "end": datetime.combine(end, datetime.max.time().replace(microsecond=0), NEW_YORK).isoformat(),
              "adjustment": adjustment,
              "feed": "sip", "asof": end.isoformat()}
    if token:
        params["page_token"] = token
    request = Request("https://data.alpaca.markets/v2/stocks/bars?" + urlencode(params),
                      headers={"APCA-API-KEY-ID": key, "APCA-API-SECRET-KEY": secret})
    with build_opener(NoRedirect()).open(request, timeout=12) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError("Oversized Alpaca response")
    return json.loads(body, parse_float=Decimal)


def audit(day, key, secret, download=fetch):
    report = {"source": "alpaca_delayed_sip", "trade_date": day.isoformat(), "requested": len(SYMBOLS)}
    if not key or not secret:
        return {**report, "status": "key_unconfigured"}
    try:
        payload = download(day, key, secret)
        if payload.get("next_page_token"):
            raise ValueError("Unexpected pagination")
        verified = len(read_bars(payload, SYMBOLS, day, day))
        return {**report, "status": "sample_verified" if verified == len(SYMBOLS) else "sample_incomplete",
                "verified": verified}
    except HTTPError as error:
        error.close()
        return {**report, "status": "unavailable", "http_status": error.code}
    except (OSError, ValueError, TypeError, KeyError):
        return {**report, "status": "response_unverified"}


def read_bars(payload, symbols, start, end):
    bars = payload["bars"]
    if not isinstance(bars, dict) or bars.keys() - set(symbols):
        raise ValueError("Unexpected symbols")
    result = {}
    for symbol, rows in bars.items():
        if not isinstance(rows, list):
            raise ValueError("Unexpected daily bar list")
        for row in rows:
            stamp = datetime.fromisoformat(row["t"])
            session = stamp.astimezone(NEW_YORK).date() if stamp.tzinfo is not None else None
            close = row["c"]
            identity = (symbol, session)
            if (session is None or not start <= session <= end or identity in result
                    or type(close) not in (int, Decimal) or not Decimal(close).is_finite() or close <= 0):
                raise ValueError("Invalid or duplicate dated close")
            result[identity] = Decimal(close)
    return result


def collect(day, symbols, key, secret, download=request_bars):
    closes = {}
    queried = 0
    failure = {}
    for offset in range(0, len(symbols), 100):
        batch = symbols[offset:offset + 100]
        try:
            payload = download(day, day, batch, "raw", 1000, key, secret)
            if payload.get("next_page_token"):
                raise ValueError("Unexpected pagination for one session")
            closes.update(read_bars(payload, batch, day, day))
        except HTTPError as error:
            error.close()
            failure = {"http_status": error.code}
            break
        except (OSError, ValueError, TypeError, KeyError) as error:
            failure = {"error": type(error).__name__}
            break
        queried += len(batch)
        if queried < len(symbols):
            time.sleep(0.35)
    return {"scope": len(symbols), "queried": queried, "closes": len(closes),
            "status": "complete_request_pass" if queried == len(symbols) else "partial_request_pass",
            **failure}, [{"symbol": symbol, "close_usd": str(close)} for (symbol, _), close in sorted(closes.items())]


def history_sample(day, key, secret):
    start = day.replace(year=day.year - 5, day=min(day.day, 28) if day.month == 2 else day.day)
    rows = {}
    token = None
    try:
        for _ in range(8):
            payload = request_bars(start, day, SYMBOLS, "split", 500, key, secret, token)
            page = read_bars(payload, SYMBOLS, start, day)
            if rows.keys() & page.keys():
                raise ValueError("Overlapping history pages")
            rows.update(page)
            next_token = payload.get("next_page_token")
            if not next_token:
                counts = {}
                for symbol in SYMBOLS:
                    dates = sorted(session for code, session in rows if code == symbol)
                    counts[symbol] = {"sessions": len(dates)}
                    if dates:
                        counts[symbol].update(first=dates[0].isoformat(), last=dates[-1].isoformat())
                five_year_span = all(value["sessions"] >= 1200
                                     and date.fromisoformat(value["first"]) <= start + timedelta(days=7)
                                     and date.fromisoformat(value["last"]) >= day - timedelta(days=7)
                                     for value in counts.values())
                return {"status": "five_year_span_verified" if five_year_span else "sample_incomplete",
                        "symbols": counts}
            if not isinstance(next_token, str) or len(next_token) > 2048 or next_token == token:
                raise ValueError("Invalid history page token")
            token = next_token
            time.sleep(0.35)
        return {"status": "pagination_budget_reached"}
    except HTTPError as error:
        error.close()
        return {"status": "unavailable", "http_status": error.code}
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"status": "response_unverified", "error": type(error).__name__}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("session", type=date.fromisoformat, nargs="?")
    parser.add_argument("--scope", type=Path)
    parser.add_argument("--close-output", type=Path)
    args = parser.parse_args()
    key = os.getenv("ALPACA_PAPER_KEY_ID", "").strip()
    secret = os.getenv("ALPACA_PAPER_SECRET_KEY", "").strip()
    day = args.session
    if args.scope:
        scope = json.loads(args.scope.read_text(encoding="utf-8"))
        day = date.fromisoformat(scope["trade_date"])
        symbols = scope["symbols"]
        if not (args.close_output and 0 < len(symbols) <= 12_000 and len(set(symbols)) == len(symbols)
                and all(re.fullmatch(r"[A-Z0-9.$+^=/_-]{1,24}", symbol) for symbol in symbols)):
            parser.error("Expected a verified listing scope and private output file")
    if day is None:
        parser.error("Expected a session date or listing scope")
    report = audit(day, key, secret)
    if args.scope and report["status"] == "sample_verified":
        report["daily"], closes = collect(day, sorted(symbols), key, secret)
        if closes:
            args.close_output.write_text(json.dumps({"trade_date": day.isoformat(), "closes": closes}),
                                         encoding="utf-8")
        report["five_year_history_probe"] = history_sample(day, key, secret)
    print(json.dumps(report))

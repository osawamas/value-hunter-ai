"""Verify dated raw SIP daily bars through Alpaca's historical endpoint."""
import argparse
from datetime import date, datetime, timedelta, timezone
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
    return alpaca_json("/v2/stocks/bars", params, key, secret)


def alpaca_json(path, params, key, secret):
    request = Request("https://data.alpaca.markets" + path + "?" + urlencode(params),
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


def split_audit(day, scope, key, secret, fetch=alpaca_json):
    # Use a wider process-date range, then filter by ex-date.
    lower = day - timedelta(days=520)
    params = {"types": "forward_split,reverse_split", "start": (lower - timedelta(days=60)).isoformat(),
              "end": datetime.now(timezone.utc).date().isoformat(), "limit": 1000}
    dates = {}
    seen_actions = set()
    seen_tokens = set()
    try:
        for _ in range(8):
            payload = fetch("/v1/corporate-actions", params, key, secret)
            actions = payload["corporate_actions"]
            if not isinstance(actions, dict) or actions.keys() - {"forward_splits", "reverse_splits"}:
                raise ValueError("Unexpected corporate action type")
            for entries in actions.values():
                for row in entries:
                    action = row["id"]
                    symbol = row["symbol"]
                    effective = date.fromisoformat(row["ex_date"])
                    if not action or action in seen_actions or not isinstance(symbol, str):
                        raise ValueError("Invalid corporate action identity")
                    seen_actions.add(action)
                    if symbol in scope and lower <= effective <= day:
                        dates[symbol] = max(dates.get(symbol, effective), effective)
            token = payload["next_page_token"]
            if token is None:
                if not seen_actions or not dates:
                    raise ValueError("Empty corporate actions coverage")
                return {"status": "verified", "scoped_symbols": len(dates)}, {
                    symbol: effective.isoformat() for symbol, effective in dates.items()}
            if not isinstance(token, str) or not token or len(token) > 2048 or token in seen_tokens:
                raise ValueError("Invalid corporate actions page token")
            seen_tokens.add(token)
            params["page_token"] = token
            time.sleep(0.35)
    except HTTPError as error:
        error.close()
        return {"status": "unavailable", "http_status": error.code}, None
    except (OSError, ValueError, TypeError, KeyError) as error:
        return {"status": "response_unverified", "error": type(error).__name__}, None
    return {"status": "pagination_budget_reached"}, None


def replay_history(rows):
    """Compare matched sessions without letting a forward return enter a signal."""
    by_symbol = [{day: value for (code, day), value in rows.items() if code == symbol}
                 for symbol in SYMBOLS]
    dates = sorted(by_symbol[0].keys() & by_symbol[1].keys())
    prices = [[series[day] for day in dates] for series in by_symbol]
    first_signal, forward_sessions = 252, 20
    windows = eligible = positive = relative_wins = 0
    for i in range(first_signal, len(dates) - forward_sessions, forward_sessions):
        windows += 1
        trailing = [series[i] / series[i - 252] for series in prices]
        if trailing[0] == trailing[1]:
            continue
        leader = 0 if trailing[0] > trailing[1] else 1
        series = prices[leader]
        if series[i] * 200 <= sum(series[i - 199:i + 1]):
            continue
        eligible += 1
        returns = [series[i + forward_sessions] / series[i] for series in prices]
        positive += returns[leader] > 1
        relative_wins += returns[leader] > returns[1 - leader]
    return {"matched_sessions": len(dates), "test_windows": windows, "qualified_signals": eligible,
            "positive_forward_windows": positive, "relative_wins": relative_wins,
            "lookback_sessions": 252, "trend_sessions": 200, "forward_sessions": forward_sessions}


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
                        "symbols": counts, **({"technical_replay": replay_history(rows)} if five_year_span else {})}
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
            report["splits"], splits = split_audit(day, set(symbols), key, secret)
            args.close_output.write_text(json.dumps({"trade_date": day.isoformat(), "closes": closes,
                                                        "splits": splits}),
                                         encoding="utf-8")
        report["five_year_history_probe"] = history_sample(day, key, secret)
    print(json.dumps(report))

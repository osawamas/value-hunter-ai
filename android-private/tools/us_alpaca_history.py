"""Collect split-adjusted Alpaca SIP history into a private resumable local database."""
import argparse
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal
import json
import os
from pathlib import Path
import re
import sqlite3
import time
from urllib.error import HTTPError

from us_alpaca_close_probe import read_bars, request_bars, valuation_history


def five_year_start(day):
    try:
        return day.replace(year=day.year - 5)
    except ValueError:
        return day.replace(year=day.year - 5, day=28)


class DownloadBudget(Exception):
    pass


def pages(start, day, symbols, fetch):
    rows, tokens = {}, set()
    token = None
    for _ in range(20):
        page = fetch(start, day, symbols, token)
        values = read_bars(page, symbols, start, day)
        if rows.keys() & values.keys():
            raise ValueError("Duplicate historical bar across pages")
        rows.update(values)
        token = page["next_page_token"]
        if token is None:
            return rows
        if not isinstance(token, str) or not token or len(token) > 2048 or token in tokens:
            raise ValueError("Invalid Alpaca pagination token")
        tokens.add(token)
    raise ValueError("Five-year pagination limit exceeded")


def schema(db):
    db.executescript("""
        CREATE TABLE IF NOT EXISTS series (
            symbol TEXT PRIMARY KEY,
            start TEXT NOT NULL,
            checked_through TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS close (
            symbol TEXT NOT NULL,
            session TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (symbol, session)
        );
    """)


def update_batch(db, batch, start, day, previous, fetch):
    begin = start if previous is None else max(start, previous - timedelta(days=14))
    rows = pages(begin, day, batch, fetch)
    if previous is not None:
        old = {(code, date.fromisoformat(session)): Decimal(value)
               for code in batch for session, value in db.execute(
                   "SELECT session, value FROM close WHERE symbol=? AND session BETWEEN ? AND ?",
                   (code, begin.isoformat(), previous.isoformat()))}
        overlap = {key: value for key, value in rows.items() if key[1] <= previous}
        if not old or old != overlap:
            # A split, symbol mapping change or provider correction may rebase history.
            rows = pages(start, day, batch, fetch)
            begin = start
    with db:
        db.executemany("DELETE FROM close WHERE symbol=? AND (session>=? OR session<?)",
                       [(code, begin.isoformat(), start.isoformat()) for code in batch])
        db.executemany("INSERT INTO close VALUES (?,?,?)",
                       [(code, session.isoformat(), str(value)) for (code, session), value in rows.items()])
        db.executemany("INSERT OR REPLACE INTO series VALUES (?,?,?)",
                       [(code, start.isoformat(), day.isoformat()) for code in batch])


def collect(db, symbols, day, fetch):
    schema(db)
    start = five_year_start(day)
    pending = {}
    for code in dict.fromkeys(("IWV", *symbols)):
        checkpoint = db.execute("SELECT start, checked_through FROM series WHERE symbol=?", (code,)).fetchone()
        previous = None
        if checkpoint:
            old_start, last = map(date.fromisoformat, checkpoint)
            if last == day and old_start == start:
                continue
            if old_start <= start and timedelta(days=0) < day - last <= timedelta(days=31):
                previous = last
        pending.setdefault(previous, []).append(code)
    stop = None
    try:
        for previous, codes in pending.items():
            for offset in range(0, len(codes), 24):
                update_batch(db, codes[offset:offset + 24], start, day, previous, fetch)
    except HTTPError as error:
        stop = f"http_{error.code}"
        error.close()
    except (DownloadBudget, OSError, ValueError, KeyError, TypeError) as error:
        stop = type(error).__name__
    finished = {row[0] for row in db.execute("SELECT symbol FROM series WHERE start=? AND checked_through=?",
                                            (start.isoformat(), day.isoformat()))}
    benchmark = list(db.execute("SELECT session,value FROM close WHERE symbol='IWV' ORDER BY session"))
    market = {("IWV", date.fromisoformat(session)): Decimal(value) for session, value in benchmark}
    confirmed, legacy, horizons = {}, {}, {}
    eligible = Counter()
    full = final_close = returned = 0
    for code in finished.intersection(symbols):
        data = {(code, date.fromisoformat(session)): Decimal(value)
                for session, value in db.execute("SELECT session,value FROM close WHERE symbol=?", (code,))}
        returned += bool(data)
        final_close += (code, day) in data
        five_year_span = (len(data) >= 1200 and min(key[1] for key in data) <= start + timedelta(days=7)
                          and (code, day) in data)
        full += five_year_span
        if "IWV" not in finished or code == "IWV":
            continue
        values = market | data
        if five_year_span:
            legacy.update(valuation_history(values, (code,), "IWV", day)["confirmed"])
        adaptive = valuation_history(values, (code,), "IWV", day, adaptive=True)
        eligible.update(adaptive["eligible_horizons"].values())
        confirmed.update(adaptive["confirmed"])
        horizons.update(adaptive["horizons"])
    return ({"trade_date": day.isoformat(), "scope": len(symbols),
             "request_complete": len(finished.intersection(symbols)), "symbols_with_bars": returned,
             "symbols_with_session_close": final_close, "five_year_span": full,
             "valuation_history_confirmed": len(confirmed), "legacy_history_confirmed": len(legacy),
             "eligible_by_years": eligible, "confirmed_by_years": Counter(horizons.values()), "stop": stop},
            {"date": day.isoformat(), "benchmark": "IWV", "confirmed": confirmed,
             "horizons": horizons, "legacy_confirmed": legacy})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", type=Path, required=True)
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--history-output", type=Path)
    parser.add_argument("--time-budget", type=int, default=1800)
    args = parser.parse_args()
    raw = json.loads(args.scope.read_text(encoding="utf-8"))
    day = date.fromisoformat(raw["trade_date"])
    symbols = raw["symbols"]
    if not (0 < len(symbols) <= 12_000 and len(set(symbols)) == len(symbols)
            and all(re.fullmatch(r"[A-Z0-9.$+^=/_-]{1,24}", symbol) for symbol in symbols)):
        parser.error("Expected a verified listing scope")
    key, secret = (os.getenv(name, "").strip() for name in ("ALPACA_PAPER_KEY_ID", "ALPACA_PAPER_SECRET_KEY"))
    if not key or not secret:
        print(json.dumps({"scope": len(symbols), "status": "key_unconfigured"}))
        return
    deadline = time.monotonic() + args.time_budget
    calls = 0

    def fetch(start, end, batch, token):
        nonlocal calls
        if time.monotonic() + 13 >= deadline:
            raise DownloadBudget()
        calls += 1
        try:
            return request_bars(start, end, batch, "split", 7500, key, secret, token)
        finally:
            time.sleep(0.45)

    args.database.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(args.database) as db:
        report, history = collect(db, sorted(symbols), day, fetch)
    report["requests"] = calls
    if args.history_output is not None:
        args.history_output.write_text(json.dumps(history), encoding="utf-8")
    print(json.dumps(report))


if __name__ == "__main__":
    main()

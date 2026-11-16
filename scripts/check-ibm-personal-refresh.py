#!/usr/bin/env python3
"""Fetch IBM daily closes and compare two dates for local personal research."""
import argparse
import csv
import json
import math
import os
from datetime import date
from pathlib import Path
import subprocess
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ENDPOINT = "https://www.alphavantage.co/query"
CHECKER = Path(__file__).with_name("check-representative-valuations.js")


def trading_date(value):
    try:
        if date.fromisoformat(value).isoformat() == value:
            return value
    except ValueError:
        pass
    raise argparse.ArgumentTypeError("expected YYYY-MM-DD")


def read_closes(payload, dates):
    if not isinstance(payload, dict) or not isinstance(payload.get("Meta Data"), dict):
        raise ValueError("Alpha Vantage did not return the daily series. Check access or quota.")
    metadata = payload["Meta Data"]
    series = payload.get("Time Series (Daily)")
    if metadata.get("2. Symbol") != "IBM" or not isinstance(series, dict):
        raise ValueError("The response does not identify an IBM daily series.")
    result = {}
    for day in dates:
        if day not in series:
            raise ValueError(f"No IBM close for {day} in the returned daily series.")
        try:
            close = float(series[day]["4. close"])
        except (KeyError, TypeError, ValueError, OverflowError) as error:
            raise ValueError(f"Invalid IBM close for {day}.") from error
        if not math.isfinite(close) or close <= 0:
            raise ValueError(f"Invalid IBM close for {day}.")
        result[day] = close
    return result


def compare(closes, previous, current, *, demo):
    with TemporaryDirectory(prefix="value-hunter-ibm-") as directory:
        snapshots = []
        for day in (previous, current):
            snapshot = Path(directory) / f"{day}.csv"
            with snapshot.open("w", newline="", encoding="utf-8") as handle:
                writer = csv.writer(handle)
                writer.writerow(("market_id", "date", "currency", "close"))
                writer.writerow(("US:IBM", day, "USD", closes[day]))
            snapshots.append(snapshot)
        process = subprocess.run(
            ["node", CHECKER, "--compare", *snapshots], capture_output=True, text=True, check=True
        )
    report = json.loads(process.stdout)
    ibm = next(row for row in report["results"] if row["id"] == "US:IBM")
    trials = ibm["latestObservedTrials"]
    passed = all(
        trial["status"] == "trial_calculated"
        and all(isinstance(trial["valuation"][metric], (int, float))
                and math.isfinite(trial["valuation"][metric]) for metric in ("cap", "per", "pbr"))
        for trial in trials.values()
    )
    return {
        "provider": "Alpha Vantage TIME_SERIES_DAILY",
        "providerAccess": "official_demo" if demo else "personal_api_key",
        "scope": "local_personal_research",
        "publicRankingEligible": False,
        "retrievals": 1,
        "passed": passed,
        "filingDataSha256": report["filingDataSha256"],
        "latestObservedTrials": trials,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use the public IBM example key")
    parser.add_argument("previous", type=trading_date)
    parser.add_argument("current", type=trading_date)
    args = parser.parse_args()
    if args.previous >= args.current:
        parser.error("provide two dates in increasing order")
    key = "demo" if args.demo else os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key:
        parser.error("set ALPHA_VANTAGE_API_KEY locally or use --demo")
    query = urlencode({"function": "TIME_SERIES_DAILY", "symbol": "IBM", "apikey": key})
    try:
        with urlopen(ENDPOINT + "?" + query, timeout=20) as response:
            closes = read_closes(json.load(response), (args.previous, args.current))
        report = compare(closes, args.previous, args.current, demo=args.demo)
    except HTTPError as error:
        parser.exit(1, f"Alpha Vantage returned HTTP {error.code}.\n")
    except (URLError, TimeoutError, OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        parser.exit(1, "IBM prices could not be retrieved or evaluated.\n")
    except ValueError as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

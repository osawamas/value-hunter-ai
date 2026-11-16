#!/usr/bin/env python3
"""Fetch IBM daily closes and compare two dates for local personal research."""
import argparse
import csv
import hashlib
import json
import math
import os
from datetime import date, datetime, timezone
from pathlib import Path
import subprocess
from shutil import copyfile
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

ENDPOINT = "https://www.alphavantage.co/query"
CHECKER = Path(__file__).with_name("check-representative-valuations.js")
FILING_FILES = (
    "market-research-v315.json", "latest.json", "sgx-s63-two-website-close-v129.json",
    "sgx-s63-historical-shares-v423.json",
)
PROVIDER = "Alpha Vantage TIME_SERIES_DAILY"


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


def complete_trial(trial):
    return trial["status"] == "trial_calculated" and all(
        type(trial["valuation"][metric]) in (int, float) and math.isfinite(trial["valuation"][metric])
        for metric in ("cap", "per", "pbr")
    )


def compare(closes, previous, current, *, demo, retrieved_at=()):
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
    passed = all(complete_trial(trial) for trial in trials.values())
    return {
        "provider": PROVIDER,
        "providerAccess": "official_demo" if demo else "personal_api_key",
        "scope": "local_personal_research",
        "publicRankingEligible": False,
        "retrievals": len(retrieved_at) or 1,
        "retrievedAtUtc": list(retrieved_at),
        "passed": passed,
        "filingDataSha256": report["filingDataSha256"],
        "latestObservedTrials": trials,
    }


def fetch_closes(query, dates):
    with urlopen(ENDPOINT + "?" + query, timeout=20) as response:
        closes = read_closes(json.load(response), dates)
    return closes, datetime.now(timezone.utc).isoformat()


def file_digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_snapshot(directory):
    receipt = json.loads((directory / "receipt.json").read_text(encoding="utf-8"))
    if not isinstance(receipt, dict) or receipt.get("provider") != PROVIDER:
        raise ValueError("Previous snapshot does not contain an IBM daily receipt.")
    day = receipt.get("date")
    timestamp = receipt.get("retrievedAtUtc")
    if (not isinstance(day, str) or not isinstance(timestamp, str)
            or trading_date(day) != day or receipt.get("providerAccess") not in ("official_demo", "personal_api_key")
            or datetime.fromisoformat(timestamp).utcoffset() != timezone.utc.utcoffset(None)):
        raise ValueError("Previous IBM receipt has invalid provenance.")
    if receipt.get("quoteSha256") != file_digest(directory / "quotes.csv"):
        raise ValueError("Previous IBM quote does not match its receipt.")
    if receipt.get("filingSha256") != {
        name: file_digest(directory / "filings" / name) for name in FILING_FILES
    }:
        raise ValueError("Previous IBM filings do not match their receipt.")
    return receipt


def save_refresh(destination, previous, query, day, *, demo):
    if destination.exists() or destination.is_symlink():
        raise ValueError("Snapshot directory already exists. Choose a new destination.")
    earlier = validate_snapshot(previous) if previous is not None else None
    if earlier and earlier["date"] >= day:
        raise ValueError("The new IBM trading date must follow the saved snapshot.")
    access = "official_demo" if demo else "personal_api_key"
    if earlier and earlier["providerAccess"] != access:
        raise ValueError("Use the same IBM provider access mode as the saved snapshot.")
    with TemporaryDirectory(prefix=".value-hunter-ibm-", dir=destination.parent) as temporary:
        snapshot = Path(temporary) / "snapshot"
        snapshot.mkdir(mode=0o700)
        filings = snapshot / "filings"
        filings.mkdir()
        for name in FILING_FILES:
            copyfile(CHECKER.parent.parent / "docs" / "data" / name, filings / name)
        closes, stamp = fetch_closes(query, (day,))
        quotes = snapshot / "quotes.csv"
        with quotes.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(("market_id", "date", "currency", "close"))
            writer.writerow(("US:IBM", day, "USD", closes[day]))
        receipt = {
            "provider": PROVIDER, "providerAccess": access, "date": day, "retrievedAtUtc": stamp,
            "quoteSha256": file_digest(quotes),
            "filingSha256": {name: file_digest(filings / name) for name in FILING_FILES},
        }
        command = ["node", CHECKER, "--filing-dir", filings]
        if earlier:
            if datetime.fromisoformat(earlier["retrievedAtUtc"]) >= datetime.fromisoformat(stamp):
                raise ValueError("IBM acquisition timestamps must advance.")
            command += ["--previous-filing-dir", previous / "filings", "--compare", previous / "quotes.csv"]
        else:
            command += ["--compare", quotes]
        result = subprocess.run([*command, quotes], capture_output=True, text=True, check=True)
        report = json.loads(result.stdout)
        ibm = next(row for row in report["results"] if row["id"] == "US:IBM")
        if earlier:
            if (report["snapshots"]["previous"]["sha256"] != earlier["quoteSha256"]
                    or report["previousFilingDataSha256"] != earlier["filingSha256"]):
                raise ValueError("Previous IBM snapshot changed during calculation.")
            trials = ibm["latestObservedTrials"]
            if trials["previous"] is None or trials["previous"]["date"] != earlier["date"]:
                raise ValueError("Previous IBM trading date does not match its receipt.")
        else:
            trials = {"current": ibm["latestObservedTrials"]["current"]}
        passed = all(complete_trial(trial) for trial in trials.values())
        result = {
            "scope": "local_personal_research", "publicRankingEligible": False,
            "currentReceipt": receipt, "previousReceipt": earlier, "passed": passed,
            "latestObservedTrials": trials,
        }
        (snapshot / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        (snapshot / "report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        snapshot.rename(destination)
    return 0 if passed else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", help="Use the public IBM example key")
    parser.add_argument("--separate-requests", action="store_true",
                        help="Fetch each date through a separate API request")
    parser.add_argument("--output-dir", type=Path, help="Save one local snapshot")
    parser.add_argument("--previous-dir", type=Path, help="Compare with an earlier saved snapshot")
    parser.add_argument("previous", type=trading_date, help="First date, or the only date with --output-dir")
    parser.add_argument("current", nargs="?", type=trading_date)
    args = parser.parse_args()
    if args.output_dir:
        if args.current or args.separate_requests:
            parser.error("--output-dir accepts a single trading date")
    elif args.previous_dir or args.current is None:
        parser.error("provide two dates, or use --output-dir with one date")
    elif args.previous >= args.current:
        parser.error("provide two dates in increasing order")
    key = "demo" if args.demo else os.environ.get("ALPHA_VANTAGE_API_KEY", "").strip()
    if not key:
        parser.error("set ALPHA_VANTAGE_API_KEY locally or use --demo")
    query = urlencode({"function": "TIME_SERIES_DAILY", "symbol": "IBM", "apikey": key})
    try:
        if args.output_dir:
            status = save_refresh(args.output_dir, args.previous_dir, query, args.previous, demo=args.demo)
            print(args.output_dir / "report.json")
            return status
        dates = (args.previous, args.current)
        request_dates = [(day,) for day in dates] if args.separate_requests else [dates]
        closes, retrieved_at = {}, []
        for requested in request_dates:
            observations, stamp = fetch_closes(query, requested)
            closes.update(observations)
            retrieved_at.append(stamp)
        report = compare(closes, *dates, demo=args.demo, retrieved_at=retrieved_at)
    except HTTPError as error:
        parser.exit(1, f"Alpha Vantage returned HTTP {error.code}.\n")
    except (URLError, TimeoutError, OSError, subprocess.CalledProcessError, json.JSONDecodeError):
        parser.exit(1, "IBM prices could not be retrieved or evaluated.\n")
    except (ValueError, argparse.ArgumentTypeError) as error:
        parser.exit(1, str(error) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

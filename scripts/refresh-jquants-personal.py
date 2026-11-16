#!/usr/bin/env python3
"""Save a personal J-Quants snapshot and optionally compare it with a prior snapshot."""
import argparse
from calendar import monthrange
from datetime import date, datetime, timedelta
import json
from pathlib import Path
from shutil import copyfile
import subprocess
import sys
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo


SCRIPTS = Path(__file__).resolve().parent


def capture(command, *, allowed_exit_codes=(0,)):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode not in allowed_exit_codes:
        raise ValueError(result.stderr.strip() or f"{Path(command[0]).name} exited with {result.returncode}")
    return result


def refresh(destination, previous, export_args, *, require_toyota_refresh=False):
    if require_toyota_refresh and previous is None:
        raise ValueError("Toyota refresh verification requires a previous snapshot.")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Snapshot directory already exists. Choose a new destination.")
    with TemporaryDirectory(prefix=".jquants-", dir=destination.parent) as work:
        snapshot = Path(work) / "snapshot"
        snapshot.mkdir(mode=0o700)
        quotes = snapshot / "quotes.csv"
        receipt = snapshot / "receipt.json"
        exported = capture([
            sys.executable, SCRIPTS / "export-jquants-personal-quotes.py",
            "--require-all", "--provenance", "--output", quotes, *export_args,
        ])
        receipt.write_text(exported.stderr, encoding="utf-8")
        filing_dir = snapshot / "filings"
        filing_dir.mkdir()
        for name in ("market-research-v315.json", "latest.json", "sgx-s63-two-website-close-v129.json",
                     "sgx-s63-historical-shares-v423.json", "sgx-s63-shares-2026-11-16-v479.json"):
            copyfile(SCRIPTS.parent / "docs" / "data" / name, filing_dir / name)
        valuation_cli = ["node", SCRIPTS / "check-representative-valuations.js", "--filing-dir", filing_dir]
        if previous is None:
            report = capture([*valuation_cli, "--jquants", quotes, receipt])
        else:
            previous_filings = previous / "filings"
            if previous_filings.exists():
                valuation_cli.extend(["--previous-filing-dir", previous_filings])
            if require_toyota_refresh:
                valuation_cli.append("--require-toyota-refresh")
            report = capture([
                *valuation_cli, "--compare-jquants",
                previous / "quotes.csv", previous / "receipt.json", quotes, receipt,
            ], allowed_exit_codes=(0, 2) if require_toyota_refresh else (0,))
        (snapshot / "report.json").write_text(report.stdout, encoding="utf-8")
        snapshot.rename(destination)
        return report.returncode


def toyota_free_sessions(as_of):
    cutoff = (as_of - timedelta(weeks=12)).isoformat()
    first_year = as_of.year - 2
    first_day = min(as_of.day, monthrange(first_year, as_of.month)[1])
    earliest = as_of.replace(year=first_year, day=first_day).isoformat()
    result = capture(["node", SCRIPTS / "check-representative-valuations.js", "--toyota-share-sessions"])
    sessions = sorted({
        share["date"] for share in json.loads(result.stdout)
        if earliest <= share["date"] <= cutoff and (share.get("disclosedOn") or share["date"]) <= as_of.isoformat()
    })
    if len(sessions) < 2:
        raise ValueError(f"Fewer than two Toyota share dates in the estimated free-plan window ({earliest} to {cutoff}).")
    return sessions[-2:]


def refresh_toyota_pair(destination, sessions):
    earlier, later = sessions
    if date.fromisoformat(earlier).isoformat() != earlier or date.fromisoformat(later).isoformat() != later or earlier >= later:
        raise ValueError("Provide two Toyota sessions in increasing YYYY-MM-DD order.")
    if destination.exists() or destination.is_symlink():
        raise ValueError("Snapshot directory already exists. Choose a new destination.")
    with TemporaryDirectory(prefix=".jquants-pair-", dir=destination.parent) as work:
        pair = Path(work) / "pair"
        pair.mkdir(mode=0o700)
        baseline = pair / "earlier"
        current = pair / "later"
        # Query the single security, avoiding market-wide pagination for a single close.
        refresh(baseline, None, [f"--from={earlier}", f"--to={earlier}", "--", "7203"])
        status = refresh(current, baseline, [f"--from={later}", f"--to={later}", "--", "7203"],
                         require_toyota_refresh=True)
        pair.rename(destination)
        return status


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--previous-dir", type=Path)
    parser.add_argument("--require-toyota-refresh", action="store_true",
                        help="With --previous-dir, require complete Toyota valuations and a later session")
    parser.add_argument("--date")
    parser.add_argument("--from", dest="first")
    parser.add_argument("--to", dest="last")
    toyota = parser.add_mutually_exclusive_group()
    toyota.add_argument("--toyota-sessions", nargs=2, metavar=("EARLIER", "LATER"),
                        help="Retrieve and compare two exact Toyota sessions into one local directory")
    toyota.add_argument("--toyota-free-latest", action="store_true",
                        help="Select the latest Toyota share dates beyond the free-plan delay")
    parser.add_argument("codes", nargs="*")
    args = parser.parse_args()
    if args.toyota_sessions or args.toyota_free_latest:
        if any((args.codes, args.date, args.first, args.last, args.previous_dir, args.require_toyota_refresh)):
            parser.error("Toyota pair modes accept only --output-dir and the selected Toyota option")
        try:
            sessions = args.toyota_sessions
            if args.toyota_free_latest:
                sessions = toyota_free_sessions(datetime.now(ZoneInfo("Asia/Tokyo")).date())
                print("Toyota share dates selected: " + ", ".join(sessions))
            status = refresh_toyota_pair(args.output_dir, sessions)
        except (OSError, ValueError) as error:
            parser.exit(1, f"Refresh failed: {error}\n")
        print(args.output_dir / "later" / "report.json")
        return status
    if not args.codes:
        parser.error("provide at least one stock code")
    export_args = []
    for option, value in (("--date", args.date), ("--from", args.first), ("--to", args.last)):
        if value is not None:
            export_args.append(f"{option}={value}")
    try:
        status = refresh(args.output_dir, args.previous_dir, [*export_args, "--", *args.codes],
                         require_toyota_refresh=args.require_toyota_refresh)
    except (OSError, ValueError) as error:
        parser.exit(1, f"Refresh failed: {error}\n")
    print(args.output_dir / "report.json")
    return status


if __name__ == "__main__":
    sys.exit(main())

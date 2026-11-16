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


class MissingClose(ValueError):
    pass


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
        ], allowed_exit_codes=(0, 3))
        if exported.returncode == 3:
            raise MissingClose(exported.stderr.strip())
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


def toyota_share_evidence():
    result = capture(["node", SCRIPTS / "check-representative-valuations.js", "--toyota-share-sessions"])
    return {share["date"]: share for share in json.loads(result.stdout)}


def free_plan_window(as_of):
    cutoff = as_of - timedelta(weeks=12)
    first_year = as_of.year - 2
    first_day = min(as_of.day, monthrange(first_year, as_of.month)[1])
    return as_of.replace(year=first_year, day=first_day), cutoff


def toyota_free_share_evidence(as_of):
    earliest, cutoff = (day.isoformat() for day in free_plan_window(as_of))
    sessions = {
        share["date"]: share for share in toyota_share_evidence().values()
        if earliest <= share["date"] <= cutoff and (share.get("disclosedOn") or share["date"]) <= as_of.isoformat()
    }
    if len(sessions) < 2:
        raise ValueError(f"Fewer than two Toyota share dates in the estimated free-plan window ({earliest} to {cutoff}).")
    return [sessions[day] for day in sorted(sessions)[-2:]]


def annotate_free_plan(evidence, as_of):
    earliest, latest = free_plan_window(as_of)
    annotated = []
    for row in evidence:
        session = date.fromisoformat(row["date"])
        coverage = {"status": "within_estimated_window"}
        if session < earliest:
            coverage["status"] = "older_than_estimated_window"
        elif session > latest:
            coverage = {"status": "awaiting_delay", "estimatedAvailableOn": (session + timedelta(weeks=12)).isoformat()}
        annotated.append({**row, "freePlanEstimate": coverage})
    return annotated


def toyota_free_sessions(as_of):
    return [share["date"] for share in toyota_free_share_evidence(as_of)]


def validate_toyota_pair(sessions):
    earlier, later = sessions
    if date.fromisoformat(earlier).isoformat() != earlier or date.fromisoformat(later).isoformat() != later or earlier >= later:
        raise ValueError("Provide two Toyota sessions in increasing YYYY-MM-DD order.")


def toyota_pair_evidence(sessions):
    validate_toyota_pair(sessions)
    evidence = toyota_share_evidence()
    missing = [day for day in sessions if day not in evidence]
    if missing:
        raise ValueError("No exact Toyota share filing for: " + ", ".join(missing))
    return [evidence[day] for day in sessions]


def toyota_preflight(sessions):
    validate_toyota_pair(sessions)
    report = []
    with TemporaryDirectory(prefix="toyota-preflight-") as work:
        for session in sessions:
            snapshot = Path(work) / session
            try:
                refresh(snapshot, None, [f"--from={session}", f"--to={session}", "--", "7203"])
            except MissingClose:
                report.append({"date": session, "close": "missing", "annual": "unavailable"})
                continue
            except (OSError, ValueError) as error:
                print(f"Toyota {session}: {error}", file=sys.stderr)
                report.append({"date": session, "close": "verification_failed", "annual": "unavailable"})
                break
            result = json.loads((snapshot / "report.json").read_text(encoding="utf-8"))
            row = next(item for item in result["results"] if item["id"] == "JP:7203")
            trial = row.get("latestAvailableTrial", row)
            interim = trial.get("interimValuation")
            ratios = trial.get("valuation", {})
            annual = "trial_calculated" if trial["status"] == "trial_calculated" and all(
                ratios.get(key) is not None for key in ("per", "pbr")
            ) else ("incomplete_ratios" if trial["status"] == "trial_calculated" else "unavailable")
            entry = {"date": session, "close": "retrieved", "annual": annual}
            if interim and interim["periodEnd"] == session:
                entry["interim"] = {key: interim[key] for key in ("source", "disclosedOn")}
            report.append(entry)
    report.extend({"date": session, "close": "not_attempted", "annual": "unavailable"}
                  for session in sessions[len(report):])
    return report


def refresh_toyota_pair(destination, sessions):
    validate_toyota_pair(sessions)
    earlier, later = sessions
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
    parser.add_argument("--output-dir", type=Path)
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
    toyota.add_argument("--toyota-free-evidence", action="store_true",
                        help="List the two eligible Toyota share filings without fetching prices")
    toyota.add_argument("--toyota-pair-evidence", nargs=2, metavar=("EARLIER", "LATER"),
                        help="Verify two specified Toyota share filing dates without fetching prices")
    toyota.add_argument("--toyota-preflight", nargs=2, metavar=("EARLIER", "LATER"),
                        help="Verify each session and emit statuses without saving prices")
    parser.add_argument("codes", nargs="*")
    args = parser.parse_args()
    if args.toyota_free_evidence or args.toyota_pair_evidence or args.toyota_preflight:
        if any((args.codes, args.date, args.first, args.last, args.previous_dir,
                args.require_toyota_refresh, args.output_dir)):
            parser.error("Toyota evidence and preflight modes accept no snapshot or quote options")
        if args.toyota_preflight:
            try:
                checks = toyota_preflight(args.toyota_preflight)
            except (OSError, ValueError) as error:
                parser.exit(1, f"Preflight failed: {error}\n")
            print(json.dumps(checks, indent=2))
            if len(checks) != 2 or any(check["close"] != "retrieved" for check in checks):
                return 1
            return 0 if all(check["annual"] == "trial_calculated" for check in checks) else 2
        as_of = datetime.now(ZoneInfo("Asia/Tokyo")).date()
        try:
            evidence = (toyota_pair_evidence(args.toyota_pair_evidence) if args.toyota_pair_evidence
                        else toyota_free_share_evidence(as_of))
        except (OSError, ValueError) as error:
            parser.exit(1, f"Evidence selection failed: {error}\n")
        print(json.dumps(annotate_free_plan(evidence, as_of), indent=2))
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required to save a snapshot")
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

#!/usr/bin/env python3
"""Save a personal J-Quants snapshot and optionally compare it with a prior snapshot."""
import argparse
from pathlib import Path
from shutil import copyfile
import subprocess
import sys
from tempfile import TemporaryDirectory


SCRIPTS = Path(__file__).resolve().parent


def capture(command):
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode:
        raise ValueError(result.stderr.strip() or f"{Path(command[0]).name} exited with {result.returncode}")
    return result


def refresh(destination, previous, export_args):
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
        for name in ("market-research-v315.json", "latest.json", "sgx-s63-two-website-close-v129.json"):
            copyfile(SCRIPTS.parent / "docs" / "data" / name, filing_dir / name)
        valuation_cli = ["node", SCRIPTS / "check-representative-valuations.js", "--filing-dir", filing_dir]
        if previous is None:
            report = capture([*valuation_cli, "--jquants", quotes, receipt])
        else:
            previous_filings = previous / "filings"
            if previous_filings.exists():
                valuation_cli.extend(["--previous-filing-dir", previous_filings])
            report = capture([
                *valuation_cli, "--compare-jquants",
                previous / "quotes.csv", previous / "receipt.json", quotes, receipt,
            ])
        (snapshot / "report.json").write_text(report.stdout, encoding="utf-8")
        snapshot.rename(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--previous-dir", type=Path)
    parser.add_argument("--date")
    parser.add_argument("--from", dest="first")
    parser.add_argument("--to", dest="last")
    parser.add_argument("codes", nargs="+")
    args = parser.parse_args()
    export_args = []
    for option, value in (("--date", args.date), ("--from", args.first), ("--to", args.last)):
        if value is not None:
            export_args.append(f"{option}={value}")
    try:
        refresh(args.output_dir, args.previous_dir, [*export_args, "--", *args.codes])
    except (OSError, ValueError) as error:
        parser.exit(1, f"Refresh failed: {error}\n")
    print(args.output_dir / "report.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Find newer periodic SEC reports for the US issuers in the research snapshot."""

import argparse
from datetime import date
import json
from pathlib import Path
import re
import sys
import time

from importlib.util import module_from_spec, spec_from_file_location


ROOT = Path(__file__).resolve().parents[1]
SOURCE_MODULE = spec_from_file_location("verify_market_sources", ROOT / "scripts/verify-market-sources-v315.py")
source = module_from_spec(SOURCE_MODULE)
SOURCE_MODULE.loader.exec_module(source)
PERIODIC = {"10-K", "10-K/A", "10-Q", "10-Q/A"}


def recent_reports(submissions, cik, baseline_date, baseline_accession):
    if int(submissions["cik"]) != cik:
        raise ValueError("SEC submissions CIK mismatch")
    recent = submissions["filings"]["recent"]
    reports = []
    for form, period, filed, accession, document in zip(
        recent["form"], recent["reportDate"], recent["filingDate"],
        recent["accessionNumber"], recent["primaryDocument"], strict=True,
    ):
        if form not in PERIODIC or accession == baseline_accession:
            continue
        if date.fromisoformat(period) < baseline_date:
            continue
        if period == baseline_date.isoformat() and form not in {"10-K/A", "10-Q/A"}:
            continue
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession) or not re.fullmatch(r"[\w.-]+\.html?", document, re.ASCII):
            raise ValueError("invalid SEC primary-document reference")
        reports.append({
            "form": form,
            "period_end": period,
            "filed": date.fromisoformat(filed).isoformat(),
            "accession": accession,
            "source": f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{document}",
        })
    return sorted(reports, key=lambda row: (row["filed"], row["accession"]), reverse=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--symbol", action="append", help="Filter to one or more research tickers")
    args = parser.parse_args()
    rows = json.loads(source.DATA.read_text())["records"]
    selected = [row for row in rows if row["market"] == "US" and row.get("financials") and
                (not args.symbol or row["symbol"] in args.symbol)]
    if args.symbol and set(args.symbol) != {row["symbol"] for row in selected}:
        parser.error("one or more tickers are missing from the US research coverage")
    results = {}
    failures = {}
    for row in selected:
        cik = row["cik"]
        url = f"https://data.sec.gov/submissions/CIK{cik:010d}.json"
        try:
            raw = json.loads(source.fetch(url))
            finance = row["financials"]
            baseline = date.fromisoformat(finance["periods"][-1]["end"])
            results[row["symbol"]] = {
                "snapshot_annual_end": baseline.isoformat(),
                "submissions_url": url,
                "reports_for_review": recent_reports(raw, cik, baseline, finance["accession"]),
            }
        except (OSError, ValueError, KeyError, TypeError) as error:
            failures[row["symbol"]] = str(error)
        time.sleep(0.25)
    print(json.dumps({"results": results, "failed": failures}, indent=2))
    return int(bool(failures))


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Build comparable latest SEC 10-Q research rows from discovery and Company Facts."""

import argparse
from datetime import date
import hashlib
import json
from pathlib import Path

from importlib.util import module_from_spec, spec_from_file_location

ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("verify_market_sources", ROOT / "scripts/verify-market-sources-v315.py")
source = module_from_spec(SPEC)
SPEC.loader.exec_module(source)

FIELDS = {"operating_income": "OperatingIncomeLoss", "net_income": "NetIncomeLoss"}


def quarter_facts(entries, accession, end):
    found = {(item["start"], item["val"]) for item in entries
             if item.get("accn") == accession and item.get("form") == "10-Q"
             and item.get("end") == end and item.get("start")
             and 75 <= (date.fromisoformat(end) - date.fromisoformat(item["start"])).days <= 105}
    if len(found) != 1:
        raise ValueError(f"missing or ambiguous quarter at {accession} / {end}")
    return found.pop()


def build_quarter(raw, company, report):
    obj = json.loads(raw)
    if obj["cik"] != company["cik"]:
        raise ValueError("SEC Company Facts CIK mismatch")
    tags = {"revenue": company["financials"]["revenue_tag"], **FIELDS}
    current = date.fromisoformat(report["period_end"])
    # Derive the comparative quarter end from the matching filing, including 52/53-week fiscal calendars.
    revenue = obj["facts"]["us-gaap"][tags["revenue"]]["units"]["USD"]
    prior_ends = {item["end"] for item in revenue if item.get("accn") == report["accession"]
                  and item.get("form") == "10-Q" and item.get("start")
                  and 345 <= (current - date.fromisoformat(item["end"])).days <= 385
                  and 75 <= (date.fromisoformat(item["end"]) - date.fromisoformat(item["start"])).days <= 105}
    if len(prior_ends) != 1:
        raise ValueError("matching prior-year quarter could not be identified")
    periods = []
    for end in (prior_ends.pop(), current.isoformat()):
        values = {field: quarter_facts(obj["facts"]["us-gaap"][tag]["units"]["USD"], report["accession"], end)
                  for field, tag in tags.items()}
        starts = {start for start, _ in values.values()}
        if len(starts) != 1:
            raise ValueError("quarter start differs across SEC facts")
        periods.append({"start": starts.pop(), "end": end, **{key: val for key, (_, val) in values.items()}})
    return {"currency": "USD", "source": report["source"], "form": report["form"],
            "accession": report["accession"], "filed": report["filed"], "companyfacts_sha256": hashlib.sha256(raw).hexdigest(),
            "periods": periods}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("discovery", type=Path, help="JSON from check-sec-filing-updates.py")
    parser.add_argument("--fixture-directory", type=Path, help="Optional downloaded SYMBOL.json Company Facts originals")
    args = parser.parse_args()
    findings = json.loads(args.discovery.read_text())
    if findings["failed"]:
        raise ValueError("resolve filing discovery failures before regenerating all quarters")
    companies = json.loads(source.DATA.read_text())["records"]
    result = {}
    for company in companies:
        ticker = company["symbol"]
        if company["market"] != "US" or ticker not in findings["results"]:
            continue
        reports = findings["results"][ticker]["reports_for_review"]
        report = max((row for row in reports if row["form"] == "10-Q"),
                     key=lambda row: (row["period_end"], row["filed"]), default=None)
        if not report:
            continue
        if any(row["period_end"] == report["period_end"] and row["form"] == "10-Q/A" for row in reports):
            raise ValueError(f"review amended quarter before importing {ticker}")
        raw = ((args.fixture_directory / (ticker + ".json")).read_bytes() if args.fixture_directory
               else source.fetch(company["financials"]["source"]))
        result[company["id"]] = build_quarter(raw, company, report)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

"""Fail-closed JPX financial evidence accounting; no external dependencies.

Input is a JSON object with `universe` (unique 4-character ticker strings)
and `records` (ticker, source_url, source_sha256, financial_eligible,
on_hold). A record without source evidence is never counted as retrieved.
This is a standalone audit utility, not an assertion that data was fetched.
"""
import argparse
import json
import re
from collections import Counter
from pathlib import Path

TICKER = re.compile(r"[0-9][0-9A-Z]{3}")
SHA256 = re.compile(r"[0-9a-f]{64}")


def audit(document):
    universe = document["universe"]
    if (not isinstance(universe, list)
            or any(not isinstance(s, str) or not TICKER.fullmatch(s) for s in universe)
            or len(universe) != len(set(universe))):
        raise ValueError("invalid or duplicate universe ticker")
    universe = set(universe)
    seen = set()
    counts = Counter({"source_retrieved": 0, "financial_eligible": 0,
                      "on_hold": 0, "not_started": 0})
    for record in document["records"]:
        ticker = record["ticker"]
        if ticker not in universe or ticker in seen:
            raise ValueError("unknown or duplicate record ticker")
        seen.add(ticker)
        address = record.get("source_url")
        evidence = (isinstance(address, str)
                    and re.fullmatch(rf"https://www2\.jpx\.co\.jp/disc/{ticker}0/"
                                     r"[0-9]+_tse-a(?:ce|ne)[A-Za-z0-9-]+-ixbrl\.htm", address)
                    is not None
                    and isinstance(record.get("source_sha256"), str)
                    and SHA256.fullmatch(record["source_sha256"]) is not None)
        eligible = record.get("financial_eligible") is True
        hold = record.get("on_hold") is True
        if eligible and hold:
            raise ValueError("eligible and on_hold are mutually exclusive")
        if eligible and not evidence:
            raise ValueError("financially eligible without original evidence")
        if evidence:
            counts["source_retrieved"] += 1
            if eligible:
                counts["financial_eligible"] += 1
            else:
                counts["on_hold"] += 1
        else:
            if hold:
                counts["on_hold"] += 1
            else:
                counts["not_started"] += 1
    counts["not_started"] += len(universe) - len(seen)
    counts["universe"] = len(universe)
    counts["records_seen"] = len(seen)
    return dict(counts)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    args = parser.parse_args()
    print(json.dumps(audit(json.loads(args.manifest.read_text(encoding="utf-8"))),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Read SGX candidate identifiers from a public HTML directory."""
import argparse
from collections import Counter
from datetime import date, datetime, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
from urllib.request import Request, urlopen

URL = "https://getresearch.ai/sg"
BOARDS = {"SGX": "Mainboard", "SGX-CATALIST": "Catalist"}
SUMMARY_HEADER = ["exchange", "code", "listed companies with a page"]
ISSUER_HEADER = ["issuer", "exchange", "ticker", "ISIN"]
MAX_HTML = 1_000_000
LISTING_EVIDENCE = Path(__file__).resolve().parents[2] / "docs/data/sgx-listing-evidence.json"
CONFIRMED_REPLACEMENTS = (
    {
        "old_symbol": "42S",
        "old_isin": "SG1CB5000005",
        "new_symbol": "9SY",
        "new_isin": "SGXE75609730",
        "effective_on": "2026-09-17",
        "source_url": (
            "https://links.sgx.com/FileOpen/Astaka%20-%20Announcement%20on%20Share%20"
            "Consolidation%20Completion.ashx?App=Announcement&FileID=904486"
        ),
    },
)


class DirectoryTables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = None
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.table is not None:
                raise ValueError("nested directory table")
            self.table = []
        elif tag == "tr" and self.table is not None:
            self.row = []
        elif tag in ("td", "th") and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self.cell is not None:
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == "table" and self.table is not None:
            self.tables.append(self.table)
            self.table = None


def valid_isin(isin):
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{9}[0-9]", isin):
        return False
    digits = "".join(str(int(char, 36)) for char in isin)
    checksum = 0
    for index, char in enumerate(reversed(digits)):
        number = int(char) * (2 if index % 2 else 1)
        checksum += number // 10 + number % 10
    return checksum % 10 == 0


def single_table(parser, header):
    tables = [table for table in parser.tables if table and table[0] == header]
    if len(tables) != 1 or not tables[0][1:]:
        raise ValueError(f"missing or ambiguous table: {header[0]}")
    return tables[0][1:]


def parse_directory(html):
    as_of_dates = re.findall(r"record as of (\d{4}-\d{2}-\d{2})", html)
    if len(as_of_dates) != 1:
        raise ValueError("missing or ambiguous source date")
    as_of = date.fromisoformat(as_of_dates[0]).isoformat()
    parser = DirectoryTables()
    parser.feed(html)
    parser.close()
    if parser.table is not None:
        raise ValueError("incomplete directory HTML table")

    expected = {}
    for name, board, count in single_table(parser, SUMMARY_HEADER):
        if board in expected or BOARDS.get(board) != name or not re.fullmatch(r"[1-9][0-9]*", count):
            raise ValueError("invalid board summary")
        expected[board] = int(count)
    if expected.keys() != BOARDS.keys():
        raise ValueError("board missing from the source summary")

    records = {}
    counts = Counter()
    for issuer, board, symbol, isin in single_table(parser, ISSUER_HEADER):
        if not issuer or board not in BOARDS or not re.fullmatch(r"[A-Z0-9]{1,12}", symbol):
            raise ValueError("invalid issuer, board or ticker")
        if not valid_isin(isin) or symbol in records:
            raise ValueError(f"invalid ISIN or duplicate ticker: {symbol}")
        records[symbol] = {"symbol": symbol, "isin": isin, "issuer": issuer, "board": BOARDS[board]}
        counts[board] += 1
    if counts != expected:
        raise ValueError("issuer row counts do not match the source board summary")

    return as_of, records, {BOARDS[board]: counts[board] for board in BOARDS}


def exclude_replaced_codes(records, as_of):
    exclusions = [
        change for change in CONFIRMED_REPLACEMENTS
        if change["effective_on"] <= as_of
        and records.get(change["old_symbol"], {}).get("isin") == change["old_isin"]
    ]
    excluded = {change["old_symbol"] for change in exclusions}
    candidates = {symbol: row for symbol, row in records.items() if symbol not in excluded}
    replacements = [
        {**change, "replacement_present": (
            records.get(change["new_symbol"], {}).get("isin") == change["new_isin"]
        )} for change in exclusions
    ]
    return candidates, replacements


def supplement_directory(directory, evidence):
    """Add reviewed identities and flag conflicting identifiers for review."""
    candidates = dict(directory)
    evidence_codes = set()
    added, conflicts = [], []
    for row in evidence:
        symbol = row["symbol"]
        if (symbol in evidence_codes or not re.fullmatch(r"[A-Z0-9]{1,12}", symbol)
                or not valid_isin(row["isin"]) or row["board"] not in BOARDS.values()
                or not row["issuer"].strip() or not row["security_type"].strip()
                or not row["source_url"].startswith("https://links.sgx.com/")):
            raise ValueError(f"invalid SGX listing evidence for {symbol}")
        date.fromisoformat(row["evidence_date"])
        evidence_codes.add(symbol)
        current = directory.get(symbol)
        if current is None:
            candidates[symbol] = row
            added.append(symbol)
        elif current["isin"] != row["isin"] or current["board"] != row["board"]:
            conflicts.append(symbol)
        else:
            candidates[symbol] = {**current, **row}
    return candidates, {
        "reviewed_count": len(evidence_codes),
        "directory_missing_count": len(added),
        "added_codes": sorted(added),
        "conflicting_codes": sorted(conflicts),
        "unresolved_count": len(conflicts),
    }


def download():
    request = Request(URL, headers={
        "Accept": "text/html",
        "User-Agent": "VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
    })
    with urlopen(request, timeout=25) as response:
        if response.geturl() != URL or response.headers.get_content_type() != "text/html":
            raise ValueError("unexpected directory URL or content type")
        body = response.read(MAX_HTML + 1)
        if len(body) > MAX_HTML:
            raise ValueError("directory HTML exceeds the size limit")
        return body


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--include-records", action="store_true", help="include candidate rows in local output")
    args = cli.parse_args()
    try:
        body = download()
        as_of, records, board_counts = parse_directory(body.decode("utf-8"))
        directory, exclusions = exclude_replaced_codes(records, as_of)
        evidence = json.loads(LISTING_EVIDENCE.read_text(encoding="utf-8"))
        candidates, audit = supplement_directory(directory, evidence)
    except (OSError, ValueError) as error:
        print(f"SGX candidate directory fetch failed: {error}", file=sys.stderr)
        return 1
    report = {
        "source_url": URL,
        "source_as_of": as_of,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "html_sha256": sha256(body).hexdigest(),
        "source_row_count": len(records),
        "source_board_counts": board_counts,
        "directory_candidate_count": len(directory),
        "candidate_count": len(candidates),
        "listing_evidence": audit,
        "market_missing_count": None,
        "distinct_isin_count": len({row["isin"] for row in candidates.values()}),
        "board_candidate_counts": {
            board: sum(row["board"] == board for row in candidates.values())
            for board in board_counts
        },
        "officially_replaced_codes": exclusions,
        "current_listing_status_verified": False,
        "security_types_verified": False,
        "official_market_coverage_verified": False,
        "stock_quotes_fetched": False,
    }
    if args.include_records:
        report["candidates"] = [candidates[symbol] for symbol in sorted(candidates)]
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

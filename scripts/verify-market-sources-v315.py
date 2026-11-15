#!/usr/bin/env python3
"""Reconcile the three-market research page against JPX, SEC and issuer originals."""
import argparse
import datetime as dt
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data/market-research-v315.json"
SOURCES = {
    "jpx": "https://www.jpx.co.jp/english/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_e.xlsx",
    "sec": "https://www.sec.gov/files/company_tickers_exchange.json",
    "apple": "https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json",
    "toyota": "https://global.toyota/pages/global_toyota/ir/financial-results/2026_4q_summary_en.pdf",
}
MAX_BYTES = 12_000_000
APPLE_TAGS = {
    "revenue": "RevenueFromContractWithCustomerExcludingAssessedTax",
    "operating_income": "OperatingIncomeLoss",
    "net_income": "NetIncomeLoss",
    "assets": "Assets",
    "parent_equity": "StockholdersEquity",
}


def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "VALUE HUNTER AI research https://github.com/osawamas/value-hunter-ai",
    })
    with urllib.request.urlopen(request, timeout=35) as response:
        if response.geturl() != url:
            raise ValueError(f"Unexpected source redirect: {url}")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"Source exceeds download limit: {url}")
    return raw


def jpx_directory(raw):
    workbook = openpyxl.load_workbook(io.BytesIO(raw), read_only=True, data_only=True)
    try:
        rows = iter(workbook.active.values)
        if next(rows)[:4] != ("Effective Date", "Local Code", "Name (English)", "Section/Products"):
            raise ValueError("Unexpected JPX spreadsheet headings")
        accepted = {}
        observed_dates = set()
        for date, code, name, section, *_ in rows:
            if not re.fullmatch(r"(Prime|Standard|Growth) Market\s*\(Domestic\)", str(section)):
                continue
            code = str(code)
            if not re.fullmatch(r"[0-9A-Z]{4,5}", code) or code in accepted or not isinstance(name, str) or not name.strip():
                raise ValueError(f"Invalid or repeated JPX code: {code}")
            observed_dates.add(dt.datetime.strptime(str(date), "%Y%m%d").date().isoformat())
            accepted[code] = (name, section.split()[0])
        if not accepted or len(observed_dates) != 1:
            raise ValueError("Missing or mixed JPX snapshot dates")
        return next(iter(observed_dates)), accepted
    finally:
        workbook.close()


def sec_directory(raw):
    obj = json.loads(raw)
    if obj["fields"] != ["cik", "name", "ticker", "exchange"]:
        raise ValueError("Unexpected SEC directory headings")
    return {(exchange, ticker, cik): name
            for cik, name, ticker, exchange in obj["data"]
            if exchange in {"NYSE", "Nasdaq"}}


def tag_value(entries, accession, end, start=None):
    candidates = {r["val"] for r in entries if r.get("accn") == accession
                  and r.get("form") == "10-K" and r.get("end") == end
                  and r.get("start") == start}
    if len(candidates) != 1:
        raise ValueError(f"Missing or conflicting SEC fact for {accession} / {end}")
    return candidates.pop()


def apple_financials(raw, record):
    obj = json.loads(raw)
    if obj["cik"] != record["cik"]:
        raise ValueError("Apple CIK mismatch")
    facts = obj["facts"]
    filing = record["financials"]
    accession = filing["accession"]
    amounts = facts["us-gaap"]
    for period in filing["periods"]:
        for field, tag in APPLE_TAGS.items():
            start = period["start"] if field in {"revenue", "operating_income", "net_income"} else None
            value = tag_value(amounts[tag]["units"]["USD"], accession, period["end"], start)
            if value != period[field]:
                raise ValueError(f"Apple {field} mismatch at {period['end']}")
    shares = filing["shares"]
    if tag_value(facts["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"],
                 accession, shares["as_of"]) != shares["value"]:
        raise ValueError("Apple outstanding common shares mismatch")


def toyota_financials(raw, record):
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "source.pdf"
        pdf.write_bytes(raw)
        text = subprocess.check_output(["pdftotext", "-layout", str(pdf), "-"], text=True)
    for period in record["financials"]["periods"]:
        year = "FY" + period["end"][:4]
        sales, operating, net, assets, equity = (f"{period[k] // 1_000_000:,}" for k in
                                                  ("revenue", "operating_income", "net_income", "assets", "parent_equity"))
        if not re.search(rf"^\s*{year}\s+{sales}\s+[-.\d]+\s+{operating}\s+[-.\d]+\s+[\d,]+\s+[-.\d]+\s+[\d,]+\s+[-.\d]+\s+{net}\b", text, re.M):
            raise ValueError(f"Toyota {year} income summary mismatch")
        if not re.search(rf"^\s*{year}\s+{assets}\s+[\d,]+\s+{equity}\b", text, re.M):
            raise ValueError(f"Toyota {year} balance sheet summary mismatch")
    shares = record["financials"]["shares"]
    if (not re.search(rf"including treasury stock\)\s*:\s*FY2026 {shares['issued']:,} shares", text)
            or not re.search(rf"Number of treasury stock at the end of each fiscal year:\s*FY2026 {shares['treasury']:,} shares", text)
            or shares["value"] != shares["issued"] - shares["treasury"]):
        raise ValueError("Toyota March share capital mismatch")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-directory", type=Path, help="Use locally downloaded originals")
    args = parser.parse_args()
    raw = {k: (args.fixture_directory / filename).read_bytes() if args.fixture_directory else fetch(SOURCES[k])
           for k, filename in (("jpx", "jpx.xlsx"), ("sec", "sec.json"),
                               ("apple", "apple.json"), ("toyota", "toyota.pdf"))}
    snapshot = json.loads(DATA.read_text())
    date, jpx = jpx_directory(raw["jpx"])
    sec = sec_directory(raw["sec"])
    if date != snapshot["jpx_snapshot_date"]:
        raise ValueError("JPX month-end changed; refresh or use the dated original workbook")
    for record in snapshot["records"]:
        if record["market"] == "JP":
            expected = (record["name"], record["board"])
            if jpx.get(record["symbol"]) != expected:
                raise ValueError(f"JPX identity mismatch: {record['symbol']}")
        elif sec.get((record["exchange"], record["symbol"], record["cik"])) != record["name"]:
            raise ValueError(f"SEC identity mismatch: {record['symbol']}")
    toyota = next(x for x in snapshot["records"] if x["id"] == "JP:7203")
    apple = next(x for x in snapshot["records"] if x["id"] == "US:AAPL")
    toyota_financials(raw["toyota"], toyota)
    apple_financials(raw["apple"], apple)
    report = {
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "jpx_snapshot_date": date,
        "jpx_domestic_prime_standard_growth_rows": len(jpx),
        "sec_nyse_nasdaq_ticker_cik_exchange_rows": len(sec),
        "source_sha256": {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()},
        "financials_verified": [toyota["id"], apple["id"]],
        "quotes_verified": False,
    }
    destination = ROOT / "build/research/market-source-verification-v315.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

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
import time
import urllib.error
import urllib.request

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "docs/data/market-research-v315.json"
SOURCES = {
    "jpx": "https://www.jpx.co.jp/english/markets/statistics-equities/misc/tvdivq0000001vg2-att/data_e.xlsx",
    "sec": "https://www.sec.gov/files/company_tickers_exchange.json",
    "toyota": "https://global.toyota/pages/global_toyota/ir/financial-results/2026_4q_summary_en.pdf",
    "oji": "https://www.ojiholdings.co.jp/en/uploads/docs/en0515irnews01.pdf",
}
MAX_BYTES = 12_000_000
SEC_TAGS = {
    "operating_income": "OperatingIncomeLoss",
    "net_income": "NetIncomeLoss",
    "assets": "Assets",
    "parent_equity": "StockholdersEquity",
}


def fetch(url):
    request = urllib.request.Request(url, headers={
        "User-Agent": "VALUE HUNTER AI research https://github.com/osawamas/value-hunter-ai",
    })
    try:
        with urllib.request.urlopen(request, timeout=35) as response:
            if response.geturl() != url:
                raise ValueError(f"Unexpected source redirect: {url}")
            raw = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise ValueError(f"HTTP {error.code} while retrieving {url}") from error
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


def sec_financials(raw, record):
    obj = json.loads(raw)
    if obj["cik"] != record["cik"]:
        raise ValueError("SEC CIK mismatch")
    facts = obj["facts"]
    filing = record["financials"]
    accession = filing["accession"]
    amounts = facts["us-gaap"]
    approved_revenue = {"Revenues", "RevenueFromContractWithCustomerExcludingAssessedTax"}
    if filing["revenue_tag"] not in approved_revenue:
        raise ValueError("Unrecognized SEC revenue concept")
    tags = {"revenue": filing["revenue_tag"], **SEC_TAGS}
    for period in filing["periods"]:
        for field, tag in tags.items():
            start = period["start"] if field in {"revenue", "operating_income", "net_income"} else None
            entries = amounts.get(tag, {}).get("units", {}).get("USD", [])
            if field == "operating_income" and period[field] is None:
                if any(r.get("accn") == accession and r.get("form") == "10-K" and
                       r.get("end") == period["end"] and r.get("start") == start for r in entries):
                    raise ValueError(f"{record['symbol']} operating income is present in SEC facts")
                continue
            value = tag_value(entries, accession, period["end"], start)
            if value != period[field]:
                raise ValueError(f"{record['symbol']} {field} mismatch at {period['end']}")
    if "share_classes" in filing:
        cover = filing["share_classes"]
        classes = cover["classes"]
        if ("shares" in filing or len(classes) < 2 or len({c["label"] for c in classes}) != len(classes)
                or sum(c["symbol"] == record["symbol"] for c in classes) != 1
                or any(type(c["value"]) is not int or c["value"] <= 0 for c in classes)
                or type(cover["rounded"]) is not bool):
            raise ValueError("Invalid SEC multi-class share data")
        dt.date.fromisoformat(cover["as_of"])
        if "reviewed_cover" in obj and obj["reviewed_cover"] != cover:
            raise ValueError("SEC share class counts differ from the reviewed cover")
        return
    shares = filing["shares"]
    if tag_value(facts["dei"]["EntityCommonStockSharesOutstanding"]["units"]["shares"],
                 accession, shares["as_of"]) != shares["value"]:
        raise ValueError("SEC outstanding common shares mismatch")


def pdf_text(raw, last_page=None, *, first_page=None):
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "source.pdf"
        pdf.write_bytes(raw)
        pages = ["-l", str(last_page)] if last_page else []
        if first_page:
            pages += ["-f", str(first_page)]
        return subprocess.check_output(["pdftotext", "-layout", *pages, str(pdf), "-"], text=True)


def check_s63_parent_equity(evidence, source_bytes):
    if (evidence["symbol"], evidence["period_end"], evidence["unit"], evidence["status"],
            evidence["independent_verification"]) != (
            "S63", "2025-12-31", "SGD_thousands", "MATCHED_TWO_ISSUER_FILINGS", False):
        raise ValueError("Unexpected S63 parent equity evidence scope")

    columns = r"[ \t]+"
    groups = {
        "parent_equity": r"Equity attributable to owners\s+of the Company",
        "non_controlling_interests": r"Non-controlling interests(?:[ \t]+F3)?",
        "total_equity": r"Net assets",
    }
    for name, page, heading in (
        ("annual_report", 131, r"^\s*ANNUAL REPORT 2025[ \t]+" + str(evidence["annual_report_printed_page"]) + r"\b"),
        ("results", 9, r"^\s*Page " + str(evidence["results_printed_page"]) + r" of 31\b"),
    ):
        raw = source_bytes(evidence[name + "_url"], name + ".pdf")
        digest = hashlib.sha256(raw).hexdigest()
        if digest != evidence[name + "_sha256"]:
            raise ValueError(f"S63 {name} PDF hash mismatch: {digest}")
        text = pdf_text(raw, page, first_page=page)
        if not re.search(heading, text, re.M) or "STATEMENT OF FINANCIAL POSITION" not in text:
            raise ValueError(f"S63 {name} financial position page mismatch")
        for field, label in groups.items():
            cells = re.findall(r"^\s*" + label + columns + r"([\d,]+)\b", text, re.M | re.I)
            if len(cells) != 1 or int(cells[0].replace(",", "")) != evidence[field]:
                raise ValueError(f"S63 {name} {field} mismatch")
        print(f"SG:S63 {name} matched, SHA256 {digest}")

    if evidence["parent_equity"] + evidence["non_controlling_interests"] != evidence["total_equity"]:
        raise ValueError("S63 parent equity reconciliation failed")


def toyota_financials(raw, record):
    text = pdf_text(raw, 3)
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


def japanese_financials(raw, record):
    text = pdf_text(raw, 2).translate(str.maketrans("　０１２３４５６７８９", " 0123456789"))
    finance = record["financials"]
    if not re.search(r"コ\s*ー\s*ド\s*番\s*号\s*" + record["symbol"] + r"\b", text):
        raise ValueError(f"TDnet identifier mismatch: {record['id']}")
    income = text.split("連結経営成績", 1)[1].split("連結財政状態", 1)[0]
    balance = text.split("連結財政状態", 1)[1].split("連結キャッシュ", 1)[0]
    amount = lambda value: ("△" if value < 0 else "") + f"{abs(value) // 1_000_000:,}"
    date_label = lambda date: rf"{date[:4]}年\s*{int(date[5:7])}月期"
    for row in finance["periods"]:
        label = date_label(row["end"])
        revenue, operating, net, assets = (amount(row[k]) for k in
                                            ("revenue", "operating_income", "net_income", "assets"))
        cell = r"\s+[△―－\d,.]+"
        if not re.search(rf"^\s*{label}\s+{revenue}{cell}\s+{operating}(?:{cell}){{3}}\s+{net}(?=\s)", income, re.M):
            raise ValueError(f"TDnet income mismatch: {record['id']} {row['end']}")
        if not re.search(rf"^\s*{label}\s+{assets}(?=\s)", balance, re.M):
            raise ValueError(f"TDnet assets mismatch: {record['id']} {row['end']}")
        if not re.search(rf"自己資本[^\n]*{label}\s+{amount(row['parent_equity'])}百万円", balance):
            raise ValueError(f"TDnet parent equity mismatch: {record['id']} {row['end']}")
    shares = finance["shares"]
    label = date_label(shares["as_of"])
    if (not re.search(rf"期末発行済株式数[^\n]*{label}\s+{shares['issued']:,}株", text)
            or not re.search(rf"期末自己株式数\s+{label}\s+{shares['treasury']:,}株", text)
            or shares["issued"] - shares["treasury"] != shares["value"]):
        raise ValueError(f"TDnet share capital mismatch: {record['id']}")


def oji_financials(raw, record):
    text = pdf_text(raw, 2)
    if "Code No. 3861 Tokyo Stock Exchange" not in text or "Year Ended March 31, 2026" not in text:
        raise ValueError("Oji issuer or reporting year mismatch")
    finance = record["financials"]
    for row in finance["periods"]:
        year = f"FY{int(row['end'][:4]) - 1}"
        sales, operating, net, assets, equity = (f"{row[k] // 1_000_000:,}" for k in
                                                 ("revenue", "operating_income", "net_income", "assets", "parent_equity"))
        if not re.search(rf"^\s*{year}\s+{sales}\s+[\d.()]+\s+{operating}\s+[\d.()]+\s+[\d,]+\s+[\d.()]+\s+{net}\b", text, re.M):
            raise ValueError(f"Oji {year} income mismatch")
        if not re.search(rf"^\s*{year}\s+{assets}\s+[\d,]+\s+[\d.]+\s+[\d,.]+\s*$", text, re.M):
            raise ValueError(f"Oji {year} assets mismatch")
        if not re.search(rf"Note: Shareholders' equity[^\n]*{year}\s+{equity}\s+million yen", text):
            raise ValueError(f"Oji {year} equity mismatch")
    capital = text.split("Outstanding balance of issued shares (common stock)", 1)[1]
    shares = finance["shares"]
    if (not re.search(rf"FY2025\s+{shares['issued']:,}\b", capital.split("Outstanding balance of treasury shares", 1)[0])
            or not re.search(rf"Outstanding balance of treasury shares\s+FY2025\s+{shares['treasury']:,}\b", capital)
            or shares["issued"] - shares["treasury"] != shares["value"]):
        raise ValueError("Oji year-end shares mismatch")


def japanese_interim(raw, record):
    from unicodedata import normalize

    filing = record["quarterly"]
    text = normalize("NFKC", pdf_text(raw, 2))
    if not re.search(r"コ\s*ー\s*ド\s*番\s*号\s*" + record["symbol"] + r"\b", text):
        raise ValueError(f"Interim issuer differs: {record['id']}")
    if "連結経営成績(累計)" not in re.sub(r"\s+", "", text):
        raise ValueError(f"Cumulative heading not found: {record['id']}")
    start, end = (dt.date.fromisoformat(filing["periods"][-1][key]) for key in ("start", "end"))
    start_label = f"{start.year}年{start.month}月{start.day}日"
    end_label = f"{end.year}年{end.month}月{end.day}日"
    compact = re.sub(r"\s+", "", text)
    issued_on = dt.date.fromisoformat(filing["filed"])
    if (f"{issued_on.year}年{issued_on.month}月{issued_on.day}日" not in compact or
            start_label + "~" + end_label not in compact):
        raise ValueError(f"Interim period or announcement date differs: {record['id']}")
    term = r"3月期中間期" if start.month == 4 else r"12月期第3四半期"
    fiscal_offset = int(start.month == 4)
    for row in filing["periods"]:
        label = str(int(row["start"][:4]) + fiscal_offset) + "年" + term
        table = text.split("連結経営成績", 1)[1].split("連結財政状態", 1)[0]
        match = re.search(r"^\s*" + label + r"\s+(.+)$", table, re.M)
        if not match:
            raise ValueError(f"Interim income row missing: {record['id']} {row['end']}")
        cells = match[1].split()
        net_column = 8 if record["symbol"] == "7203" else 6
        values = [int(cells[index].replace(",", "").replace("△", "-")) * 1_000_000
                  for index in (0, 2, net_column)]
        if values != [row[key] for key in ("revenue", "operating_income", "net_income")]:
            raise ValueError(f"Interim amounts differ: {record['id']}")
    shares = filing["shares"]
    share_label = str(start.year + fiscal_offset) + ("年3月期中間期" if fiscal_offset else "年12月期3Q")
    for key, heading in (("issued", "期末発行済株式数"), ("treasury", "期末自己株式数")):
        pattern = heading + r"[^\n]*?" + share_label + rf"\s+{shares[key]:,}株"
        if not re.search(pattern, text):
            raise ValueError(f"Interim shares differ: {record['id']} {key}")
    if shares["value"] != shares["issued"] - shares["treasury"] or shares["as_of"] != end.isoformat():
        raise ValueError(f"Interim share calculation/date differs: {record['id']}")


def check_sec_originals(records, source_bytes):
    checked = {}
    for record in records:
        if record["market"] != "US" or not record.get("financials"):
            continue
        url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{record['cik']:010d}.json"
        if record["financials"]["source"] != url:
            raise ValueError("SEC company facts URL changed")
        raw = source_bytes(url, record["symbol"].lower() + ".json")
        sec_financials(raw, record)
        checked[record["id"]] = raw
    return checked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-directory", type=Path, help="Use locally downloaded originals")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-sec-excerpts", action="store_true", help="Check selected saved SEC facts offline")
    modes.add_argument("--sec-originals-only", action="store_true", help="Replay original SEC company facts independently of the listing directory")
    modes.add_argument("--jp-interim-only", action="store_true", help="Replay Japanese interim filing originals")
    modes.add_argument("--jp-only", action="store_true", help="Replay the Japanese originals")
    modes.add_argument("--sgx-s63-equity-only", action="store_true", help="Replay both S63 FY2025 issuer PDFs")
    args = parser.parse_args()
    snapshot = json.loads(DATA.read_text())
    if args.check_sec_excerpts:
        excerpts = json.loads((ROOT / "tests/fixtures/sec-filing-excerpts-v316.json").read_text())
        for record in snapshot["records"]:
            if record["market"] == "US" and record.get("financials"):
                sec_financials(json.dumps(excerpts[record["symbol"]]), record)
        print("Saved SEC filing excerpts match. Live sources were not checked in this step.")
        return

    def source_bytes(url, filename):
        if not args.fixture_directory and "sec.gov/" in url:
            time.sleep(0.25)
        return (args.fixture_directory / filename).read_bytes() if args.fixture_directory else fetch(url)

    if args.sgx_s63_equity_only:
        equity = json.loads((ROOT / "docs/data/sgx-s63-parent-equity-v395.json").read_text())
        check_s63_parent_equity(equity, source_bytes)
        return

    if args.jp_interim_only:
        for record in snapshot["records"]:
            if record["market"] == "JP" and record.get("quarterly"):
                raw = source_bytes(record["quarterly"]["source"], record["symbol"] + ".pdf")
                japanese_interim(raw, record)
                print(f"{record['id']} interim matched, SHA256 {hashlib.sha256(raw).hexdigest()}")
        return

    if args.sec_originals_only:
        originals = check_sec_originals(snapshot["records"], source_bytes)
        print(json.dumps({
            "source": "SEC company facts",
            "evidence": "local_originals" if args.fixture_directory else "downloaded_originals",
            "sha256": {key: hashlib.sha256(raw).hexdigest() for key, raw in originals.items()},
        }, indent=2))
        return

    raw = {"jpx": source_bytes(SOURCES["jpx"], "jpx.xlsx")}
    if not args.jp_only:
        raw["sec"] = source_bytes(SOURCES["sec"], "sec.json")
    date, jpx = jpx_directory(raw["jpx"])
    sec = sec_directory(raw["sec"]) if "sec" in raw else None
    reference_date = snapshot["jpx_snapshot_date"]
    if date < reference_date:
        raise ValueError("JPX workbook predates the research snapshot")
    if date > reference_date:
        print(f"JPX used newer month-end {date}; replay of {reference_date} requires the dated original.")
    for record in snapshot["records"]:
        if record["market"] == "JP":
            expected = (record["name"], record["board"])
            if jpx.get(record["symbol"]) != expected:
                raise ValueError(f"JPX identity mismatch: {record['symbol']}")
        elif sec is not None and sec.get((record["exchange"], record["symbol"], record["cik"])) != record["name"]:
            raise ValueError(f"SEC identity mismatch: {record['symbol']}")
    verified = []
    for record in snapshot["records"]:
        finance = record.get("financials")
        if not finance or (args.jp_only and record["market"] != "JP"):
            continue
        key = record["symbol"].lower()
        if record["market"] == "JP":
            url = finance["source"]
            if record["symbol"] == "7203" and url == SOURCES["toyota"]:
                raw[key] = source_bytes(url, "toyota.pdf")
                toyota_financials(raw[key], record)
            elif record["symbol"] == "3861" and url == SOURCES["oji"]:
                raw[key] = source_bytes(url, key + ".pdf")
                oji_financials(raw[key], record)
            elif re.fullmatch(rf"https://www2\.jpx\.co\.jp/disc/{key}0/\d+\.pdf", url):
                raw[key] = source_bytes(url, key + ".pdf")
                japanese_financials(raw[key], record)
            else:
                raise ValueError(f"Unexpected Japanese filing source: {record['id']}")
            verified.append(record["id"])
            continue
    if not args.jp_only:
        originals = check_sec_originals(snapshot["records"], source_bytes)
        raw.update({key.split(":")[1].lower(): value for key, value in originals.items()})
        verified.extend(originals)
    report = {
        "checked_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "jpx_snapshot_date": date,
        "jpx_research_snapshot_date": reference_date,
        "jpx_snapshot_replayed": date == reference_date,
        "jpx_domestic_prime_standard_growth_rows": len(jpx),
        "sec_nyse_nasdaq_ticker_cik_exchange_rows": len(sec) if sec is not None else None,
        "source_sha256": {k: hashlib.sha256(v).hexdigest() for k, v in raw.items()},
        "financials_verified": verified,
        "quotes_verified": False,
    }
    destination = ROOT / "build/research/market-source-verification-v315.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()

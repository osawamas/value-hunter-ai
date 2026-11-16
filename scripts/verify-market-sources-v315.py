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
import sys
import tempfile
import time
import urllib.error
import urllib.request
from xml.etree import ElementTree

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


def filing_column(text, label, column):
    cells = re.findall(r"^\s*" + re.escape(label) + r"[ \t]+([()0-9,].*)$", text, re.M)
    if len(cells) != 1:
        raise ValueError(f"Issuer results: expected one row for {label}")
    value = cells[0].split()[column].replace(",", "")
    return -int(value[1:-1]) if value.startswith("(") else int(value)



def recalculate_s63_results(raw, balance_text, feed_row):
    income = pdf_text(raw, 2, first_page=2)
    group_profit = filing_column(income, "Profit after taxation", 3)
    minority_profit = filing_column(income, "Non-controlling interests", 3)
    reported_profit = filing_column(income, "Shareholders of the Company", 3)
    recalculated_profit = group_profit - minority_profit
    if recalculated_profit != reported_profit or recalculated_profit != feed_row["attributable_profit_sgd_thousands"]:
        raise ValueError("S63 attributable profit recalculation mismatch")

    labels = ("Share capital", "Treasury shares", "Capital reserves", "Other reserves", "Retained earnings")
    recalculated_equity = sum(filing_column(balance_text, label, 0) for label in labels)
    if recalculated_equity != feed_row["parent_equity_sgd_thousands"]:
        raise ValueError("S63 parent equity component sum mismatch")
    print(f"SG:S63 FY2025 components agree with feed: profit {recalculated_profit:,}, "
          f"parent equity {recalculated_equity:,} (SGD thousands)")


def check_s63_interim(raw, evidence, row):
    if hashlib.sha256(raw).hexdigest() != evidence["source_sha256"]:
        raise ValueError("S63 interim PDF hash mismatch")
    income = pdf_text(raw, 6, first_page=6)
    balance = pdf_text(raw, 12, first_page=12)
    audit = pdf_text(raw, 22, first_page=22)
    if (evidence["symbol"], evidence["period_end"], evidence["currency"], evidence["unit"],
            evidence["assurance"]) != ("S63", "2026-06-30", "SGD", "SGD_thousands", "UNAUDITED_AND_UNREVIEWED"):
        raise ValueError("Unexpected S63 interim metadata")
    if ("SINGAPORE TECHNOLOGIES ENGINEERING LTD" not in income
            or "CONSOLIDATED INCOME STATEMENT FOR THE FIRST HALF-YEAR ENDED 30 JUNE 2026" not in income
            or not re.search(r"Group\s+1H2026\s+1H2025[^\n]*\n\s*\$'000\s+\$'000", income)
            or not re.search(r"Group\s+Company\s+30-Jun-26\s+31-Dec-25[^\n]*\n\s*\$'000\s+\$'000", balance)
            or "have not been audited or reviewed" not in audit):
        raise ValueError("Unexpected S63 interim filing scope")
    owner_equity = re.sub(r"Equity attributable to owners\s+of the Company", "Parent equity", balance)
    for column, profit_key, equity_key in (
        (0, "attributable_profit_h1", "parent_equity"),
        (1, "attributable_profit_prior_h1", "prior_year_end_parent_equity"),
    ):
        profit = filing_column(income, "Profit after taxation", column) - filing_column(income, "Non-controlling interests", column)
        equity = filing_column(balance, "NET ASSETS", column) - filing_column(balance, "Non-controlling interests", column)
        if profit != evidence[profit_key] or profit != filing_column(income, "Shareholders of the Company", column):
            raise ValueError("S63 interim attributable profit mismatch")
        if equity != evidence[equity_key] or equity != filing_column(owner_equity, "Parent equity", column):
            raise ValueError("S63 interim parent equity mismatch")
    if row["fiscal_year"] != 2025 or row["parent_equity_sgd_thousands"] != evidence["prior_year_end_parent_equity"]:
        raise ValueError("S63 interim comparative equity does not match the annual feed")
    trailing_profit = row["attributable_profit_sgd_thousands"] + evidence["attributable_profit_h1"] - evidence["attributable_profit_prior_h1"]
    print(f"SG:S63 interim filing matched (unaudited and unreviewed), trailing profit {trailing_profit:,}, "
          f"parent equity {evidence['parent_equity']:,} (SGD thousands), SHA256 {evidence['source_sha256']}")


def check_g13_financials(raw, row):
    if row["fiscal_year"] != 2025:
        raise ValueError("G13 feed fiscal year mismatch")
    income = pdf_text(raw, 1)
    balance = pdf_text(raw, 4, first_page=4)
    if ("Genting Singapore Limited (Company Registration No. 201818581G)" not in income
            or "FINANCIAL STATEMENTS FOR THE FINANCIAL YEAR ENDED 31 DECEMBER 2025" not in income
            or "Statement of Comprehensive Income for the Group" not in income
            or "Statements of Financial Position (Continued)" not in balance
            or "Equity attributable to ordinary" not in balance
            or not re.search(r"Group\s+Company\s+31 December 31 December\s+31 December 31 December\s+2025\s+2024", balance)):
        raise ValueError("G13 FY2025 results PDF identity or reporting scope mismatch")
    profit = filing_column(income, "Profit before taxation", 0) + filing_column(income, "Taxation", 0)
    reported_profit = filing_column(income, "Net profit attributable to ordinary shareholders of the Company", 0)
    if profit != reported_profit or profit != row["attributable_profit_sgd_thousands"]:
        raise ValueError("G13 attributable profit recalculation mismatch")
    labels = ("Share capital", "Treasury shares", "Other reserves", "Retained earnings")
    equity = sum(filing_column(balance, label, 0) for label in labels)
    if equity != filing_column(balance, "Total equity", 0) or equity != row["parent_equity_sgd_thousands"]:
        raise ValueError("G13 parent equity component sum mismatch")
    print(f"SG:G13 FY2025 components agree with feed: profit {profit:,}, "
          f"parent equity {equity:,} (SGD thousands), SHA256 {hashlib.sha256(raw).hexdigest()}")


def check_s63_equity_movements(raw, evidence, feed_row):
    labels = pdf_text(raw, 132, first_page=132)
    amounts = pdf_text(raw, 133, first_page=133)
    if ("CONSOLIDATED STATEMENT OF CHANGES IN EQUITY" not in labels
            or "FOR THE YEAR ENDED 31 DECEMBER 2025" not in labels
            or not re.search(r"^\s*ANNUAL REPORT 2025[ \t]+131\b", amounts, re.M)
            or "Non-controlling" not in amounts):
        raise ValueError("S63 equity movement table scope mismatch")

    cell = r"(?:–|\([\d,]+\)|[\d,]+)"
    label_rows = re.findall(rf"^\s*(\S[^\n]*?)[ \t]+{cell}[ \t]+{cell}[ \t]*$", labels, re.M)
    amount_rows = [line.split() for line in amounts.splitlines()
                   if re.fullmatch(rf"\s*{cell}(?:[ \t]+{cell}){{5}}\s*", line)]
    if len(label_rows) != 24 or len(amount_rows) != len(label_rows):
        raise ValueError("S63 equity movement table row alignment mismatch")

    def values(pattern):
        matching = [row for label, row in zip(label_rows, amount_rows) if re.fullmatch(pattern, label.strip())]
        if len(matching) != 1:
            raise ValueError(f"S63 equity movement row missing or ambiguous: {pattern}")
        return tuple(0 if value == "–" else int(value.replace(",", "").replace("(", "-").replace(")", ""))
                     for value in matching[0][3:])

    opening = values("At 1 January 2025")
    profit = values("Profit after taxation")
    other = values("Other comprehensive income for the year, net of tax")
    comprehensive = values("Total comprehensive income for the year, net of tax")
    hedging = values("cost of inventory")
    transactions = values("Total transactions with owners of the Company")
    closing = values("Balance at 31 December 2025")
    expected = (evidence["parent_equity"], evidence["non_controlling_interests"], evidence["total_equity"])
    if (profit[0] != feed_row["attributable_profit_sgd_thousands"]
            or tuple(a + b for a, b in zip(profit, other)) != comprehensive
            or tuple(sum(parts) for parts in zip(opening, comprehensive, hedging, transactions)) != closing
            or closing != expected or closing[0] != feed_row["parent_equity_sgd_thousands"]):
        raise ValueError("S63 equity movement or attributable profit reconciliation failed")
    print(f"SG:S63 audited equity movements reconcile: shareholder profit {profit[0]:,}, "
          f"year-end parent equity {closing[0]:,} (SGD thousands)")


def check_s63_parent_equity(evidence, source_bytes, feed_row):
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
        if name == "annual_report":
            check_s63_equity_movements(raw, evidence, feed_row)
        else:
            recalculate_s63_results(raw, text, feed_row)
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


def check_toyota_q1_shares(raw, report):
    digest = hashlib.sha256(raw).hexdigest()
    if digest != report["source_sha256"]:
        raise ValueError("Toyota Q1 share disclosure hash mismatch")
    cover = pdf_text(raw, 2, first_page=2)
    notes = pdf_text(raw, 3, first_page=3)
    if (report["as_of"] != "2026-06-30" or report["disclosedOn"] != "2026-08-04"
            or report["rounded"] is not False
            or "August 4, 2026" not in cover or "June 30, 2026" not in cover
            or not re.search(r"Code number\s*:\s*7203\b", cover)
            or not re.search(r"shares held by the Trust are included in both the number of shares of treasury stock", notes)):
        raise ValueError("Toyota Q1 share disclosure date or scope mismatch")
    issued = re.search(r"including treasury stock\): FY2027 first quarter ([\d,]+)\s+shares", notes)
    treasury = re.search(r"Number of treasury stock at the end of each period: FY2027 first quarter ([\d,]+) shares", notes)
    counts = tuple(int(match[1].replace(",", "")) for match in (issued, treasury) if match)
    if counts != (report["issued"], report["treasury"]) or report["issued"] - report["treasury"] != report["value"]:
        raise ValueError("Toyota Q1 share counts mismatch")
    print(f"JP:7203 June quarter shares matched (ESOP shares included in treasury), SHA256 {digest}")


def check_toyota_month_end_treasury(raw, report):
    digest = hashlib.sha256(raw).hexdigest()
    if digest != report["source_sha256"]:
        raise ValueError("Toyota EDINET monthly report hash mismatch")
    cover = pdf_text(raw, 1)
    holding = pdf_text(raw, 3, first_page=3)
    as_of = dt.date.fromisoformat(report["as_of"])
    filed = dt.date.fromisoformat(report["filed"])
    if ("【提出日】" not in cover or f"{filed.year}年{filed.month}月{filed.day}日" not in cover
            or "トヨタ自動車株式会社(E02144)" not in holding
            or f"{as_of.year}年{as_of.month}月{as_of.day}日現在" not in holding
            or report["scope"] != "ISSUER_HELD_TREASURY_EXCLUDES_ESOP_TRUST"
            or "株式付与ESOP信託が保有する当社株式は含まれておりません" not in holding):
        raise ValueError("Toyota EDINET monthly report scope mismatch")
    for key, label in (("issued", "発行済株式総数"), ("treasury", "保有自己株式数")):
        if filing_column(holding, label, 0) != report[key]:
            raise ValueError(f"Toyota monthly {key} count mismatch")
    print(f"JP:7203 EDINET month-end {as_of} shares matched, SHA256 {digest}")


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


def check_ibm_share_filing(raw, record):
    namespaces = {"ix": "http://www.xbrl.org/2013/inlineXBRL",
                  "xbrli": "http://www.xbrl.org/2003/instance"}
    root = ElementTree.fromstring(raw)
    shares = record["quarterly"]["shares"]
    contexts = {
        context.get("id")
        for context in root.findall(".//xbrli:context", namespaces)
        if context.findtext("xbrli:entity/xbrli:identifier", namespaces=namespaces) == "0000051143"
        and context.findtext("xbrli:period/xbrli:instant", namespaces=namespaces) == shares["as_of"]
        and context.find("xbrli:entity/xbrli:segment", namespaces) is None
        and context.find("xbrli:scenario", namespaces) is None
    }
    units = {
        unit.get("id") for unit in root.findall(".//xbrli:unit", namespaces)
        if unit.findtext("xbrli:measure", namespaces=namespaces) == "xbrli:shares"
    }
    values = set()
    for fact in root.findall(".//ix:nonFraction", namespaces):
        if (fact.get("name") != "dei:EntityCommonStockSharesOutstanding"
                or fact.get("contextRef") not in contexts or fact.get("unitRef") not in units):
            continue
        digits = "".join(fact.itertext()).strip().replace(",", "")
        if (fact.get("scale", "0") != "0" or fact.get("decimals") != "0"
                or fact.get("sign") is not None or not re.fullmatch(r"[0-9]+", digits)):
            raise ValueError("IBM share fact is not an exact positive share count")
        values.add(int(digits))
    if shares["rounded"] is not False or shares["value"] <= 0 or values != {shares["value"]}:
        raise ValueError("IBM share count or filing date differs from the stored evidence")


def check_ibm_annual_filing(main_filing, exhibit, finance):
    fields = {"revenue": finance["revenue_tag"], "net_income": SEC_TAGS["net_income"],
              "assets": SEC_TAGS["assets"], "parent_equity": SEC_TAGS["parent_equity"]}
    expected = [(tag, period["start"] if field in ("revenue", "net_income") else None,
                 period["end"], period[field]) for period in finance["periods"]
                for field, tag in fields.items()]
    check_ibm_financial_facts(main_filing, exhibit, expected)


def check_ibm_financial_facts(main_filing, exhibit, expected):
    namespaces = {"ix": "http://www.xbrl.org/2013/inlineXBRL",
                  "xbrli": "http://www.xbrl.org/2003/instance"}
    root = ElementTree.fromstring(main_filing)
    contexts = {}
    for context in root.findall(".//xbrli:context", namespaces):
        if (context.findtext("xbrli:entity/xbrli:identifier", namespaces=namespaces) != "0000051143"
                or context.find("xbrli:entity/xbrli:segment", namespaces) is not None
                or context.find("xbrli:scenario", namespaces) is not None):
            continue
        period = context.find("xbrli:period", namespaces)
        if period is not None:
            start = period.findtext("xbrli:startDate", namespaces=namespaces)
            end = period.findtext("xbrli:endDate", namespaces=namespaces)
            instant = period.findtext("xbrli:instant", namespaces=namespaces)
            contexts[context.get("id")] = (start, end) if start and end else (None, instant)
    usd_units = {
        unit.get("id") for unit in root.findall(".//xbrli:unit", namespaces)
        if unit.findtext("xbrli:measure", namespaces=namespaces) == "iso4217:USD"
    }
    facts = ElementTree.fromstring(exhibit).findall(".//ix:nonFraction", namespaces)
    for tag, start, end, amount in expected:
        values = set()
        for fact in facts:
            if (fact.get("name") != "us-gaap:" + tag or fact.get("unitRef") not in usd_units
                    or contexts.get(fact.get("contextRef")) != (start, end)):
                continue
            digits = "".join(fact.itertext()).strip().replace(",", "")
            sign = fact.get("sign")
            if (fact.get("scale") != "6" or fact.get("decimals") != "-6"
                    or sign not in (None, "-") or not re.fullmatch(r"[0-9]+", digits)):
                raise ValueError(f"Unexpected IBM filing numeric format for {tag}")
            values.add(int(digits) * (-1 if sign == "-" else 1) * 1_000_000)
        if values != {amount}:
            raise ValueError(f"IBM {end} {tag} differs from the filing")


def check_s63_share_notice(raw, evidence):
    sys.path.insert(0, str(ROOT / "SGX_PDF_connection_probe"))
    from sgx_s63_buyback_v109 import parse_notice

    notice = parse_notice(raw, evidence["sgx_share_source_url"])
    broadcast = dt.datetime.strptime(notice["broadcast_sgt_text"], "%d-%b-%Y %H:%M:%S")
    broadcast = broadcast.replace(tzinfo=dt.timezone(dt.timedelta(hours=8))).isoformat()
    fields = {
        "symbol": notice["symbol"],
        "session_date_sgt": notice["purchase_date"],
        "sgx_share_announcement_reference": notice["reference"],
        "sgx_share_disclosed_at_sgt": broadcast,
        "sgx_share_source_url": notice["source_url"],
        "original_sgx_shares_ex_treasury": notice["issued_excluding_treasury_after_purchase"],
    }
    for key, value in fields.items():
        if evidence.get(key) != value:
            raise ValueError(f"S63 share evidence does not match the source: {key}")
    expected_digest = evidence.get("sgx_share_source_sha256")
    if expected_digest is not None and expected_digest != notice["source_sha256"]:
        raise ValueError("S63 share notice hash mismatch")
    if evidence.get("original_sgx_share_snapshot_on_same_date") is not True:
        raise ValueError("S63 share evidence is missing its same-date confirmation")
    print(f"SG:S63 share notice matched, SHA256 {notice['source_sha256']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture-directory", type=Path, help="Use locally downloaded originals")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check-sec-excerpts", action="store_true", help="Check selected saved SEC facts offline")
    modes.add_argument("--sec-originals-only", action="store_true", help="Replay original SEC company facts independently of the listing directory")
    modes.add_argument("--jp-interim-only", action="store_true", help="Replay Japanese interim filing originals")
    modes.add_argument("--jp-only", action="store_true", help="Replay the Japanese originals")
    modes.add_argument("--sgx-g13-financials-only", action="store_true", help="Recalculate G13 FY2025 issuer financials")
    modes.add_argument("--sgx-s63-equity-only", action="store_true", help="Replay both S63 FY2025 issuer PDFs")
    modes.add_argument("--sgx-s63-shares-only", action="store_true", help="Replay the S63 SGXNet share notice")
    modes.add_argument("--sec-ibm-shares-only", action="store_true", help="Reconcile IBM shares against its original SEC 10-Q")
    modes.add_argument("--sec-ibm-annual-only", action="store_true", help="Reconcile IBM financials against the original SEC 10-K exhibit")
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

    if args.sgx_g13_financials_only:
        feed = json.loads((ROOT / "docs/data/latest.json").read_text())
        row = next(row for row in feed["records"] if row["symbol"] == "G13")
        url = "https://links.sgx.com/FileOpen/2.%20GENS%20FY2025%20SGX%20Results%20Announcement.ashx?App=Announcement&FileID=875733"
        raw = source_bytes(url, "g13-results.pdf")
        if not raw.startswith(b"%PDF-"):
            raise ValueError("SGX did not return the G13 FY2025 results PDF")
        check_g13_financials(raw, row)
        sys.path.insert(0, str(ROOT / "SGX_PDF_connection_probe"))
        from g13_sgx_buyback_v122 import URL, parse

        saved = json.loads((ROOT / "docs/data/sgx-g13-june10-shares-v122.json").read_text())
        notice = parse(source_bytes(URL, "G13-buyback-2026-06-10.html"))
        if saved["source_url"] != URL or saved["status"] != notice["status"] or notice != saved["record"]:
            raise ValueError("G13 SGXNet June 10 share evidence differs from saved original")
        print(f"SG:G13 June 10 share notice matched, SHA256 {notice['html_sha256']}")
        return

    if args.sgx_s63_equity_only:
        equity = json.loads((ROOT / "docs/data/sgx-s63-parent-equity-v395.json").read_text())
        feed = json.loads((ROOT / "docs/data/latest.json").read_text())
        row = next(row for row in feed["records"] if row["symbol"] == equity["symbol"])
        if row["fiscal_year"] != int(equity["period_end"][:4]):
            raise ValueError("S63 feed fiscal year mismatch")
        check_s63_parent_equity(equity, source_bytes, row)
        interim = json.loads((ROOT / "docs/data/sgx-s63-interim-v469.json").read_text())
        check_s63_interim(source_bytes(interim["source_url"], "S63-interim.pdf"), interim, row)
        return

    if args.sgx_s63_shares_only:
        from urllib.parse import urlsplit

        for name, fixture in (
            ("sgx-s63-two-website-close-v129.json", "S63-buyback.html"),
            ("sgx-s63-historical-shares-v423.json", "S63-buyback-2026-10-26.html"),
            ("sgx-s63-shares-2026-11-16-v479.json", "S63-buyback-2026-11-16.html"),
        ):
            evidence = json.loads((ROOT / "docs/data" / name).read_text())
            source = evidence["sgx_share_source_url"]
            url = urlsplit(source)
            if url.scheme != "https" or url.netloc != "links.sgx.com":
                raise ValueError("S63 share notice must use the official SGX archive")
            check_s63_share_notice(source_bytes(source, fixture), evidence)
        return

    if args.sec_ibm_shares_only:
        record = next(record for record in snapshot["records"] if record["id"] == "US:IBM")
        raw = source_bytes(record["quarterly"]["source"], "IBM-10Q.html")
        check_ibm_share_filing(raw, record)
        interim = record["quarterly"]["valuation_basis"]
        check_ibm_financial_facts(raw, raw, [
            ("NetIncomeLoss", interim["current_start"], interim["period_end"], interim["current_net_income"]),
            ("NetIncomeLoss", interim["prior_start"], interim["prior_end"], interim["prior_net_income"]),
            ("StockholdersEquity", None, interim["period_end"], interim["parent_equity"]),
            ("StockholdersEquity", None, interim["annual_period_end"], interim["comparative_parent_equity"]),
        ])
        print(f"US:IBM SEC 10-Q shares and interim financials matched, SHA256 {hashlib.sha256(raw).hexdigest()}")
        historical, = record["historical_share_filings"]
        raw = source_bytes(historical["source"], "IBM-10Q-June.html")
        check_ibm_share_filing(raw, {"quarterly": {"shares": historical}})
        print(f"US:IBM June SEC 10-Q shares matched, SHA256 {hashlib.sha256(raw).hexdigest()}")
        return

    if args.sec_ibm_annual_only:
        finance = next(record["financials"] for record in snapshot["records"] if record["id"] == "US:IBM")
        main_filing = source_bytes(finance["filing_url"], "IBM-10K.html")
        exhibit = "https://www.sec.gov/Archives/edgar/data/51143/000005114326000010/ibm-20251231_d2.htm"
        raw = source_bytes(exhibit, "IBM-10K-EX13.html")
        check_ibm_annual_filing(main_filing, raw, finance)
        print(f"US:IBM SEC 10-K context SHA256 {hashlib.sha256(main_filing).hexdigest()}")
        print(f"US:IBM SEC 10-K Exhibit 13 financials matched, SHA256 {hashlib.sha256(raw).hexdigest()}")
        return

    if args.jp_interim_only:
        for record in snapshot["records"]:
            if record["market"] == "JP" and record.get("quarterly"):
                raw = source_bytes(record["quarterly"]["source"], record["symbol"] + ".pdf")
                japanese_interim(raw, record)
                print(f"{record['id']} interim matched, SHA256 {hashlib.sha256(raw).hexdigest()}")
            if record["id"] == "JP:7203":
                q1 = next(item for item in record["historical_share_filings"] if item["as_of"] == "2026-06-30")
                check_toyota_q1_shares(source_bytes(q1["source"], "7203-q1.pdf"), q1)
                report = record["month_end_treasury_report"]
                check_toyota_month_end_treasury(source_bytes(report["source"], "7203-edinet.pdf"), report)
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

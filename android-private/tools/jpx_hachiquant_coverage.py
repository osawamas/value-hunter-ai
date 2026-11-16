"""Measure JPX and Hachiquant coverage using local JPX reports and the free REST API."""
import argparse
from collections import Counter
from datetime import date
from decimal import Decimal
import json
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from jpx_daily_probe import CODE, MARKETS, ordinary_stocks, read_quotes
from jpx_valuation_probe import trading_date

BASE = "https://hachiquant.com/api/v1"
PAGE_SIZE = 200
DOC_ID = re.compile(r"S[0-9A-Z]{7}")


def fetch(path):
    request = Request(BASE + path, headers={
        "Accept": "application/json",
        "User-Agent": "VALUE-HUNTER-AI coverage verification",
    })
    for attempt in range(2):
        try:
            with urlopen(request, timeout=20) as response:
                body = response.read(4_000_001)
                if len(body) > 4_000_000:
                    raise ValueError("Hachiquant response exceeded the size limit")
                return json.loads(body, parse_float=Decimal), response.headers.get("X-Data-As-Of")
        except HTTPError as error:
            wait = error.headers.get("Retry-After", "")
            if attempt or error.code != 429 or not wait.isdecimal() or int(wait) > 30:
                raise
            time.sleep(max(1.2, int(wait)))


def annual_rows():
    rows = {}
    total = None
    as_of = None
    for page in range(40):
        if page:
            time.sleep(1.2)
        offset = PAGE_SIZE * page
        payload, stamp = fetch(f"/screener?limit={PAGE_SIZE}&offset={offset}")
        if page == 0:
            total = payload["total"]
            as_of = date.fromisoformat(stamp)
            if type(total) is not int or not 1 <= total <= PAGE_SIZE * 40:
                raise ValueError("Unexpected number of Hachiquant company records")
        if stamp != as_of.isoformat() or payload["total"] != total or payload["offset"] != offset:
            raise ValueError("Hachiquant snapshot changed during pagination")
        items = payload["results"]
        if len(items) != min(PAGE_SIZE, total - offset):
            raise ValueError("Hachiquant returned an incomplete page")
        for row in items:
            ticker = row["ticker"]
            if not CODE.fullmatch(ticker) or ticker in rows:
                raise ValueError("Invalid or duplicate ticker in Hachiquant snapshot")
            rows[ticker] = row
        if len(rows) == total:
            return rows, as_of, page + 1
    raise ValueError("Hachiquant pagination did not finish")


def numeric(value):
    return type(value) in (int, Decimal) and Decimal(value).is_finite()


def summarize(stocks, prices, duplicates, rows, day):
    totals = {"all": Counter(), **{market: Counter() for market in MARKETS.values()}}
    for code, market in stocks.items():
        matched = rows.get(code)
        am, pm = prices.get(code, (None, None))
        close = pm if pm is not None else am
        flags = ["listed"]
        if matched is not None:
            flags.append("financial_row")
        if code not in duplicates and close is not None and close > 0:
            flags.append("close")
            if matched is not None and matched.get("currency") == "JPY" and matched.get("span") == "FY":
                metrics = matched["metrics"]
                eps, bps = metrics.get("eps"), metrics.get("bvps")
                if numeric(eps) and numeric(bps):
                    flags.append("close_and_eps_bps")
                    if eps > 0 and bps > 0:
                        flags.append("close_and_positive_eps_bps")
                        doc_id = matched.get("source_doc_id")
                        if isinstance(doc_id, str) and DOC_ID.fullmatch(doc_id):
                            flags.append("close_positive_and_source_id")
                            # The latest periodic filing may be newer than the annual source.
                            # This date is a diagnostic, never the annual source's filing date.
                            latest = matched.get("latest_filing_date")
                            if latest and date.fromisoformat(latest) < day:
                                flags.append("close_positive_source_and_latest_periodic_date_before_quote")
        for group in ("all", market):
            totals[group].update(flags)
    return {group: dict(counter) for group, counter in totals.items()}


def verify_filing_sample(code, row):
    time.sleep(1.2)
    filings, _ = fetch(f"/companies/{code}/filings?doc_type=120,130")
    doc_id = row["source_doc_id"]
    filing, = [item for item in filings if item["doc_id"] == doc_id]
    if (filing["sec_code"] != code + "0" or filing["period_end"] != row["period_end"]
            or filing.get("withdrawal_status") != "0" or filing.get("disclosure_status") == "2"):
        raise ValueError("Annual metrics do not match the sampled filing identity")
    filed_on = date.fromisoformat(filing["date"])
    if filed_on <= date.fromisoformat(row["period_end"]):
        raise ValueError("The sampled filing date does not follow the financial period")
    return {"code": code, "annual_source_id": doc_id, "actual_filing_date": filed_on.isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("universe")
    parser.add_argument("reports", nargs="+")
    parser.add_argument("--check-filing", action="append", default=[])
    args = parser.parse_args()
    stocks = ordinary_stocks(args.universe)
    rows, as_of, pages = annual_rows()
    for code in args.check_filing:
        if code not in stocks or code not in rows:
            parser.error("Requested filing sample is absent from one market universe")
    reports = {}
    for report in args.reports:
        day = trading_date(report)
        prices, duplicates = read_quotes(report, stocks)
        reports[day.isoformat()] = summarize(stocks, prices, duplicates, rows, day)
    if any(not result["all"].get("close_and_eps_bps") for result in reports.values()):
        raise ValueError("No JPX closes matched yen-denominated EPS and BPS")
    print(json.dumps({
        "financial_snapshot_as_of": as_of.isoformat(),
        "financial_snapshot_rows": len(rows),
        "financial_snapshot_pages": pages,
        "historical_valuation_verified": False,
        "reports": reports,
        "sampled_annual_filings": [verify_filing_sample(code, rows[code]) for code in args.check_filing],
    }, indent=2))


if __name__ == "__main__":
    main()

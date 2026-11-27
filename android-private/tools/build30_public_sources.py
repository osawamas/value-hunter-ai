"""Acquire dated official inputs and report source availability without inventing coverage."""
import datetime as dt
import hashlib
import json
import re
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from jpx_daily_probe import ordinary_stocks, read_quotes

JPX_INDEX = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/"
JPX_ROOT = "https://www.jpx.co.jp/automation/markets/statistics-equities/daily/files/"


def get(url, path, journal):
    item = {"url": url, "at": dt.datetime.now(dt.timezone.utc).isoformat()}
    journal.append(item)
    try:
        request = Request(url, headers={"User-Agent": "ValueHunter-public-market-audit/1.0"})
        with urlopen(request, timeout=25) as response:
            item["http"] = response.status
            content = response.read(33_000_001)
            if len(content) > 33_000_000:
                raise ValueError("source size limit")
            path.write_bytes(content)
            item["sha256"] = hashlib.sha256(content).hexdigest()
            return True
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        item["error"] = type(error).__name__
        if isinstance(error, HTTPError):
            item["http"] = error.code
        return False


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def jpx(out, journal):
    index, workbook = out / "jpx-index.html", out / "jpx-list.xlsx"
    if not get(JPX_INDEX, index, journal):
        return {"status": "listing_unavailable"}
    urls = set(re.findall(r"""href=["']([^"']+/data_j\.xlsx)["']""",
                          index.read_text(encoding="utf-8"), re.I))
    if len(urls) != 1:
        return {"status": "listing_link_unverified"}
    address = urljoin(JPX_INDEX, urls.pop())
    if not address.startswith("https://www.jpx.co.jp/") or not get(address, workbook, journal):
        return {"status": "listing_unavailable"}
    today = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
    for offset in range(5):
        day = today - dt.timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        pdf = out / "jpx-session.pdf"
        url = JPX_ROOT + f"{day:%Y%m}/stq_{day:%Y%m%d}.pdf"
        if get(url, pdf, journal):
            stocks = ordinary_stocks(workbook)
            quotes, ambiguous = read_quotes(pdf, stocks)
            return {"status": "price_inputs_only", "trade_date": day.isoformat(),
                    "listing_reference_count": len(stocks), "matched_close_count": sum(
                        (morning is not None or afternoon is not None) for morning, afternoon in quotes.values()),
                    "ambiguous_count": len(ambiguous),
                    "valuation": None}
        if journal[-1].get("http") not in (404, 410):
            break
        time.sleep(1)
    return {"status": "dated_closes_unavailable"}


def main():
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    journal = []
    try:
        for file in ("nasdaqlisted.txt", "otherlisted.txt"):
            get(DIRECTORY + file, out / file, journal)
        try:
            result = jpx(out, journal)
        except (ValueError, OSError, KeyError) as error:
            result = {"status": "input_validation_failed", "error": type(error).__name__}
        save(out / "jpx-public-coverage.json", result)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        save(out / "public-source-status.json", journal)


if __name__ == "__main__":
    main()

"""Look up official JPX rights reports and check which months can be used."""
import argparse
from datetime import date
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

import openpyxl
import pymupdf

from jpx_share_basis import read_monthly_rights

MONTHLY_INDEX = "https://www.jpx.co.jp/markets/statistics-equities/monthly/index.html"
DAILY_INDEX = "https://www.jpx.co.jp/listing/others/ex-rights/"
MONTHLY_FILE = re.compile(r"/17_kenri(\d{2})(0[1-9]|1[0-2])\.pdf$", re.IGNORECASE)
FILE_LIMIT = 4_000_000


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.urls.append(href)


def official_url(url):
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.netloc == "www.jpx.co.jp"


def download(url):
    if not official_url(url):
        raise ValueError("Unexpected JPX source URL")
    request = Request(url, headers={"User-Agent": "VALUE-HUNTER-AI source verification"})
    with urlopen(request, timeout=25) as response:
        if not official_url(response.geturl()):
            raise ValueError("JPX response redirected to an unexpected host")
        body = response.read(FILE_LIMIT + 1)
        if len(body) > FILE_LIMIT:
            raise ValueError("JPX response exceeded the size limit")
        return body


def page_links(index):
    page = Links()
    page.feed(download(index).decode("utf-8"))
    return list(dict.fromkeys(
        url for href in page.urls if official_url(url := urljoin(index, href))
    ))


def monthly_links(urls, year):
    result = {}
    for url in urls:
        match = MONTHLY_FILE.search(urlsplit(url).path)
        if match and int(match[1]) + 2000 == year:
            month = date(year, int(match[2]), 1)
            if month in result and result[month] != url:
                raise ValueError(f"Multiple official JPX links for {month:%Y-%m}")
            result[month] = url
    return result


def daily_sample(urls):
    files = [
        url for url in urls
        if "/listing/others/ex-rights/" in urlsplit(url).path
        and urlsplit(url).path.lower().endswith((".xlsx", ".pdf", ".xls", ".csv"))
    ]
    result = {"download_links_found": len(files)}
    if files:
        url = files[0]
        data = download(url)
        if data.startswith(b"%PDF-"):
            with pymupdf.open(stream=data, filetype="pdf") as report:
                result["first_file_type"] = "pdf"
                result["sample_pages"] = len(report)
                result["sample_header"] = " ".join(report[0].get_text().split())[:260]
        elif data.startswith(b"PK"):
            with BytesIO(data) as buffer:
                workbook = openpyxl.load_workbook(buffer, read_only=True, data_only=True)
                try:
                    result["first_file_type"] = "xlsx"
                    result["sample_sheets"] = workbook.sheetnames
                    rows = workbook.worksheets[0].iter_rows(min_row=1, max_row=8, values_only=True)
                    result["sample_header"] = " ".join(
                        str(cell) for row in rows for cell in row if cell is not None
                    )[:260]
                finally:
                    workbook.close()
        else:
            result["first_file_type"] = Path(urlsplit(url).path).suffix
        result["sample_filename"] = Path(urlsplit(url).path).name
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--cutoff-month", required=True, type=int, choices=range(1, 13))
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    selected = monthly_links(page_links(MONTHLY_INDEX), args.year)
    accepted = {}
    rejected = {}
    unpublished = []
    for number in range(1, args.cutoff_month + 1):
        month = date(args.year, number, 1)
        key = month.strftime("%Y-%m")
        if month not in selected:
            unpublished.append(key)
            continue
        body = download(selected[month])
        try:
            found, events = read_monthly_rights(body)
            if found != month:
                raise ValueError("Report header month differs from the index link")
        except (ValueError, pymupdf.FileDataError) as error:
            rejected[key] = str(error)
            continue
        accepted[key] = sum(map(len, events.values()))
        (args.output / f"rights-{key}.pdf").write_bytes(body)
    if not accepted:
        raise SystemExit("No JPX monthly rights reports passed validation")
    print(json.dumps({
        "monthly_reports": accepted,
        "monthly_reports_rejected": rejected,
        "no_monthly_link_found": unpublished,
        "daily_catalog_sample": daily_sample(page_links(DAILY_INDEX)),
        "daily_catalog_certifies_historical_coverage": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

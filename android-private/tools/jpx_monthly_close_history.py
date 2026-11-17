"""Collect local reference history from JPX monthly stock quotation PDFs."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
from tempfile import NamedTemporaryFile
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

BASE = "https://www.jpx.co.jp/markets/statistics-equities/price/"
MONTHLY_PDF = re.compile(r"/st_(\d{6})-2\.pdf$")
ARCHIVE = re.compile(r"/00-archives-\d{2}\.html$")
TICKER = re.compile(r"[0-9][0-9A-Z]{3}")
NUMBER = r"(?:[0-9][0-9,]*(?:\.[0-9]+)?|-)"
DAY = r"(?:[0-9]{1,2}|-)"
PRICE_ROW = re.compile(
    rf"^\s*(?P<month>\d{{4}}/\d{{2}})\s+(?P<code>[0-9][0-9A-Z]{{3}})"
    rf"\s+.+?\s+普通株式\s+{NUMBER}\s+(?P<first_day>{DAY})\s+{NUMBER}\s+{DAY}\s+{NUMBER}\s+{DAY}"
    rf"\s+(?P<close>{NUMBER})\s+(?P<day>{DAY})\s+{NUMBER}\s*$"
)


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.archives = {}
        self.option_url = None

    def handle_starttag(self, tag, attrs):
        href = dict(attrs).get("href") if tag == "a" else None
        if href:
            self.urls.append(urljoin(BASE, href))
        if tag == "option":
            self.option_url = urljoin(BASE, dict(attrs).get("value", ""))

    def handle_data(self, data):
        year = data.strip()
        if (self.option_url and self.option_url.startswith(BASE)
                and ARCHIVE.search(urlsplit(self.option_url).path)
                and re.fullmatch(r"[0-9]{4}年", year)):
            self.archives[year[:4]] = self.option_url

    def handle_endtag(self, tag):
        if tag == "option":
            self.option_url = None


def download(url, limit):
    if not url.startswith(BASE):
        raise ValueError("unexpected JPX source URL")
    request = Request(url, headers={"User-Agent": "VALUE-HUNTER-AI public data research"})
    with urlopen(request, timeout=25) as response:
        if not response.geturl().startswith(BASE):
            raise ValueError("unexpected JPX redirect")
        content = response.read(limit + 1)
    if len(content) > limit:
        raise ValueError("JPX response exceeds size limit")
    return content


def links(url):
    page = Links()
    page.feed(download(url, 2_000_000).decode("utf-8"))
    return page


def months_ending(end_month, count):
    for offset in range(count):
        year, month = divmod(end_month.year * 12 + end_month.month - 1 - offset, 12)
        yield date(year, month + 1, 1)


def read_month(layout, month, codes):
    prefix = month.strftime("%Y/%m")
    requested = set(codes)
    segments = {}
    ambiguous = set()
    if not re.search(rf"(?m)^\s*{prefix}\s+[0-9][0-9A-Z]{{3}}\s", layout):
        raise ValueError("JPX PDF has no rows for the requested month")

    for page in layout.split("\f"):
        if "Average Closing Price" not in page:
            continue
        for line in page.splitlines():
            match = PRICE_ROW.fullmatch(line)
            if not match or match["month"] != prefix or match["code"] not in requested:
                continue
            code = match["code"]
            if "-" in (match["close"], match["first_day"], match["day"]):
                continue
            close = Decimal(match["close"].replace(",", ""))
            if close <= 0:
                continue
            start = month.replace(day=int(match["first_day"]))
            end = month.replace(day=int(match["day"]))
            if start > end:
                ambiguous.add(code)
                continue
            segments.setdefault(code, set()).add((start, end, close))

    points = {}
    for code, rows in segments.items():
        ordered = sorted(rows)
        # A split month can have separate pre- and post-split rows.
        # Use the last segment's close only when their sessions do not overlap.
        if any(left[1] >= right[0] for left, right in zip(ordered, ordered[1:])):
            ambiguous.add(code)
        if code not in ambiguous:
            _, session, close = ordered[-1]
            points[code] = {"session": session.isoformat(), "close": str(close)}
    return points, sorted(ambiguous)


def report_sources(wanted):
    index = links(BASE)
    years = {month[:4] for month in wanted}
    archives = sorted(url for year, url in index.archives.items() if year in years)

    def read_archive(url):
        try:
            return links(url).urls
        except (OSError, ValueError):
            return []
    sources = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        for urls in [index.urls, *pool.map(read_archive, archives)]:
            for link in urls:
                match = MONTHLY_PDF.search(urlsplit(link).path)
                if link.startswith(BASE) and match and match[1] in wanted:
                    previous = sources.setdefault(match[1], link)
                    if previous != link:
                        raise ValueError(f"conflicting JPX documents for {match[1]}")
    return sources


def collect_month(month, source, codes, cache):
    if source is None:
        return {"status": "source_missing"}
    try:
        filename = cache / Path(urlsplit(source).path).name if cache is not None else None
        body = filename.read_bytes() if filename is not None and filename.is_file() else download(source, 8_000_000)
        if not body.startswith(b"%PDF-"):
            raise ValueError("JPX report is not a PDF")
        output = subprocess.run(
            ["pdftotext", "-layout", "-", "-"], input=body, capture_output=True, check=True, timeout=25
        )
        prices, ambiguous = read_month(output.stdout.decode("utf-8"), month, codes)
        if filename is not None and not filename.exists():
            with NamedTemporaryFile(dir=cache, delete=False) as temp:
                temporary = Path(temp.name)
                try:
                    temp.write(body)
                    temp.close()
                    temporary.replace(filename)
                finally:
                    temporary.unlink(missing_ok=True)
        return {"status": "read", "source": source, "prices": prices, "ambiguous_codes": ambiguous}
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return {"status": "error", "source": source, "reason": type(error).__name__}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("end_month", help="most recent completed month in YYYY-MM")
    parser.add_argument("codes", nargs="+", type=str.upper)
    parser.add_argument("--months", type=int, choices=range(1, 61), default=60)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--include-prices", action="store_true", help="include unadjusted prices in local output")
    args = parser.parse_args()
    if any(not TICKER.fullmatch(code) for code in args.codes):
        parser.error("expected four-character JPX ticker codes")
    if args.cache_dir is not None:
        args.cache_dir.mkdir(parents=True, exist_ok=True)
    end_month = date.fromisoformat(args.end_month + "-01")
    window = list(reversed(list(months_ending(end_month, args.months))))
    sources = report_sources({month.strftime("%Y%m") for month in window})

    def run(month):
        return collect_month(month, sources.get(month.strftime("%Y%m")), args.codes, args.cache_dir)

    with ThreadPoolExecutor(max_workers=4) as pool:
        monthly = {month.strftime("%Y-%m"): result for month, result in zip(window, pool.map(run, window))}
    count = {
        code: sum(code in result.get("prices", {}) for result in monthly.values())
        for code in args.codes
    }
    if not args.include_prices:
        for result in monthly.values():
            result.pop("prices", None)
    print(json.dumps({
        "months_requested": len(window),
        "months_read": sum(result["status"] == "read" for result in monthly.values()),
        "months_with_close_by_code": count,
        "price_basis": "jpx_monthly_unadjusted",
        "months": monthly,
    }, ensure_ascii=False, indent=2))
    return int(not any(count.values()))


if __name__ == "__main__":
    raise SystemExit(main())

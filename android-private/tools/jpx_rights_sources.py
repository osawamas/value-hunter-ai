"""Look up official JPX rights reports and check which months can be used."""
import argparse
from collections import Counter, defaultdict
from datetime import date
from html.parser import HTMLParser
from hashlib import sha256
import json
from pathlib import Path
import re
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

import pymupdf
import xlrd

from jpx_share_basis import read_monthly_rights
from jpx_daily_rights import rapid_exclusions, read_daily_rights

MONTHLY_INDEX = "https://www.jpx.co.jp/markets/statistics-equities/monthly/index.html"
PREVIOUS_YEAR_INDEX = urljoin(MONTHLY_INDEX, "00-archives-01.html")
DAILY_INDEX = "https://www.jpx.co.jp/listing/others/ex-rights/"
MONTHLY_FILE = re.compile(r"/(?:17|18)_kenri(\d{2})(0[1-9]|1[0-2])\.pdf$", re.IGNORECASE)
FILE_LIMIT = 4_000_000


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.urls = []
        self.archives = {}
        self.option = None

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.urls.append(href)

        if tag == "option":
            self.option = urljoin(MONTHLY_INDEX, dict(attrs).get("value", ""))

    def handle_data(self, data):
        year = re.fullmatch(r"(20[0-9]{2})年", data.strip())
        if (year and self.option and official_url(self.option)
                and re.fullmatch(r"/markets/statistics-equities/monthly/(?:index|00-archives-[0-9]{2})\.html",
                                 urlsplit(self.option).path)):
            self.archives[int(year[1])] = self.option

    def handle_endtag(self, tag):
        if tag == "option":
            self.option = None


def official_url(url):
    parts = urlsplit(url)
    return parts.scheme == "https" and parts.netloc == "www.jpx.co.jp"


def download(url, *, limit=FILE_LIMIT):
    if not official_url(url):
        raise ValueError("Unexpected JPX source URL")
    request = Request(url, headers={"User-Agent": "VALUE-HUNTER-AI source verification"})
    with urlopen(request, timeout=25) as response:
        if not official_url(response.geturl()):
            raise ValueError("JPX response redirected to an unexpected host")
        body = response.read(limit + 1)
        if len(body) > limit:
            raise ValueError("JPX response exceeded the size limit")
        return body


def page_links(index):
    page = Links()
    page.feed(download(index).decode("utf-8"))
    return official_links(index, page.urls)


def official_links(index, hrefs):
    return list(dict.fromkeys(
        url for href in hrefs if official_url(url := urljoin(index, href))
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


def monthly_archive_links(years):
    """Use the official year selector rather than assuming archive numbers stay fixed."""
    index = Links()
    index.feed(download(MONTHLY_INDEX).decode("utf-8"))
    reports = {}
    for year in sorted(years & index.archives.keys()):
        archive = index.archives[year]
        links = official_links(archive, index.urls) if archive == MONTHLY_INDEX else page_links(archive)
        reports.update(monthly_links(links, year))
    return reports


def workbook_notes(body):
    workbook = xlrd.open_workbook(file_contents=body)
    try:
        matching = [sheet for sheet in workbook.sheets() if "留意点" in sheet.name]
        if len(matching) != 1:
            raise ValueError("JPX daily rights workbook notes worksheet is missing or ambiguous")
        sheet = matching[0]
        return [
            " ".join(str(cell).strip() for cell in sheet.row_values(index) if str(cell).strip())
            for index in range(sheet.nrows)
            if any(str(cell).strip() for cell in sheet.row_values(index))
        ]
    finally:
        workbook.release_resources()


def daily_sources(urls, output):
    results = {}
    notes_by_release = {}
    dates_by_event = defaultdict(set)
    for url in urls:
        path = urlsplit(url).path
        if "/listing/others/ex-rights/" not in path or not re.search(r"/\d{8}\.xls$", path):
            continue
        filename = Path(path).name
        body = download(url)
        published_on, notices, flags = read_daily_rights(body, filename)
        counts = Counter(entry.kind for entries in notices.values() for entry in entries)
        for code, entries in notices.items():
            for entry in entries:
                dates_by_event[code, entry.kind, entry.record_on].add(entry.ex_on)
        release_key = published_on.isoformat()
        digest = sha256(body).hexdigest()
        if release_key in results:
            previous = results[release_key]
            if previous["sha256"] != digest:
                raise ValueError(f"Conflicting JPX daily workbook editions for {release_key}")
            continue
        results[release_key] = {
            "changes": dict(counts),
            "update_flags": sorted(flags),
            "official_url": url,
            "sha256": digest,
        }
        notes_by_release[published_on.isoformat()] = workbook_notes(body)
        (output / filename).write_bytes(body)
    comparison = {
        "distinct_event_keys": len(dates_by_event),
        "event_keys_with_conflicting_ex_dates": sum(len(days) > 1 for days in dates_by_event.values()),
    }
    return results, notes_by_release, comparison


def verified_rapid_exclusions(previous_day, latest_day, output):
    if not isinstance(previous_day, date) or not isinstance(latest_day, date):
        raise ValueError("JPX rapid comparison requires date objects")
    if previous_day >= latest_day:
        raise ValueError("JPX rapid comparison dates must be strictly increasing")
    days = (previous_day, latest_day)
    filenames = {f"{day:%Y%m%d}.xls" for day in days}
    links = [url for url in page_links(DAILY_INDEX) if Path(urlsplit(url).path).name in filenames]
    releases, _, _ = daily_sources(links, output)
    if releases.keys() != {day.isoformat() for day in days}:
        raise ValueError("Both official JPX rights editions are required")
    bodies = [(output / f"{day:%Y%m%d}.xls").read_bytes() for day in days]
    if any(sha256(body).hexdigest() != releases[day.isoformat()]["sha256"] for day, body in zip(days, bodies)):
        raise ValueError("JPX workbooks changed after the original download")
    return {
        "previousDay": previous_day.isoformat(),
        "latestDay": latest_day.isoformat(),
        "excludedCodes": sorted(rapid_exclusions(previous_day, latest_day, *bodies)),
        "sources": {day: {"url": value["official_url"], "sha256": value["sha256"]}
                    for day, value in releases.items()},
    }


def monthly_sources(first_month, last_month, output):
    year = last_month.year
    selected = monthly_links(page_links(MONTHLY_INDEX), year)
    if first_month.year < year:
        selected.update(monthly_links(page_links(PREVIOUS_YEAR_INDEX), first_month.year))
    accepted = {}
    provenance = {}
    rejected = {}
    unpublished = []
    months = [date(year, number, 1) for year in range(first_month.year, last_month.year + 1)
              for number in range(1, 13)]
    for month in months:
        if not first_month <= month <= last_month:
            continue
        key = month.strftime("%Y-%m")
        if month not in selected:
            unpublished.append(key)
            continue
        body = download(selected[month])
        digest = sha256(body).hexdigest()
        try:
            found, events = read_monthly_rights(body)
            if found != month:
                raise ValueError("Report header month differs from the index link")
        except (ValueError, pymupdf.FileDataError) as error:
            rejected[key] = {"reason": str(error), "official_url": selected[month], "sha256": digest}
            continue
        accepted[key] = sum(map(len, events.values()))
        provenance[key] = {"official_url": selected[month], "sha256": digest}
        (output / f"rights-{key}.pdf").write_bytes(body)
    return accepted, provenance, rejected, unpublished


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--cutoff-month", required=True, type=int, choices=range(1, 13))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--daily-only", action="store_true")
    parser.add_argument("--start-month", help="First month to check, as YYYY-MM")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    daily, notes_by_release, comparison = daily_sources(page_links(DAILY_INDEX), args.output)
    if args.daily_only:
        latest_notes = notes_by_release[max(notes_by_release)] if notes_by_release else []
        print(json.dumps({
            "daily_workbooks": daily,
            "daily_edition_comparison": comparison,
            "latest_workbook_notes": latest_notes,
        }, ensure_ascii=False, indent=2))
        return
    first_month = date(args.year, 1, 1)
    if args.start_month:
        try:
            first_month = date.fromisoformat(args.start_month + "-01")
        except ValueError:
            parser.error("--start-month must use YYYY-MM")
    last_month = date(args.year, args.cutoff_month, 1)
    if first_month > last_month or first_month.year not in (args.year - 1, args.year):
        parser.error("--start-month must be in the current catalog year or its previous year")
    accepted, provenance, rejected, unpublished = monthly_sources(first_month, last_month, args.output)
    if not accepted:
        raise SystemExit("No JPX monthly rights reports passed validation")
    print(json.dumps({
        "monthly_reports": accepted,
        "monthly_report_provenance": provenance,
        "monthly_reports_rejected": rejected,
        "no_monthly_link_found": unpublished,
        "daily_workbooks": daily,
        "daily_edition_comparison": comparison,
        "daily_workbook_notes_variants": len({tuple(notes) for notes in notes_by_release.values()}),
        "daily_catalog_certifies_historical_coverage": False,
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Find issuer filings to review after a dated SEC cover-page share count."""

from calendar import monthrange
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
import re

HEADER = b"CIK|Company Name|Form Type|Date Filed|Filename"
RECEIVED = re.compile(rb"Last Data Received:\s+(\w+)\s+(\d{1,2}),\s+(\d{4})")
ACCESSION = re.compile(rb"edgar/data/[0-9]+/([0-9]{10}-[0-9]{2}-[0-9]{6})\.txt")
MONTHS = (b"January", b"February", b"March", b"April", b"May", b"June",
          b"July", b"August", b"September", b"October", b"November", b"December")
REGISTRATION_FORMS = {b"S-1", b"S-3", b"S-4", b"F-1", b"F-3", b"F-4"}
FORMS = REGISTRATION_FORMS | {b"8-K", b"6-K", b"10-K", b"10-Q", b"20-F", b"40-F", b"DEF 14A", b"PRE 14A"}


def quarter(day):
    return day.year, (day.month - 1) // 3 + 1


def scan_index(path, expected, visit):
    if not 0 < Path(path).stat().st_size <= 64_000_000:
        raise ValueError("Unexpected EDGAR master index size")
    with open(path, "rb") as source:
        received = None
        for _ in range(20):
            line = source.readline().strip()
            match = RECEIVED.fullmatch(line)
            if match:
                month, day, year = match.groups()
                received = date(int(year), MONTHS.index(month) + 1, int(day))
            if line == HEADER:
                break
        else:
            raise ValueError("EDGAR master index header missing")
        separator = source.readline().strip()
        if received is None or quarter(received) != expected or not separator or set(separator) != {ord("-")}:
            raise ValueError("EDGAR master index quarter or separator mismatch")
        observed = None
        for raw in source:
            row = raw.rstrip(b"\r\n")
            if not row:
                continue
            cik, _, form, filed, filename = row.split(b"|", 4)
            filed_day = date.fromisoformat(filed.decode("ascii"))
            if quarter(filed_day) != expected or filed_day > received:
                raise ValueError("EDGAR master index contains a date outside its declared coverage")
            observed = filed_day if observed is None else max(observed, filed_day)
            visit(int(cik), form, filed_day, filename)
    if observed != received:
        raise ValueError("EDGAR master index ends before its declared date")
    return received


def read_index(path, expected, cutoff, share_dates, accessions, events):
    def visit(issuer, form, filed_day, filename):
        if issuer not in share_dates or not share_dates[issuer] <= filed_day <= cutoff:
            return
        base_form = form.removesuffix(b"/A")
        if base_form not in FORMS and not base_form.startswith(b"424B"):
            return
        match = ACCESSION.fullmatch(filename)
        if match is None:
            raise ValueError("Unexpected SEC submission filename")
        accession = match[1]
        if accession != accessions[issuer]:
            events[issuer].add((filed_day, accession, base_form))

    return scan_index(path, expected, visit)


def check(indexes, cutoff, share_dates, accessions, securities, report_groups):
    events = defaultdict(set)
    through = {}
    for key, path in indexes.items():
        through[key] = read_index(path, key, cutoff, share_dates, accessions, events)

    def covers(start):
        year, part = quarter(start)
        while (year, part) <= quarter(cutoff):
            month = part * 3
            end = min(cutoff, date(year, month, monthrange(year, month)[1]))
            if through.get((year, part), date.min) < end:
                return False
            year, part = (year + 1, 1) if part == 4 else (year, part + 1)
        return True

    status = {}
    for cik, start in share_dates.items():
        if events[cik]:
            status[cik] = "filing_needs_review"
        elif covers(start):
            status[cik] = "no_selected_form_detected"
        else:
            status[cik] = "index_interval_incomplete"

    def counts(tickers):
        buckets = Counter(status[cik] for cik in tickers.values() if cik in status)
        result = {key: buckets[key] for key in (
            "filing_needs_review", "no_selected_form_detected", "index_interval_incomplete"
        )}
        result["with_registration_or_prospectus"] = sum(
            any(form in REGISTRATION_FORMS or form.startswith(b"424B") for _, _, form in events[cik])
            for cik in tickers.values() if cik in status
        )
        return result

    result = counts(securities)
    result["index_through"] = {f"{year}q{part}": day.isoformat() for (year, part), day in sorted(through.items())}
    if report_groups:
        result["by_market_or_index"] = {name: counts(tickers) for name, tickers in report_groups.items()}
    return result

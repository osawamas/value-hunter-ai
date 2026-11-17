"""Measure disclosed cover-page share counts using SEC monthly notes archives."""

from calendar import monthrange
from collections import Counter, defaultdict
from contextlib import ExitStack
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from zipfile import ZipFile

from us_sec_filing_followup import check as check_edgar
from us_sec_statement_coverage import collect_filings, latest_unique

TAG = b"EntityCommonStockSharesOutstanding"
NUM_HEADER = (
    b"adsh", b"tag", b"version", b"ddate", b"qtrs", b"uom", b"dimh", b"iprx", b"value",
    b"footnote", b"footlen", b"dimn", b"coreg", b"durp", b"datp", b"dcml",
)


def share_date(rounded, proximity):
    month_end = date.fromisoformat(rounded.decode("ascii"))
    if month_end.day != monthrange(month_end.year, month_end.month)[1]:
        raise ValueError("SEC notes date is not a rounded month end")
    offset = Decimal(proximity.decode("ascii"))
    # The current monthly archive stores the offset in whole days, with positive
    # values before the rounded date. Earlier archive formats may differ.
    if not offset.is_finite() or offset != offset.to_integral_value() or abs(offset) > 16:
        raise ValueError("Unsupported day offset in SEC notes archive")
    return month_end - timedelta(days=int(offset))


def cover_facts(archives, filings, cutoff):
    relevant = {filing.accession: filing for filing in filings.values()}
    reported = defaultdict(set)
    blocked = defaultdict(set)
    for archive in archives:
        with archive.open("num.tsv") as table:
            if tuple(table.readline().rstrip(b"\r\n").split(b"\t")) != NUM_HEADER:
                raise ValueError("Unexpected SEC notes numeric header")
            for line in table:
                accession, tag, _ = line.split(b"\t", 2)
                if accession not in relevant or tag != TAG:
                    continue
                _, _, version, rounded, duration, unit, dimension, _, value, _, _, dims, coreg, _, offset, precision = (
                    line.rstrip(b"\r\n").split(b"\t")
                )
                if not version.startswith(b"dei/") or unit != b"shares" or duration != b"0" or coreg:
                    continue
                if dimension != b"0x00000000" or dims != b"0":
                    blocked[accession].add("class_detail_requires_review")
                    continue
                try:
                    effective = share_date(rounded, offset)
                    amount = Decimal(value.decode("ascii"))
                    if (effective > relevant[accession].filed or effective > cutoff or precision not in (b"0", b"32767")
                            or not amount.is_finite() or amount <= 0 or amount != amount.to_integral_value()):
                        raise ValueError("Unsupported share count or effective date")
                except (InvalidOperation, ValueError, OverflowError):
                    blocked[accession].add("date_or_precision_unconfirmed")
                    continue
                reported[accession].add((effective, int(amount)))
    return reported, blocked


def measure(paths, cutoff, securities, report_groups, multiple_classes, indexes=None):
    issuers = set(securities.values())
    for group in report_groups.values():
        issuers.update(group.values())
    eligible = defaultdict(dict)
    with ExitStack() as stack:
        archives = [stack.enter_context(ZipFile(path)) for path in paths]
        for archive in archives:
            for name, maximum in (("sub.tsv", 30_000_000), ("num.tsv", 2_500_000_000)):
                if not 0 < archive.getinfo(name).file_size <= maximum:
                    raise ValueError("Unexpected SEC notes archive member size")
            collect_filings(archive, cutoff, issuers, eligible, member="sub.tsv")
        latest = {}
        for cik, choices in eligible.items():
            filing = latest_unique(choices.values())
            if filing is not None:
                latest[cik] = filing
        reported, blocked = cover_facts(archives, latest, cutoff)

    status = {}
    effective_dates = {}
    for cik, filing in latest.items():
        accession = filing.accession
        values = reported[accession]
        if cik in multiple_classes or "class_detail_requires_review" in blocked[accession]:
            status[cik] = "class_detail_requires_review"
        elif "date_or_precision_unconfirmed" in blocked[accession] or len(values) > 1:
            status[cik] = "date_precision_or_value_unconfirmed"
        elif len(values) == 1:
            effective_dates[cik], _ = next(iter(values))
        else:
            status[cik] = "no_usable_cover_fact"

    def counts(tickers):
        reasons = Counter(status.get(cik, "no_eligible_filing") for cik in tickers.values()
                          if cik not in effective_dates)
        return {
            "securities_checked": len(tickers),
            "with_dated_cover_share_count": sum(cik in effective_dates for cik in tickers.values()),
            "cover_date_within_30_days": sum(
                0 <= (cutoff - effective_dates[cik]).days <= 30
                for cik in tickers.values() if cik in effective_dates
            ),
            "unconfirmed": dict(sorted(reasons.items())),
        }

    result = counts(securities)
    if report_groups:
        result["by_market_or_index"] = {name: counts(group) for name, group in report_groups.items()}
    if indexes:
        accessions = {cik: latest[cik].accession for cik in effective_dates}
        result["edgar_filing_followup"] = check_edgar(
            indexes, cutoff, effective_dates, accessions, securities, report_groups
        )
    return result, effective_dates

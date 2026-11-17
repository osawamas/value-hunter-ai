"""Measure financial fact availability from one SEC Financial Statement Data Sets ZIP."""

from collections import defaultdict
from contextlib import ExitStack
from datetime import date
from decimal import Decimal, InvalidOperation
from zipfile import ZipFile

SUB_HEADER = {b"adsh", b"cik", b"form", b"period", b"filed"}
NUM_HEADER = [b"adsh", b"tag", b"version", b"ddate", b"qtrs", b"uom",
              b"segments", b"coreg", b"value", b"footnote"]
EQUITY = b"StockholdersEquity"
INCOME = b"NetIncomeLoss"
ORIGINAL_FORMS = {b"10-K", b"10-Q"}


def collect_filings(archive, cutoff, issuers, eligible):
    with archive.open("sub.txt") as table:
        headers = table.readline().rstrip(b"\r\n").split(b"\t")
        if not SUB_HEADER.issubset(headers) or len(headers) != len(set(headers)):
            raise ValueError("Unexpected SEC sub.txt header")
        id_col, cik_col, form_col, period_col, filed_col = [
            headers.index(key) for key in (b"adsh", b"cik", b"form", b"period", b"filed")
        ]
        allowed = {str(cik).encode(): cik for cik in issuers}
        for row in table:
            fields = row.rstrip(b"\r\n").split(b"\t")
            if len(fields) != len(headers):
                raise ValueError("Malformed SEC submission row")
            form, cik = fields[form_col], allowed.get(fields[cik_col])
            if cik is None or form not in ORIGINAL_FORMS:
                continue
            period, filed = fields[period_col], fields[filed_col]
            period_date = date.fromisoformat(period.decode("ascii"))
            filed_date = date.fromisoformat(filed.decode("ascii"))
            # The filing date alone cannot establish availability at that session's close.
            if period_date > filed_date or filed_date >= cutoff:
                continue
            accession = fields[id_col]
            terms = (period, filed, form)
            if eligible[cik].setdefault(accession, terms) != terms:
                raise ValueError("Conflicting SEC submission metadata")


def latest_filings(archives, cutoff, issuers):
    eligible = defaultdict(dict)
    for archive in archives:
        collect_filings(archive, cutoff, issuers, eligible)
    selected = {}
    for cik, rows in eligible.items():
        newest = max((period, filed) for period, filed, _ in rows.values())
        contenders = [(accession, data) for accession, data in rows.items() if data[:2] == newest]
        if len(contenders) == 1:
            accession, (period, _, form) = contenders[0]
            selected[accession] = (cik, period, form)
    return selected


def collect_facts(archive, filings, facts):
    with archive.open("num.txt") as table:
        if table.readline().rstrip(b"\r\n").split(b"\t") != NUM_HEADER:
            raise ValueError("Unexpected SEC num.txt header")
        for row in table:
            prefix = row.split(b"\t", 2)
            if len(prefix) != 3:
                raise ValueError("Malformed SEC numeric row")
            accession, tag, tail = prefix
            if tag not in {EQUITY, INCOME} or accession not in filings:
                continue
            cik, period, form = filings[accession]
            version, end, quarters, unit, segment, coreg, value, _ = tail.split(b"\t", 7)
            expected_quarters = b"0" if tag == EQUITY else (b"4" if form == b"10-K" else b"1")
            if (not version.startswith(b"us-gaap/") or end != period or quarters != expected_quarters
                    or unit != b"USD" or segment or coreg):
                continue
            try:
                amount = Decimal(value.decode("ascii"))
            except InvalidOperation:
                continue
            if amount.is_finite():
                facts[cik][tag].add(amount)


def measure(paths, cutoff, securities):
    """Count securities with eligible filings and paired facts, without emitting values."""
    with ExitStack() as stack:
        archives = [stack.enter_context(ZipFile(path)) for path in paths]
        for archive in archives:
            for name, limit in (("sub.txt", 30_000_000), ("num.txt", 2_500_000_000)):
                if not 0 < archive.getinfo(name).file_size <= limit:
                    raise ValueError("Unexpected SEC statement archive member size")
        filings = latest_filings(archives, cutoff, set(securities.values()))
        facts = defaultdict(lambda: defaultdict(set))
        if filings:
            for archive in archives:
                collect_facts(archive, filings, facts)
    covered = {cik for cik, tags in facts.items() if len(tags[EQUITY]) == 1 and len(tags[INCOME]) == 1}
    with_filing = {cik for cik, _, _ in filings.values()}
    return {
        "securities_checked": len(securities),
        "unique_issuers_checked": len(set(securities.values())),
        "securities_with_original_10k_or_10q": sum(cik in with_filing for cik in securities.values()),
        "securities_with_equity_and_period_profit": sum(cik in covered for cik in securities.values()),
        "unique_issuers_with_equity_and_period_profit": len(covered),
    }

"""Measure financial fact availability from SEC Financial Statement Data Sets ZIPs."""

from calendar import monthrange
from collections import defaultdict
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from zipfile import ZipFile

SUB_FIELDS = (b"adsh", b"cik", b"form", b"period", b"filed", b"fy", b"fp")
NUM_HEADER = [b"adsh", b"tag", b"version", b"ddate", b"qtrs", b"uom",
              b"segments", b"coreg", b"value", b"footnote"]
EQUITY = b"StockholdersEquity"
INCOME = b"NetIncomeLoss"
ANNUAL = b"10-K"
QUARTERLY = b"10-Q"
FISCAL_QUARTERS = {b"Q1": 1, b"Q2": 2, b"Q3": 3}


@dataclass(frozen=True)
class Filing:
    accession: bytes
    form: bytes
    period: date
    filed: date
    fiscal_year: int | None
    fiscal_focus: bytes


def collect_filings(archive, cutoff, issuers, eligible, member="sub.txt"):
    with archive.open(member) as table:
        headers = table.readline().rstrip(b"\r\n").split(b"\t")
        if not set(SUB_FIELDS).issubset(headers) or len(headers) != len(set(headers)):
            raise ValueError(f"Unexpected SEC {member} header")
        columns = [headers.index(key) for key in SUB_FIELDS]
        allowed = {str(cik).encode(): cik for cik in issuers}
        for row in table:
            fields = row.rstrip(b"\r\n").split(b"\t")
            if len(fields) != len(headers):
                raise ValueError("Malformed SEC submission row")
            accession, raw_cik, form, period, filed, fiscal_year, focus = (fields[i] for i in columns)
            cik = allowed.get(raw_cik)
            if cik is None or form not in (ANNUAL, QUARTERLY):
                continue
            period_date = date.fromisoformat(period.decode("ascii"))
            filed_date = date.fromisoformat(filed.decode("ascii"))
            # The filing date alone cannot establish availability at that session's close.
            if period_date > filed_date or filed_date >= cutoff:
                continue
            year = int(fiscal_year) if fiscal_year.isdigit() else None
            filing = Filing(accession, form, period_date, filed_date, year, focus)
            if eligible[cik].setdefault(accession, filing) != filing:
                raise ValueError("Conflicting SEC submission metadata")


def latest_unique(rows):
    key = max(((row.period, row.filed) for row in rows), default=None)
    winners = [row for row in rows if (row.period, row.filed) == key]
    return winners[0] if len(winners) == 1 else None


def months_between(start, end):
    return (end.year - start.year) * 12 + end.month - start.month


def same_month_prior_year(day):
    year = day.year - 1
    return date(year, day.month, monthrange(year, day.month)[1])


def filings_for_measurement(archives, cutoff, issuers):
    eligible = defaultdict(dict)
    for archive in archives:
        collect_filings(archive, cutoff, issuers, eligible)
    current = {}
    previous_annual = {}
    for cik, rows in eligible.items():
        latest = latest_unique(rows.values())
        if latest is None:
            continue
        current[cik] = latest
        qtrs = FISCAL_QUARTERS.get(latest.fiscal_focus)
        if latest.form != QUARTERLY or qtrs is None or latest.fiscal_year is None:
            continue
        earlier = [row for row in rows.values() if row.form == ANNUAL and row.fiscal_focus == b"FY"
                   and row.fiscal_year == latest.fiscal_year - 1 and row.filed <= latest.filed
                   and months_between(row.period, latest.period) == 3 * qtrs]
        annual = latest_unique(earlier)
        if annual is not None:
            previous_annual[cik] = annual
    return current, previous_annual


def fact_key(filing, tag, end, quarters):
    return filing.accession, tag, end.strftime("%Y%m%d").encode(), str(quarters).encode()


def requested_facts(current, previous_annual):
    wanted = set()
    for cik, filing in current.items():
        wanted.add(fact_key(filing, EQUITY, filing.period, 0))
        wanted.add(fact_key(filing, INCOME, filing.period, 4 if filing.form == ANNUAL else 1))
        if cik in previous_annual:
            annual = previous_annual[cik]
            qtrs = FISCAL_QUARTERS[filing.fiscal_focus]
            wanted.add(fact_key(annual, INCOME, annual.period, 4))
            wanted.add(fact_key(filing, INCOME, filing.period, qtrs))
            wanted.add(fact_key(filing, INCOME, same_month_prior_year(filing.period), qtrs))
    return wanted


def collect_facts(archive, wanted, accessions, facts):
    with archive.open("num.txt") as table:
        if table.readline().rstrip(b"\r\n").split(b"\t") != NUM_HEADER:
            raise ValueError("Unexpected SEC num.txt header")
        for row in table:
            prefix = row.split(b"\t", 2)
            if len(prefix) != 3:
                raise ValueError("Malformed SEC numeric row")
            accession, tag, tail = prefix
            if tag not in (EQUITY, INCOME) or accession not in accessions:
                continue
            version, end, quarters, unit, segment, coreg, value, _ = tail.split(b"\t", 7)
            key = (accession, tag, end, quarters)
            if (key not in wanted or not version.startswith(b"us-gaap/")
                    or unit != b"USD" or segment or coreg):
                continue
            try:
                amount = Decimal(value.decode("ascii"))
            except InvalidOperation:
                continue
            if amount.is_finite():
                facts[key].add(amount)


def fact_value(facts, key):
    amounts = facts.get(key, ())
    return next(iter(amounts)) if len(amounts) == 1 else None


def trailing_profit(filing, annual, facts):
    if filing.form == ANNUAL:
        return fact_value(facts, fact_key(filing, INCOME, filing.period, 4))
    if annual is None:
        return None
    qtrs = FISCAL_QUARTERS[filing.fiscal_focus]
    full_year = fact_value(facts, fact_key(annual, INCOME, annual.period, 4))
    this_ytd = fact_value(facts, fact_key(filing, INCOME, filing.period, qtrs))
    prior_ytd = fact_value(facts, fact_key(filing, INCOME, same_month_prior_year(filing.period), qtrs))
    if any(value is None for value in (full_year, this_ytd, prior_ytd)):
        return None
    return full_year + this_ytd - prior_ytd


def measure(paths, cutoff, securities, report_groups=None, share_dates=None):
    """Count securities with eligible filings and financial inputs, without emitting values."""
    report_groups = report_groups or {}
    issuers = set(securities.values())
    for group in report_groups.values():
        issuers.update(group.values())
    with ExitStack() as stack:
        archives = [stack.enter_context(ZipFile(path)) for path in paths]
        for archive in archives:
            for name, limit in (("sub.txt", 30_000_000), ("num.txt", 2_500_000_000)):
                if not 0 < archive.getinfo(name).file_size <= limit:
                    raise ValueError("Unexpected SEC statement archive member size")
        current, previous_annual = filings_for_measurement(archives, cutoff, issuers)
        wanted = requested_facts(current, previous_annual)
        facts = defaultdict(set)
        if wanted:
            accessions = {key[0] for key in wanted}
            for archive in archives:
                collect_facts(archive, wanted, accessions, facts)
    with_period = set()
    with_trailing = set()
    for cik, filing in current.items():
        if fact_value(facts, fact_key(filing, EQUITY, filing.period, 0)) is None:
            continue
        quarters = 4 if filing.form == ANNUAL else 1
        if fact_value(facts, fact_key(filing, INCOME, filing.period, quarters)) is not None:
            with_period.add(cik)
        if trailing_profit(filing, previous_annual.get(cik), facts) is not None:
            with_trailing.add(cik)
    def counts(tickers):
        ids = set(tickers.values())
        result = {
            "securities_checked": len(tickers),
            "unique_issuers_checked": len(ids),
            "securities_with_original_10k_or_10q": sum(cik in current for cik in tickers.values()),
            "securities_with_equity_and_period_profit": sum(cik in with_period for cik in tickers.values()),
            "unique_issuers_with_equity_and_period_profit": len(ids & with_period),
            "securities_with_equity_and_trailing_profit": sum(cik in with_trailing for cik in tickers.values()),
            "unique_issuers_with_equity_and_trailing_profit": len(ids & with_trailing),
        }
        if share_dates is not None:
            result["with_equity_trailing_profit_and_dated_cover_shares"] = sum(
                cik in with_trailing and cik in share_dates for cik in tickers.values()
            )
        return result

    result = counts(securities)
    if report_groups:
        result["by_market_or_index"] = {name: counts(tickers) for name, tickers in report_groups.items()}
    return result

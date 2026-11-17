"""Read monthly JPX split/consolidation events and flag potentially mixed share bases."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
import re
import unicodedata

import pymupdf

from jpx_daily_probe import CODE

MONTH_HEADER = re.compile(r"(\d{4})\s*年\s*(\d{1,2})\s*月")
ACTION = re.compile(r"株\s*式\s*(?:分\s*割|併\s*合|無\s*償\s*割\s*当\s*て)")
RATIO = re.compile(r"(\d+(?:\.\d+)?):(\d+(?:\.\d+)?)株式(分割|併合|無償割当て)")
TABLE_DATE = re.compile(r"\b\d{4}\s*\.\s*\d{1,2}\s*\.\s*\d{1,2}(?!\d)")


@dataclass(frozen=True)
class ShareEvent:
    ex_on: date
    record_on: date
    ratio_left: Decimal
    ratio_right: Decimal


def table_date(value):
    if not TABLE_DATE.fullmatch(value):
        raise ValueError("Missing or ambiguous date on a JPX corporate-action row")
    return date(*map(int, value.split(".")))


def read_monthly_rights(path):
    events = defaultdict(set)
    source = pymupdf.open(stream=path, filetype="pdf") if isinstance(path, bytes) else pymupdf.open(path)
    with source as document:
        match = MONTH_HEADER.search(unicodedata.normalize("NFKC", document[0].get_text()))
        if not match:
            raise ValueError("JPX corporate-action report month could not be read")
        month = date(int(match[1]), int(match[2]), 1)
        for page in document:
            page_text = unicodedata.normalize("NFKC", page.get_text())
            expected_actions = len(ACTION.findall(page_text))
            words = [
                ((x0 + x1) / (2 * page.rect.width), (y0 + y1) / 2,
                 unicodedata.normalize("NFKC", value))
                for x0, y0, x1, y1, value, *_ in page.get_text("words")
            ]
            parsed_actions = 0
            for x, y, code in words:
                if x >= .4 or not CODE.fullmatch(code):
                    continue
                line = " ".join(word[2] for word in sorted(
                    word for word in words if word[0] > x and abs(word[1] - y) < 2.5
                ))
                if not ACTION.search(line):
                    continue
                dates = list(TABLE_DATE.finditer(line))
                if len(dates) != 2:
                    raise ValueError(f"Could not read both JPX corporate-action dates for {code}")
                description = "".join(line[dates[-1].end():].split())
                ratio = RATIO.fullmatch(description)
                if not ratio:
                    raise ValueError(f"Could not read the JPX corporate-action ratio for {code}")
                ex_on, record_on = (table_date(item.group()) for item in dates)
                left, right = Decimal(ratio[1]), Decimal(ratio[2])
                valid_ratio = left > 0 and right > 0 and (
                    ratio[3] == "無償割当て" or
                    (left < right if ratio[3] == "分割" else right < left)
                )
                if ex_on.replace(day=1) != month or ex_on > record_on or not valid_ratio:
                    raise ValueError(f"Inconsistent JPX corporate action for {code}")
                events[code].add(ShareEvent(ex_on, record_on, left, right))
                parsed_actions += 1
            if expected_actions != parsed_actions:
                raise ValueError(
                    f"JPX page {page.number + 1} declares {expected_actions} split or "
                    f"consolidation rows, but extracted {parsed_actions}"
                )
    return month, events


def load_rights_reports(paths):
    coverage = set()
    events = defaultdict(set)
    for path in paths:
        month, new_events = read_monthly_rights(path)
        if month in coverage:
            raise ValueError("Use one JPX corporate-action report per month")
        coverage.add(month)
        for code, actions in new_events.items():
            events[code].update(actions)
    return coverage, events


def share_basis_status(code, period_end, quote_day, rights):
    coverage, events = rights
    for action in events.get(code, ()):
        if action.ex_on <= quote_day and action.record_on >= period_end:
            return "hold_share_basis_change"
    month = period_end.replace(day=1)
    while month <= quote_day:
        if month not in coverage:
            return "hold_rights_report_gap"
        month = date(month.year + month.month // 12, month.month % 12 + 1, 1)
    return "no_share_change_in_supplied_reports"

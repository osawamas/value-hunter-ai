"""Read share-change notices from an official JPX daily rights workbook."""
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re
import unicodedata

import xlrd

from jpx_daily_probe import CODE

NOTICE_DATE = re.compile(r"(\d{4}/\d{1,2}/\d{1,2})公表分")
DAILY_PERIOD = re.compile(r"対象期間:(\d{4}/\d{1,2}/\d{1,2})~(\d{4}/\d{1,2}/\d{1,2})")
HEADERS = ("基準日", "権利落日(普通取引)", "銘柄コード", "備考", "更新フラグ")


@dataclass(frozen=True)
class DailyShareNotice:
    published_on: date
    ex_on: date
    record_on: date
    kind: str
    update_flag: str


def normalized(value):
    return "".join(unicodedata.normalize("NFKC", str(value)).split())


def notice_kind(remarks):
    if "併合" in remarks:
        return "consolidation"
    if "無償割当" in remarks:
        return "bonus_allotment"
    if "分割" in remarks or remarks in {"新株落", "新株落ち"}:
        return "split_or_ex_new_shares"
    if remarks == "その他":
        return "unclassified_rights"
    return None


def workbook_date(cell, datemode):
    if cell.ctype in (xlrd.XL_CELL_DATE, xlrd.XL_CELL_NUMBER):
        return xlrd.xldate_as_datetime(cell.value, datemode).date()
    return date(*map(int, re.split(r"[/.-]", normalized(cell.value))))


def read_daily_rights(body, filename, *, rapid_day=None):
    workbook = xlrd.open_workbook(file_contents=body)
    try:
        sheet = workbook.sheet_by_index(0)
        if not sheet.nrows:
            raise ValueError("JPX daily rights worksheet has no rows")
        title = "".join(map(normalized, sheet.row_values(0)))
        match = NOTICE_DATE.search(title)
        if not match:
            raise ValueError("JPX daily rights publication date is missing")
        published_on = date(*map(int, match[1].split("/")))
        if filename != f"{published_on:%Y%m%d}.xls":
            raise ValueError("JPX daily rights filename and publication date differ")
        for header_index in range(min(sheet.nrows, 10)):
            labels = list(map(normalized, sheet.row_values(header_index)))
            if all(labels.count(label) == 1 for label in HEADERS):
                record, ex, ticker, remarks, update = map(labels.index, HEADERS)
                break
        else:
            raise ValueError("JPX daily rights columns could not be identified")

        if rapid_day is not None:
            titles = [normalized(cell) for row in range(header_index) for cell in sheet.row_values(row)]
            periods = [match for text in titles if (match := DAILY_PERIOD.fullmatch(text))]
            if len(periods) != 1:
                raise ValueError("JPX rights coverage period is missing or ambiguous")
            first, last = (date(*map(int, value.split("/"))) for value in periods[0].groups())
            if first != published_on or not first <= rapid_day <= last:
                raise ValueError("JPX rights workbook does not cover the comparison end date")

        notices = defaultdict(set)
        flags = set()
        for index in range(header_index + 1, sheet.nrows):
            row = sheet.row(index)
            remark = normalized(row[remarks].value)
            flag = normalized(row[update].value)
            if flag:
                flags.add(flag)
            kind = notice_kind(remark)
            if rapid_day is not None and any(normalized(row[col].value) for col in (record, ex, ticker)):
                # Unrecognized and mixed corporate-event descriptions also block alerts.
                kind = kind or ("dividend" if "配当" in remark else "other_event")
            if kind is None:
                continue
            raw_code = row[ticker].value
            code = str(int(raw_code)) if isinstance(raw_code, float) and raw_code.is_integer() else normalized(raw_code)
            if len(code) == 5 and code.endswith("0"):
                code = code[:4]
            if not CODE.fullmatch(code):
                raise ValueError(f"Unexpected security code on JPX daily rights row {index + 1}")
            record_on = workbook_date(row[record], workbook.datemode)
            ex_on = workbook_date(row[ex], workbook.datemode)
            if ex_on > record_on:
                raise ValueError(f"Inconsistent dates on JPX daily rights row {index + 1}")
            if rapid_day is not None and ex_on != rapid_day:
                continue
            notices[code].add(DailyShareNotice(published_on, ex_on, record_on, kind, flag))
        return published_on, notices, flags
    finally:
        workbook.release_resources()


def rapid_exclusions(previous_day, latest_day, previous_body, latest_body):
    """Return codes with an event on the comparison day, using both official editions."""
    if not 1 <= (latest_day - previous_day).days <= 7:
        raise ValueError("Invalid JPX comparison interval")
    blocked = set()
    for day, body in ((previous_day, previous_body), (latest_day, latest_body)):
        _, notices, _ = read_daily_rights(body, f"{day:%Y%m%d}.xls", rapid_day=latest_day)
        blocked.update(notices)
    return blocked


def load_daily_rights(paths):
    result = defaultdict(set)
    for name in paths:
        path = Path(name)
        _, notices, _ = read_daily_rights(path.read_bytes(), path.name)
        for code, entries in notices.items():
            result[code].update(entries)
    return result

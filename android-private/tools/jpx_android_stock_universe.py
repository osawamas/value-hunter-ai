"""Build the Android ordinary-share list from an official JPX data_j.xlsx."""
import argparse
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from openpyxl import load_workbook

from jpx_daily_probe import MARKETS, ordinary_stocks


def stock_universe(workbook_path):
    stocks = ordinary_stocks(workbook_path)
    with workbook_rows(workbook_path) as rows:
        segments = {f"{name}（内国株式）" for name in MARKETS}
        dates = {str(row[0]) for row in rows if row[3] in segments}
    if len(dates) != 1:
        raise ValueError("Expected one listing reference date")
    as_of = datetime.strptime(dates.pop(), "%Y%m%d").date()
    return "\n".join([as_of.isoformat(), *sorted(stocks)]) + "\n"


@contextmanager
def workbook_rows(path):
    book = load_workbook(path, read_only=True, data_only=True)
    try:
        yield book.worksheets[0].iter_rows(min_row=2, values_only=True)
    finally:
        book.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(stock_universe(args.workbook), encoding="ascii")


if __name__ == "__main__":
    main()

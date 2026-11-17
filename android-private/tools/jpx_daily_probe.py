"""Validate extraction of domestic common-stock closes from a local JPX daily report."""
import argparse
import json
import re
import unicodedata
from collections import Counter
from decimal import Decimal

import pymupdf as fitz
from openpyxl import load_workbook

MARKETS = {"プライム": "prime", "スタンダード": "standard", "グロース": "growth"}
CODE = re.compile(r"[0-9][0-9A-Z]{3}")
PRICE = re.compile(r"[0-9][0-9,]*(?:\.[0-9]+)?")


def ordinary_stocks(path):
    workbook = load_workbook(path, read_only=True, data_only=True)
    stocks = {}
    for row in workbook.worksheets[0].iter_rows(min_row=2, values_only=True):
        segment = str(row[3])
        for label, market in MARKETS.items():
            if segment != f"{label}（内国株式）":
                continue
            value = row[1]
            code = str(int(value)) if isinstance(value, float) else str(value)
            if CODE.fullmatch(code):
                stocks[code] = market
    workbook.close()
    if len(stocks) < 3000:
        raise ValueError("Unexpected JPX domestic common-stock universe")
    return stocks


def band_price(row, left, right, width):
    values = [
        Decimal(text.replace(",", ""))
        for x0, _, x1, _, text, *_ in row
        if left < (x0 + x1) / (2 * width) < right and PRICE.fullmatch(text)
    ]
    if len(values) > 1:
        raise ValueError("Ambiguous JPX closing price column")
    return values[0] if values else None


def foreign_or_off_exchange_page(page):
    text = unicodedata.normalize("NFKC", page.get_text())
    return re.search(r"(?m)^\s*(外国株式|Foreign Stock|ToSTNeT市場)\s*$", text) is not None


def read_quotes(path, stocks):
    prices = {}
    duplicates = set()
    with fitz.open(path) as doc:
        for page in doc:
            if foreign_or_off_exchange_page(page):
                break
            width = page.rect.width
            words = page.get_text("words")
            for word in words:
                x0, y0, x1, y1, code, *_ = word
                if code not in stocks or not .057 < (x0 + x1) / (2 * width) < .094:
                    continue
                y = (y0 + y1) / 2
                row = [item for item in words if abs((item[1] + item[3]) / 2 - y) < 2.5]
                morning = band_price(row, .389, .439, width)
                afternoon = band_price(row, .591, .641, width)
                pair = (morning, afternoon)
                if code in prices and prices[code] != pair:
                    duplicates.add(code)
                prices[code] = pair
    for code in duplicates:
        prices.pop(code)
    return prices, duplicates


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("universe")
    parser.add_argument("--check", action="append", nargs=2, default=[], metavar=("CODE", "CLOSE"))
    args = parser.parse_args()
    stocks = ordinary_stocks(args.universe)
    prices, duplicates = read_quotes(args.pdf, stocks)
    counts = {market: Counter() for market in MARKETS.values()}
    for code, market in stocks.items():
        count = counts[market]
        count["universe"] += 1
        if code in duplicates:
            count["ambiguous"] += 1
        elif code not in prices:
            count["not_matched"] += 1
        else:
            morning, afternoon = prices[code]
            count["matched"] += 1
            if afternoon is not None:
                count["afternoon_close"] += 1
            elif morning is not None:
                count["morning_close_only"] += 1
            else:
                count["no_close"] += 1
    print(json.dumps(counts, indent=2))
    for code, expected in args.check:
        morning, afternoon = prices.get(code, (None, None))
        if (afternoon if afternoon is not None else morning) != Decimal(expected):
            raise SystemExit(f"JPX reference close did not match for {code}")
    if len(prices) < len(stocks) * .95:
        raise SystemExit("Less than 95% of the JPX ordinary-stock universe was matched")


if __name__ == "__main__":
    main()

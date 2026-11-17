"""Compare the Android quote-table matcher with the existing PyMuPDF reference."""
import argparse
from decimal import Decimal
import subprocess
from tempfile import TemporaryDirectory

import pymupdf

from jpx_daily_probe import foreign_or_off_exchange_page, ordinary_stocks, read_quotes


def verify(pdf, stocks, java_command):
    expected, expected_conflicts = read_quotes(pdf, stocks)
    with TemporaryDirectory() as scratch, pymupdf.open(pdf) as document:
        with open(f"{scratch}/words.tsv", "w+", encoding="utf-8") as positioned:
            print("\t".join(sorted(stocks)), file=positioned)
            for page in document:
                if foreign_or_off_exchange_page(page):
                    break
                print(page.rect.width, file=positioned)
                for word in page.get_text("words"):
                    print(*word[:5], sep="\t", file=positioned)
            positioned.seek(0)
            output = subprocess.run(java_command, stdin=positioned, capture_output=True,
                                    text=True, check=True).stdout
    prices = {}
    conflicts = set()
    for line in output.splitlines():
        code, *values = line.split("\t")
        if values == ["conflict"]:
            conflicts.add(code)
        else:
            prices[code] = tuple(Decimal(value) if value else None for value in values)
    if prices != expected or conflicts != expected_conflicts:
        differences = {code for code in prices.keys() | expected.keys() if prices.get(code) != expected.get(code)}
        raise ValueError(f"JPX Java/Python mismatch: {len(differences)} price and "
                         f"{len(conflicts ^ expected_conflicts)} conflict rows")
    count = sum(morning is not None or afternoon is not None for morning, afternoon in prices.values())
    print(f"Java and Python matched for {len(prices)} JPX ordinary-stock rows ({count} with closes).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("universe")
    parser.add_argument("classes")
    args = parser.parse_args()
    verify(args.pdf, ordinary_stocks(args.universe),
           ["java", "-cp", args.classes, "jp.valuehunter.privatewatch.JpxCloseTableCheck"])

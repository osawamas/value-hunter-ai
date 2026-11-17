"""Compare the Android quote-table matcher with the existing PyMuPDF reference."""
import argparse
from decimal import Decimal
import subprocess
from tempfile import TemporaryDirectory
import xml.etree.ElementTree as ET

import pymupdf

from jpx_daily_probe import foreign_or_off_exchange_page, ordinary_stocks, read_quotes


def poppler_words(pdf, page_count, output_path):
    """Read independent word coordinates for the domestic pages selected by the reference."""
    subprocess.run(["pdftotext", "-bbox", "-enc", "UTF-8", "-l", str(page_count),
                    pdf, output_path], check=True)
    namespace = "{http://www.w3.org/1999/xhtml}"
    count = 0
    for _, page in ET.iterparse(output_path, events=("end",)):
        if page.tag != namespace + "page":
            continue
        count += 1
        words = []
        for word in page.iter(namespace + "word"):
            value = (word.text or "").strip()
            if len(value.split()) == 1:
                bounds = tuple(word.attrib[key] for key in ("xMin", "yMin", "xMax", "yMax"))
                words.append((*bounds, value))
        yield page.attrib["width"], words
        page.clear()
    if count != page_count:
        raise ValueError(f"Expected {page_count} Poppler pages, got {count}")


def verify(pdf, stocks, java_command, use_poppler=False):
    expected, expected_conflicts = read_quotes(pdf, stocks)
    with TemporaryDirectory() as scratch, pymupdf.open(pdf) as document:
        page_count = next((page.number for page in document if foreign_or_off_exchange_page(page)),
                          len(document))
        if not page_count:
            raise ValueError("No domestic pages in JPX report")
        if use_poppler:
            pages = poppler_words(pdf, page_count, f"{scratch}/poppler.html")
        else:
            pages = ((page.rect.width, page.get_text("words"))
                     for page in (document[index] for index in range(page_count)))
        with open(f"{scratch}/words.tsv", "w+", encoding="utf-8") as positioned:
            print("\t".join(sorted(stocks)), file=positioned)
            for width, words in pages:
                print(width, file=positioned)
                for word in words:
                    print(*word[:5], sep="\t", file=positioned)
            positioned.seek(0)
            output = subprocess.run(java_command, stdin=positioned, stdout=subprocess.PIPE,
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
    source = "Poppler" if use_poppler else "PyMuPDF"
    print(f"Java ({source} coordinates) and Python matched for {len(prices)} JPX "
          f"ordinary-stock rows ({count} with closes).")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf")
    parser.add_argument("universe")
    parser.add_argument("classes")
    parser.add_argument("--poppler", action="store_true", help="use pdftotext for Java word coordinates")
    args = parser.parse_args()
    verify(args.pdf, ordinary_stocks(args.universe),
           ["java", "-cp", args.classes, "jp.valuehunter.privatewatch.JpxCloseTableCheck"], args.poppler)

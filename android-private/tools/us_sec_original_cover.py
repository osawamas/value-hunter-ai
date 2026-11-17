"""Verify dated share counts against the XBRL instance attached to SEC originals."""

import argparse
from collections import defaultdict
from datetime import date
from functools import lru_cache
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
import time
from tempfile import TemporaryDirectory
from xml.etree import ElementTree as ET

from us_public_files_probe import (
    DIRECTORY, SEC_DIRECTORY, SEC_INDEX, SYMBOL, fetch, issuers_requiring_class_review,
    read_directory, read_sec_directory,
)
from us_sec_filing_followup import ACCESSION, scan_index

SEC = "https://www.sec.gov"
DATA = "/Archives/edgar/data/"
XBRLI = "http://www.xbrl.org/2003/instance"
NS = {"x": XBRLI}
DEI = re.compile(r"\{https?://xbrl\.sec\.gov/dei/[^}]+\}(EntityCommonStockSharesOutstanding|TradingSymbol)")
GAAP_AXIS = re.compile(r"https?://fasb\.org/us-gaap/[^#]+")
LEGAL_AXIS = re.compile(r"https?://xbrl\.sec\.gov/dei/[^#]+")
EXPLICIT = "{http://xbrl.org/2006/xbrldi}explicitMember"
MAX_INSTANCE_BYTES = 32_000_000


class FilingLinks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.add(href)


def instance_path(content, accession):
    parser = FilingLinks()
    parser.feed(content.decode("utf-8", errors="replace"))
    pattern = re.compile(rf"{DATA}[0-9]+/{accession.replace('-', '')}/[A-Za-z0-9_.-]+_htm\.xml")
    links = {href for href in parser.links if pattern.fullmatch(href)}
    if len(links) != 1:
        raise ValueError("No unique SEC-extracted XBRL instance link")
    return links.pop()


def canonical_ticker(ticker):
    if re.fullmatch(r"[A-Z]+[-.][A-Z]", ticker):
        return ticker.replace("-", ".")
    return ticker


def qualified(value, namespaces):
    prefix, colon, name = (value or "").partition(":")
    if not colon:
        name, prefix = prefix, ""
    uris = namespaces.get(prefix, set())
    return (next(iter(uris)), name) if len(uris) == 1 and name else ("", "")


def issuer_context(fact, contexts, cik, namespaces):
    context = contexts.get(fact.get("contextRef"))
    if context is None:
        raise ValueError("Share count or trading symbol has no XBRL context")
    entity = context.find("x:entity/x:identifier", NS)
    if entity is None or entity.get("scheme") != "http://www.sec.gov/CIK" or not (entity.text or "").isdigit():
        raise ValueError("Share count or trading symbol has no SEC issuer ID")
    if int(entity.text) != cik:
        return None, "other_entity", None
    if context.find("x:scenario", NS) is not None:
        return context, "unconfirmed", None
    segment = context.find("x:entity/x:segment", NS)
    if segment is None:
        return context, "issuer", None
    if len(segment) != 1 or segment[0].tag != EXPLICIT:
        return context, "unconfirmed", None
    member = segment[0]
    uri, axis = qualified(member.get("dimension"), namespaces)
    value = qualified(member.text, namespaces)
    if not value[0]:
        return context, "unconfirmed", None
    if axis == "LegalEntityAxis" and LEGAL_AXIS.fullmatch(uri):
        return context, "other_entity", None
    if axis == "StatementClassOfStockAxis" and GAAP_AXIS.fullmatch(uri):
        return context, "share_class", value
    return context, "unconfirmed", None


def original_share_count(xml, cik, filed, symbol=None, require_class=False):
    if not 0 < len(xml) <= MAX_INSTANCE_BYTES or re.search(rb"<!DOCTYPE|<!ENTITY", xml, re.I):
        raise ValueError("Unexpected SEC XBRL instance size or markup")
    root = ET.fromstring(xml)
    if root.tag != f"{{{XBRLI}}}xbrl":
        raise ValueError("Expected an XBRL instance")
    namespaces = defaultdict(set)
    for _, (prefix, uri) in ET.iterparse(BytesIO(xml), events=["start-ns"]):
        namespaces[prefix].add(uri)
    contexts = {el.get("id"): el for el in root.findall("x:context", NS)}
    units = {el.get("id"): el for el in root.findall("x:unit", NS)}
    symbols_by_class = defaultdict(set)
    requested_classes = set()
    requested_symbol_seen = False
    if symbol is not None:
        requested_symbol = canonical_ticker(symbol)
        for fact in root:
            match = DEI.fullmatch(fact.tag)
            if not match or match[1] != "TradingSymbol" or not fact.text:
                continue
            _, scope, member = issuer_context(fact, contexts, cik, namespaces)
            tagged = canonical_ticker(fact.text.strip())
            if scope == "share_class":
                symbols_by_class[member].add(tagged)
            if tagged == requested_symbol and scope in {"issuer", "share_class"}:
                requested_symbol_seen = True
                if member is not None:
                    requested_classes.add(member)
        if not requested_symbol_seen or len(requested_classes) > 1:
            raise ValueError("No unique cover-page trading symbol for the requested listing")

    facts = set()
    other_classes = False
    for fact in root:
        match = DEI.fullmatch(fact.tag)
        if not match or match[1] != "EntityCommonStockSharesOutstanding":
            continue
        context, scope, member = issuer_context(fact, contexts, cik, namespaces)
        if scope == "other_entity":
            continue
        if scope == "unconfirmed":
            raise ValueError("Share-class or segment detail needs separate review")
        if scope == "share_class" and member not in requested_classes:
            other_classes = True
            continue
        if scope == "share_class" and symbols_by_class[member] != {requested_symbol}:
            raise ValueError("The stock class maps to multiple trading symbols")
        instant = context.findtext("x:period/x:instant", namespaces=NS)
        unit = units.get(fact.get("unitRef"))
        measures = [] if unit is None else unit.findall("x:measure", NS)
        label = (measures[0].text or "") if len(measures) == 1 else ""
        prefix, colon, name = label.partition(":")
        if not colon:
            name, prefix = prefix, ""
        precision = fact.get("decimals", "")
        if (not instant or name != "shares" or namespaces[prefix] != {XBRLI}
                or not (precision == "INF" or re.fullmatch(r"0|-[1-9]", precision))
                or not re.fullmatch(r"[0-9]+", fact.text or "")):
            raise ValueError("Share count date, unit or precision is unconfirmed")
        day, amount = date.fromisoformat(instant), int(fact.text)
        if day > filed or amount <= 0:
            raise ValueError("Share count date or amount is invalid")
        facts.add((day, amount, int(precision) if precision != "INF" else 0, scope))
    specific = {fact for fact in facts if fact[3] == "share_class"}
    if specific or require_class or other_classes:
        facts = specific
    if len(facts) != 1:
        raise ValueError("No unique cover-page share count with the required scope")
    return facts.pop()


def recent_filings(indexes, target_ciks, cutoff):
    found = defaultdict(set)
    def visit(cik, form, filed, filename):
        if cik not in target_ciks or form not in {b"10-K", b"10-Q"} or filed >= cutoff:
            return
        match = ACCESSION.fullmatch(filename)
        if match is None:
            raise ValueError("Unexpected SEC submission filename")
        prefix = filename.rsplit(b"/", 1)[0].decode("ascii")
        found[cik].add((filed, prefix.split("/")[-1], match[1].decode("ascii")))

    through = {key: scan_index(path, key, visit) for key, path in indexes.items()}
    selected = {}
    for cik, rows in found.items():
        newest = max(row[0] for row in rows)
        candidates = [row for row in rows if row[0] == newest]
        if len(candidates) == 1:
            selected[cik] = candidates[0]
    return selected, through


def resolve_tickers(symbols, directory, listings):
    class_review = issuers_requiring_class_review(listings, directory)
    result = {}
    errors = {}
    for symbol in symbols:
        listing = listings.get(symbol)
        if listing is None and re.fullmatch(r"[A-Z]+-[A-Z]", symbol):
            listing = listings.get(symbol.replace("-", "."))
        if listing is None or listing[0] not in {"Nasdaq", "NYSE"} or listing[1] == "other_security":
            errors[symbol] = "No compatible NYSE or Nasdaq listing"
            continue
        references = directory.get(symbol, set())
        if re.fullmatch(r"[A-Z]+\.[A-Z]", symbol) and symbol.replace(".", "-") not in listings:
            references = references | directory.get(symbol.replace(".", "-"), set())
        issuers = {cik for cik, venue in references if venue == listing[0]}
        if len(issuers) != 1:
            errors[symbol] = "No unique NYSE or Nasdaq issuer in SEC directory"
            continue
        cik = next(iter(issuers))
        result[symbol] = (cik, cik in class_review)
    return result, errors


def verify(cik, filing, download, symbol, require_class):
    filed, directory, accession = filing
    folder = f"{DATA}{directory}/{accession.replace('-', '')}/"
    index_url = SEC + folder + f"{accession}-index.htm"
    xml_url = SEC + instance_path(download(index_url), accession)
    day, count, decimals, scope = original_share_count(download(xml_url), cik, filed, symbol, require_class)
    status = "exact_as_disclosed" if decimals == 0 else "rounded_as_disclosed"
    return {"status": status, "cik": cik, "filed": filed.isoformat(), "share_date": day.isoformat(),
            "shares": count, "decimals": decimals, "share_scope": scope, "filing_url": index_url}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("trading_day", type=date.fromisoformat)
    parser.add_argument("--ticker", action="append", required=True)
    parser.add_argument("--sec-index-quarter", action="append", required=True, help="YYYYqN")
    args = parser.parse_args()
    if len(args.ticker) > 30 or len(set(args.ticker)) != len(args.ticker) or any(
            not SYMBOL.fullmatch(ticker) for ticker in args.ticker):
        parser.error("Provide up to 30 distinct uppercase tickers")
    keys = []
    for value in args.sec_index_quarter:
        match = re.fullmatch(r"(20[0-9]{2})q([1-4])", value)
        if not match:
            parser.error("Use YYYYqN for the index quarter")
        keys.append(tuple(map(int, match.groups())))
    if len(set(keys)) != len(keys) or len(keys) > 4:
        parser.error("Provide up to four distinct index quarters")
    with TemporaryDirectory() as directory:
        work = Path(directory)
        indexes = {}
        for year, part in keys:
            path = work / f"{year}q{part}.idx"
            fetch(f"{SEC_INDEX}{year}/QTR{part}/master.idx", path)
            indexes[year, part] = path
        listings = {}
        for name in ("nasdaqlisted.txt", "otherlisted.txt"):
            _, rows = read_directory(fetch(DIRECTORY + name), name == "nasdaqlisted.txt")
            if listings.keys() & rows.keys():
                raise ValueError("Listing directories overlap")
            listings.update(rows)
        jobs, errors = resolve_tickers(args.ticker, read_sec_directory(fetch(SEC_DIRECTORY)), listings)
        filings, through = recent_filings(indexes, {cik for cik, _ in jobs.values()}, args.trading_day)

        @lru_cache(maxsize=2)
        def download(url):
            # Two requests per issuer, below the SEC's request-rate limit.
            time.sleep(0.2)
            scratch = work / "document"
            fetch(url, scratch, max_bytes=MAX_INSTANCE_BYTES)
            if not 0 < scratch.stat().st_size <= MAX_INSTANCE_BYTES:
                raise ValueError("SEC filing document exceeds the size limit")
            return scratch.read_bytes()

        results = {ticker: {"status": "held", "reason": reason} for ticker, reason in errors.items()}
        for ticker, (cik, require_class) in jobs.items():
            try:
                if cik not in filings:
                    raise ValueError("No unique original 10-K or 10-Q in the supplied index interval")
                results[ticker] = verify(cik, filings[cik], download, ticker, require_class)
            except (OSError, ValueError, ET.ParseError) as error:
                results[ticker] = {"status": "held", "reason": str(error)}
    print(json.dumps({"trading_day": args.trading_day.isoformat(),
                      "index_through": {f"{y}q{q}": day.isoformat() for (y, q), day in sorted(through.items())},
                      "results": results}, indent=2))


if __name__ == "__main__":
    main()

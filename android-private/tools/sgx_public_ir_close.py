#!/usr/bin/env python3
"""Probe a dated close on an issuer's public HTML for private SGX research."""
import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

URL = "https://investorrelations.sgx.com/stock-information/historic-stock-lookup"
MAX_HTML = 1_000_000
DATE_FORMAT = "%b %d, %Y"


class HistoricalTable(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.depth = 0
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            if self.depth:
                self.depth += 1
            elif "historical-lookup" in (dict(attrs).get("class") or "").split():
                self.depth = 1
                self.tables.append([])
        elif self.depth == 1:
            if tag == "tr":
                self.row = []
            elif tag in ("td", "th") and self.row is not None:
                self.cell = []

    def handle_data(self, data):
        if self.depth == 1 and self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag == "table" and self.depth:
            self.depth -= 1
        elif self.depth == 1:
            if tag in ("td", "th") and self.cell is not None:
                self.row.append(" ".join("".join(self.cell).split()))
                self.cell = None
            elif tag == "tr" and self.row is not None:
                self.tables[-1].append(self.row)
                self.row = None


def read_close(html: str, session: date) -> Decimal | None:
    parser = HistoricalTable()
    parser.feed(html)
    parser.close()
    if parser.depth or len(parser.tables) != 1 or not parser.tables[0]:
        raise ValueError("expected one complete historical lookup table")
    header, *rows = parser.tables[0]
    required = ("Date Requested", "Closing Price", "Split Adjustment Factor")
    if any(header.count(column) != 1 for column in required):
        raise ValueError("historical lookup headers changed")
    date_index = header.index("Date Requested")
    price_index = header.index("Closing Price")

    matches = []
    for row in rows:
        if len(row) != len(header):
            raise ValueError("historical lookup row width changed")
        row_date = datetime.strptime(row[date_index], DATE_FORMAT).date()
        if row_date == session:
            matches.append(row[price_index])

    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError("multiple rows for requested trading date")
    value = matches[0]
    if not re.fullmatch(r"\$(?:[0-9]+|[0-9]{1,3}(?:,[0-9]{3})+)\.[0-9]+", value):
        raise ValueError("invalid close format")
    price = Decimal(value[1:].replace(",", ""))
    if price <= 0:
        raise ValueError("nonpositive close")
    return price


class DateLookupForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.forms = []
        self.fields = {}

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.active = attrs.get("id") == "historical-lookup-form"
            if self.active:
                self.forms.append(attrs)
        if self.active and tag in ("input", "select"):
            name = attrs.get("name")
            if name:
                if name in self.fields:
                    raise ValueError("duplicate form field")
                self.fields[name] = attrs.get("value", "")

    def handle_endtag(self, tag):
        if tag == "form":
            self.active = False


def lookup_data(html: str, session: date) -> bytes:
    form = DateLookupForm()
    form.feed(html)
    form.close()
    if len(form.forms) != 1 or form.active:
        raise ValueError("expected one complete date lookup form")
    attrs = form.forms[0]
    if attrs.get("action") != urlsplit(URL).path or attrs.get("method", "").lower() != "post":
        raise ValueError("unexpected date lookup action")
    fields = {name: form.fields.get(name) for name in ("form_build_id", "form_id", "op")}
    if not fields["form_build_id"] or fields["form_id"] != "historical_lookup_form" or not fields["op"]:
        raise ValueError("required date lookup fields missing")
    values = {"month": f"{session.month:02}", "day": str(session.day), "year": str(session.year)}
    for part, value in values.items():
        keys = [name for name in form.fields if name.endswith(f"[SGXL_SI][date_{part}]")]
        if len(keys) != 1:
            raise ValueError("unexpected date lookup field")
        fields[keys[0]] = value
    return urlencode(fields).encode("ascii")


def fetch_html(data: bytes | None = None) -> str:
    request = Request(URL, data=data, headers={
        "Accept": "text/html",
        "Referer": URL,
        "User-Agent": "VALUE-HUNTER-AI-research/1.0 (+https://github.com/osawamas/value-hunter-ai)",
    })
    with urlopen(request, timeout=20) as response:
        final_url = urlsplit(response.geturl())
        if final_url._replace(query="", fragment="").geturl() != URL:
            raise ValueError("unexpected lookup URL")
        if response.headers.get_content_type() != "text/html":
            raise ValueError("unexpected lookup content type")
        body = response.read(MAX_HTML + 1)
        if len(body) > MAX_HTML:
            raise ValueError("HTML exceeds size limit")
        return body.decode(response.headers.get_content_charset() or "utf-8")


def main() -> int:
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("session", type=date.fromisoformat, help="SGX trading date YYYY-MM-DD")
    args = cli.parse_args()
    report = {
        "symbol": "S68",
        "source_url": URL,
        "session": args.session.isoformat(),
        "checked_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "price_basis": "issuer_adjusted_for_splits_and_or_dividends",
        "matched_count": 0,
    }
    try:
        html = fetch_html()
        close = read_close(html, args.session)
        report["lookup"] = "default_page"
        if close is None:
            report["lookup"] = "public_date_form"
            close = read_close(fetch_html(lookup_data(html, args.session)), args.session)
        report["matched_count"] = int(close is not None)
        report["status"] = "matched" if close is not None else "date_missing"
    except HTTPError as error:
        report["status"] = "http_error"
        report["http_status"] = error.code
    except (URLError, TimeoutError):
        report["status"] = "transport_error"
    except (ValueError, LookupError) as error:
        report["status"] = "invalid_page"
        print(f"SGX IR page validation failed ({type(error).__name__})", file=sys.stderr)
    print(json.dumps(report, ensure_ascii=False))
    return {"matched": 0, "date_missing": 1}.get(report["status"], 2)


if __name__ == "__main__":
    raise SystemExit(main())

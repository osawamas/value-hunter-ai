"""Acquire dated official inputs and report source availability without inventing coverage."""
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

from jpx_daily_probe import ordinary_stocks, read_quotes
from openpyxl import load_workbook

JPX_INDEX = "https://www.jpx.co.jp/markets/statistics-equities/misc/01.html"
DIRECTORY = "https://www.nasdaqtrader.com/dynamic/SymDir/"
JPX_ROOT = "https://www.jpx.co.jp/automation/markets/statistics-equities/daily/files/"


def get(url, path, journal):
    item = {"url": url, "at": dt.datetime.now(dt.timezone.utc).isoformat()}
    journal.append(item)
    try:
        request = Request(url, headers={"User-Agent": "ValueHunter-public-market-audit/1.0"})
        with urlopen(request, timeout=25) as response:
            item["http"] = response.status
            content = response.read(33_000_001)
            if len(content) > 33_000_000:
                raise ValueError("source size limit")
            path.write_bytes(content)
            item["sha256"] = hashlib.sha256(content).hexdigest()
            return True
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        item["error"] = type(error).__name__
        if isinstance(error, HTTPError):
            item["http"] = error.code
        return False


def save(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def listing_breakdown(workbook):
    source = load_workbook(workbook, read_only=True, data_only=True)
    try:
        return dict(Counter(str(row[3]) for row in source.worksheets[0].iter_rows(
            min_row=2, values_only=True) if len(row) > 3 and row[3]))
    finally:
        source.close()


def jpx(out, journal):
    index, workbook = out / "jpx-index.html", out / "jpx-list.xlsx"
    if not get(JPX_INDEX, index, journal):
        return {"status": "listing_unavailable"}
    urls = set(re.findall(r"""href=["']([^"']+/data_j\.xlsx)["']""",
                          index.read_text(encoding="utf-8"), re.I))
    if len(urls) != 1:
        return {"status": "listing_link_unverified"}
    address = urljoin(JPX_INDEX, urls.pop())
    if not address.startswith("https://www.jpx.co.jp/") or not get(address, workbook, journal):
        return {"status": "listing_unavailable"}
    today = dt.datetime.now(ZoneInfo("Asia/Tokyo")).date()
    for offset in range(5):
        day = today - dt.timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        pdf = out / "jpx-session.pdf"
        url = JPX_ROOT + f"{day:%Y%m}/stq_{day:%Y%m%d}.pdf"
        if get(url, pdf, journal):
            with pdf.open("rb") as stream:
                if stream.read(5) != b"%PDF-":
                    pdf.unlink()
                    return {"status": "invalid_daily_pdf", "trade_date": day.isoformat()}
            for name, page in (("listings", "new"), ("delistings", "delisted")):
                get(f"https://www.jpx.co.jp/listing/stocks/{page}/", out / f"jpx-{name}.html", journal)
            try:
                stocks = ordinary_stocks(workbook)
                quotes, ambiguous = read_quotes(pdf, stocks)
            except (ValueError, OSError) as error:
                return {"status": "reference_parser_unavailable", "trade_date": day.isoformat(),
                        "error": type(error).__name__}
            return {"status": "price_inputs_only", "trade_date": day.isoformat(),
                    "listing_reference_count": len(stocks), "listing_reference_segments": dict(Counter(stocks.values())),
                    "official_workbook_all_product_rows": listing_breakdown(workbook),
                    "matched_close_count": sum(
                        (morning is not None or afternoon is not None) for morning, afternoon in quotes.values()),
                    "ambiguous_count": len(ambiguous),
                    "valuation": None}
        if journal[-1].get("http") not in (404, 410):
            break
        time.sleep(1)
    return {"status": "dated_closes_unavailable"}


def summarize(out):
    def load(name):
        path = out / name
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {"status": "invalid_result"}

    jpx_source = load("jpx-public-coverage.json")
    us = load("us-public-coverage.json")
    jpx = load("jpx-valuation.json")
    labels = []
    for market, detail, result in (("JPX", jpx_source, jpx), ("US", us, us.get("valuation", {}))):
        state = result.get("status", detail.get("status", "unavailable"))
        day = result.get("trading_date", detail.get("trade_date", "undated"))
        if "total_assessed" not in result:
            closes = detail.get("closes", detail.get("matched_close_count", "unknown"))
            labels.append(f"{market} {day} {state} closes={closes}")
            continue
        tiers = result.get("tiers")
        if tiers is None:
            tiers = [a + b for a, b in zip(result["strict_tiers"], result["flexible_tiers"])]
        flexible = result.get("flexible_added", result.get("partial_assessed", 0))
        rate = result.get("full_scope_assessed_percent")
        rate_label = f"{rate:.2f}%" if rate is not None else "unverified"
        labels.append(f"{market} {day} {state} strict={result['strict_assessed']} flexible={flexible}"
                      f" total={result['total_assessed']}/{result['scope']} {rate_label} tiers="
                      + "/".join(map(str, tiers)))
    if os.getenv("JPX_BUILD_OUTCOME") == "failure":
        log = out / "jpx-build.log"
        data = log.read_text(encoding="utf-8", errors="replace") if log.exists() else ""
        failures = (("Gradle daemon disappeared", "daemon_exited"),
                    ("Could not resolve", "dependency_resolution"),
                    ("Compilation failed", "compilation"),
                    ("SDK location not found", "sdk_configuration"))
        reason = next((label for phrase, label in failures if phrase in data), "see_build_log")
        labels.append(f"JPX instrumentation build failed {reason}")
    journal = load("public-source-status.json")
    sources = (journal if isinstance(journal, list) else []) + us.get("sources", [])
    from urllib.parse import urlparse
    status = {}
    for item in sources:
        host = item.get("host") or urlparse(item.get("url", "")).hostname
        if host:
            status.setdefault(host, set()).add(str(item.get("http", item.get("error", "unknown"))))
    labels.extend(f"Source {host} {','.join(sorted(values))}" for host, values in sorted(status.items()))
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
        print("labels=" + json.dumps(labels), file=output)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as output:
        print("## Observed results", file=output)
        for label in labels:
            print(f"- {label}", file=output)
        print("\nBounded financial passes report observed coverage from collected inputs.", file=output)


def main():
    if sys.argv[1:2] == ["--summary"]:
        summarize(Path(sys.argv[2]))
        return
    out = Path(sys.argv[1])
    out.mkdir(parents=True, exist_ok=True)
    journal = []
    try:
        for file in ("nasdaqlisted.txt", "otherlisted.txt"):
            get(DIRECTORY + file, out / file, journal)
        try:
            result = jpx(out, journal)
        except (ValueError, OSError, KeyError) as error:
            result = {"status": "input_validation_failed", "error": type(error).__name__}
        save(out / "jpx-public-coverage.json", result)
        print(json.dumps(result, ensure_ascii=False))
    finally:
        save(out / "public-source-status.json", journal)


if __name__ == "__main__":
    main()

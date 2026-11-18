"""Put JPX monthly closing prices on one share basis using audited JPX rights reports."""
import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from decimal import Decimal
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import pymupdf

from jpx_rights_sources import download, monthly_archive_links

from jpx_share_basis import load_rights_reports, missing_rights_months, read_monthly_rights
from value_candidate_screen import range_position, usable


def monthly_quotes(report):
    if report["price_basis"] != "jpx_monthly_unadjusted":
        raise ValueError("Expected unadjusted JPX monthly prices")
    points = defaultdict(list)
    for month, row in sorted(report["months"].items()):
        if row["status"] != "read":
            continue
        if "prices" not in row:
            raise ValueError("Run the monthly close tool with --include-prices")
        for code, entry in row["prices"].items():
            day = date.fromisoformat(entry["session"])
            close = Decimal(entry["close"])
            if day.strftime("%Y-%m") != month or not usable(close):
                raise ValueError(f"Invalid monthly close for {code} in {month}")
            points[code].append((day, close))
    return points


def adjusted_prices(points, events):
    """Quotes on an ex-date already trade on the new basis."""
    newest = points[-1][0]
    factor = Decimal(1)
    pending = iter(sorted(events, key=lambda event: event.ex_on, reverse=True))
    event = next(pending, None)
    adjusted = []
    for day, close in reversed(points):
        while event is not None and day < event.ex_on <= newest:
            factor *= event.ratio_left / event.ratio_right
            event = next(pending, None)
        adjusted.append((day, close * factor))
    return list(reversed(adjusted))


def analyze(points, coverage, events, *, include_prices=False, include_range=False):
    if not points:
        return {"status": "no_closes", "months_with_close": 0}
    first, last = points[0][0], points[-1][0]
    summary = {"months_with_close": len(points), "first_session": first.isoformat(),
               "last_session": last.isoformat()}
    missing = missing_rights_months(first, last, coverage)
    if missing:
        return {**summary, "status": "rights_report_gap", "missing_months": missing}

    actions = [event for event in events if first < event.ex_on <= last]
    if any(event.kind not in {"分割", "併合"} for event in actions):
        return {**summary, "status": "other_share_change"}
    if len({event.ex_on for event in actions}) != len(actions):
        return {**summary, "status": "conflicting_share_events"}
    series = adjusted_prices(points, actions)
    closes = [close for _, close in series]
    position = range_position(closes[-1], closes)
    result = {
        **summary,
        "status": "split_adjusted",
        "splits_or_consolidations": len(actions),
        "range_position": str(position.quantize(Decimal(".0001"))) if position is not None else None,
    }
    if include_range and position is not None:
        result["range_low"] = format(min(closes), "f")
        result["range_high"] = format(max(closes), "f")
    if include_prices:
        result["points"] = [{"session": day.isoformat(), "close": str(close)} for day, close in series]
    return result


def verified_rights(months, cache):
    cache.mkdir(parents=True, exist_ok=True)
    links = monthly_archive_links({month.year for month in months})
    coverage = set()
    by_code = defaultdict(set)
    failed = {}
    unpublished = [f"{month:%Y-%m}" for month in sorted(months - links.keys())]

    def get(month):
        url = links[month]
        path = cache / url.rsplit("/", 1)[-1]
        try:
            return path, path.read_bytes() if path.is_file() else download(url), None
        except (OSError, ValueError) as error:
            return path, None, str(error)

    expected = sorted(months & links.keys())
    with ThreadPoolExecutor(max_workers=4) as pool:
        for month, (path, body, download_error) in zip(expected, pool.map(get, expected)):
            if download_error is not None:
                failed[f"{month:%Y-%m}"] = download_error
                continue
            try:
                found, events = read_monthly_rights(body)
                if found != month:
                    raise ValueError("JPX archive report month differs from the index")
                if not path.is_file():
                    with TemporaryDirectory(dir=cache) as staging:
                        pending = Path(staging) / path.name
                        pending.write_bytes(body)
                        pending.replace(path)
            except (OSError, ValueError, pymupdf.FileDataError) as error:
                failed[f"{month:%Y-%m}"] = str(error)
                continue
            coverage.add(month)
            for code, actions in events.items():
                by_code[code].update(actions)
    return (coverage, by_code), unpublished, failed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("monthly_json", type=Path)
    parser.add_argument("rights_pdf", type=Path, nargs="*")
    parser.add_argument("--include-prices", action="store_true", help="include adjusted prices in local output")
    parser.add_argument("--include-range", action="store_true", help="include adjusted price bounds for a private APK")
    parser.add_argument("--rights-cache", type=Path, help="fetch official archived rights reports into this directory")
    args = parser.parse_args()
    if bool(args.rights_pdf) == bool(args.rights_cache):
        parser.error("provide rights PDF paths or --rights-cache")
    report = json.loads(args.monthly_json.read_text(encoding="utf-8"))
    points = monthly_quotes(report)
    if args.rights_cache:
        months = {date.fromisoformat(month + "-01") for month in report["months"]}
        (coverage, by_code), unpublished, failed = verified_rights(months, args.rights_cache)
    else:
        coverage, by_code = load_rights_reports(args.rights_pdf)
        unpublished, failed = [], {}
    result = {code: analyze(points[code], coverage, by_code.get(code, ()),
                            include_prices=args.include_prices, include_range=args.include_range)
              for code in report["months_with_close_by_code"]}
    print(json.dumps({"months_requested": report["months_requested"],
                      "rights_months_verified": len(coverage),
                      "rights_months_unpublished": unpublished, "rights_months_failed": failed,
                      "by_code": result}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

"""Compare an official JPX cash close with previously published annual EPS and BPS."""
import argparse
from datetime import date
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
import unicodedata

import pymupdf as fitz

from jpx_daily_probe import CODE, ordinary_stocks, read_quotes


def trading_date(report):
    with fitz.open(report) as doc:
        header = unicodedata.normalize("NFKC", doc[0].get_text(clip=fitz.Rect(
            0, 0, doc[0].rect.width, doc[0].rect.height * 0.12,
        )))
    dates = re.findall(r"(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日", header)
    if len(set(dates)) != 1:
        raise ValueError("Could not determine a unique trading date in the JPX report header")
    return date(*map(int, dates[0]))


def load_financials(path):
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    validated = []
    keys = set()
    for row in rows:
        code = row["code"]
        period_end = date.fromisoformat(row["period_end"])
        disclosed_on = date.fromisoformat(row["disclosed_on"])
        if (
            not CODE.fullmatch(code) or period_end >= disclosed_on
            or not row["source"].startswith("https://")
            or row["basis"] != "annual_reported_unadjusted"
        ):
            raise ValueError("Invalid annual financial record")
        key = code, period_end, disclosed_on
        if key in keys:
            raise ValueError("Duplicate annual financial record")
        keys.add(key)
        validated.append((code, period_end, disclosed_on, row))
    return validated


def ratio(close, per_share):
    try:
        value = Decimal(per_share) if isinstance(per_share, str) else Decimal("NaN")
    except InvalidOperation:
        return None
    return close / value if value.is_finite() and value > 0 else None


def latest_financials(day, financials):
    latest = {}
    pending = set()
    for code, period_end, disclosed_on, row in financials:
        # A disclosure date alone cannot establish availability before market close.
        if disclosed_on >= day:
            pending.add(code)
            continue
        stamp = period_end, disclosed_on
        if code not in latest or stamp > latest[code][0]:
            latest[code] = stamp, row

    return latest, pending


def associate(day, stocks, prices, duplicates, financials):
    latest, pending = latest_financials(day, financials)
    results = {}
    for code in sorted(stocks):
        if code in duplicates:
            results[code] = {"status": "ambiguous_close"}
            continue
        am, pm = prices.get(code, (None, None))
        close = pm if pm is not None else am
        if close is None or close <= 0:
            results[code] = {"status": "no_close"}
            continue
        if code not in latest:
            status = "financials_not_yet_public" if code in pending else "no_financials"
            results[code] = {"status": status}
            continue
        stamp, row = latest[code]
        per, pbr = ratio(close, row["eps_jpy"]), ratio(close, row["bps_jpy"])
        results[code] = {
            "status": "annual_reference" if per is not None and pbr is not None
            else "unusable_eps_or_bps",
            "close_jpy": str(close),
            "close_session": "afternoon" if pm is not None else "morning",
            "annual_period_end": stamp[0].isoformat(),
            "disclosed_on": stamp[1].isoformat(),
            "financial_source": row["source"],
            "annual_reference_per": str(round(per, 4)) if per is not None else None,
            "annual_reference_pbr": str(round(pbr, 4)) if pbr is not None else None,
        }
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", help="Locally available JPX daily report")
    parser.add_argument("universe", help="Locally available exchange symbol list")
    parser.add_argument("financials", help="Source-checked reference annual financial JSON")
    args = parser.parse_args()

    stocks = ordinary_stocks(args.universe)
    prices, duplicates = read_quotes(args.pdf, stocks)
    day = trading_date(args.pdf)
    financials = load_financials(args.financials)
    print(json.dumps({
        "trading_date": day.isoformat(),
        "valuation_kind": "annual_reference_only",
        "results": associate(day, stocks, prices, duplicates, financials),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

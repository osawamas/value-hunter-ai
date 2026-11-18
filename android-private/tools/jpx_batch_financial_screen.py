"""Batch-screen locally verified JP observations without publishing prices.

Input is a local JSON object with trade_date, observations (code, close,
financial_as_of, per, pbr, single_share_supported). Ratios must already
have been independently verified and adjusted to the close's share basis.
Alternatively, build observations directly from a local JPX daily report,
listing workbook and source-checked annual financial and rights files.
Outputs contain counts only.
"""
import argparse
from collections import Counter
import json
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from jpx_daily_probe import CODE, ordinary_stocks, read_quotes
from jpx_share_basis import load_rights_reports, share_basis_status
from jpx_valuation_probe import latest_financials, load_financials, trading_date
from value_candidate_screen import BUDGET, classify


def decimal_or_none(value):
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("Boolean is not a number")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Invalid numeric field") from exc
    if not result.is_finite():
        raise ValueError("Non-finite numeric field")
    return result


def screen(payload):
    trade_date = date.fromisoformat(payload["trade_date"])
    seen = set()
    counts = {"priority": 0, "reference": 0, "held": 0, "excluded": 0}
    reasons = {}
    processed = 0
    for row in payload["observations"]:
        code = str(row["code"])
        if not CODE.fullmatch(code) or code in seen:
            raise ValueError("Invalid or duplicated JP security code")
        seen.add(code)
        financial_date = row.get("financial_as_of")
        if financial_date is not None and date.fromisoformat(financial_date) > trade_date:
            raise ValueError("Future financial basis date")
        # A financial date alone does not prove price/share-basis comparability.
        # The producer must explicitly attest to independent verification.
        verified = (financial_date is not None and row.get("financial_verified") is True
                    and row.get("share_basis_verified") is True)
        close = decimal_or_none(row.get("close"))
        per = decimal_or_none(row.get("per")) if verified else None
        pbr = decimal_or_none(row.get("pbr")) if verified else None
        result = classify(close, Decimal("1"), per, pbr,
                          row.get("single_share_supported") is True)
        counts[result.tier] += 1
        reasons[result.reason] = reasons.get(result.reason, 0) + 1
        processed += 1
    return {"trade_date": trade_date.isoformat(), "market": "JP",
            "processed": processed, "tiers": counts, "reasons": reasons,
            "note": "Counts only; no quotes, candidates or alerts exported"}


def financial_ratio(close, per_share):
    denominator = decimal_or_none(per_share)
    if denominator is None or denominator == 0:
        return denominator
    return close / denominator


def screen_report(day, stocks, prices, duplicates, financials, rights, single_share_codes=()):
    latest, pending = latest_financials(day, financials)
    observations = []
    source_counts = Counter()
    for code in sorted(stocks):
        row = {"code": code, "single_share_supported": code in single_share_codes}
        observations.append(row)
        if code in duplicates:
            source_counts["ambiguous_close"] += 1
            continue
        morning, afternoon = prices.get(code, (None, None))
        close = afternoon if afternoon is not None else morning
        if close is None or close <= 0:
            source_counts["no_close"] += 1
            continue
        row["close"] = close
        source_counts["valid_close"] += 1
        if close * 100 <= BUDGET:
            source_counts["within_100_share_budget"] += 1
        if code not in latest:
            source_counts["financials_not_yet_public" if code in pending else "no_financials"] += 1
            continue

        (period_end, _), financial = latest[code]
        basis = share_basis_status(code, period_end, day, rights)
        source_counts[basis] += 1
        if basis != "no_share_change_in_supplied_reports":
            continue
        row.update(financial_as_of=period_end.isoformat(), financial_verified=True, share_basis_verified=True,
                   per=financial_ratio(close, financial.get("eps_jpy")),
                   pbr=financial_ratio(close, financial.get("bps_jpy")))

    result = screen({"trade_date": day.isoformat(), "observations": observations})
    result["source_counts"] = dict(source_counts)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local JSON observations or JPX daily PDF")
    parser.add_argument("--jpx-universe", type=Path, help="JPX listing workbook")
    parser.add_argument("--annual-financials", type=Path, help="Source-checked annual financial JSON")
    parser.add_argument("--rights-pdf", type=Path, action="append", default=[])
    parser.add_argument("--single-share-code", action="append", default=[])
    args = parser.parse_args()
    if args.jpx_universe or args.annual_financials or args.rights_pdf or args.single_share_code:
        if not args.jpx_universe or not args.annual_financials:
            parser.error("JPX PDF mode requires --jpx-universe and --annual-financials")
        stocks = ordinary_stocks(args.jpx_universe)
        single_share = set(args.single_share_code)
        if not single_share <= stocks.keys():
            parser.error("--single-share-code must identify a code present in the JPX list")
        day = trading_date(args.input)
        prices, duplicates = read_quotes(args.input, stocks)
        result = screen_report(day, stocks, prices, duplicates, load_financials(args.annual_financials),
                               load_rights_reports(args.rights_pdf), single_share)
    else:
        result = screen(json.loads(args.input.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

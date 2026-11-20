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
        disclosed = row.get("financial_disclosed_on")
        if disclosed is not None and date.fromisoformat(disclosed) >= trade_date:
            raise ValueError("Financial disclosure not available before trade date")
        if (row.get("financial_verified") is True and disclosed is None):
            raise ValueError("Verified financials require a disclosure date")
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
    # Report source coverage separately from quote, budget and valuation counts.
    # Financial rows are already deduplicated by load_financial_batches.
    source_counts["financial_records_loaded"] = len(financials)
    source_counts["financial_codes_loaded"] = len({code for code, _, _, _ in financials})
    source_counts["financial_codes_in_universe"] = len({code for code, _, _, _ in financials if code in stocks})
    source_counts["financial_codes_public_before_trade"] = len(set(latest) & set(stocks))
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

        (period_end, disclosed_on), financial = latest[code]
        basis = share_basis_status(code, period_end, day, rights)
        source_counts[basis] += 1
        if basis != "no_share_change_in_supplied_reports":
            continue
        per = financial_ratio(close, financial.get("eps_jpy"))
        pbr = financial_ratio(close, financial.get("bps_jpy"))
        source_counts["financial_basis_verified"] += 1
        if per is not None and per > 0 and pbr is not None and pbr > 0:
            source_counts["both_ratios_usable"] += 1
        else:
            source_counts["incomplete_or_nonpositive_ratios"] += 1
        row.update(financial_as_of=period_end.isoformat(), financial_disclosed_on=disclosed_on.isoformat(),
                   financial_verified=True, share_basis_verified=True,
                   per=per, pbr=pbr)

    result = screen({"trade_date": day.isoformat(), "observations": observations})
    result["source_counts"] = dict(source_counts)
    return result


def load_financial_batches(paths):
    """Merge source-checked batches; reject conflicting records."""
    merged = {}
    # Repeated --annual-financials paths (including directory overlap) must not
    # trigger duplicate disk reads; retain the first occurrence's ordering.
    seen_paths = set()
    for path in paths:
        canonical = Path(path).resolve()
        if canonical in seen_paths:
            continue
        seen_paths.add(canonical)
        for code, period_end, disclosed_on, row in load_financials(path):
            key = (code, period_end, disclosed_on)
            if key in merged and merged[key] != row:
                raise ValueError("Conflicting annual financial record across files")
            merged[key] = row
    return [(code, period_end, disclosed_on, row)
            for (code, period_end, disclosed_on), row in sorted(merged.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Local JSON observations or JPX daily PDF")
    parser.add_argument("--jpx-universe", type=Path, help="JPX listing workbook")
    parser.add_argument("--annual-financials", type=Path, action="append", default=[], help="Source-checked annual financial JSON; repeat for multiple batches")
    parser.add_argument("--annual-financials-dir", type=Path, action="append", default=[], help="Local directory of source-checked annual JSON batches; nested files are sorted and merged")
    parser.add_argument("--rights-pdf", type=Path, action="append", default=[])
    parser.add_argument("--single-share-code", action="append", default=[])
    args = parser.parse_args()
    financial_paths = list(args.annual_financials)
    for directory in args.annual_financials_dir:
        if not directory.is_dir():
            parser.error(f"Annual financial directory does not exist: {directory}")
        financial_paths.extend(sorted(path for path in directory.rglob("*.json") if path.is_file()))
    if args.annual_financials_dir and not financial_paths:
        parser.error("No annual financial JSON files found")
    if args.jpx_universe or financial_paths or args.rights_pdf or args.single_share_code:
        if not args.jpx_universe or not financial_paths:
            parser.error("JPX PDF mode requires --jpx-universe and --annual-financials")
        stocks = ordinary_stocks(args.jpx_universe)
        single_share = set(args.single_share_code)
        if not single_share <= stocks.keys():
            parser.error("--single-share-code must identify a code present in the JPX list")
        day = trading_date(args.input)
        prices, duplicates = read_quotes(args.input, stocks)
        result = screen_report(day, stocks, prices, duplicates, load_financial_batches(financial_paths),
                               load_rights_reports(args.rights_pdf), single_share)
    else:
        result = screen(json.loads(args.input.read_text(encoding="utf-8")))
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()

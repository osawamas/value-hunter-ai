"""SGX financial/valuation comparison: fail-closed ranking eligibility.

The v27 cross-document audit checks a second document from the SAME issuer:
this is not third-party independent verification.
"""
import argparse
import csv
import json
import math
from datetime import datetime, timezone, date
from pathlib import Path

SYMBOLS = ("S68", "G13", "S20")
METRICS = ("revenue", "attributable_profit", "assets", "liabilities", "equity")


def number(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def value(fin, field, year):
    entry = fin.get("metrics", {}).get(field, {}).get(str(year), {})
    return entry.get("value") if isinstance(entry, dict) else None


def age_quote(timestamp, now):
    if not isinstance(timestamp, str):
        return None
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return (now - parsed).total_seconds() / 86400 if parsed.tzinfo else None
    except (ValueError, TypeError):
        return None


def age_shares(value, now):
    if not isinstance(value, str):
        return None
    try:
        return (now.date() - date.fromisoformat(value)).days
    except ValueError:
        return None


def evaluate(fin, valuation, audit, now):
    symbol = fin.get("symbol", valuation.get("symbol", audit.get("symbol")))
    year = fin.get("fiscal_year")
    reasons = []
    def deny(reason):
        if reason not in reasons:
            reasons.append(reason)

    fields = {field: value(fin, field, year) for field in METRICS}
    revenue = number(fields["revenue"])
    previous = number(value(fin, "revenue", year - 1)) if isinstance(year, int) else None
    profit = number(fields["attributable_profit"])
    assets = number(fields["assets"])
    liabilities = number(fields["liabilities"])
    equity = number(fields["equity"])
    operating = number(value(fin, "operating_profit", year))
    for key, val in fields.items():
        if number(val) is None:
            deny("FINANCIAL_MISSING_" + key.upper())
    if not isinstance(year, int):
        deny("FISCAL_YEAR_UNKNOWN")
    if symbol == "S68" or fin.get("source_kind") == "HISTORICAL_V14_ISSUER_SPECIFIC_FIXTURE":
        deny("HISTORICAL_FIXED_FINANCIALS")
    if assets is None or liabilities is None or equity is None or abs(assets - liabilities - equity) > 1:
        deny("BALANCE_UNVERIFIED_OR_MISMATCH")

    checks = {c.get("metric"): c for c in audit.get("checks", []) if isinstance(c, dict)}
    for metric in ("revenue", "attributable_profit"):
        if checks.get(metric, {}).get("status") != "MATCH_LIVE_SECOND_ISSUER_DOCUMENT":
            deny("SECOND_ISSUER_DOCUMENT_NOT_MATCHED_" + metric.upper())
    deny("INDEPENDENT_FINANCIAL_VERIFICATION_NOT_AVAILABLE")

    quote = valuation.get("quote") or valuation.get("price") or {}
    shares = valuation.get("shares") or {}
    price = number(quote.get("price_sgd"))
    shares_count = number(shares.get("shares_outstanding"))
    quote_age = age_quote(quote.get("market_timestamp_utc"), now)
    shares_age = age_shares(shares.get("as_of_date"), now)
    if price is None or price <= 0:
        deny("PRICE_MISSING")
    if quote_age is None or not -1 <= quote_age <= 7:
        deny("QUOTE_OLD_OR_UNDATED")
    if shares_count is None or shares_count <= 0:
        deny("SHARES_MISSING")
    if shares_age is None or not -1 <= shares_age <= 180:
        deny("SHARES_OLD_OR_UNDATED")
    if not shares.get("source_url"):
        deny("SHARES_SOURCE_MISSING")
    if shares.get("share_count_basis") not in ("issued_excluding_treasury", "outstanding_excluding_treasury"):
        deny("TREASURY_SHARE_BASIS_UNCONFIRMED")

    market_cap = price * shares_count if price is not None and price > 0 and shares_count is not None and shares_count > 0 else None
    per = round(market_cap / (profit * 1000), 4) if market_cap is not None and profit is not None and profit > 0 else None
    if profit is not None and profit <= 0:
        deny("NEGATIVE_EARNINGS_PER_NOT_APPLICABLE")
    owner_equity = number(valuation.get("parent_equity_sgd_thousands"))
    pbr_reference = round(market_cap / (owner_equity * 1000), 4) if market_cap is not None and owner_equity is not None and owner_equity > 0 else None
    if valuation.get("parent_equity_status") != "PARENT_EQUITY_INDEPENDENTLY_VERIFIED":
        deny("PARENT_EQUITY_NOT_INDEPENDENTLY_VERIFIED")

    return {
        "symbol": symbol,
        "fiscal_year": year,
        "revenue_sgd_thousands": revenue,
        "revenue_growth_pct": round(100 * (revenue - previous) / previous, 2) if revenue is not None and previous is not None and previous > 0 else None,
        "operating_margin_pct": round(100 * operating / revenue, 2) if operating is not None and revenue is not None and revenue > 0 else None,
        "equity_ratio_pct": round(100 * equity / assets, 2) if equity is not None and assets is not None and assets > 0 else None,
        "assets_sgd_thousands": assets,
        "liabilities_sgd_thousands": liabilities,
        "equity_sgd_thousands": equity,
        "balance_difference_sgd_thousands": assets - liabilities - equity if None not in (assets, liabilities, equity) else None,
        "balance_source_status": fin.get("g13_balance_evidence", {}).get("status") or (
            fin.get("metrics", {}).get("assets", {}).get(str(year), {}).get("status")
        ),
        "balance_source_page": fin.get("g13_balance_evidence", {}).get("page_pdf_number"),
        "parent_equity_sgd_thousands": owner_equity,
        "parent_equity_status": valuation.get("parent_equity_status"),
        "parent_equity_source_url": valuation.get("parent_equity_source"),
        "attributable_profit_sgd_thousands": profit,
        "price_sgd": price,
        "shares_outstanding": shares_count,
        "market_cap_sgd": round(market_cap, 2) if market_cap is not None else None,
        "per_reference": per,
        "pbr_reference_unverified": pbr_reference,
        "pbr_verified": pbr_reference if valuation.get("parent_equity_status") == "PARENT_EQUITY_INDEPENDENTLY_VERIFIED" else None,
        "financial_source_url": fin.get("source_url"),
        "financial_source_kind": fin.get("source_kind"),
        "financial_pdf_sha256": fin.get("pdf_sha256"),
        "audit_source_url": audit.get("url"),
        "audit_pdf_sha256": audit.get("pdf_sha256"),
        "audit_reference_type": "SECOND_ISSUER_DOCUMENT_NOT_THIRD_PARTY",
        "audit_pages_by_metric": {
            key: [ev.get("page") for ev in checks.get(key, {}).get("reference_extraction", {}).get("evidence", [])
                  if isinstance(ev, dict) and isinstance(ev.get("page"), int)]
            for key in ("revenue", "operating_profit", "attributable_profit")
        },
        "quote_url": quote.get("source_url"),
        "quote_timestamp_utc": quote.get("market_timestamp_utc"),
        "shares_source_url": shares.get("source_url"),
        "shares_as_of_date": shares.get("as_of_date"),
        "shares_verification_status": shares.get("verification_status"),
        "shares_count_basis": shares.get("share_count_basis"),
        "quote_source_type": quote.get("source"),
        "audit_states": {key: checks.get(key, {}).get("status", "NOT_VERIFIED") for key in ("revenue", "operating_profit", "attributable_profit")},
        "ranking_eligible": not reasons,
        "ranking_score": None,
        "exclusion_reasons": reasons,
    }


def compare(financials, valuations, audits, now=None, universe=None):
    now = now or datetime.now(timezone.utc)
    if universe is None:
        issuers = [{"symbol": symbol, "issuer": {
            "S68": "Singapore Exchange Limited",
            "G13": "Genting Singapore Limited",
            "S20": "The Straits Trading Company Limited"
        }[symbol]} for symbol in SYMBOLS]
    else:
        from sgx_universe_v30 import validate_universe
        issuers = validate_universe(universe)
    sources = [
        {item["symbol"]: item for item in feed.get("records", [])}
        for feed in (financials, valuations, audits)
    ]
    records = [evaluate(*(source.get(item["symbol"], {"symbol": item["symbol"]}) for source in sources), now)
               for item in issuers]
    return {
        "issuer_universe": [{"symbol": item["symbol"], "issuer": item["issuer"],
                             "financial_pdf_url": item.get("financial_pdf_url")}
                            for item in issuers],
        "universe_status": "REGISTERED_ISSUERS_ONLY_NOT_FULL_SGX",
        "schema_version": "value_hunter_sgx_v28",
        "generated_at_utc": now.isoformat(),
        "records": records,
        "ranking": [record for record in records if record["ranking_eligible"]],
        "excluded": [{"symbol": record["symbol"], "reasons": record["exclusion_reasons"]} for record in records if not record["ranking_eligible"]],
        "ranking_eligible_count": sum(record["ranking_eligible"] for record in records),
        "note": "Cross-document checks on issuer disclosures do not establish independent financial verification.",
    }


def write(result, output):
    folder = Path(output)
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "comparison_v28.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    fields = ["symbol", "fiscal_year", "revenue_growth_pct", "operating_margin_pct", "equity_ratio_pct",
              "price_sgd", "market_cap_sgd", "per_reference", "pbr_reference_unverified",
              "ranking_eligible", "exclusion_reasons"]
    with (folder / "comparison_v28.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for record in result["records"]:
            writer.writerow({key: ";".join(record[key]) if key == "exclusion_reasons" else record.get(key) for key in fields})
    def show(val):
        return "—" if val is None else str(val)
    lines = [
        "# VALUE HUNTER AI / SGX v28",
        "",
        "※ 参考値。独立検証が完了していない銘柄を投資ランキングには採用しない。",
        "",
        "| 銘柄 | 株価 SGD | 時価総額 SGD | PER参考 | PBR参考（未検証） | 判定 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for record in result["records"]:
        lines.append("| {} | {} | {} | {} | {} | {} |".format(
            record["symbol"], show(record["price_sgd"]), show(record["market_cap_sgd"]),
            show(record["per_reference"]), show(record["pbr_reference_unverified"]),
            "採用" if record["ranking_eligible"] else "除外"))
    lines.append("")
    for record in result["records"]:
        lines.append("**{}：** {}".format(record["symbol"], ", ".join(record["exclusion_reasons"]) or "除外なし"))
    lines.append("\nランキング対象：{}社".format(result["ranking_eligible_count"]))
    (folder / "summary_v28.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--financials", required=True)
    parser.add_argument("--valuation", required=True)
    parser.add_argument("--audit", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--universe", help="Validated SGX issuer registry")
    args = parser.parse_args()
    load = lambda path: json.loads(Path(path).read_text(encoding="utf-8"))
    result = compare(load(args.financials), load(args.valuation), load(args.audit),
                     universe=load(args.universe) if args.universe else None)
    write(result, args.output)
    print(json.dumps({"ranking_eligible_count": result["ranking_eligible_count"], "excluded": result["excluded"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()

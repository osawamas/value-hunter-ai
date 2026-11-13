"""Publish a conservative, schema-checked JSON feed for a static SGX dashboard.

Only GitHub Actions should replace the published snapshot after the complete
pipeline succeeds; no random/demo financial numbers are emitted.
"""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

SYMBOLS = ("S68", "G13", "S20")
NAMES = {
    "S68": "Singapore Exchange Limited",
    "G13": "Genting Singapore Limited",
    "S20": "The Straits Trading Company Limited",
}
ALLOWED_KEYS = {
    "symbol", "fiscal_year", "revenue_sgd_thousands",
    "revenue_growth_pct", "operating_margin_pct", "equity_ratio_pct",
    "assets_sgd_thousands", "liabilities_sgd_thousands",
    "equity_sgd_thousands", "balance_difference_sgd_thousands",
    "balance_source_status", "balance_source_page",
    "parent_equity_sgd_thousands", "parent_equity_status",
    "parent_equity_source_url",
    "attributable_profit_sgd_thousands", "price_sgd",
    "shares_outstanding", "market_cap_sgd", "per_reference",
    "pbr_reference_unverified", "pbr_verified", "financial_source_url",
    "financial_source_kind", "financial_pdf_sha256", "audit_source_url",
    "audit_pdf_sha256", "audit_reference_type", "audit_pages_by_metric",
    "shares_verification_status", "shares_count_basis",
    "shares_pdf_sha256", "gross_issued_shares", "treasury_shares", "quote_source_type",
    "quote_url", "quote_timestamp_utc",
    "shares_source_url", "shares_as_of_date", "audit_states",
    "ranking_eligible", "ranking_score", "exclusion_reasons",
}
PUBLIC_KEYS = (
    "fiscal_year", "revenue_sgd_thousands", "revenue_growth_pct",
    "operating_margin_pct", "equity_ratio_pct",
    "assets_sgd_thousands", "liabilities_sgd_thousands",
    "equity_sgd_thousands", "balance_difference_sgd_thousands",
    "balance_source_status", "balance_source_page",
    "parent_equity_sgd_thousands", "parent_equity_status",
    "parent_equity_source_url",
    "attributable_profit_sgd_thousands", "price_sgd",
    "shares_outstanding", "market_cap_sgd", "per_reference",
    "pbr_reference_unverified", "pbr_verified", "financial_source_url",
    "financial_source_kind", "financial_pdf_sha256", "audit_source_url",
    "audit_pdf_sha256", "audit_reference_type", "audit_pages_by_metric",
    "shares_verification_status", "shares_count_basis", "quote_source_type",
    "quote_url", "quote_timestamp_utc",
    "shares_source_url", "shares_as_of_date", "audit_states",
    "ranking_eligible", "ranking_score", "exclusion_reasons",
)


def https_url(value):
    if not isinstance(value, str):
        return None
    return value if value.startswith("https://") and len(value) <= 2048 else None


def build(source, now=None):
    if source.get("schema_version") != "value_hunter_sgx_v28":
        raise ValueError("Unsupported financial comparison schema")
    entries = source.get("records")
    if not isinstance(entries, list):
        raise ValueError("No records array")
    declared = source.get("issuer_universe")
    if declared is None:
        symbols = list(SYMBOLS)
        names = NAMES
    else:
        if not isinstance(declared, list) or not declared:
            raise ValueError("Invalid declared universe")
        names = {}
        for issuer in declared:
            if not isinstance(issuer, dict):
                raise ValueError("Bad universe registration")
            symbol, name, url = issuer.get("symbol"), issuer.get("issuer"), issuer.get("financial_pdf_url")
            if not isinstance(symbol, str) or not symbol.isalnum() or len(symbol) > 8 or symbol in names:
                raise ValueError("Duplicate/invalid universe symbol")
            if not isinstance(name, str) or not name.strip():
                raise ValueError("Issuer name missing")
            if not https_url(url):
                raise ValueError("Unproven issuer document URL")
            names[symbol] = name
        symbols = list(names)
    by_symbol = {}
    for item in entries:
        if not isinstance(item, dict) or item.get("symbol") not in symbols:
            raise ValueError("Invalid symbol record")
        symbol = item["symbol"]
        if symbol in by_symbol:
            raise ValueError("Duplicate symbol record")
        by_symbol[symbol] = item
    if set(by_symbol) != set(symbols):
        raise ValueError("Incomplete declared issuer snapshot")
    records = []
    for symbol in symbols:
        item = by_symbol[symbol]
        if item.get("ranking_eligible") is not False:
            # v28 is not yet independent verification; never silently publish
            # a ranking from a newer/incompatible producer.
            raise ValueError("Unexpected ranking eligibility")
        reasons = item.get("exclusion_reasons")
        if not isinstance(reasons, list) or not reasons or any(not isinstance(x, str) for x in reasons):
            raise ValueError("Missing exclusion evidence")
        row = {"symbol": symbol, "issuer": names[symbol]}
        for key in PUBLIC_KEYS:
            if key in ("financial_source_url", "audit_source_url", "quote_url", "shares_source_url", "parent_equity_source_url"):
                row[key] = https_url(item.get(key))
            elif key == "ranking_eligible":
                row[key] = False
            elif key == "exclusion_reasons":
                row[key] = reasons[:50]
            else:
                row[key] = item.get(key)
        row["data_state"] = "PARTIAL_UNVERIFIED"
        records.append(row)
    return {
        "schema_version": "value_hunter_web_v29",
        "updated_at_utc": (now or datetime.now(timezone.utc)).isoformat(),
        "input_generated_at_utc": source.get("generated_at_utc"),
        "source_type": "GITHUB_ACTIONS_PDF_AND_UNOFFICIAL_MARKET_FEED",
        "ranking_eligible_count": 0,
        "ranking_enabled": False,
        "currency": "SGD",
        "financial_unit": "SGD_thousands",
        "coverage": {"listed_universe": "SGX", "tested_symbols": list(symbols),
                     "registered_count": len(symbols), "all_sgx_listed": False},
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.source).read_text(encoding="utf-8"))
    result = build(source)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Published {len(result['records'])} records; ranking eligible: 0")


if __name__ == "__main__":
    main()

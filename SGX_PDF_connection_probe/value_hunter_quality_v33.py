"""v33 publication safety gate for VALUE HUNTER AI dashboard snapshots.

Detect quote/share age and arithmetic inconsistencies before publishing.
Source prices and official-source references remain in the feed, but unsafe
derived valuations are suppressed, and evidence is retained as quality flags.
"""
import argparse
import json
import math
from datetime import datetime, date, timezone
from pathlib import Path

REQUIRED_SCHEMA = "value_hunter_web_v29"
QUOTE_MAX_DAYS = 7
SHARES_MAX_DAYS = 180
CURRENCY = "SGD"


def numeric(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def timestamp(value):
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if result.tzinfo is None:
            return None
        return result.astimezone(timezone.utc)
    except ValueError:
        return None


def reference_date(value):
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def near(actual, expected, tolerance):
    return numeric(actual) and numeric(expected) and abs(actual - expected) <= max(abs(expected) * tolerance, 0.02)


def audit_record(record, now):
    record = dict(record)
    flags = []
    def add(code):
        if code not in flags:
            flags.append(code)

    price = record.get("price_sgd")
    shares = record.get("shares_outstanding")
    cap = record.get("market_cap_sgd")
    profit = record.get("attributable_profit_sgd_thousands")
    per = record.get("per_reference")
    pbr = record.get("pbr_reference_unverified")
    quote_time = timestamp(record.get("quote_timestamp_utc"))
    share_time = reference_date(record.get("shares_as_of_date"))
    if not numeric(price) or price <= 0:
        add("QUOTE_NOT_AVAILABLE")
    if quote_time is None:
        add("QUOTE_TIMESTAMP_MISSING")
    else:
        age_days = (now - quote_time).total_seconds() / 86400
        if age_days > QUOTE_MAX_DAYS:
            add("QUOTE_STALE")
        elif age_days < -1:
            add("QUOTE_DATE_IN_FUTURE")
    if not numeric(shares) or shares <= 0:
        add("SHARES_NOT_AVAILABLE")
    if share_time is None:
        add("SHARES_DATE_MISSING")
    else:
        share_age = (now.date() - share_time).days
        if share_age > SHARES_MAX_DAYS:
            add("SHARES_STALE")
        elif share_age < -1:
            add("SHARES_DATE_IN_FUTURE")
    gross = record.get("gross_issued_shares")
    treasury = record.get("treasury_shares")
    shares_hash = record.get("shares_pdf_sha256")
    share_evidence_present = gross is not None or treasury is not None or shares_hash is not None
    shares_reconciled = True
    if share_evidence_present:
        shares_reconciled = (
            all(isinstance(x, int) and not isinstance(x, bool)
                for x in (gross, treasury, shares))
            and gross > 0 and 0 <= treasury < gross
            and gross - treasury == shares
            and record.get("shares_count_basis") == "issued_excluding_treasury"
        )
        if not shares_reconciled:
            add("TREASURY_SHARE_ARITHMETIC_OR_BASIS_MISMATCH")
        if shares_hash is not None and (
                not isinstance(shares_hash, str)
                or len(shares_hash) != 64
                or any(ch not in "0123456789abcdef" for ch in shares_hash.lower())):
            add("SHARE_SOURCE_PDF_SHA256_INVALID")
            shares_reconciled = False
    if record.get("ranking_eligible") is not False:
        raise ValueError("Unexpected ranking eligibility")
    if not isinstance(record.get("exclusion_reasons"), list) or not record["exclusion_reasons"]:
        raise ValueError("Missing explicit exclusion reasons")

    cap_valid = (
        numeric(price) and price > 0 and numeric(shares) and shares > 0
        and shares_reconciled and numeric(cap) and cap >= 0 and near(cap, price * shares, 0.005)
    )
    if numeric(cap) and not cap_valid:
        if shares_reconciled:
            add("MARKET_CAP_ARITHMETIC_MISMATCH")
        record["market_cap_sgd"] = None
        cap = None
    if per is not None:
        if not cap_valid or not numeric(profit) or profit <= 0 or not near(per, cap / (profit * 1000), 0.01):
            add("PER_ARITHMETIC_MISMATCH_OR_INVALID")
            record["per_reference"] = None
    if pbr is not None:
        owner_equity = record.get("parent_equity_sgd_thousands")
        if (not cap_valid or not numeric(pbr) or pbr <= 0
                or not numeric(owner_equity) or owner_equity <= 0
                or not near(pbr, cap / (owner_equity * 1000), 0.01)):
            add("PBR_DENOMINATOR_MISSING_OR_ARITHMETIC_MISMATCH")
            record["pbr_reference_unverified"] = None
    if record.get("pbr_verified") is not None and record.get("ranking_eligible") is False:
        # v29 is an unverified research feed: suppress a verified-label field
        # until there is a separate, explicit audited validation schema.
        add("VERIFIED_PBR_LABEL_UNSUPPORTED")
        record["pbr_verified"] = None
    for code in flags:
        if code not in record["exclusion_reasons"]:
            record["exclusion_reasons"].append(code)
    record["quality_flags"] = flags
    record["quote_freshness"] = (
        "MISSING" if "QUOTE_NOT_AVAILABLE" in flags or "QUOTE_TIMESTAMP_MISSING" in flags
        else "STALE" if any(x in flags for x in ("QUOTE_STALE", "QUOTE_DATE_IN_FUTURE"))
        else "RECENT"
    )
    record["share_freshness"] = (
        "MISSING" if "SHARES_NOT_AVAILABLE" in flags or "SHARES_DATE_MISSING" in flags
        else "STALE" if any(x in flags for x in ("SHARES_STALE", "SHARES_DATE_IN_FUTURE"))
        else "RECENT"
    )
    return record


def inspect_feed(feed, now=None):
    now = now or datetime.now(timezone.utc)
    if feed.get("schema_version") != REQUIRED_SCHEMA:
        raise ValueError("Unsupported public data schema")
    if feed.get("ranking_enabled") is not False or feed.get("ranking_eligible_count") != 0:
        raise ValueError("Ranking unexpectedly enabled")
    raw = feed.get("records")
    if not isinstance(raw, list) or not raw:
        raise ValueError("No issuer records")
    symbols = [r.get("symbol") for r in raw if isinstance(r, dict)]
    if len(symbols) != len(raw) or len(set(symbols)) != len(symbols):
        raise ValueError("Duplicate or invalid issuer entries")
    updated = timestamp(feed.get("updated_at_utc"))
    if updated is None:
        raise ValueError("Missing feed generation timestamp")
    checked = [audit_record(r, now) for r in raw]
    copy = dict(feed)
    copy["records"] = checked
    copy["quality_checked_at_utc"] = now.isoformat()
    copy["quality_schema_version"] = "value_hunter_quality_v33"
    copy["ranking_eligible_count"] = 0
    copy["ranking_enabled"] = False
    copy["quality_counts"] = {
        "issuers": len(checked),
        "quote_stale": sum(r["quote_freshness"] == "STALE" for r in checked),
        "quote_missing": sum(r["quote_freshness"] == "MISSING" for r in checked),
        "shares_stale": sum(r["share_freshness"] == "STALE" for r in checked),
        "arithmetically_inconsistent": sum(any("MISMATCH" in flag for flag in r["quality_flags"]) for r in checked),
        "treasury_share_inconsistent": sum("TREASURY_SHARE_ARITHMETIC_OR_BASIS_MISMATCH" in r["quality_flags"] for r in checked),
        "ranking_eligible": 0,
    }
    return copy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    checked = inspect_feed(source)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(checked, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(checked["quality_counts"], ensure_ascii=False))


if __name__ == "__main__":
    main()

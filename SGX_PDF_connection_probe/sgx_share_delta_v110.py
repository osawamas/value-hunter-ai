"""v110: reconcile published S63 shares with a newer official dated SGX buyback snapshot.

Diagnostic only. Never reprice a record, rewrite a share count or imply
that a later buyback snapshot is automatically the current market denominator.
"""
import argparse
import hashlib
import json
from datetime import date, datetime
from pathlib import Path

EXPECTED_SOURCE = "SGX_PRIMARY_BUYBACK_13NOV2026_HISTORICAL_SNAPSHOT"
EXPECTED_SYMBOL = "S63"
EXPECTED_REF = "SG261113OTHRPXGV"
EXPECTED_ISIN = "SG1F60858221"

def reconcile(feed, evidence):
    if not isinstance(feed, dict) or feed.get("schema_version") != "value_hunter_web_v29":
        raise ValueError("Unexpected financial feed")
    if feed.get("ranking_eligible_count") != 0 or feed.get("ranking_enabled") is not False:
        raise ValueError("Ranking cannot already be enabled")
    records = feed.get("records", [])
    matches = [r for r in records if isinstance(r, dict) and r.get("symbol") == EXPECTED_SYMBOL]
    if len(matches) != 1:
        raise ValueError("Expected exactly one S63 published record")
    item = matches[0]
    if not isinstance(evidence, dict) or evidence.get("schema_version") != "sgx-s63-buyback-original-v109":
        raise ValueError("Unexpected SGX evidence schema")
    snapshot = evidence.get("record")
    if evidence.get("status") != EXPECTED_SOURCE or not isinstance(snapshot, dict):
        raise ValueError("Unverified SGX evidence cannot be used")
    if (snapshot.get("status") != EXPECTED_SOURCE or
        snapshot.get("reference") != EXPECTED_REF or
        snapshot.get("symbol") != EXPECTED_SYMBOL or
        snapshot.get("isin") != EXPECTED_ISIN or
        snapshot.get("purchase_date") != "2026-11-13" or
        snapshot.get("source_url") != evidence.get("source_url") or
        snapshot.get("dated_historical_snapshot_only") is not True or
        snapshot.get("allow_market_cap_or_per_pbr") is not False or
        snapshot.get("ranking_eligible") is not False):
        raise ValueError("Official source provenance or status mismatch")
    if not isinstance(snapshot.get("source_sha256"), str) or len(snapshot["source_sha256"]) != 64:
        raise ValueError("Missing original-source content hash")
    for f in ("shares_purchased","shares_cancelled","purchased_as_treasury",
              "issued_excluding_treasury_after_purchase","treasury_shares_after_purchase"):
        if type(snapshot.get(f)) is not int or snapshot[f] < 0:
            raise ValueError("Invalid SGX share counts")
    if (snapshot["shares_purchased"] != snapshot["shares_cancelled"] + snapshot["purchased_as_treasury"] or
        snapshot["shares_purchased"] != 500000 or snapshot["shares_cancelled"] != 0 or
        snapshot["issued_excluding_treasury_after_purchase"] != 3115847115 or
        snapshot["treasury_shares_after_purchase"] != 6648082):
        raise ValueError("SGX share quantities do not match verified evidence")
    older = item.get("shares_outstanding")
    if type(older) is not int or older <= 0 or item.get("shares_count_basis") != "issued_excluding_treasury":
        raise ValueError("Older share count basis unknown")
    old_date = date.fromisoformat(item["shares_as_of_date"])
    new_date = date.fromisoformat(snapshot["purchase_date"])
    if new_date <= old_date:
        raise ValueError("SGX snapshot is not newer than published reference")
    latest_count = snapshot["issued_excluding_treasury_after_purchase"]
    difference = latest_count - older
    return {
        "schema_version": "sgx-share-snapshot-difference-v110",
        "symbol": EXPECTED_SYMBOL,
        "published_financial_record_as_of_date": str(old_date),
        "published_financial_shares": older,
        "new_sgx_primary_snapshot_date": str(new_date),
        "new_sgx_primary_issued_ex_treasury": latest_count,
        "new_sgx_primary_treasury_shares": snapshot["treasury_shares_after_purchase"],
        "new_sgx_primary_buyback_shares": snapshot["shares_purchased"],
        "new_sgx_primary_source_url": snapshot["source_url"],
        "new_sgx_primary_announcement_reference": EXPECTED_REF,
        "new_sgx_primary_html_sha256": snapshot["source_sha256"],
        "new_minus_published_shares": difference,
        "relative_change_pct": round(100*difference/older,6),
        "published_reference_is_older": True,
        "price_timestamp_not_independently_reconciled": True,
        "current_shares_verified": False,
        "price_or_per_pbr_recomputed": False,
        "financial_feed_modified": False,
        "warning": "Existing reference market capitalization and PER may use an older share denominator; do not treat as independently verified valuation",
        "ranking_eligible": False,
    }

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--feed",required=True)
    parser.add_argument("--sgx-evidence",required=True)
    parser.add_argument("--output",required=True)
    args=parser.parse_args()
    feed_path=Path(args.feed); evidence_path=Path(args.sgx_evidence)
    before=hashlib.sha256(feed_path.read_bytes()).hexdigest()
    result=reconcile(json.loads(feed_path.read_text(encoding="utf-8")),
                     json.loads(evidence_path.read_text(encoding="utf-8")))
    if hashlib.sha256(feed_path.read_bytes()).hexdigest()!=before:
        raise ValueError("Financial feed unexpectedly modified")
    dest=Path(args.output)
    dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("S63 older/newer shares:",result["published_financial_shares"],
          result["new_sgx_primary_issued_ex_treasury"],"delta:",result["new_minus_published_shares"])

if __name__=="__main__":
    main()

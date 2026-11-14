"""v117: factual, fail-closed ranking-readiness blockers for seven registered SGX issuers.

Only audits published evidence; cannot grant ranking eligibility or certify
independence. Banks use banking-specific conditions, never industrial blanks.
"""
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

INDUSTRIAL = ("S68", "G13", "S20", "S63")
BANKS = ("D05", "O39", "U11")
SYMBOLS = INDUSTRIAL + BANKS

def audit(feed, snapshot=None):
    if not isinstance(feed, dict) or feed.get("schema_version")!="value_hunter_web_v29":
        raise ValueError("Incorrect published feed")
    if feed.get("ranking_eligible_count")!=0 or feed.get("ranking_enabled") is not False:
        raise ValueError("Unsafe or inconsistent rank state")
    rows=feed.get("records")
    if not isinstance(rows,list) or len(rows)!=7 or {r.get("symbol") for r in rows}!=set(SYMBOLS):
        raise ValueError("Expected exactly seven distinct registered issuers")
    by={r["symbol"]:r for r in rows}
    result=[]
    for symbol in SYMBOLS:
        x=by[symbol]
        if x.get("ranking_eligible") is not False or x.get("ranking_score") is not None:
            raise ValueError("Already promoted ranking")
        bank=symbol in BANKS
        signals={}
        if bank:
            evidence=x.get("bank_financial_state") or {}
            signals["issuer_bank_financials_parsed"]=(
                evidence.get("status")=="AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED"
                and evidence.get("banking_metrics_parsed") is True
                and bool(evidence.get("pdf_sha256")))
            signals["bank_independent_financial_check"]=evidence.get("third_party_numerical_verification") is True
            signals["current_bank_quote_verified"]=evidence.get("current_quote_verified") is True and x.get("price_sgd") is not None
            signals["current_bank_shares_verified"]=evidence.get("current_share_count_verified") is True and x.get("shares_outstanding") is not None
            # Do not use industrial revenue, operating margin, or bank "generic" exclusion counts.
        else:
            signals["issuer_primary_financial_pdf"]=bool(x.get("financial_pdf_sha256") and x.get("financial_source_url"))
            states=x.get("audit_states") or {}
            signals["issuer_two_document_revenue_crosscheck"]=states.get("revenue")=="MATCH_LIVE_SECOND_ISSUER_DOCUMENT"
            signals["issuer_two_document_profit_crosscheck"]=states.get("attributable_profit")=="MATCH_LIVE_SECOND_ISSUER_DOCUMENT"
            signals["parent_equity_independently_checked"]=False
            signals["financials_independently_checked"]=False
            signals["quote_independently_exchange_verified"]=False
            signals["updated_treasury_adjusted_shares_independently_checked"]=False
            signals["same_date_quote_shares_compatible"]=False
            signals["valid_earnings_for_positive_per"]=(
                isinstance(x.get("attributable_profit_sgd_thousands"),(int,float))
                and x["attributable_profit_sgd_thousands"]>0)
        # A sourced, dated snapshot, rather than a promotional financial number.
        latest_primary = (snapshot or {}).get("record") if symbol=="S63" else None
        signals["dated_primary_buyback_snapshot_available"] = bool(
            symbol=="S63" and isinstance(latest_primary,dict)
            and latest_primary.get("symbol")=="S63"
            and latest_primary.get("reference")=="SG261113OTHRPXGV"
            and latest_primary.get("purchase_date")=="2026-11-13"
            and latest_primary.get("dated_historical_snapshot_only") is True
            and latest_primary.get("ranking_eligible") is False)
        pending=[key for key,value in signals.items()
                 if not value and key!="dated_primary_buyback_snapshot_available"]
        result.append({
            "symbol":symbol,
            "sector_model":"BANKING" if bank else "INDUSTRIAL",
            "published_issuer_financial_state":x.get("data_state"),
            "original_ranking_exclusion_reasons":x.get("exclusion_reasons"),
            "observed_evidence_signals":signals,
            "remaining_verification_tasks":pending,
            "issuer_document_checks_are_not_third_party_independence":True,
            "eligible_for_ranking":False,
            "estimated_completion_percentage":None,
            "market_cap_or_per_pbr_promoted":False
        })
    return {
        "schema_version":"sgx-ranking-readiness-evidence-v117",
        "generated_at_utc":datetime.now(timezone.utc).isoformat(),
        "published_feed_updated_at_utc":feed.get("updated_at_utc"),
        "registered_issuers":len(result),
        "third_party_candidate_count_is_not_registered_count":True,
        "issuer_source_evidence_not_independent_numerical_verification":True,
        "safe_candidate_first_industrial_order":["G13","S63","S68","S20"],
        "priority_reason":"G13 has three issuer-to-issuer financial matches; S63 has three and newer dated official share snapshot. This is work ordering, not investment merit.",
        "ranking_eligible_count":0,
        "all_issuers_still_blocked":True,
        "changes_to_financial_feed":False,
        "records":result
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--feed",required=True)
    p.add_argument("--s63-buyback",required=True)
    p.add_argument("--output",required=True)
    args=p.parse_args()
    path=Path(args.feed)
    old_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    result=audit(json.loads(path.read_text()),
                 json.loads(Path(args.s63_buyback).read_text()))
    if old_hash != hashlib.sha256(path.read_bytes()).hexdigest():
        raise ValueError("Financial feed was unexpectedly modified")
    output=Path(args.output)
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("Seven issuers audited, eligible",result["ranking_eligible_count"])
if __name__=="__main__":
    main()

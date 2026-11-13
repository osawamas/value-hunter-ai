"""v92: explain, but do not verify, pending UOB 13-Nov buyback.
Checks last available PRIMARY 12-Nov SGX Section D and newer SECONDARY
13-Nov SGXNet syndication for arithmetic consistency. This is neither
primary verification of 13-Nov nor a current shares/quote claim.
"""
import argparse, json, re
from pathlib import Path

STATUS="SECONDARY_NOV13_ARITHMETICALLY_CONSISTENT_PRIMARY_NOT_VERIFIED"
NET12=1646711591
TREASURY12=14548000
NET13=1646677591
REF13="SG261113OTHRHOAF"
DATE12="2026-11-12"
DATE13="2026-11-13"
PURCHASED13=34000
CANCELLED13=34000
HELD13=0

def attach(feed):
    if feed.get("schema_version")!="value_hunter_web_v29":
        raise ValueError("unexpected feed schema")
    rows=[x for x in feed.get("records",[]) if x.get("symbol")=="U11"]
    if len(rows)!=1:
        raise ValueError("UOB missing/duplicated")
    row=rows[0]
    official=row.get("bank_primary_recent_share_event") or {}
    chain=row.get("bank_primary_three_day_chain") or {}
    lead=row.get("bank_share_discovery") or {}
    days=chain.get("records") or []
    if (official.get("status")!="ORIGINAL_SGX_DAILY_BUYBACK_2026_11_12_RECONCILED"
        or official.get("as_of_date")!=DATE12
        or official.get("issued_excluding_treasury")!=NET12
        or official.get("treasury_shares")!=TREASURY12
        or not re.fullmatch(r"[0-9a-f]{64}",official.get("primary_html_sha256",""))
        or chain.get("status")!="ORIGINAL_SGX_U11_THREE_DAY_BUYBACK_CHAIN_2026_11_10_TO_12_VERIFIED"
        or len(days)!=3 or days[-1].get("as_of_date")!=DATE12
        or days[-1].get("issued_excluding_treasury")!=NET12
        or days[-1].get("official_html_sha256")!=official["primary_html_sha256"]):
        raise ValueError("prior primary SGX UOB history inconsistent")
    if (lead.get("status")!="SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED"
        or lead.get("claim_source_class")!="SECONDARY_SGXNET_SYNDICATION"
        or lead.get("event_date")!=DATE13
        or lead.get("sgx_announcement_reference")!=REF13
        or lead.get("candidate_shares_excluding_treasury")!=NET13
        or lead.get("candidate_treasury_shares")!=TREASURY12
        or lead.get("primary_sgx_announcement_url") is not None
        or lead.get("primary_document_sha256") is not None
        or lead.get("primary_issuer_count_reconciled") is not False):
        raise ValueError("later UOB candidate unexpectedly marked verified")
    if (row.get("ranking_eligible") is not False
        or any(row.get(k) is not None for k in
            ("shares_outstanding","price_sgd","market_cap_sgd",
             "per_reference","pbr_reference_unverified","pbr_verified"))):
        raise ValueError("unverified shares cannot be market priced")
    if (type(NET12) is not int or type(NET13) is not int
        or NET12-NET13!=PURCHASED13
        or PURCHASED13!=CANCELLED13+HELD13
        or lead["candidate_treasury_shares"]!=official["treasury_shares"]):
        raise ValueError("secondary bank notice cannot be reconciled")
    result=json.loads(json.dumps(feed))
    dest=next(x for x in result["records"] if x["symbol"]=="U11")
    dest["bank_pending_buyback_consistency"]={
        "status":STATUS,
        "primary_as_of_date":DATE12,
        "secondary_as_of_date":DATE13,
        "primary_after_purchase_shares":NET12,
        "secondary_claim_after_purchase_shares":NET13,
        "implied_share_decrease":NET12-NET13,
        "secondary_claim_purchased_shares":PURCHASED13,
        "secondary_claim_cancelled_shares":CANCELLED13,
        "secondary_claim_held_as_treasury_shares":HELD13,
        "secondary_claim_treasury_balance":TREASURY12,
        "secondary_sgxnet_reference":REF13,
        "secondary_source_url":lead["secondary_source_url"],
        "primary_source_url":official["primary_source_url"],
        "secondary_primary_url":None,
        "secondary_primary_hash":None,
        "check_scope":"ARITHMETIC_ONLY_NOT_ORIGINAL_ISSUER_VERIFICATION",
        "later_events_not_ruled_out":True,
        "latest_current_shares_verified":False,
        "current_share_count_usable":False,
        "market_cap_per_pbr_usable":False,
        "ranking_eligible":False
    }
    return result

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--input",required=True)
    p.add_argument("--output",required=True)
    a=p.parse_args()
    result=attach(json.loads(Path(a.input).read_text(encoding="utf-8")))
    dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
    dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("UOB later syndicated 13-Nov claim arithmetic consistent; still unverified")

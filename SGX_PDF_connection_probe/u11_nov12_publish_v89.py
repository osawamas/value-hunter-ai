"""v89: publish UOB 12-Nov-2026 first-party SGX shares as dated verified evidence.

Preserve Sep-07 primary record, Sep-30 secondary event, and Nov-13
secondary event. Never treat the latest *found* official document as proof
of today's share count. No quote/market cap/PER/PBR/ranking promotion.
"""
import argparse,json,re
from pathlib import Path
from u11_nov12_primary_v88 import URL,REF,DATE

STATUS="SGX_ORIGINAL_U11_2026_11_12_BUYBACK_RECONCILED"

def attach(feed,proof):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Wrong SGX feed")
 matches=[r for r in feed.get("records",[]) if r.get("symbol")=="U11"]
 if len(matches)!=1:raise ValueError("Missing/duplicate UOB")
 row=matches[0]
 event=proof.get("record") or {}
 if (proof.get("symbol")!="U11"
     or proof.get("status")!=STATUS
     or proof.get("source_url")!=URL
     or event.get("symbol")!="U11"
     or event.get("status")!="DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY"
     or event.get("reference")!=REF or event.get("as_of_date")!=DATE
     or event.get("source_url")!=URL
     or not re.fullmatch("[a-f0-9]{64}",event.get("primary_sgx_page_sha256",""))
     or event.get("ranking_eligible") is not False
     or event.get("valuation_eligible") is not False
     or event.get("not_proof_of_latest") is not True):
  raise ValueError("UOB SGX Nov-12 original source identity failed")
 net,treasury,gross=(event.get(k) for k in (
   "issued_excluding_treasury","treasury_shares","issued_including_treasury_derived"))
 if (any(type(n) is not int for n in (net,treasury,gross))
     or (net,treasury,gross)!=(1646711591,14548000,1661259591)
     or net+treasury!=gross):
  raise ValueError("UOB Nov-12 original share count failed cross-foot")
 older=row.get("bank_primary_share_history") or {}
 if (older.get("status")!="ORIGINAL_SGX_DAILY_BUYBACK_2026_09_07_RECONCILED"
     or older.get("as_of_date","")>=DATE):
  raise ValueError("September primary issuer evidence missing")
 secondary=row.get("bank_share_discovery") or {}
 history=row.get("bank_share_discovery_history") or []
 if (secondary.get("status")!="SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED"
     or secondary.get("event_date")!="2026-11-13"
     or secondary.get("current_share_count_usable") is not False
     or len(history)!=1 or history[0].get("event_date")!="2026-09-30"):
  raise ValueError("November newer secondhand event or September history missing")
 if (row.get("ranking_eligible") is not False
     or any(row.get(k) is not None for k in (
       "price_sgd","shares_outstanding","market_cap_sgd",
       "per_reference","pbr_reference_unverified","pbr_verified"))):
  raise ValueError("UOB current trading data unexpectedly populated")
 out=json.loads(json.dumps(feed))
 target=next(r for r in out["records"] if r["symbol"]=="U11")
 target["bank_primary_recent_share_event"]={
   "status":"ORIGINAL_SGX_DAILY_BUYBACK_2026_11_12_RECONCILED",
   "as_of_date":DATE,"sgxnet_reference":REF,
   "issued_excluding_treasury":net,
   "treasury_shares":treasury,
   "gross_issued_derived":gross,
   "primary_source_url":URL,
   "primary_html_sha256":event["primary_sgx_page_sha256"],
   "historical_only":True,
   "later_2026_11_13_notification_primary_unverified":True,
   "not_proof_of_current_shares":True,
   "ranking_eligible":False,
 }
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--feed",required=True)
 p.add_argument("--source",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 result=attach(json.loads(Path(a.feed).read_text(encoding="utf-8")),
               json.loads(Path(a.source).read_text(encoding="utf-8")))
 target=Path(a.output);target.parent.mkdir(parents=True,exist_ok=True)
 target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("SGX UOB original 12-Nov-2026 dated share count published as past evidence only")

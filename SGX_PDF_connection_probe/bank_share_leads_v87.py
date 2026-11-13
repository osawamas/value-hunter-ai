"""v87: add 13-Nov-2026 UOB SGXNet syndication lead without replacing 30-Sep evidence.

The newer event is still SECONDARY, not an actual primary SGX page.
Do not infer shares as of today, calculate cumulative buybacks, or change
live shares, market capitalisation, PER, PBR, or ranking.
"""
import argparse,json,re
from pathlib import Path
from bank_share_leads_v83 import STATUS

NOV13={
  "status":STATUS,
  "event_type":"SHARE_BUYBACK_DAILY_NOTICE",
  "event_date":"2026-11-13",
  "published_date":"2026-11-13",
  "sgx_announcement_reference":"SG261113OTHRHOAF",
  "secondary_source_url":"https://classic.shareinvestor.com/news/news.html?nid=515671689&source=regional_sgxnet",
  "candidate_shares_excluding_treasury":1646677591,
  "candidate_treasury_shares":14548000,
  "source_excerpts_are_secondhand":True,
  "reason":"13-Nov SGXNet syndication has Section D but original links.sgx.com notice not yet verified",
  "primary_sgx_announcement_url":None,
  "primary_document_sha256":None,
  "primary_issuer_count_reconciled":False,
  "claim_source_class":"SECONDARY_SGXNET_SYNDICATION",
  "independent_verification":False,
  "current_share_count_usable":False,
  "market_cap_per_pbr_usable":False,
  "ranking_eligible":False,
  "discovered_event_not_proof_of_latest":True,
}

def update(feed):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Wrong SGX feed")
 bank=[r for r in feed.get("records",[]) if r.get("symbol")=="U11"]
 if len(bank)!=1:raise ValueError("UOB absent or duplicated")
 old=bank[0]
 previous=old.get("bank_share_discovery") or {}
 if (previous.get("status")!=STATUS
     or previous.get("event_date")!="2026-09-30"
     or previous.get("sgx_announcement_reference")!="SG260930OTHRNN9Y"
     or previous.get("candidate_shares_excluding_treasury")!=1647838591
     or previous.get("candidate_treasury_shares")!=14548000
     or previous.get("claim_source_class")!="SECONDARY_SGXNET_SYNDICATION"
     or previous.get("current_share_count_usable") is not False):
  raise ValueError("September UOB source lead was changed without verification")
 if (old.get("ranking_eligible") is not False
     or any(old.get(k) is not None for k in (
      "shares_outstanding","price_sgd","market_cap_sgd","per_reference",
      "pbr_reference_unverified","pbr_verified"))):
  raise ValueError("Secondary UOB leads must not be priced")
 if not re.fullmatch(r"SG\d{6}OTHR[A-Z0-9]+",NOV13["sgx_announcement_reference"]):
  raise ValueError("Invalid latest SGXNet reference")
 if previous["event_date"]>=NOV13["event_date"]:
  raise ValueError("New event must be more recent than preserved lead")
 out=json.loads(json.dumps(feed))
 target=next(r for r in out["records"] if r["symbol"]=="U11")
 target["bank_share_discovery_history"]=[previous]
 target["bank_share_discovery"]=json.loads(json.dumps(NOV13))
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--input",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 data=json.loads(Path(a.input).read_text(encoding="utf-8"))
 out=update(data)
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("UOB Nov-13 SGXNet syndication saved as unverified lead; Sep-30 history preserved")

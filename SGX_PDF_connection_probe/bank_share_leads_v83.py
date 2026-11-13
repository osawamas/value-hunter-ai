"""v83: SGX bank share-event discovery leads without numeric valuation promotion.

Sources below include SGXNet-derived secondary syndication. They are leads,
NOT a verified primary SGX filing. Capture historical UOB September count
only as an unverified secondary claim; OCBC Nov treasury movement remains
an unresolved event. No assumption that these are the latest disclosures.
"""
import argparse,json,re
from pathlib import Path

LEADS={
 "U11":{
  "event_type":"SHARE_BUYBACK_DAILY_NOTICE",
  "event_date":"2026-09-30",
  "published_date":"2026-09-30",
  "sgx_announcement_reference":"SG260930OTHRNN9Y",
  "secondary_source_url":"https://a.siasset.com/news/news.html?nid=515665417&source=regional_sgxnet",
  "candidate_shares_excluding_treasury":1647838591,
  "candidate_treasury_shares":14548000,
  "source_excerpts_are_secondhand":True,
  "reason":"secondary SGXNet syndication displays post-purchase Section D shares; no primary filing URL validated",
 },
 "O39":{
  "event_type":"USE_OF_TREASURY_SHARES",
  "event_date":"2026-11-12",
  "published_date":"2026-11-12",
  "sgx_announcement_reference":"SG261112OTHRXH64",
  "secondary_source_url":"https://classic.shareinvestor.com/news/news.html?nid=515671461&source=sg_sgxnet",
  "candidate_shares_excluding_treasury":None,
  "candidate_treasury_shares":None,
  "source_excerpts_are_secondhand":True,
  "reason":"12-Nov treasury transfer notice identified but official attachment figures not extracted",
 },
}
STATUS="SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED"

def annotate(feed):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Public SGX schema not accepted")
 output=json.loads(json.dumps(feed))
 for row in output.get("records",[]):
  symbol=row.get("symbol")
  if symbol not in LEADS:continue
  lead=LEADS[symbol]
  if (row.get("ranking_eligible") is not False
      or any(row.get(k) is not None for k in (
       "shares_outstanding","price_sgd","market_cap_sgd",
       "per_reference","pbr_reference_unverified","pbr_verified"))):
   raise ValueError("Secondary evidence cannot override priced/eligible bank")
  if row.get("bank_financial_state",{}).get("status")!="AUDITED_ISSUER_GROUP_BANK_FINANCIALS_EXTRACTED":
   raise ValueError("Unknown bank source state")
  if row.get("bank_historical_shares",{}).get("as_of_date","")>lead["event_date"]:
   raise ValueError("Candidate lead older than verified historical share event")
  if not re.fullmatch(r"SG\d{6}OTHR[A-Z0-9]+",lead["sgx_announcement_reference"]):
   raise ValueError("SGXNet reference pattern invalid")
  if not lead["secondary_source_url"].startswith("https://"):
   raise ValueError("Secondary lead URL invalid")
  if (lead["candidate_shares_excluding_treasury"] is not None
      or lead["candidate_treasury_shares"] is not None):
   outstanding,treasury=lead["candidate_shares_excluding_treasury"],lead["candidate_treasury_shares"]
   if any(type(x) is not int or x<0 for x in (outstanding,treasury)) or outstanding<=0:
    raise ValueError("Unverified stock count candidate invalid")
  row["bank_share_discovery"]={
   **lead,
   "status":STATUS,
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
 return output

if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--input",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 f=json.loads(Path(a.input).read_text(encoding="utf-8"))
 out=annotate(f)
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("Unverified bank share leads recorded:",[r["symbol"] for r in out["records"] if r.get("bank_share_discovery")])

"""v91: publish verified SGX UOB Nov-10..12 share buyback chain historically.

A verified consecutive three-day chain does not authenticate the 13-Nov
secondary claim and cannot provide today's issued shares, market cap or PBR.
Requires same source URLs, SHA256 content identities and audited 12-Nov entry.
"""
import argparse,json,re
from pathlib import Path
from u11_buyback_chain_v90 import NOTICES

STATUS="ORIGINAL_SGX_U11_THREE_DAY_BUYBACK_CHAIN_2026_11_10_TO_12_VERIFIED"
EXPECTED={"2026-11-10":1646779591,"2026-11-11":1646745591,"2026-11-12":1646711591}

def attach(feed,proof):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Unexpected SGX feed")
 rows=[r for r in feed.get("records",[]) if r.get("symbol")=="U11"]
 if len(rows)!=1 or proof.get("symbol")!="U11" or proof.get("status")!=STATUS:
  raise ValueError("UOB chain source not verified")
 result=proof.get("record") or {}
 if (result.get("status")!=STATUS or result.get("symbol")!="U11"
     or result.get("treasury_constant") is not True
     or result.get("consecutive_day_net_decrease")!=34000
     or result.get("latest_primary_in_chain")!="2026-11-12"
     or result.get("later_2026_11_13_claim_verified") is not False
     or result.get("not_proof_of_latest_as_of_today") is not True
     or result.get("current_market_cap_eligible") is not False
     or result.get("ranking_eligible") is not False):
  raise ValueError("SGX consecutive historical chain status inconsistent")
 records=result.get("records") or []
 if len(records)!=len(NOTICES):
  raise ValueError("SGX primary chain requires all three days")
 for r,(day,ref,url,net,treasury) in zip(records,NOTICES):
  if (r.get("status")!="DIRECT_SGX_BUYBACK_SECTION_D_PARSED_DIAGNOSTIC_ONLY"
     or r.get("symbol")!="U11" or r.get("reference")!=ref
     or r.get("source_url")!=url or r.get("as_of_date")!=day
     or r.get("issued_excluding_treasury")!=net
     or r.get("treasury_shares")!=treasury
     or r.get("issued_including_treasury_derived")!=net+treasury
     or r.get("valuation_eligible") is not False
     or r.get("not_proof_of_latest") is not True
     or not re.fullmatch("[a-f0-9]{64}",r.get("primary_sgx_page_sha256",""))):
   raise ValueError("UOB source URL/date/reference/amount for "+day+" failed")
 for a,b in zip(records,records[1:]):
  if (a["issued_excluding_treasury"]-b["issued_excluding_treasury"]!=34000
      or a["treasury_shares"]!=b["treasury_shares"]):
   raise ValueError("SGX day-on-day account changes invalid")
 row=rows[0]
 recent=row.get("bank_primary_recent_share_event") or {}
 if (recent.get("status")!="ORIGINAL_SGX_DAILY_BUYBACK_2026_11_12_RECONCILED"
     or recent.get("primary_html_sha256")!=records[-1]["primary_sgx_page_sha256"]
     or recent.get("issued_excluding_treasury")!=records[-1]["issued_excluding_treasury"]):
  raise ValueError("Existing 12-Nov primary SGX record differs from 3-day chain")
 newer=row.get("bank_share_discovery") or {}
 if (newer.get("status")!="SECONDARY_SGXNET_EVENT_LEAD_NOT_PRIMARY_VALIDATED"
     or newer.get("event_date")!="2026-11-13"
     or newer.get("current_share_count_usable") is not False):
  raise ValueError("13-Nov pending original source must remain separate")
 if (row.get("ranking_eligible") is not False
     or any(row.get(k) is not None for k in
       ("shares_outstanding","price_sgd","market_cap_sgd","per_reference",
        "pbr_reference_unverified","pbr_verified"))):
  raise ValueError("Market valuation/share promotion prohibited")
 out=json.loads(json.dumps(feed))
 target=next(x for x in out["records"] if x["symbol"]=="U11")
 target["bank_primary_three_day_chain"]={
   "status":STATUS,
   "period_start":"2026-11-10","period_end":"2026-11-12",
   "verified_original_source_count":3,
   "records":[{"as_of_date":r["as_of_date"],
               "reference":r["reference"],
               "issued_excluding_treasury":r["issued_excluding_treasury"],
               "treasury_shares":r["treasury_shares"],
               "official_source_url":r["source_url"],
               "official_html_sha256":r["primary_sgx_page_sha256"]} for r in records],
   "net_decrease_each_consecutive_day":34000,
   "2026_11_13_original_verified":False,
   "not_current_share_count":True,
   "market_cap_eligible":False,
   "ranking_eligible":False,
 }
 return out

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--feed",required=True)
 p.add_argument("--source",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 result=attach(json.loads(Path(a.feed).read_text(encoding="utf-8")),
               json.loads(Path(a.source).read_text(encoding="utf-8")))
 path=Path(a.output);path.parent.mkdir(parents=True,exist_ok=True)
 path.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("UOB 3-day primary share chain published as historical source evidence only")

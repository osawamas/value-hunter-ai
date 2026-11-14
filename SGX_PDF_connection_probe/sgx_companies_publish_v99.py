"""v99: safe publication of actual structured SGX THIRD-PARTY candidates.

Accept only a live JSON response parsed by v98. Publish separate, explicit
partial coverage inventory; NEVER append candidates to docs/data/latest.json
without issuer-level primary verification. Never label 49 providers as the
full SGX list, and never attach price/market-cap/financial fields.
"""
import argparse,hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path

STATUS="THIRD_PARTY_COMPANY_JSON_CANDIDATES_DIAGNOSTIC_ONLY"
CODE=re.compile(r"^[A-Z0-9]{1,6}$")
SHA=re.compile(r"^[0-9a-f]{64}$")

def publish(feed,discovery):
 if feed.get("schema_version")!="value_hunter_web_v29":
  raise ValueError("Input verified application schema invalid")
 existing=feed.get("records") or []
 verified=[x.get("symbol") for x in existing]
 if len(verified)!=7 or len(verified)!=len(set(verified)):
  raise ValueError("Expected existing 7 verified issuer records")
 if (discovery.get("status")!=STATUS or discovery.get("source_url")!="https://stocks.com.sg/api/v1/companies"
     or not SHA.fullmatch(discovery.get("source_response_sha256",""))
     or discovery.get("all_sgx_listings_verified") is not False
     or discovery.get("current_market_price_verified") is not False
     or discovery.get("ranking_eligible") is not False):
  raise ValueError("Source is not acceptable as partial third-party candidate index")
 candidates=discovery.get("companies") or []
 if (not isinstance(candidates,list) or len(candidates)<20 or len(candidates)>1200
     or discovery.get("accepted_candidates")!=len(candidates)
     or discovery.get("raw_rows_count",0)<len(candidates)):
  raise ValueError("Partial source coverage invalid")
 seen=set();rows=[]
 for item in candidates:
  symbol=item.get("symbol")
  name=item.get("display_name")
  if (not isinstance(symbol,str) or not CODE.fullmatch(symbol)
      or not isinstance(name,str) or len(name)<3 or symbol in seen):
   raise ValueError("Duplicate, invalid, or unnamed candidate SGX ticker")
  seen.add(symbol)
  rows.append({"symbol":symbol,"display_name":name,
               "source_verification":"THIRD_PARTY_CANDIDATE_NOT_EXCHANGE_VERIFIED",
               "financial_verification":False,"ranking_eligible":False})
 if rows!=sorted(rows,key=lambda x:x["symbol"]):
  raise ValueError("Candidate source records must be sorted")
 if set(discovery.get("known_symbols_present",[])) != (seen & set(verified)):
  raise ValueError("Provider overlap with 7 known records not consistent")
 if set(discovery.get("known_symbols_missing",[])) != (set(verified)-seen):
  raise ValueError("Provider missing known symbols not consistent")
 if discovery.get("all_7_known_present") is not (len(seen&set(verified))==7):
  raise ValueError("Provider known coverage metadata wrong")
 return {
  "schema_version":"sgx-third-party-company-candidates-v99",
  "generated_at_utc":datetime.now(timezone.utc).isoformat(),
  "source_url":discovery["source_url"],
  "source_json_sha256":discovery["source_response_sha256"],
  "source_kind":"THIRD_PARTY_LISTED_COMPANY_API_FREE_TIER",
  "coverage":"PARTIAL_UNVERIFIED",
  "provider_raw_rows":discovery["raw_rows_count"],
  "provider_accepted_candidate_count":len(rows),
  "known_verified_issuer_count":len(verified),
  "known_verified_issuer_overlap":len(set(verified)&seen),
  "known_verified_issuer_missing":sorted(set(verified)-seen),
  "full_sgx_listing_completeness_verified":False,
  "records_not_added_to_verified_financial_feed":True,
  "stock_quote_or_financial_metrics_fetched":False,
  "eligible_for_ranking":False,
  "candidates":rows
 }

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--feed",required=True)
 p.add_argument("--discovery",required=True);p.add_argument("--output",required=True)
 a=p.parse_args()
 feed=json.loads(Path(a.feed).read_text(encoding="utf-8"))
 evidence=json.loads(Path(a.discovery).read_text(encoding="utf-8"))
 if not evidence.get("record"):raise SystemExit("No successful provider candidate source")
 out=publish(feed,evidence["record"])
 dest=Path(a.output);dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("Published",len(out["candidates"]),"SECONDARY candidate SGX tickers, not a complete exchange universe")

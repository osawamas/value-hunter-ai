"""v137: strict evidence matrix for first eligible SGX industrial issuer.

READ-ONLY assessment. Current reference prices are Yahoo-derived and may not
be used as authenticated exchange execution quotes. The original feed remains
unchanged; no company can become ranked merely through this diagnostic.
"""
import argparse, hashlib, json, re
from datetime import datetime, timezone, date
from pathlib import Path

FOCUS=("G13","S63")
REQUIRED=(
 "fy2025_external_auditor_opinion",
 "parent_equity_independent_reperformance",
 "financial_numerical_independent_reperformance",
 "authenticated_sgx_execution_quote",
 "authenticated_quote_exact_trade_time",
 "latest_treasury_adjusted_shares",
 "quote_share_effective_date_compatible",
 "current_earnings_period_applicable"
)
def iso_date(value):
 if not isinstance(value,str): return None
 try:return date.fromisoformat(value)
 except ValueError:return None

def assess(feed,assurance,primary_g13,primary_s63,s63_price):
 if (not isinstance(feed,dict) or feed.get("schema_version")!="value_hunter_web_v29" or
     feed.get("ranking_enabled") is not False or feed.get("ranking_eligible_count")!=0 or
     len(feed.get("records",[]))!=7):
  raise ValueError("Unexpected financial feed rank state")
 if (not isinstance(assurance,dict) or assurance.get("schema_version")!="sgx-fy2025-audit-assurance-v132" or
     assurance.get("linked_published_feed_updated_at_utc")!=feed.get("updated_at_utc") or
     assurance.get("external_auditor_fy2025_opinion_confirmed_count")!=2 or
     assurance.get("numeric_recalculation_completed_count")!=0 or
     assurance.get("ranking_eligible_count")!=0 or
     assurance.get("financial_feed_modified") is not False):
  raise ValueError("Stale or unsupported auditor assurance")
 if (not isinstance(primary_g13,dict) or primary_g13.get("schema_version")!="sgx-g13-h1-direct-primary-share-confirmation-v127" or
     primary_g13.get("published_june30_count_original_primary_supported") is not True or
     primary_g13.get("shares_after_june30_unchanged_verified") is not False or
     primary_g13.get("ranking_eligible") is not False):
  raise ValueError("G13 dated primary shares not verified")
 if (not isinstance(primary_s63,dict) or primary_s63.get("schema_version")!="sgx-share-snapshot-difference-v110" or
     primary_s63.get("symbol")!="S63" or
     primary_s63.get("new_sgx_primary_snapshot_date")!="2026-11-13" or
     primary_s63.get("current_shares_verified") is not False or
     primary_s63.get("price_or_per_pbr_recomputed") is not False or
     primary_s63.get("ranking_eligible") is not False):
  raise ValueError("S63 dated primary shares not verified")
 if (not isinstance(s63_price,dict) or s63_price.get("schema_version")!="sgx-s63-historical-close-second-website-v129" or
     s63_price.get("primary_exchange_execution_quote_verified") is not False or
     s63_price.get("upstream_market_data_provider_independence_verified") is not False or
     s63_price.get("ranking_eligible") is not False):
  raise ValueError("S63 price provenance unacceptable")
 audited={x.get("symbol"):x for x in assurance.get("records",[])}
 if set(audited)!=set(FOCUS) or len(assurance.get("records",[]))!=2:
  raise ValueError("External opinions not uniquely linked to both companies")
 results=[]
 for symbol in FOCUS:
  rows=[x for x in feed["records"] if x.get("symbol")==symbol]
  if len(rows)!=1:raise ValueError("Duplicated or missing issuer")
  r=rows[0];a=audited[symbol]
  if (r.get("ranking_eligible") is not False or r.get("ranking_score") is not None or
      r.get("fiscal_year")!=2025 or
      a.get("fiscal_year")!=2025 or
      a.get("annual_report_primary_sha256")!=r.get("financial_pdf_sha256") or
      a.get("annual_report_primary_source_url")!=r.get("financial_source_url") or
      a.get("external_auditor_opinion_is_not_live_market_verification") is True):
   raise ValueError("FY2025 source binding inconsistent")
  opinion=(a.get("independent_external_audit_opinion_observed") is True and
           a.get("auditor")=="PricewaterhouseCoopers LLP" and
           a.get("auditor_scope_end")=="2025-12-31")
  if (a.get("reperformed_independent_financial_calculations") is not False or
      a.get("parent_equity_independently_reperformed") is not False or
      a.get("current_shares_and_quote_independently_verified") is not False or
      a.get("eligible_for_ranking") is not False):
   raise ValueError("Source claims numerical or market promotion")
  expected_shares=12063642274 if symbol=="G13" else 3115847115
  original_share_date="2026-06-30" if symbol=="G13" else "2026-11-13"
  historical_share_count=primary_g13["issued_ex_treasury_at_june30"] if symbol=="G13" else primary_s63["new_sgx_primary_issued_ex_treasury"]
  if historical_share_count!=expected_shares:
   raise ValueError("Official share evidence count differs")
  checks={
   "fy2025_external_auditor_opinion":opinion,
   "parent_equity_independent_reperformance":False,
   "financial_numerical_independent_reperformance":False,
   "authenticated_sgx_execution_quote":False,
   "authenticated_quote_exact_trade_time":False,
   "latest_treasury_adjusted_shares":False,
   "quote_share_effective_date_compatible":False,
   "current_earnings_period_applicable":False
  }
  if tuple(checks)!=REQUIRED:raise ValueError("Missing required check")
  if not opinion:raise ValueError("Auditor source originally validated but opinion unexpectedly absent")
  results.append({
   "symbol":symbol,"issuer":r.get("issuer"),"fiscal_year":2025,
   "as_of_snapshot_for_shares":original_share_date,
   "verified_historical_shares_ex_treasury":historical_share_count,
   "historical_reference_quote_provider":r.get("quote_source_type"),
   "evidence_requirements":checks,
   "unmet_requirements":[k for k in REQUIRED if not checks[k]],
   "audit_opinion_fy2025_does_not_audit_2026_interim":True,
   "separate_provider_quotes_are_not_primary_execution_tape":True,
   "historical_share_snapshot_is_not_current":True,
   "eligible_for_ranking":False,
   "promoted_market_cap_per_pbr":False
  })
 return {
   "schema_version":"sgx-first-issuer-evidence-gate-v137",
   "feed_updated_at_utc":feed.get("updated_at_utc"),
   "checked_issuers":len(results),"required_evidence_fields":list(REQUIRED),
   "eligible_count":0,"ranking_activation_permitted":False,
   "no_financial_feed_changes":True,
   "records":results
 }

def main():
 p=argparse.ArgumentParser()
 for flag in ("feed","assurance","g13","s63","s63-price","output"):
  p.add_argument("--"+flag,required=True)
 a=p.parse_args()
 f=Path(a.feed);old=hashlib.sha256(f.read_bytes()).hexdigest()
 data=assess(*[json.loads(Path(q).read_text()) for q in
  (a.feed,a.assurance,a.g13,a.s63,a.s63_price)])
 if hashlib.sha256(f.read_bytes()).hexdigest()!=old:
  raise ValueError("The published feed was changed")
 output=Path(a.output);output.parent.mkdir(parents=True,exist_ok=True)
 output.write_text(json.dumps(data,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("v137 checked",data["checked_issuers"],"eligible",data["eligible_count"])

if __name__=="__main__":main()

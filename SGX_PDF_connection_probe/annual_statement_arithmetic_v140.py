"""v140 issuer FY2025 statement arithmetic, not independent third-party validation."""
import argparse,hashlib,json
from pathlib import Path
from decimal import Decimal

SYMBOLS=("G13","S63")
def calculate(feed,assurance):
 if not isinstance(feed,dict) or feed.get("schema_version")!="value_hunter_web_v29" or feed.get("ranking_eligible_count")!=0 or feed.get("ranking_enabled") is not False:
  raise ValueError("Unsafe feed")
 if (not isinstance(assurance,dict) or assurance.get("schema_version")!="sgx-fy2025-audit-assurance-v132" or
     assurance.get("linked_published_feed_updated_at_utc")!=feed.get("updated_at_utc") or
     assurance.get("external_auditor_fy2025_opinion_confirmed_count")!=2 or
     assurance.get("numeric_recalculation_completed_count")!=0):
  raise ValueError("Stale auditor evidence")
 rows=[]
 for symbol in SYMBOLS:
  candidates=[x for x in feed.get("records",[]) if x.get("symbol")==symbol]
  attest=[x for x in assurance.get("records",[]) if x.get("symbol")==symbol]
  if len(candidates)!=1 or len(attest)!=1:raise ValueError("Missing issuer")
  x=candidates[0];a=attest[0]
  if (x.get("fiscal_year")!=2025 or x.get("ranking_eligible") is not False or
      x.get("financial_pdf_sha256")!=a.get("annual_report_primary_sha256") or
      x.get("financial_source_url")!=a.get("annual_report_primary_source_url") or
      a.get("independent_external_audit_opinion_observed") is not True or
      a.get("reperformed_independent_financial_calculations") is not False or
      a.get("parent_equity_independently_reperformed") is not False):
   raise ValueError("Original annual audit binding invalid")
  names=("assets_sgd_thousands","liabilities_sgd_thousands","equity_sgd_thousands",
         "parent_equity_sgd_thousands","attributable_profit_sgd_thousands")
  values=[]
  for n in names:
   v=x.get(n)
   if type(v) is not int:raise ValueError("Not a signed integer: "+n)
   values.append(v)
  assets,liabilities,equity,parent,profit=values
  if min(assets,liabilities,equity,parent)<=0 or parent>equity or profit<=0:
   raise ValueError("Invalid accounting scope/units")
  nci=equity-parent
  if assets-liabilities!=equity or x.get("balance_difference_sgd_thousands")!=0:
   raise ValueError("Group balance equation failed")
  if equity!=parent+nci:raise ValueError("Parent plus NCI sum failed")
  if x.get("parent_equity_status") not in (
   "GROUP_ORDINARY_SHAREHOLDER_EQUITY_SAME_ISSUER_PDF",
   "EXTRACTED_AUDITED_ISSUER_PDF_ARITHMETIC_MATCHED"):
   raise ValueError("Parent equity source insufficient")
  rows.append({
   "symbol":symbol,"statement_year":2025,"unit":"SGD_thousands",
   "assets":assets,"liabilities":liabilities,"group_equity":equity,
   "parent_attributable_equity":parent,
   "calculated_noncontrolling_interest":nci,
   "assets_minus_liabilities_minus_group_equity":assets-liabilities-equity,
   "group_equity_minus_parent_minus_nci":equity-parent-nci,
   "same_issuer_audited_statement_arithmetic_passed":True,
   "independent_external_auditor_opinion_observed":True,
   "independent_third_party_reperformance_completed":False,
   "independent_parent_equity_source_completed":False,
   "valid_current_quote_and_shares_proven":False,
   "official_2026_earnings_audited":False,
   "market_cap_per_pbr_promoted":False,"ranking_eligible":False,
   "original_annual_report_sha256":x["financial_pdf_sha256"]})
 return {"schema_version":"sgx-annual-statement-arithmetic-v140",
  "feed_updated_at_utc":feed["updated_at_utc"],
  "checked_issuers":2,"arithmetically_reconciled_count":2,
  "independent_numerical_verification_count":0,
  "eligible_count":0,"financial_feed_modified":False,"records":rows}

def main():
 p=argparse.ArgumentParser()
 for key in ("feed","assurance","output"):p.add_argument("--"+key,required=True)
 args=p.parse_args()
 f=Path(args.feed);before=hashlib.sha256(f.read_bytes()).hexdigest()
 result=calculate(json.loads(f.read_text()),json.loads(Path(args.assurance).read_text()))
 if hashlib.sha256(f.read_bytes()).hexdigest()!=before:raise ValueError("Feed mutated")
 o=Path(args.output);o.parent.mkdir(parents=True,exist_ok=True)
 o.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("v140 reconciled",result["checked_issuers"],"independent",result["independent_numerical_verification_count"])
if __name__=="__main__":main()
